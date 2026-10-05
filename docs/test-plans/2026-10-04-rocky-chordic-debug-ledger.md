# Rocky Desktop + Chordic debugging and test-evidence ledger

**Date recorded:** 2026-10-04  
**Scope:** Documentation/test-evidence only; no production behavior change  
**Repository baseline inspected:** `58218d83774ae437c51ed23130ba03267e4946da` on `main`  
**Primary merged work:** PR #11, "Test Chordic EXP-002 through Rocky timing and Brain boundary"

This ledger preserves the real debugging sequence around Rocky Desktop V1.1, the local personality/provider repair work, and the Chordic EXP-002 integration. It intentionally distinguishes committed/automated evidence from user-observed local evidence. A local observation is not promoted to CI evidence simply because a related invariant exists in the repository.

## Evidence labels

- **AUTOMATED** — directly exercised by committed tests/CI, with a run or test named below.
- **REPOSITORY** — directly visible in committed source/configuration/documentation, but not by itself proof of a runtime observation.
- **MANUAL / USER-OBSERVED** — reported from the user's local Windows/manual session. Preserve as real acceptance/debug history, but do not represent it as CI.
- **NOT RUN / SUBJECTIVE** — not executed, not implemented, or requiring human listening/judgment beyond automated evidence.

## Repository state inspected before this update

- `main`: `58218d83774ae437c51ed23130ba03267e4946da`, merge commit for PR #11.
- Merged PR #11 head: `fb226d5b35fcd9907f9a60ce79c969503998f300`.
- `feat/rocky-desktop-v1-1`: `7882956d87447be005107b456cb91f8d10250514`.
- `feat/rocky-conversation-v1`: `37b0ba4a03def2c3904b9d66712e6f65175223a1`.
- `feat/chordic-exp-002-integration`: currently `9554fcd420b12c4ceb02d6850e69f30ada738278`, one commit ahead of and one merge commit behind `main`. That post-merge branch commit contains an unmerged personality-profile edit; it is evidence of ongoing personality experimentation, not part of merged PR #11.
- Existing evidence documents reviewed: `docs/test-plans/rocky-desktop-v1-1.md` and `docs/test-plans/chordic-exp-002.md`.
- Current code/tests reviewed for the personality schema, provider system prompt, deterministic Dummy provider, check-no-audio invariant, and Windows launcher regression.

## Detailed bug/test ledger

| Order | Feature/test | Reproduction | Exact symptom/error | Root cause | Fix | Verification | Final status | Evidence | Related commit/PR/run |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | PR #11 EXP-002 integration | Run pinned EXP-002 timing tests and send a benchmark utterance through Brain/Safety/Task | Integration goal; no defect claimed | N/A | Added pinned read-only EXP-002 snapshot and focused tests without replacing production CT2 | PR #11 merged; committed plan states production Brain/SafetyValidator/Task/hardware/CT1/CT2/launcher/audio behavior was not replaced | **PASS / MERGED** | AUTOMATED + REPOSITORY | PR #11; merge `58218d8...` |
| 2 | EXP-002 integration CI | Push PR #11 corrections and run normal workflow | Runs #42-#44 failed in **Conversational Brain V1 tests (no model or speakers)**; Arduino passed | See entries 3-4 | Corrected test-only backend and capability declaration | Run #45 passed Windows/Linux x Python 3.12/3.13, browser protocol and Arduino; post-merge #46 passed | **PASS**; earlier failures preserved | AUTOMATED | Runs #42-#46 |
| 3 | Initial Brain-path test backend | Execute new Brain-path test with initial `SimulatorHardware` | Conversational Brain V1 step failed across matrix | `SimulatorHardware` unsuitable for arbitrary `ConversationOutput` dispatch in this test | Replaced with dedicated communication-only backend | Commit `b54d007...`; later failure changed to missing capability rather than backend mismatch | **FIXED** | AUTOMATED + REPOSITORY | run #42; commit `b54d007...` |
| 4 | Communication-only backend capability | Run Brain-path test without `TEXT_COMMUNICATION` | SafetyValidator correctly rejected conversational utterance | Test backend advertised communication but omitted explicit text communication capability | Added `Capability.TEXT_COMMUNICATION` to test backend only; no motion capability added | Final backend has COMMUNICATION, TEXT_COMMUNICATION, LOCAL_STOP; test confirms host motion remains disabled; run #45 green | **FIXED / SAFETY PRESERVED** | AUTOMATED + REPOSITORY | commits `45746ad...`, `fb226d5...`; runs #43-#45 |
| 5 | Local virtual environment | Local machine used stale `.venv-1` | Referenced missing Python314 executable | Stale/broken interpreter reference; exact origin not preserved | Rocky setup/repair restored working `.venv-rocky` | Existing Desktop V1.1 acceptance independently records successful setup/repair using `.venv-rocky` | **PASS locally after repair** | MANUAL; final state corroborated by repo docs | `rocky-desktop-v1-1.md` |
| 6 | Desktop shortcut | Launch original desktop shortcut | Opened `rpa-1-rocky-pentapod-v11` instead of current `rpa-1-rocky-pentapod` | Shortcut target pointed at old/different checkout | Recreated shortcut for current checkout | User later observed correct repo and `.venv-rocky`; prior Desktop V1.1 acceptance records shortcut launching without manual activation | **PASS locally after recreation** | MANUAL | no exact commit/run found |
| 7 | Personality identity | Ask real local model identity/self-description questions | Rocky described itself like software/a desktop conversation program | Merged personality self-description says "currently a desktop conversation program"; merged provider system prompt also says "You are a desktop conversation program..." | Local wording adjusted so normal identity can be Rocky-first while capability limits remain immutable | User later observed desired Rocky-style wording; no headless CI can prove subjective persona quality | **IMPROVED manually; merged wording still deserves deliberate follow-up** | REPOSITORY + MANUAL | merged files; post-merge branch `9554fcd...` |
| 8 | Manual `providers.py` edit | Run Rocky/tests after manual edit | `IndentationError: unexpected indent` around line 159 | Manual edit introduced invalid indentation | Repaired file | User reports `py_compile` then succeeded; current committed provider is syntactically valid and CI green | **PASS locally after repair** | MANUAL | no broken intermediate commit found |
| 9 | Personality schema | Load edited profile/startup tests | `personality.speaking_style must be 1-500 printable characters` (repo renders `1–500`) | Edited style violated explicit printable/length constraint | Shortened style; moved detailed behavior to appropriate provider/system instructions | `personality.py` enforces <=500 printable chars; inspected post-merge branch style is 475 chars; local errors reportedly cleared | **PASS locally; schema retained** | REPOSITORY + MANUAL | `personality.py`; branch `9554fcd...` |
| 10 | DummyConversationProvider deterministic diagnostic | Run worker/provider regression after wording change | Expected phrase `dummy test mode` disappeared | User-facing wording edit changed a deterministic diagnostic contract | Restored Dummy wording/behavior | Current provider returns `dummy test mode`; test explicitly asserts it; main CI #46 green | **PASS / protected** | transient failure MANUAL; restored invariant AUTOMATED + REPOSITORY | provider/test files; run #46 |
| 11 | `test_check_never_generates_or_opens_audio` | Run focused desktop-upgrade tests in broken local personality/provider state | Test also failed during broken state | Exact transient local failure path not preserved, so no narrower cause claimed | Repair local state; do not weaken assertion | Current test patches `DesktopHardware.open` and asserts not called; main CI #46 green | **PASS currently / invariant protected** | failure MANUAL; current protection AUTOMATED + REPOSITORY | `test_desktop_upgrade.py`; run #46 |
| 12 | Windows launcher temporary environment | Run `test_valid_environment_and_broken_explicit_override` locally | `No module named 'yaml'` | Selected temporary/local Python lacked YAML module | Environment/PyYAML repaired; exact repair command intentionally not invented | User reports later local suite had no failures; GitHub Windows CI had already passed launcher suite | **PASS locally after environment repair** | local failure/fix MANUAL; CI AUTOMATED | Desktop runs #36-#38; main #41/#46 |
| 13 | Real-model personality acceptance | Converse with real local model after repairs | Prior software-like identity replaced by Rocky-style phrasing | See entry 7 | Local personality/provider repair | User observed example `Rocky is name. You friend. Good.`; third-person/telegraphic style working | **MANUAL PASS** | MANUAL / SUBJECTIVE | no exact merged commit/run establishes qualitative output |
| 14 | Normal CT2 fallback runtime duration | Allow normal free-form real-model replies to use current production CT2 fallback | User-observed durations about 14.07 s, 50.84 s, 35.06 s, 24.32 s | Current fallback scales with arbitrary reply text and can become too long for conversation | No production codec replacement claimed here; evidence motivates production EXP-002 integration/evaluation | Separate automated fixed 17-case benchmark: current CT2 mean 8.030 s/max 10.875 s; EXP-002 mean 6.794 s/max 8.400 s, 17/17 <=10 s | **OPEN runtime problem** | free-form durations MANUAL; benchmark AUTOMATED | PR #11; `chordic-exp-002.md`; runs #45/#46 |

## CI progression for PR #11

| Run | Head | Result | Relevant evidence |
| --- | --- | --- | --- |
| #42 | `7388181...` | FAIL | Conversational Brain V1 step failed in all four Python matrix cells; Arduino passed. |
| #43 | `b54d007...` | FAIL | Communication-only backend was in place, but the focused conversational path still failed. |
| #44 | `45746ad...` | FAIL | Conversational Brain V1 step still failed; Arduino passed. |
| #45 | `fb226d5...` | PASS | Windows/Linux x Python 3.12/3.13, browser protocol, and Arduino all passed. |
| #46 | `58218d8...` | PASS | Post-merge `main` verification passed. |

PR #11's final validation comment records the development failure sequence: unsuitable `SimulatorHardware`, then missing `TEXT_COMMUNICATION`, then final green with a communication-only, no-motion backend.

## Timing evidence: do not mix these populations

| Evidence | Population | Result | Classification |
| --- | --- | --- | --- |
| Production/current CT2 baseline in EXP-002 test | Fixed 17-case benchmark, 3x | mean 8.030 s; max 10.875 s; 1 case >10 s | AUTOMATED |
| Chordic EXP-002 candidate | Same fixed 17-case benchmark, 3x | mean 6.794 s; max 8.400 s; 17/17 <=10 s | AUTOMATED |
| Normal CT2 fallback runtime examples | Free-form real-model replies | ~14.07 s, 50.84 s, 35.06 s, 24.32 s | MANUAL / USER-OBSERVED |

The long free-form CT2 observations are evidence that production fallback still needs improvement. They are **not** evidence that EXP-002 itself takes 14-51 seconds.

## Manual, automated, and NOT RUN boundaries

### Automated evidence that exists

- PR #11 focused EXP-002 tests, including pinned snapshot, timing benchmark, registry uniqueness, Brain/Safety/Task traversal, and motion-disabled assertion.
- Full CI matrix on run #45 and post-merge run #46.
- Personality schema enforcement in `software/rocky/personality.py`.
- Deterministic Dummy diagnostic regression containing `dummy test mode`.
- `test_check_never_generates_or_opens_audio` invariant.
- Windows launcher regression suite, including `test_valid_environment_and_broken_explicit_override`.

### Manual/user-observed evidence

- Broken local `.venv-1` referring to missing Python314.
- Repair/use of `.venv-rocky` and corrected shortcut target.
- `IndentationError: unexpected indent` during manual `providers.py` editing, followed by successful `py_compile`.
- Personality schema failure during local profile experimentation and subsequent repair.
- Temporary Dummy diagnostic and check-no-audio failures during the broken local state.
- Temporary `No module named 'yaml'` local environment failure and eventual no-failure local suite after environment repair.
- Real-model personality acceptance, including third-person/telegraphic output.
- Long free-form CT2 runtime duration examples.

### NOT RUN / do not claim

- **Spoken-English TTS:** no claim that an English TTS voice feature was implemented or tested in this work.
- **Contextual English prosody/inflection:** no claim that contextual prosody was implemented or tested.
- **EXP-002 subjective listening:** the committed EXP-002 plan still lists candidate listening at 1x/3x as manual work to do.
- **EXP-002 microphone/acoustic recognition:** not run; no human/listener/noise-tolerance claim.
- **Physical robot hardware / Pi acceptance:** remains outside this evidence unless separately documented.
- A successful headless audio request is not the same thing as a person hearing/approving acoustic output.

## Lessons / regression protections

- Do not identify personality as software unnecessarily. Keep truthful capability boundaries without forcing normal self-description to be "desktop program."
- Personality never grants hardware authority. Profile/system wording cannot bypass Brain/SafetyValidator or enable motion.
- Keep Dummy diagnostics deterministic; `dummy test mode` is a regression contract.
- Validate personality length/schema before startup.
- Run `py_compile` after manual provider edits.
- Preserve the check-no-audio invariant.
- Keep the desktop shortcut pointed at the current checkout.
- Preserve CT2 compatibility while EXP-002 evolves.
- Do not weaken safety tests to make experimental language work pass; the missing `TEXT_COMMUNICATION` rejection was correct.
- Keep fixed benchmark timing separate from arbitrary free-form runtime timing.

## Evidence sources used

- `main` merge `58218d83774ae437c51ed23130ba03267e4946da` for PR #11.
- PR #11 body/diff and final validation comment.
- PR #11 commits:
  - `8d9cd2bd94183c6fec4b9432902b0a8d51292af1` — EXP-002 timing/Brain-path tests.
  - `b54d007111a104dd262d4a5bd75a7dc4da242c75` — communication-only Brain test backend.
  - `45746ad2d74d4665370796648aa4c5c692671100` — documentation aligned with test-backend evidence.
  - `fb226d5b35fcd9907f9a60ce79c969503998f300` — advertises conversational text capability.
- GitHub Actions runs #42-#46, especially final PR run #45 and post-merge run #46.
- `docs/test-plans/rocky-desktop-v1-1.md`.
- `docs/test-plans/chordic-exp-002.md`.
- `software/rocky/personality.py`.
- `software/rocky/config/personality.json` on `main` and the current post-merge integration branch.
- `software/rocky/providers.py`.
- `software/rocky/tests/test_conversation.py`.
- `software/rocky/tests/test_desktop_upgrade.py`.
- `software/rocky/tests/test_windows_launcher.py`.
- User-observed local Windows/debugging evidence supplied for this documentation update.

## Could not independently verify from repository/Actions

The following are preserved as manual evidence because the broken intermediate files/logs were not found in committed Git/Actions history inspected here:

- exact stale `.venv-1` Python314 path and how it was originally created;
- exact original wrong-shortcut creation command/target metadata;
- broken `providers.py` intermediate file that produced the line-159 `IndentationError`;
- exact overlength `speaking_style` intermediate text;
- precise transient cause of the local `test_check_never_generates_or_opens_audio` failure;
- exact PyYAML repair command after `No module named 'yaml'`;
- real-model transcript beyond the user-supplied example;
- raw logs for the four long free-form CT2 runtime duration examples.

These gaps are deliberate: this document preserves the reported history without inventing commands, commits, or automated evidence.


## Follow-up implementation on draft PR #14 — persistent translation / local voice / EXP-002 runtime

The earlier **NOT RUN** statements above correctly describe the state of the documentation-only update on main at that time. Draft PR #14 later implements a candidate local spoken-English path and production-selectable EXP-002 runtime. Those old statements are preserved rather than rewritten.

Current PR #14 status:
- local Windows spoken-English implementation exists, but subjective acoustic quality remains **NOT RUN**;
- persistent `/translate on|off|status` exists with `/clear` intentionally preserving the session preference;
- EXP-002 is a selectable/default desktop profile through a pinned Chordic export, with exact CT2 fallback for unsupported spans;
- CT2 remains available;
- provider identity wording no longer requires Rocky to call himself a desktop program, while immutable no-hardware authority remains;
- PR #14 CI failures #51 onward are preserved in `docs/test-plans/2026-10-04-persistent-translation-tts-exp002.md`, including the disproven loader theory, unmasked diagnostics, whitespace-fragment root cause, and final fix.

Do not treat the implementation as an acoustic PASS until the operator completes the manual Windows acceptance in that plan.


### PR #14 CI root-cause correction — runs #51-#64

The earlier PR #14 note that blamed `unittest.defaultTestLoader` was corrected after unmasked GitHub Actions diagnostics. Runs #53-#58 used `continue-on-error: true`, so their displayed green diagnostic step conclusions did not prove the underlying commands succeeded. Runs #59-#60 still failed with a fresh `unittest.TestLoader()`, disproving that theory.

Unmasked run #61 established the real boundary: the legacy Rocky suite passed through `test_learning`, and failure began when `test_translation_voice_exp002` was added. Run #62 narrowed this to EXP-002 runtime and persistent-translation tests while prosody stayed green. Run #63 isolated the failing free-form case and persistent turns containing known EXP-002 tokens separated by spaces.

Root cause: the EXP-002 adapter treated whitespace separators between known tokens as standalone CT2 fallback utterances. CT2 correctly rejects whitespace-only complete utterances, so phrases such as `Rocky help you.` failed even though the complete response was valid. Commit `fba35005cf2274294b592c3662a907fbd5278aca` changed fallback fragments to exact CT2 UTF-8 units that preserve whitespace inside the already validated parent utterance.

Verification: GitHub Actions run #64 passed all 11 method diagnostics, standard Rocky discovery, Windows/Linux Python 3.12/3.13 software cells, and Arduino. After all temporary diagnostic jobs were removed, clean run #65 also passed the normal Windows/Linux Python 3.12/3.13 matrix and Arduino. Subjective Windows speech/listening acceptance remains NOT RUN.


## Post-merge manual Windows acoustic evidence — 2026-10-04

Merged PR #14 was manually exercised on Windows after merge commit `2c7573e12326a8de28c2bc399d9787f95f1c75e7`.

Operator-confirmed evidence:
- English TTS was genuinely audible.
- Chordic pitches were genuinely audible.
- Multi-turn translated conversation worked.
- `/replay` produced replay plus completed English speech.
- `/speed 2` and `/speed 1` were exercised.
- The visible transcript reported CT2, with sample Chordic/English/sequential wall times of 13.10/7.23/20.32 s, 22.65/10.33/32.98 s, 16.01/8.69/24.70 s, 25.36/14.33/39.69 s, and replay at 12.68/14.29/26.97 s.
- Functional audibility is a PASS; acoustic naturalness is not. The operator says both English voice and Chordic tones are still "off a bit."
- New requested behavior: English translation should play concurrently over the Chordic tones.
- New personality requirement: Rocky should learn an explicitly stated session name and use it naturally/often.
- New acoustic direction: tunable English voice plus a less robotic, whale-like/resonant/vibrating Chordic timbre while preserving machine-recognizable pitch semantics.
- Longer-term direction: streaming phone/computer recognition and real-time Chordic translation.

The full evidence and acceptance plan is in `docs/test-plans/2026-10-04-post-merge-acoustic-feedback.md`.


## PR #15 post-merge acoustic iteration — automated evidence

Branch: `feat/rocky-audio-overlap-name-tuning`.

Changes under test:
- overlap English translation with actual Chordic playback start;
- explicit session-name memory and provider context;
- bounded Windows voice selection/rate/pitch/volume tuning;
- pure/resonant Chordic A/B synthesis;
- fix duplicate `/translate` status output;
- fix duplicate completed-response prompt output.

New bugs discovered while implementing:
1. `/translate on|off` printed the same status line twice in merged main.
   - root cause: duplicate adjacent print statement in CLI command handler;
   - fix: remove duplicate;
   - status: fixed on PR #15.
2. terminal printed `> ` twice after a completed response.
   - root cause: duplicate adjacent prompt print;
   - fix: remove duplicate;
   - status: fixed on PR #15.

Automated result:
- Actions run #68 on `98c7ae67409f5d542fd567f8dd02ddcfa844a71d`: Windows 3.12 PASS, Windows 3.13 PASS, Ubuntu 3.12 PASS, Ubuntu 3.13 PASS, Arduino PASS.
- No subjective acoustic claim is inferred from that green run.


## PR #15 manual Windows failures and new acoustic requirements

Second operator session on PR #15 confirmed name memory and voice selection, but exposed a reproducible tuning bug and insufficient acoustic naturalness.

Reproducible bug:
- `/voice select Microsoft David Desktop`
- `/voice rate 2`
- `/voice pitch -1`
- ask a question
- result: `TRANSLATION_VOICE_FAILED: ValueError: untrusted prosody profile`
- subsequent `/replay` continued failing with the same validation error.
- switching Chordic tone style did not repair it, correctly localizing the failure to English prosody/SSML validation.

Manual PASS:
- explicit name `Wyatt` captured and recalled;
- Microsoft David and Microsoft Zira listed and selectable;
- translated speech and tones audible;
- speed/replay worked before the TTS failure.

Manual FAIL / tuning feedback:
- question delivery lacks natural questioning cadence;
- pauses and emotional weight are insufficient;
- resonant Chordic remains too robotic with fast beep-like shifts;
- desired sound is smoother, lower, resonant, hum/rumble/vibration-like;
- desired scheduler: Chordic starts 0.5-1.0 s first, stays slightly quieter, and normally finishes shortly before English.

Observed timing samples are preserved in `docs/test-plans/2026-10-04-post-merge-acoustic-feedback.md`.
