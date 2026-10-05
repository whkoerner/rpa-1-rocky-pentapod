# Rocky local web UI v0

**Date:** 2026-10-05  
**Status:** Draft implementation on `feat/rocky-local-web-ui-v0`, stacked on Assistant V2 PR #17.

## Boundary

The browser UI is an adapter around the existing `ConversationController`. It does not create a second assistant pipeline and it does not receive raw physical-hardware authority.

```text
browser on 127.0.0.1
  -> LocalWebUI
  -> ConversationController
  -> validated AssistantResponse
  -> spoken_text only
  -> BrainController
  -> SafetyValidator
  -> TaskController / EXP-003
  -> DesktopHardware

detail_text -> browser display only
```

## Local security model

- server binds only to `127.0.0.1`;
- Host must be `127.0.0.1` or `localhost`;
- every API endpoint requires a random per-launch token embedded only in the served local page;
- CORS is not enabled and OPTIONS requests are rejected;
- request bodies must be JSON and are bounded to 8192 bytes;
- response headers use no-store, nosniff, frame denial, and a restrictive CSP;
- no external JavaScript, stylesheet, image, or CDN is loaded;
- the UI has no shell, arbitrary filesystem browser, network research tool, raw motor endpoint, E-stop bypass, or physical tuning surface.

The page itself and favicon can be fetched without the token so the browser can start. Status, polling, chat, settings, actions, import, and export all require the launch token.

## Exposed controls

The UI exposes only bounded user-facing assistant/audio controls:

- chat;
- separate spoken and detail response display;
- EXP-003 representation, semantic coverage, and fallback telemetry;
- Chordic and English timing/status;
- assistant mode: normal, study, coding, project;
- Chordic renderer, speed, and volume;
- local English voice name and bounded rate/pitch/volume offsets;
- persistent translation toggle;
- replay, mute/unmute, cancel, STOP, reset, clear;
- save profile;
- reset to recommended defaults;
- export/import tuning settings.

Physical or safety-critical parameters are intentionally absent.

## Launch

`python -m rocky web` starts the local UI. The Windows launcher exposes menu option 9 and first performs the same local-model availability check used by terminal mode.

Default address: `http://127.0.0.1:8765/`. `--ui-port` can select another local port and `--no-browser` suppresses automatic browser opening.

## Persistence

Save profile writes the selected user Rocky settings file atomically using a temporary file and `os.replace`. Existing configuration validation remains authoritative at the next normal startup. Export/import uses a small schema-versioned tuning document rather than exposing arbitrary application configuration.

## Manual acceptance still required

CI proves local binding, token checks, bounded settings, CORS refusal, import/export behavior, package-data inclusion, launcher tests, and the unchanged Brain/Safety suites. CI does **not** prove that the browser is pleasant to use, that a selected voice sounds natural, or that active translation sounds correct through the user's speakers.
