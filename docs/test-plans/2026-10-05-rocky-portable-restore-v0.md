# Rocky portable restore staging V0 — test evidence

**Date:** 2026-10-05  
**Branch:** `feat/rocky-portable-restore-v0`  
**Base:** Voice Input provisioning V0

## Safety model

Restore is intentionally a staging operation only. It cannot overwrite an existing destination and does not automatically replace the active Rocky profile.

The source archive must pass the existing strict backup verifier before extraction. Archive traversal, duplicate/unlisted members, size mismatch, and SHA mismatch therefore fail before restore.

## Automated scope

Tests require:

- explicit restore confirmation;
- successful staging of settings, personality, and memory;
- manifest preserved for inspection;
- staged bytes equal original exported bytes;
- live source/profile files unchanged;
- existing destination rejected;
- all existing backup tamper/path tests remain required;
- all Rocky/Browser/Windows/Linux/Arduino regressions remain required.

## Manual NOT RUN

- launcher option 17 with a real user backup;
- transfer to another Windows machine;
- inspection/import of real memory/settings;
- migration from a future older schema;
- uninstall/reinstall recovery workflow.

No test claims that staging a file makes it semantically compatible with a future Rocky schema.
