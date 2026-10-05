"""Connected mode V0: explicit loopback-only, read-only, audited tools."""

import http.server
import json
from pathlib import Path
import pickle
import tempfile
import threading
import unittest

from rocky.assistant_contracts import ToolCall
from rocky.connected import CAPABILITY_BY_TOOL, ConnectedGatewayClient, ConnectedGatewayError
from rocky.providers import LocalAIProvider
from rocky.tools import AssistantToolRegistry


class GatewayHandler(http.server.BaseHTTPRequestHandler):
    token = ""
    requests = []

    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        request = json.loads(raw)
        type(self).requests.append(
            {
                "path": self.path,
                "token": self.headers.get("X-Rocky-Gateway-Token"),
                "request": request,
            }
        )
        body = json.dumps(
            {
                "schema_version": 1,
                "request_id": request["request_id"],
                "ok": True,
                "source": "fixture-gateway",
                "result": {
                    "items": [{"title": "Result", "url": "https://example.invalid/item"}]
                },
                "error": "",
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class ConnectedModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.token_path = self.root / "gateway.token"
        self.token_path.write_text("t" * 48, encoding="utf-8")
        self.audit_path = self.root / "audit.jsonl"
        GatewayHandler.requests = []
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), GatewayHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def client(self):
        return ConnectedGatewayClient(
            self.server.server_port,
            self.token_path,
            self.audit_path,
            timeout_seconds=5,
        )

    def test_offline_registry_does_not_expose_connected_tools_to_model_schema(self):
        client = self.client()
        registry = AssistantToolRegistry(connected_client=client)
        provider = LocalAIProvider(tool_registry=registry)
        names = provider._schema()["properties"]["tool_calls"]["items"]["properties"]["name"]["enum"]
        self.assertNotIn("connected_web_search", names)
        self.assertFalse(any(name.startswith("connected_") for name in names))
        self.assertEqual(client.tool_names(), ())

    def test_online_registry_exposes_only_fixed_read_only_capabilities(self):
        client = self.client()
        client.set_enabled(True)
        registry = AssistantToolRegistry(connected_client=client)
        names = set(registry.names())
        self.assertTrue(set(CAPABILITY_BY_TOOL).issubset(names))
        self.assertNotIn("connected_docs_append", names)
        self.assertNotIn("connected_shell", names)
        self.assertNotIn("raw_motor", names)

    def test_connected_tool_calls_loopback_gateway_and_returns_provenance(self):
        client = self.client()
        client.set_enabled(True)
        registry = AssistantToolRegistry(connected_client=client)
        result = registry.execute(
            ToolCall(
                "c1",
                "connected_web_search",
                {"query": "current orbital launch schedule", "limit": 3},
            )
        )
        self.assertTrue(result.ok, result.error)
        payload = json.loads(result.output)
        self.assertEqual(payload["provenance"], "connected_tool_result")
        self.assertEqual(payload["source"], "fixture-gateway")
        self.assertEqual(payload["capability"], "web_search")
        self.assertEqual(len(GatewayHandler.requests), 1)
        observed = GatewayHandler.requests[0]
        self.assertEqual(observed["path"], "/v1/rocky-tool")
        self.assertEqual(observed["token"], "t" * 48)
        self.assertEqual(observed["request"]["capability"], "web_search")

    def test_offline_execution_fails_closed_before_network(self):
        client = self.client()
        registry = AssistantToolRegistry(connected_client=client)
        result = registry.execute(
            ToolCall("c1", "connected_web_search", {"query": "anything"})
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "TOOL_NOT_ALLOWED")
        self.assertEqual(GatewayHandler.requests, [])

    def test_audit_minimizes_content_and_records_hash(self):
        client = self.client()
        client.set_enabled(True)
        secretish_query = "private class project details"
        client.execute("connected_drive_search", {"query": secretish_query})
        row = json.loads(self.audit_path.read_text(encoding="utf-8").splitlines()[-1])
        self.assertTrue(row["ok"])
        self.assertEqual(row["capability"], "google_drive_search")
        self.assertEqual(row["argument_keys"], ["query"])
        self.assertNotIn(secretish_query, self.audit_path.read_text(encoding="utf-8"))
        self.assertEqual(len(row["request_sha256"]), 64)

    def test_bad_or_missing_token_blocks_online_mode(self):
        self.token_path.write_text("short", encoding="utf-8")
        client = self.client()
        with self.assertRaises(ConnectedGatewayError):
            client.set_enabled(True)
        self.assertFalse(client.enabled)

    def test_client_is_spawn_pickle_safe(self):
        client = self.client()
        restored = pickle.loads(pickle.dumps(client))
        self.assertEqual(restored.port, client.port)
        self.assertFalse(restored.enabled)


if __name__ == "__main__":
    unittest.main()
