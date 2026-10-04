# Rocky desktop V1.1 — evidence and Windows acceptance

Status: **READY FOR USER TESTING**. App version `1.1.0`; combined distribution remains `rpa1-csp` `0.2.0` (no release tag created). Date: 2026-10-03 Los Angeles / 2026-10-04 UTC.

## Provenance

- Inspected `main`/merged PR #8 at `4cc02cbb8e8805adad98dfea64eaedac326aea04`.
- Preserved newer test history from `feat/rocky-conversation-v1` at `2dd7193022bc95c0afae9d8919639c5ffb751e15` through merge commit `f0431c6` on the new branch.
- CT2, timing, background audio and translation: `0a3de19`.
- Launcher, personality, learning controls, environment/provider checks and focused tests: `e481ca8`.
- Piped-terminal asynchronous status flush, found by CLI smoke check: `5c33e0f`.
- Branch: `feat/rocky-desktop-v1-1`. Documentation follows those functional commits; obtain the exact checkout with `git rev-parse HEAD` and preserve it with each user test.

Your earlier “it worked” is recorded only at its stated scope. Existing Windows audio and DummyAI observations remain in their original records. The real Qwen multi-turn crash is unresolved; nothing here upgrades it to a pass.

## Automated results actually observed

Environment: Linux, Python **3.12.14**, Node **v24.19.0**, no speaker or real model. Baseline before changes: **77 Python tests passed**, plus Node protocol script passed.

Final full host run at functional revision `e481ca8`:

| Suite | Passed | Skipped | Failed |
|---|---:|---:|---:|
| `language/tests` | 16 | 0 | 0 |
| `software/rpa_link/tests` | 10 | 0 | 0 |
| `software/simulation/tests` | 9 | 0 | 0 |
| `software/brain/tests` | 12 | 0 | 0 |
| `software/rocky/tests` | 49 | 3 | 0 |
| **Python total** | **96** | **3** | **0** |

The three skips require actual Windows cmd/PowerShell and cover the spaced-path batch entry, missing-environment repair guidance, and valid/broken environment selection. They have **not** passed on Linux; they run in the Windows CI matrix. Existing CI is extended to Python 3.12 and 3.13 on Windows/Linux; remote CI results must be read separately before claiming a pass.

Node `software/brain_web/protocol.test.js`: **passed**. Full raw output: [host-tests.txt](results/rocky-desktop-v1-1-host-tests.txt). Executed command:

```sh
.venv-rocky-agent/bin/python scripts/run_tests.py
```

A local verification environment was created with `python -m venv --system-site-packages .venv-rocky-agent`, then `python -m pip install --no-build-isolation -e .`. Installation and `scripts/check_environment.py` passed. This reused available host dependencies; it is **not proof of a clean offline dependency installation**.

Installed CLI smoke run from a separate directory passed after the one-line `5c33e0f` status-flush fix: DummyAI response, generated WAV, auto-off/request translation, token display, learning speed, word replay, mute/unmute, stop rejection, reset and clean quit. No speaker was used. [CLI output capture, trailing spaces removed](results/rocky-desktop-v1-1-cli-smoke.txt). The smoke run initially exposed buffered asynchronous audio status in piped terminals; adding `flush=True` resolved the observed timeout. The full suites above precede that output-only fix; this distinction is preserved.

`audio-test --audio-backend wav` also completed and produced a 3.975-second Hello WAV at multiplier 3. The duration comes from PCM/sample counts, not a listening observation. `git diff --check` passed after whitespace correction.

Focused coverage includes old settings and text profiles, default/custom JSON, invalid/duplicate settings, profile permission boundaries, portable examples, CSP golden notes, CT1 compatibility, CT2 word/phrase boundaries, exact Unicode/case/punctuation round trips, explicit fallback, translation mismatch rejection, identical 1×/3× pitches, scaled note/gap duration, queued-render cancellation, mute, stop/reset, word replay safety, stale results, and existing provider/safety tests.

Development tests found that closing the executor during stop/reset prevented new renders after recovery. The adapter now recreates it on `open`; the regression confirms old audio is discarded and new operator work can play. Existing audio tests were updated to distinguish queued acceptance from later render/player failure.

## Published commit identity mapping

Publication used the connected GitHub app because command-line Git push had no credentials. Commit metadata changed IDs; the complete Git tree hashes of the merge and each functional commit were verified equal to their tested local counterparts. Raw test logs preserve the local IDs above. Use the published IDs below when inspecting GitHub or checking out tested code.

| Local validation commit | Published GitHub commit |
|---|---|
| `f0431c6` | `75eed05e3ed3d9450f7f6aafaefc006fc65442a9` |
| `0a3de19` | `3b4310bc13792c7f739cf1c88e4b71b41ab0a544` |
| `e481ca8` | `f8b2e984d1fc28bdac1ccd6975e5374cd5e3130f` |
| `5c33e0f` | `54c928f10c70a16f880063c86924591728b9fe39` |

## Not tested / unresolved

- Windows double-click/shortcut creation, native winsound playback and **actual listening** on the user's machine.
- Python 3.13 local execution (CI coverage is configured, not an observed result in this record).
- Real-model quality, personality adherence, cold/warm latency, GPU stability or disconnected-internet acceptance.
- Pi/CM5 installation, CPU performance, cooling/power, audio and authenticated PC-assisted tunnel.
- Arduino compilation/upload (compiler unavailable locally), sensors, motors or physical safety acceptance. No firmware changed.
- Microphone input or acoustic translation: **not implemented**.
- Prior `VIDEO_TDR_FAILURE (0x116)` in NVIDIA recovery: mechanism documented in [existing evidence](2026-10-03-conversational-brain-v1-qwen3-first-multiturn.md), underlying trigger still unknown. This is not a GPU-driver fix.

## Manual Windows checks

Record code SHA, Windows/Python/Ollama/model version, configuration path, audio device, actual output, elapsed observations and any exception. Mark each check PASS/FAIL/NOT RUN; a rendered WAV or playback API request is not a listening pass.

| ID | Action | Expected acceptance |
|---|---|---|
| WIN-01 | Keep your current installation. Create the separate `Rocky Desktop Test` worktree using the build guide; double-click its `.bat`. Also start it from a different PowerShell directory using a quoted full path. | Same menu; no activation/CWD dependency, no administrator prompt, errors remain visible. |
| WIN-02 | In the **test worktree only**, run before setup or temporarily set `ROCKY_PYTHON` to a nonexistent path. Select 2. Remove that temporary override afterward. | Exact repair command; no download, Git update or deletion. |
| WIN-03 | Choose 7; run it again after editing a harmless profile field. | Valid environment; existing profile edit remains. A broken existing environment is retained and a new suffixed one is created when needed. |
| WIN-04 | Choose 8, then close and double-click the new desktop shortcut. | Same menu. A repeated shortcut creation refuses to overwrite the existing `.lnk`. |
| WIN-05 | Choose 4, then 6. | Results visible and saved; failures explicit. Node absence is separately marked NOT RUN. |
| WIN-06 | Choose 3 at default multiplier 3. | Hear a comfortable, slower Hello, approximately 4 seconds. Record actual hearing and quality separately. |
| WIN-07 | Choose 2, type `hello`, then `/tokens`, `/translate`. | Dummy label, estimated duration, decoded English equal to reply; supported/fallback spans visible. |
| WIN-08 | `/word hello`, `/word thank you`, `/speed 1`, `/word hello`, `/learn`, `/word hello`. | Repeatable lexical core; learning version 3× longer than 1×, unchanged perceived pitch. |
| WIN-09 | Start a reply/replay and immediately `/mute`, `/unmute`; then replay and `/cancel`. | Prompt remains responsive; mute/cancel stop sound/rendering; unmute does not resurrect it. Record observed delay; no hard real-time claim. |
| WIN-10 | `/stop`, `/replay`, `/reset`, `/word hello`. | Replay rejected while latched; reset alone is silent; new word replay works. |
| WIN-11 | `/auto` off, new reply, then `/translate`. | Automatic English/token text hidden until requested; representation decodes exactly. |
| WIN-12 | Back up active personality; use malformed JSON or `humor: 9`, restart. Restore the original afterward. | Readable error, no silent repair. Then use example profile; real-model adherence remains a separate qualitative check. |
| WIN-13 | Stop Ollama or select an unavailable model in a temporary config, run menu 1. | Bounded availability error/instructions; no model download or cloud fallback. Restore chosen model. |
| WIN-14 | Only after reviewing the existing crash evidence, run a short real-model conversation and multi-turn recall/personality check. | Record each turn/latency/crash honestly. Availability check alone does not pass this. |
| WIN-15 | With runtime/model provisioned, disconnect internet, restart runtime/Rocky, repeat several turns. | Successful locally executed inference/audio without internet. This establishes only the tested configuration, not all hardware/offline cases. |

See [installation and customization](../build-guides/rocky-desktop-v1-1.md) and [onboard acceptance checklist](../build-guides/rocky-small-computer.md). The safe first user run for this upgrade is setup → shortcut → DummyAI, followed by the audio/manual checks.
