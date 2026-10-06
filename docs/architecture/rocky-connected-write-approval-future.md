# Future connected write approval boundary

**Date:** 2026-10-05  
**Status:** Design only — NOT IMPLEMENTED

Read-only Connected Mode V0 remains the production boundary. Real authorized read-provider acceptance is still required before any write capability is enabled.

## Non-negotiable rule

The model may **propose** an external write. It may never authorize, confirm, or execute one by itself.

```text
local model
  -> validated write proposal (data only)
  -> trusted Rocky application
  -> human preview
  -> explicit CONFIRM button
  -> one-time bounded approval
  -> separately authorized loopback gateway
  -> Google provider write
```

Write capabilities must not be placed in the model tool schema. The model only emits a proposal that the trusted application may display.

## Proposed approval object

A future trusted application approval should bind at least:

- random approval ID;
- creation/expiry time;
- exact capability;
- target provider/object identity;
- operation type;
- payload SHA-256;
- source/provenance summary;
- originating request/turn ID;
- one-time unused state.

Approval must expire quickly, be single-use, and fail if target, operation, or payload changes after preview.

## UI confirmation

A future preview must show human-readable:

- provider;
- target document/calendar;
- operation;
- exact content preview or bounded diff;
- source/provenance;
- whether content came from a lecture transcript, user text, or model-generated notes.

Buttons:

- **CONFIRM** — authorizes exactly the displayed proposal once;
- **CANCEL** — destroys the proposal.

Typing a chat message such as "yes" must not count as confirmation.

## Candidate future writes

Only after read-only provider acceptance:

- append approved lecture notes to a selected Google Doc;
- create an approved Google Doc;
- create an approved calendar event/reminder;
- save an approved file to Drive.

No arbitrary URL, arbitrary HTTP method, arbitrary file path, shell command, credential access, or physical command is introduced.

## Gateway boundary

The separately authorized gateway continues to own OAuth/API credentials. The Rocky/model process must not contain Google refresh tokens.

A future gateway write request should require:

- existing loopback token authentication;
- explicit write capability allowlist;
- approval ID;
- request/payload hash matching the approval;
- bounded request size;
- audit record;
- fail-closed audit persistence.

The gateway must never accept "user confirmed" as a free-form model-supplied string.

## Audit

Record metadata, not secret contents:

- UTC timestamp;
- request/approval IDs;
- capability;
- target identifier suitable for audit;
- argument keys;
- request/payload hashes;
- success/failure;
- provider source;
- error code.

## Current blockers

Write implementation remains blocked on:

1. real authorized read-only gateway/provider acceptance on the user's machine;
2. confirmation UI acceptance;
3. provider-specific target/permission behavior;
4. audit review.

Until those are complete, Connected Mode remains read-only.
