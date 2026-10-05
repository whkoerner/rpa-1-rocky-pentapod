# Rocky Connected Mode V0

**Date:** 2026-10-05  
**Status:** Draft implementation on `feat/rocky-connected-mode-v0`, stacked on Portability V0 PR #22.

## Goal

Connected Mode V0 adds a narrow, optional path for current/public or user-account information without turning Rocky's local model into an unrestricted network client.

OFFLINE remains the default.

```text
local model
  -> validated Assistant tool request
  -> AssistantToolRegistry
  -> RockySafetyConstitution (software domain)
  -> ConnectedGatewayClient
  -> 127.0.0.1 only
  -> separately authorized local gateway
  -> external provider / Google / search service
```

The separately authorized gateway owns OAuth/API credentials. Rocky does not store those credentials, receive them in model context, or commit them to Git.

## Available V0 capabilities

Model-visible connected tools exist only when ONLINE:

- `connected_web_search` -> `web_search`
- `connected_drive_search` -> `google_drive_search`
- `connected_drive_read` -> `google_drive_read`
- `connected_calendar_read` -> `calendar_read`

These are read-only. There is deliberately no arbitrary URL fetch, shell, filesystem bridge, Docs write, email send, calendar write, OAuth management, raw hardware action, or physical-control capability.

Write-capable connected actions require a later explicit human-confirmation contract.

## OFFLINE/ONLINE authority

When OFFLINE, connected tool names are absent from the model JSON schema. This is stronger than allowing a call and rejecting it later.

ONLINE can be enabled only if the configured gateway token file exists and passes validation. Turning the mode off removes the connected names from subsequent model calls.

Terminal command:

`/connected status|on|off`

The browser UI exposes the same explicit toggle.

## Loopback gateway protocol

Rocky always connects to numeric loopback `127.0.0.1:<configured port>` using `http.client`. It does not resolve arbitrary hosts, honor proxy environment variables, follow redirects, or accept a URL from the model.

Request:

```json
{
  "schema_version": 1,
  "request_id": "random correlation id",
  "capability": "google_drive_search",
  "arguments": {"query": "lecture notes"}
}
```

HTTP path: `POST /v1/rocky-tool`

Authentication header:

`X-Rocky-Gateway-Token: <provisioned local token>`

The token file is never committed and may not be a symlink.

Expected response:

```json
{
  "schema_version": 1,
  "request_id": "same correlation id",
  "ok": true,
  "source": "gateway/provider identifier",
  "result": {},
  "error": ""
}
```

Responses are bounded, strictly correlated, JSON-only, and returned to the assistant as explicit `connected_tool_result` provenance.

## Auditing

Each attempted connected request records:

- UTC timestamp;
- random request ID;
- capability;
- argument **keys**, not argument values;
- SHA-256 of the exact bounded request;
- success/failure;
- source;
- error code.

Raw query/document contents are intentionally omitted from the audit log. If audit persistence fails, the connected tool fails closed rather than silently returning an unaudited result.

## Safety separation

Connected tools are software tools. They do not create sensor evidence or physical authority.

A Drive result is not a sensor reading. A web result is not proof of charging state. Calendar data cannot clear an E-stop. The hard-coded constitution and existing Brain/Safety/Hardware boundaries remain authoritative.

## Provisioning

Default settings:

- `connected_enabled = false`
- `connected_gateway_port = 8787`
- `connected_gateway_token_path = ""`
- `connected_audit_path = "~/.rpa1/connected/audit.jsonl"`
- `connected_timeout_seconds = 15`

A real gateway process and provider credentials are not bundled in this milestone. They must be explicitly provisioned and authorized outside Rocky.

## NOT RUN

- real Google OAuth flow;
- real Drive/Calendar data;
- real public web-search gateway;
- revocation against a live provider;
- account-scoping UX;
- write confirmation;
- Google Docs append;
- internet-loss/reconnect acceptance on the user's Windows machine.

No claim of live Google/search functionality is made until a gateway is provisioned and manually accepted.
