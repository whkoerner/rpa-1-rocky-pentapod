"""Explicit, audited loopback gateway for optional connected assistant tools.

Rocky never stores provider OAuth/API credentials. A separately authorized local
gateway owns those credentials. Rocky can only call a fixed read-only capability
allowlist over 127.0.0.1 when connected mode is explicitly enabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import http.client
import json
from pathlib import Path
import secrets
import threading


CAPABILITY_BY_TOOL = {
    "connected_web_search": "web_search",
    "connected_drive_search": "google_drive_search",
    "connected_drive_read": "google_drive_read",
    "connected_calendar_read": "calendar_read",
}
MAX_REQUEST_BYTES = 8192
MAX_RESPONSE_BYTES = 32768


class ConnectedGatewayError(ValueError):
    pass


def _strict_json(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ConnectedGatewayError("duplicate connected JSON key")
            result[key] = value
        return result

    def reject_constant(value):
        raise ConnectedGatewayError("non-finite connected JSON value")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject_constant)


def _validate_json_value(value, *, depth=0):
    if depth > 8:
        raise ConnectedGatewayError("connected result nesting is too deep")
    if value is None or type(value) in (bool, int, float, str):
        if type(value) is str and len(value.encode("utf-8")) > 16384:
            raise ConnectedGatewayError("connected result string is too large")
        return
    if type(value) is list:
        if len(value) > 256:
            raise ConnectedGatewayError("connected result list is too large")
        for item in value:
            _validate_json_value(item, depth=depth + 1)
        return
    if type(value) is dict:
        if len(value) > 128:
            raise ConnectedGatewayError("connected result object is too large")
        for key, item in value.items():
            if type(key) is not str or not key or len(key) > 128:
                raise ConnectedGatewayError("invalid connected result key")
            _validate_json_value(item, depth=depth + 1)
        return
    raise ConnectedGatewayError("connected result contains unsupported JSON type")


@dataclass
class ConnectedGatewayClient:
    port: int
    token_path: Path
    audit_path: Path
    timeout_seconds: float = 15.0
    enabled: bool = False

    def __post_init__(self):
        self.token_path = Path(self.token_path).expanduser()
        self.audit_path = Path(self.audit_path).expanduser()
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ConnectedGatewayError("connected gateway port must be 1-65535")
        if (
            type(self.timeout_seconds) not in (int, float)
            or not 1 <= float(self.timeout_seconds) <= 60
        ):
            raise ConnectedGatewayError("connected timeout must be 1-60 seconds")
        self.timeout_seconds = float(self.timeout_seconds)
        self._audit_lock = threading.RLock()

    def set_enabled(self, enabled: bool):
        if type(enabled) is not bool:
            raise ConnectedGatewayError("connected mode must be boolean")
        if enabled:
            self.check_available()
        self.enabled = enabled

    def _token(self) -> str:
        if not str(self.token_path) or not self.token_path.is_file():
            raise ConnectedGatewayError(
                "connected gateway token file is not provisioned"
            )
        if self.token_path.is_symlink():
            raise ConnectedGatewayError("connected gateway token file may not be a symlink")
        token = self.token_path.read_text(encoding="utf-8").strip()
        if (
            not 32 <= len(token) <= 256
            or not token.isascii()
            or any(char.isspace() for char in token)
        ):
            raise ConnectedGatewayError("connected gateway token is invalid")
        return token

    def check_available(self):
        self._token()
        return True

    def tool_names(self) -> tuple[str, ...]:
        return tuple(sorted(CAPABILITY_BY_TOOL)) if self.enabled else ()

    def _audit(self, row: dict):
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        record = json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        if len(record.encode("utf-8")) > 4096:
            raise ConnectedGatewayError("connected audit record exceeds safe size")
        with self._audit_lock:
            with self.audit_path.open("a", encoding="utf-8") as handle:
                handle.write(record)

    def execute(self, tool_name: str, arguments: object) -> str:
        if not self.enabled:
            raise ConnectedGatewayError("connected mode is OFFLINE")
        capability = CAPABILITY_BY_TOOL.get(tool_name)
        if capability is None:
            raise ConnectedGatewayError("connected capability is not allowlisted")
        if type(arguments) is not dict or len(arguments) > 16:
            raise ConnectedGatewayError("connected arguments must be a small JSON object")
        _validate_json_value(arguments)
        request_id = secrets.token_hex(12)
        payload = {
            "schema_version": 1,
            "request_id": request_id,
            "capability": capability,
            "arguments": arguments,
        }
        raw_request = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if len(raw_request) > MAX_REQUEST_BYTES:
            raise ConnectedGatewayError("connected request exceeds safe size")
        digest = hashlib.sha256(raw_request).hexdigest()
        audit = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "capability": capability,
            "argument_keys": sorted(arguments),
            "request_sha256": digest,
            "ok": False,
            "source": "",
            "error_code": "",
        }
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.port, timeout=self.timeout_seconds
        )
        try:
            connection.request(
                "POST",
                "/v1/rocky-tool",
                body=raw_request,
                headers={
                    "Content-Type": "application/json",
                    "X-Rocky-Gateway-Token": self._token(),
                },
            )
            response = connection.getresponse()
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ConnectedGatewayError("connected response exceeds safe size")
            if response.status != 200:
                audit["error_code"] = f"HTTP_{response.status}"
                raise ConnectedGatewayError(
                    f"connected gateway HTTP {response.status}"
                )
            try:
                reply = _strict_json(raw.decode("utf-8"))
            except UnicodeDecodeError as exc:
                raise ConnectedGatewayError(
                    "connected gateway returned invalid UTF-8"
                ) from exc
            if type(reply) is not dict or set(reply) != {
                "schema_version",
                "request_id",
                "ok",
                "source",
                "result",
                "error",
            }:
                raise ConnectedGatewayError("connected gateway response fields are invalid")
            if reply["schema_version"] != 1 or reply["request_id"] != request_id:
                raise ConnectedGatewayError("connected gateway response correlation failed")
            if type(reply["ok"]) is not bool:
                raise ConnectedGatewayError("connected gateway ok flag is invalid")
            source = reply["source"]
            if (
                type(source) is not str
                or not source
                or len(source) > 120
                or any(ord(char) < 32 for char in source)
            ):
                raise ConnectedGatewayError("connected gateway source is invalid")
            audit["source"] = source
            if not reply["ok"]:
                error = reply["error"]
                if (
                    type(error) is not str
                    or not error
                    or len(error) > 500
                    or any(ord(char) < 32 for char in error)
                ):
                    raise ConnectedGatewayError("connected gateway error is invalid")
                audit["error_code"] = "GATEWAY_REPORTED_ERROR"
                raise ConnectedGatewayError("connected gateway: " + error)
            if reply["error"] not in ("", None):
                raise ConnectedGatewayError("successful connected reply must not contain error")
            _validate_json_value(reply["result"])
            rendered = json.dumps(
                {
                    "provenance": "connected_tool_result",
                    "source": source,
                    "capability": capability,
                    "result": reply["result"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            if len(rendered.encode("utf-8")) > 24576:
                raise ConnectedGatewayError("connected result exceeds assistant bound")
            audit["ok"] = True
            return rendered
        except (OSError, http.client.HTTPException) as exc:
            audit["error_code"] = type(exc).__name__
            raise ConnectedGatewayError(
                "connected loopback gateway is unavailable"
            ) from exc
        finally:
            connection.close()
            try:
                self._audit(audit)
            except OSError:
                pass
