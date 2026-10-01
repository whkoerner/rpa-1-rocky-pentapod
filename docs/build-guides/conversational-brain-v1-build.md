# Build guide: Rocky Conversational Brain V1

**Status:** READY FOR USER TESTING  
**Milestone:** M0, computer conversation increment  
**Version:** Conversational Brain 1.0.0; Python distribution `rpa1-csp` 0.2.0  
**Last updated:** 2026-10-01

## Goal

Type to a local language model, hear Rocky's deterministic Chordic response through your computer, and see the same response in English. No Arduino is needed. Your keyboard remains available while the model thinks.

Start with the audio diagnostic, then DummyAI, then the real model. DummyAI is a test fixture, not conversational intelligence. See [architecture](../architecture/conversational-brain-v1.md), [CT1 language extension](../../language/specification/CT1_TEXT_V1.md), and [release/test record](../milestones/conversational-brain-v1.md).

## Programs to download — manual step for Wyatt

1. [Git for Windows](https://git-scm.com/downloads/win). Skip if `git --version` already works.
2. [Python for Windows](https://www.python.org/downloads/windows/). Use a standard 64-bit **Python 3.13** installer with the Python launcher. The repository requires Python **3.10 or later**. Python 3.13 and 3.14 meet that declared requirement; the recorded execution environment here was Linux Python 3.12.14, so Windows/3.13/3.14 behavior still requires your tests. You do not have to remove another installed Python. Avoid the free-threaded experimental build for this first run.
3. [Ollama for Windows](https://ollama.com/download/windows), for the real AI only. Official Windows runtime requirements are [here](https://docs.ollama.com/windows). No Ollama account or cloud model is needed.

If you already have Python 3.13, use it. Check installed interpreters with `py -0p`, and check the exact version with `py -3.13 --version`. If you choose an existing 3.14 instead, replace only `py -3.13` in the environment-creation command with `py -3.14` and run all tests. The environment then keeps using that interpreter.

## Fresh Windows installation

Open PowerShell from the Start menu. Work from a folder where you want the project; the clone command creates `rpa-1-rocky-pentapod` there. Run these commands individually in order. This branch is the V1 review snapshot; after it is merged, `main` also contains it.

```powershell
git clone https://github.com/whkoerner/rpa-1-rocky-pentapod.git
cd rpa-1-rocky-pentapod
git switch feat/rocky-conversation-v1
git pull --ff-only
git --version
py -0p
py -3.13 --version
py -3.13 -m venv .venv-rocky
.\.venv-rocky\Scripts\python.exe -m pip install --upgrade pip
.\.venv-rocky\Scripts\python.exe -m pip install -e .
.\.venv-rocky\Scripts\python.exe --version
.\.venv-rocky\Scripts\python.exe -m unittest discover -s language/tests -v
.\.venv-rocky\Scripts\python.exe -m unittest discover -s software/rpa_link/tests -v
.\.venv-rocky\Scripts\python.exe -m unittest discover -s software/simulation/tests -v
.\.venv-rocky\Scripts\python.exe -m unittest discover -s software/brain/tests -v
.\.venv-rocky\Scripts\python.exe -m unittest discover -s software/rocky/tests -v
.\.venv-rocky\Scripts\python.exe -m rocky audio-test
.\.venv-rocky\Scripts\python.exe -m rocky --provider dummy
```

Type `hello rocky`, wait for the response, then type `/translate`, `/replay`, and `/quit`. You should hear musical audio and see English. An audio API success message alone is not proof that your speakers produced sound.

These commands deliberately call the environment's Python directly, so PowerShell activation policy cannot block setup. Optional activation is:

```powershell
.\.venv-rocky\Scripts\Activate.ps1
```

After successful activation, `python` replaces the long interpreter path. If activation is blocked, keep using the exact commands above; no execution-policy change is needed. Do not use the repository's old tracked `.venv`; create `.venv-rocky` fresh.

For an existing checkout, open PowerShell **inside its root** (the folder containing `pyproject.toml`). Run `git status` first. Keep any personal edits. Then run `git fetch origin`, `git switch feat/rocky-conversation-v1`, and `git pull --ff-only`. If Git reports a conflict with your edits, do not use force/reset; preserve those edits before switching. Continue at virtual environment creation.

## Download and run the real AI — manual step for Wyatt

Install Ollama, then open a **new PowerShell window** so `ollama` is on PATH. Quit its tray application before starting the explicit server below. First set local-only operation in your user environment:

```powershell
[Environment]::SetEnvironmentVariable('OLLAMA_NO_CLOUD', '1', 'User')
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_HOST = '127.0.0.1:11434'
ollama --version
ollama serve
```

Leave this window open. If it says the address is already in use, quit the existing Ollama tray instance and retry so this server definitely inherits the local-only setting. Do not kill unrelated processes.

In your **project PowerShell window**, run:

```powershell
ollama pull qwen3:8b
ollama list
ollama show qwen3:8b
.\.venv-rocky\Scripts\python.exe -m rocky --provider local --model qwen3:8b
```

The first model download requires internet and several gigabytes of storage. Ollama stores the model under your user profile's `.ollama\models` by default. You do **not** copy model files into GitHub or into the Python project. Verify the exact format/quantization with `ollama show`; model tags can be updated upstream. Write the model ID from `ollama list` into your manual test record.

The recommended starting model is Qwen3 8B. Your memory/GPU specifications are unknown, so no speed or memory-fit claim is made. If it is too slow or will not fit, use:

```powershell
ollama pull qwen3:4b
.\.venv-rocky\Scripts\python.exe -m rocky --provider local --model qwen3:4b --timeout 180
```

The model is replaceable; the brain does not change. A different local model must support the selected Ollama JSON-schema/chat options. Missing or incompatible models fail visibly; they never silently switch to DummyAI or cloud.

## First conversation and commands

Enter one message and wait for the reply before sending the next:

```text
Hello Rocky. How are you?
My favorite color is blue.
What color did I tell you I liked?
Help me understand what a resistor does.
/translate
/replay
/auto
What should we build next?
/translate
/mute
/unmute
/status
/model
/offline
/clear
/quit
```

`/auto` toggles automatic English display; audio still plays. `/translate` always shows the last accepted English response. `/replay` sends that response through the brain/safety/audio path again. `/mute` immediately requests playback stop and mutes future responses. `/unmute` enables future playback; it does not automatically replay.

`/cancel` cancels a pending model request. `/stop` cancels inference, stops audio and latches a stop. `/reset` explicitly recovers to disabled without replay. `/help` lists commands. `/quit` or Ctrl+C ends the program and closes audio. Recent history holds up to 12 complete turns; `/clear` forgets it. Stopping and restarting also loses that history.

## Configuration and files

No configuration edit is required for the commands above.

| File / setting | What to edit |
|---|---|
| `software/rocky/config/personality.txt` | Rocky's original personality and speaking style. Restart after editing. |
| `software/rocky/config/rocky.json` | `model`, `provider` (`local`/`dummy`), `port`, `timeout` (1–600 seconds), `audio_backend`, `volume` (0–0.30). |
| `--model`, `--timeout`, `--volume`, `--audio-backend` | Per-run overrides without editing a tracked file. |
| `--config PATH` / `--personality PATH` | Load an explicit local settings/persona file. |
| `--data-dir PATH` | Change the writable output directory. |

Default output directory is `$env:USERPROFILE\.rpa1\conversation-v1`. `events.jsonl` records brain status metadata; `last-response.wav` contains the most recent musical reply. CT1 is reversible, so this WAV can contain personal conversation content. `/clear` clears memory, not this file. To remove the WAV after quitting, use:

```powershell
Remove-Item "$env:USERPROFILE\.rpa1\conversation-v1\last-response.wav"
```

## Audio troubleshooting

Start system volume low. Digital gain does not establish a safe measured sound level.

1. Run `.\.venv-rocky\Scripts\python.exe -m rocky audio-test` independently of Ollama.
2. Select the correct Windows speaker/headphone output and check Volume Mixer for muted Python audio.
3. If needed, generate a diagnostic without playback:

```powershell
.\.venv-rocky\Scripts\python.exe -m rocky audio-test --audio-backend wav
Invoke-Item "$env:USERPROFILE\.rpa1\conversation-v1\last-response.wav"
```

4. A playable WAV confirms generation; hearing it confirms your chosen output path. `--audio-backend wav` never plays automatically.
5. An optional alternative Windows backend is pygame:

```powershell
.\.venv-rocky\Scripts\python.exe -m pip install -e ".[audio]"
.\.venv-rocky\Scripts\python.exe -m rocky audio-test --audio-backend pygame
```

Audio runs asynchronously. New playback replaces the previous phrase. Long CT1 sentences can take tens of seconds; the model is prompted to answer concisely.

## AI troubleshooting

- **Local Ollama unavailable:** start the Ollama server. This means the local runtime/port is unavailable, not that internet is required.
- **HTTP 404 / model unavailable:** run `ollama list`, then download the exact selected model while online.
- **PROVIDER_TIMEOUT:** first-load inference may be slow. Try a smaller model or `--timeout 180`; `/cancel` and `/stop` remain available.
- **INVALID_RESPONSE:** the model failed the schema/size boundary. Try a shorter question or a compatible model. Rejected output is not played or remembered.
- **BUSY:** one normal request is in flight. Wait or `/cancel`.
- **Backend fault:** inspect speakers/configuration, then restart or use the explicit stop/reset path. No silent fallback claims sound succeeded.

## Prove normal operation is offline — manual acceptance

1. While online, install dependencies and pull the model. Start a real conversation successfully once.
2. Quit Rocky. Stop the explicit Ollama server with Ctrl+C.
3. Disable Wi-Fi and disconnect Ethernet. Do not merely close your browser.
4. In the Ollama window run `$env:OLLAMA_NO_CLOUD = '1'`, `$env:OLLAMA_HOST = '127.0.0.1:11434'`, then `ollama serve` again.
5. In the project window run `.\.venv-rocky\Scripts\python.exe -m rocky --provider local --model qwen3:8b`.
6. Ask a new question, state a favorite color, then ask for that color. Hear Chordic and check English, `/translate`, and `/replay`.
7. Record pass/fail, model ID, Python version, computer hardware and any delay. `/offline` explains configuration; it is not evidence that internet is disconnected.
8. Reconnect your network when finished.

## Phone and microphone

Phone mode is **not implemented** in V1. No local web server is exposed, and there is no phone URL/IP setup to perform. The old browser prototype is not this conversation client.

Voice input is **prepared for V2** only through `software/rocky/speech.py`. `/listen` explains that it is unavailable. No microphone download is required today. V2 must add bounded offline push-to-talk recognition returning text to the existing input path; acoustic Chordic recognition is separate work.

## Raspberry Pi / Linux later

Recreate the environment on 64-bit Raspberry Pi OS/Linux; never copy a Windows venv. In a full checkout:

```bash
python3 -m venv .venv-rocky
source .venv-rocky/bin/activate
python -m pip install -e '.[audio]'
python -m rocky audio-test
python -m rocky --provider dummy
```

If venv is missing on Raspberry Pi OS, install its `python3-venv` OS package. Pygame/SDL and a working system audio device are needed for Linux playback. Use Ollama's official ARM64 installation instructions only when you are ready to measure a suitable model on the actual Pi. No Pi model speed, memory fit or audio result is claimed here. Model runtime, audio and speech are adapters; the brain stays portable.

## Full regression checks

The five Python suite commands above require no hardware/model/speakers. Maintainers with Node installed can also run the existing browser test:

```powershell
node software/brain_web/protocol.test.js
```

GitHub CI runs those suites on Windows/Linux and retains the existing Arduino compilation job. Arduino compilation and physical bench tests remain separate evidence; no firmware changed for V1.

## Acceptance checklist

- [ ] All five Python suites pass on your interpreter.
- [ ] `audio-test` is actually heard.
- [ ] DummyAI creates audio/translation without Ollama running.
- [ ] Real local AI gives useful, original, multi-turn replies.
- [ ] Favorite-color recall succeeds within the session.
- [ ] Translation toggle, replay, mute and unmute work.
- [ ] `/stop` during inference blocks the eventual reply; reset does not replay.
- [ ] Offline restart and conversation succeed with networking disconnected.
- [ ] Record results before calling this VERIFIED.

**Next step:** run the independent `audio-test` and confirm that you hear it.
