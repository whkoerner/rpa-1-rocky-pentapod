# Decision record: Rocky desktop V1.1

Status: implemented, awaiting Windows listening and real-model acceptance. Date: 2026-10-03 (Los Angeles).

Requirement: the owner's next-usable-version request: double-click launch, one editable personality, 3× listening timing, repeatable small vocabulary, translation/learning controls, and portable deployment preparation. This record is the requirement reference for the PR. The available GitHub connector has no issue-creation operation; the PR carries the requirement rather than inventing an issue number.

## Inspected baseline and authority

PR #8 was **merged**, not assumed merged: merge `4cc02cbb8e8805adad98dfea64eaedac326aea04`, original PR head `14d63ef9b9d10e9645f927c5205fff70ec926aea`. `main` still pointed at that merge. `feat/rocky-conversation-v1` had advanced to `2dd7193022bc95c0afae9d8919639c5ffb751e15` with Windows test evidence. The upgrade branch merges that history into main without rewriting either branch or the published records. Existing tracked generated package metadata comes along unchanged; cleaning historical `.venv`/egg-info is outside this upgrade.

Inspected README, packaging, CONTRIBUTING/PR checklist, all branches, PR #8 metadata, Brain v0.2 freeze and V1 addendum, controller/validation/safety/hardware contracts, CT1/CSP YAML/wire registry, terminal/provider/worker/audio/personality/settings, existing suites/CI, and subsequent Windows evidence.

[Brain v0.2](brain-v0.2-architecture.md) and its [V1 addendum](conversational-brain-v1.md) remain authoritative. The flow is unchanged:

AIProvider → validated text/request → BrainController → SafetyValidator → TaskController/codec → DesktopHardware → audio player.

No motion, sensing, serial change, GPIO, model tool or physical-control protocol is added. Vocabulary such as `ACTION.help` remains speech, not permission. The simulator still lacks TEXT_COMMUNICATION. Replays, including individual dictionary words, enter the same brain/safety path.

## Decisions and alternatives

| Decision | Why | Alternative considered / review trigger |
|---|---|---|
| Root `.bat` starts a built-in PowerShell menu | Works before Python setup, supports quoted paths, per-user desktop shortcut, readable failures | A GUI would add dependencies. Revisit after Windows usability checks. |
| Reuse valid `.venv-rocky` or `.venv`; repair creates a fresh suffixed environment if needed | Never delete an existing environment; never rely on terminal activation | Copying the tracked Windows venv to Linux is invalid. Recreate on each platform. |
| Keep `rocky.json` for runtime settings; reference one JSON personality | Clear separation of deterministic settings from model preferences | A second merged text/JSON persona would conflict. Legacy `--personality file.txt` explicitly replaces the JSON persona and remains supported. |
| Default multiplier 3; multiplier 1 remains available | Owner requested at least three times the note/gap duration | Volume and frequency remain separate. A tempo-only claim of natural speech would be misleading. |
| CT2 small lexical overlay, exact fallback; CT1 remains decodable/selectable | Reuse released lexical patterns inside sentences without changing text | Sentence hashes are unlearnable; a full grammar/vocabulary redesign is unnecessary. See [CT2 reference](../../language/specification/CT2_LEARNING_V1.md). |
| Cancellable WAV rendering in one background worker | Slow fallback must not block operator input during synthesis | Synchronous rendering blocked commands. Streaming PCM playback is a later optimization; current file must finish rendering before playback. |
| Keep inference numeric-loopback-only | Preserve V1's local-provider boundary | A separate LAN provider is deferred. PC-assisted configuration can use an operator-managed authenticated tunnel to a PC; no listener or firewall changes are performed here. |

## Audio lifecycle and evidence

Desktop dispatch validates the representation, computes an estimate, cancels the previous audio job, and accepts one new job. A single executor processes work; cancelled queued futures are removed. Rendering checks a cancellation event every 1024 samples (about 46ms of audio, not a wall-time guarantee). Stop/mute/cancel set the event and stop the player. A final locked cancellation/deadline check prevents a cancelled render from playing after reset or unmute. Reset closes and recreates the render executor; it never replays.

Accepted means **queued**, not rendered, played, heard, or physically executed. The terminal reports later WAV/playback API status separately. Render/player errors are surfaced by desktop polling and latch the brain's stop. No asynchronous successful physical-completion event is invented. The existing operation deadline bounds rendering/start; it does not bound audible playback length. `last-response.wav` is replaced only by a finished uncancelled render. Temporary render files are removed after jobs exit.

Pitch patterns are host-owned. The LLM supplies only bounded text. CT2 lives in a typed, immutable in-memory representation, not a new serial protocol. Translation is decoded from CSP/CT1/CT2 and checked against the source response. Case/spacing/punctuation remain exact. English still appears when audio is muted or cancelled; this is not an assertion that audio was heard.

## Personality limits

Profile fields become style instructions, followed by immutable application instructions: no sensors, tools, physical actions or invented measurements. They cannot alter capability flags, validation, stop state, safety checks, output byte limits or model options. No profile key grants a tool. Instructions cannot guarantee an LLM never makes a false statement: its prose remains untrusted speech, never sensor telemetry or evidence of action. The default/examples model honest uncertainty; no safety filtering based only on keyword lists is claimed.

## Compatibility and deferred work

Existing six canonical phrases retain their exact CSP messages and note sequences. CT1 encode/decode functions and old `ConversationOutput` construction remain valid; CT2 is an optional extra field, used for new noncanonical speech. Legacy runtime JSON files missing new keys inherit defaults. Duplicate JSON keys, nonfinite values, wrong types and unknown keys fail readably. An explicit legacy text profile remains supported but is not combined with JSON.

Desktop UI/console is the priority. Microphone input, acoustic recognition, phone UI, natural prosody, a larger lexicon, physical drivers and persistent personal memory remain deferred. Pi hardware/real-model performance is unmeasured. See the [build guide](../build-guides/rocky-desktop-v1-1.md), [deployment checklist](../build-guides/rocky-small-computer.md), and [test record](../test-plans/rocky-desktop-v1-1.md).

## Changed-file map

| Exact repository paths | Purpose |
|---|---|
| `Rocky.bat`, `scripts/Launch-Rocky.ps1` | Double-click menu, non-destructive setup/repair and desktop shortcut. |
| `scripts/check_environment.py`, `scripts/run_tests.py` | Verify this checkout's environment; run and report all available host suites. |
| `software/rocky/personality.py`, `software/rocky/config/personality.json`, `software/rocky/config/personality-example.json`, `software/rocky/config/rocky.json` | One selected validated profile and runtime defaults; legacy text file preserved. |
| `software/csp/learning.py`, `language/specification/CT2_LEARNING_V1.md` | Versioned lossless lexical overlay and exact reference. |
| `software/brain/contracts.py`, `software/brain/controller.py` | Optional typed CT2 field and host-owned encoding selection; original request/safety chain retained. |
| `software/rocky/audio.py`, `software/rocky/desktop.py` | Timing/estimate, chunked cancellable rendering, worker lifecycle and audio status. |
| `software/rocky/translation.py`, `software/rocky/conversation.py`, `software/rocky/cli.py` | Decoded English agreement, word/full replay, learning controls and responsive console. |
| `software/rocky/providers.py`, `software/rocky/__init__.py` | Availability check, immutable capability instructions, V1.1 app version. |
| `software/rocky/tests/test_conversation.py`, `software/rocky/tests/test_learning.py`, `software/rocky/tests/test_desktop_upgrade.py`, `software/rocky/tests/test_windows_launcher.py` | Regression, CT2, settings, audio and Windows launch tests. |
| `.github/workflows/tests.yml`, `.gitignore` | Python 3.12/3.13 CI; ignore newly created local environments/pointer. |
| `software/rocky/config/rocky-pi-standalone.example.json`, `software/rocky/config/rocky-pc-assisted.example.json` | Portable examples; no network service or tunnel automatically started. |
| `docs/build-guides/rocky-desktop-v1-1.md`, `docs/build-guides/rocky-small-computer.md` | Beginner setup, personalization, learning, sourced hardware comparison and transfer/deployment checklist. |
| `docs/test-plans/rocky-desktop-v1-1.md`, `docs/test-plans/results/rocky-desktop-v1-1-host-tests.txt`, `docs/test-plans/results/rocky-desktop-v1-1-cli-smoke.txt` | Observed evidence, limitations and manual acceptance. |
| `README.md`, `docs/INDEX.md`, `CHANGELOG.md`, `docs/architecture/rocky-desktop-v1-1.md` | Navigation, scope, decisions and version history. |

The pre-existing Windows test records and milestone updates inherited from the V1 branch are preserved in addition to this map; they are not new measurements from this upgrade.
