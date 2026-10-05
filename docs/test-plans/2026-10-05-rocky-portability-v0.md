# Portability v0 — test plan

**Date:** 2026-10-05  
**Branch:** `feat/rocky-portability-v0`  
**Base:** Voice Input V0 / PR #21  
**Status:** Draft

## Automated acceptance

- asset manifest shape/version validation;
- duplicate asset-id rejection;
- local file SHA-256 verification;
- checksum mismatch surfaced;
- missing required file surfaced;
- runtime-managed assets marked as references rather than falsely verified;
- user backup includes only settings/personality/memory;
- nearby model weights are not included;
- nearby virtual environments are not included;
- backup manifest size and SHA-256 verification;
- tampered backup rejected;
- path traversal/extra archive contents rejected;
- portable Pi and PC examples validate;
- examples use EXP-003 / vocal-v1 / multiplier 2;
- all existing Assistant, Study, Memory, Voice, UI, Brain, Chordic and Arduino tests remain required.

## Manual acceptance — NOT RUN

- Windows launcher option 11 on the user's PC;
- inspect exported ZIP contents;
- move ZIP to another Windows PC;
- manually restore settings/personality/memory from the verified archive;
- configure real whisper.cpp executable/model checksums in assets.json;
- verify a real external asset manifest;
- reinstall Rocky from a fresh clone/bootstrap;
- uninstall/update experience.

No test claims that external model weights are small or bundled.
