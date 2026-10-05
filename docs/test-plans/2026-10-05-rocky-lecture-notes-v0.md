# Rocky Lecture Notes V0 — test evidence

**Date:** 2026-10-05  
**Branch:** `feat/rocky-lecture-notes-v0`  
**Base:** `feat/rocky-lecture-mode-v0`  
**PR:** #25 (draft)

## Automated scope

Tests verify:

- valid transcript -> section notes + overall review + manifest;
- exact source transcript SHA-256 is recorded;
- manifest says transcript-only grounding and connected tools disabled;
- transcript prompt-injection text appears only after the explicit untrusted-source warning;
- section prompt instructs the model not to obey embedded transcript commands;
- final synthesis treats section notes as untrusted source data;
- study-mode context is used;
- persistent memory is not injected into the dedicated notes context;
- invalid chunk sequence is rejected;
- empty transcript cannot produce notes;
- a large transcript is sectioned in timestamp order instead of being sent as one context.

## CI evidence

Actions run **#135** passed:

- Windows Python 3.12;
- Windows Python 3.13;
- Ubuntu Python 3.12;
- Ubuntu Python 3.13;
- Arduino Uno.

## Manual NOT RUN

- actual notes from a real 2 h 40 min lecture;
- human factual/faithfulness review;
- real qwen3:8b runtime/latency for a full lecture;
- real flashcard usefulness;
- real formula preservation from imperfect STT;
- Google Docs export;
- comparison against instructor-provided lecture notes/slides.
