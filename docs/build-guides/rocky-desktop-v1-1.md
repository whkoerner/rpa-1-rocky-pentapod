# Rocky V1.1: double-click launch and slow learning

This is the desktop upgrade to Conversational Brain V1. You type English and hear musical replies. It does not listen to a microphone, decode recorded sound, move, or read sensors.

## 1. Get the upgrade without losing your edits

The review branch is `feat/rocky-desktop-v1-1`. No automatic merge or update is performed by the launcher.

Open PowerShell **inside your existing repository folder**. First:

```powershell
git status --short
git fetch origin
```

If status listed changes, keep them. The safest way to test this version alongside your working copy is a separate folder (the name must not already exist):

```powershell
git worktree add -b test/rocky-desktop-v1-1 "..\Rocky Desktop Test" origin/feat/rocky-desktop-v1-1
Set-Location "..\Rocky Desktop Test"
.\Rocky.bat
```

This preserves your existing checkout, branch, personality edits and environment. Use a different new folder/branch name if either already exists. Do not force-switch, reset, clean, or copy `.venv` into the new folder. If you prefer switching your current **clean** checkout, use `git switch --track origin/feat/rocky-desktop-v1-1` once; later use `git switch feat/rocky-desktop-v1-1`. Stop on any Git warning instead of discarding changes.

For later updates in a clean checkout of this branch:

```powershell
git fetch origin
git merge --ff-only origin/feat/rocky-desktop-v1-1
.\Rocky.bat -Action setup
```

If fast-forward fails, stop and review the divergence. Nothing in Rocky fetches, pulls, installs models, or changes configuration automatically. For a fresh clone, install Git from its official site, clone this repository, and switch to the review branch before setup.

## 2. One-time setup or repair

Double-click **Rocky.bat** in the repository root. Choose **7 — Setup/repair**. Alternatively, in PowerShell opened in that folder:

```powershell
.\Rocky.bat -Action setup
```

Normal operation needs no administrator access. Setup uses a valid project environment if found. Otherwise it looks for an installed Python 3.13, then 3.12, using the Windows `py` launcher and creates `.venv-rocky`. If that directory already exists but is broken, it creates `.venv-rocky-repair-1` (then the next unused number). It never deletes/recreates an existing folder. If Python is missing, install a per-user copy from <https://www.python.org/downloads/windows/> including the Python launcher, then retry.

Setup explicitly runs `python -m pip install -e <this project folder>`. Internet can be needed to install Python dependencies. It does not install Ollama or download model weights. A local pointer `.rocky-python-path.txt` remembers the environment for this checkout. The launcher validates Python, dependencies, CSP resources and that Rocky imports from this checkout. It works from another starting directory and with spaces in the path. Keep the complete checkout: wheel-only installs are not supported by the existing CSP resource loader.

Environment order: explicit `ROCKY_PYTHON` override, otherwise the saved pointer, `.venv-rocky`, then `.venv`. No activated shell is required. An override must name a valid venv's `Scripts\python.exe`; do not set it unless needed. If an old override blocks repair, remove it from the environment where you launch Rocky (`Remove-Item Env:ROCKY_PYTHON` in PowerShell); a persistent Windows user environment setting must also be removed in Windows Environment Variables. Setup prints the exact absolute repair command if no environment is usable.

Setup creates missing files in **`%USERPROFILE%\.rpa1\settings`**, and does not overwrite existing files there. Existing custom `personality.txt` and `rocky.json` files in your old checkout remain untouched. See migration below before replacing a customized persona.

## 3. Desktop shortcut

The easiest method: choose **8 — Create desktop shortcut**. It uses Windows' current Desktop location, including redirected/OneDrive desktops, and creates **Rocky.lnk**. It refuses to overwrite an existing shortcut. No username is hard-coded. Moving the project later requires recreating the shortcut.

Manual method: right-click `Rocky.bat` → **Show more options** (Windows 11, if needed) → **Send to → Desktop (create shortcut)**. Rename the shortcut `Rocky`. Do not copy only the `.bat` to the desktop: it needs the adjacent `scripts` folder.

| Menu | What it does |
|---|---|
| 1 | Check the selected local model via Ollama `/api/show`, then open real chat. The check does not generate a response or download anything. |
| 2 | Run deterministic DummyAI conversation diagnostics without Ollama. This is not an LLM quality test. |
| 3 | Play the fixed Hello test at your timing/volume settings. |
| 4 | Run all Python host suites and Node protocol tests if Node is installed. Failures are not hidden by later passing suites. |
| 5 | Open this guide and your settings folder. |
| 6 | Open `%USERPROFILE%\.rpa1\conversation-v1\tests-latest.txt`. |
| 7 | Explicit package setup/repair; preserve existing environments/settings. |
| 8 | Create the desktop shortcut. |
| 0 | Exit. |

The menu stays open after failures. Direct actions pause before closing; a failed direct action is also held open by the batch file.

## 4. Customize one personality

Choose menu **5**, then edit **`%USERPROFILE%\.rpa1\settings\personality.json`** in Notepad. Keep quotes, commas and brackets valid. Save as UTF-8. Restart Rocky after editing; settings are loaded at startup. `rocky.json` has just one `personality_profile` path pointing to this file.

| Personality key | What to edit |
|---|---|
| `name` | Rocky's preferred name in model replies. The terminal application is still called Rocky. |
| `self_description` | How Rocky describes its character; this never creates actual abilities. |
| `curiosity`, `enthusiasm`, `humor` | Integer 0–3, from minimal to high. |
| `detail` | 0 is very concise; 3 asks for more detail within the same hard response-size limit. |
| `follow_up_questions` | 0 rarely asks; 3 often asks. It is not an exact percentage. |
| `forms_of_address` | A JSON list, such as `["Wyatt"]` or `["you"]`. |
| `speaking_style` | Plain-language description of how to speak. |
| `example_responses` | A short list of original examples of the tone you want. |
| `interests` | A few interests or preferences. |
| `version` | Leave at `1`. |

The default is `software/rocky/config/personality.json`. An alternative is `software/rocky/config/personality-example.json`; read/copy its desired fields into your active profile. Do not maintain two active profiles or combine conflicting text and JSON settings.

**All personality sliders/text are model instructions, not deterministic behavior guarantees.** DummyAI ignores them intentionally. Deterministic controls are runtime validation, allowed capabilities, response-size limits, timeouts, volume, timing multiplier, encoding and stop/mute handling. Personality never grants tools, changes safety, fabricates sensor state, or establishes that an action occurred. A model can still make a false claim; conversational prose is not hardware evidence.

**Migrate an edited V1 persona:** keep your old file. Either transfer its style preferences into the JSON profile, or set `personality_profile` in your user `rocky.json` to that legacy `.txt` file. Relative paths resolve beside the settings file; Windows absolute JSON paths need doubled backslashes. For a direct one-session override:

```powershell
.\.venv-rocky\Scripts\python.exe -m rocky --personality "C:\path to your old checkout\software\rocky\config\personality.txt"
```

Use the actual interpreter printed by the launcher if it selected another environment. An explicit `--personality` replaces the selected profile; the two are never merged. Existing runtime JSON with only the six V1 keys is accepted and inherits the new defaults. For CLI use, `%USERPROFILE%\.rpa1\settings\rocky.json` is used if present; otherwise packaged defaults apply. `--config <file>` explicitly selects a different runtime file.

## 5. Runtime, speed and learning

In the active `rocky.json`, the important entries are:

```json
{
  "provider": "local",
  "model": "qwen3:8b",
  "port": 11434,
  "timeout": 120,
  "audio_backend": "auto",
  "volume": 0.12,
  "duration_multiplier": 3,
  "text_encoding": "ct2",
  "personality_profile": "personality.json"
}
```

`duration_multiplier: 3` makes **every note and gap last three times as long as multiplier 1**. Frequencies do not change. Allowed range is 1–6. `volume` is separate, 0–0.3; begin at the default and adjust your speaker level comfortably. No sound-pressure level has been measured.

`text_encoding: "ct2"` enables the small stable dictionary. `"ct1"` selects the old byte encoding for comparison. The six exact legacy registered phrases retain their existing CSP rendering in either mode. CT2 reduces some text to useful words/phrases, but arbitrary English still falls back to literal UTF-8 chords. The display estimates the full playback duration before playback; long replies may take over a minute at 3×. No text is silently dropped, summarized or truncated to shorten the sound.

| Chat command | Result |
|---|---|
| `/dictionary` | Supported meanings, CSP token names and note patterns. |
| `/learn` | Set this session to multiplier 3, automatic English and token display. |
| `/tokens` | Last reply's supported tokens and explicitly labeled fallback spans. |
| `/word hello` or `/word thank you` | Play one exact lowercase dictionary entry through brain/safety. |
| `/replay` | Replay the entire last accepted reply at the current speed. |
| `/speed 1` or `/speed 3` | Set next playback duration multiplier without changing volume/pitch. |
| `/translate` | Decode the last deterministic representation and display its English. |
| `/auto` | Toggle automatic English; `/translate` still works. |
| `/mute`, `/unmute` | Stop/mute audio; unmute permits future playback and never replays by itself. |
| `/cancel` | Cancel inference and audio without latching stop. |
| `/stop`, `/reset` | Cancel, silence and latch stop; explicit reset allows new work, without replay. |
| `/status` | Brain state, mute, inference/render status and timing. |
| `/clear` | Clear RAM history/last translation and cancel work. Finished local WAV remains. |
| `/quit` or Ctrl+C | Stop and exit. |

Replay replaces previous playback; there is no growing speech queue. Speed changes affect the next playback, not a WAV already rendering. Word replay does not replace the last full reply or its translation. Automatic English is decoded from the representation and checked against model source text. It is **not microphone/acoustic decoding**, and playback API acceptance does not mean someone heard sound.

## 6. Real model and failures

Keep your already-working Ollama installation. Start it, then run `ollama list` to see downloaded models. Set `model` to the exact installed local model name; menu 1 checks it and rejects remote/cloud-backed model metadata. No download is attempted. Preserve the V1 recommendation to disable Ollama cloud (`OLLAMA_NO_CLOUD=1`, then restart Ollama); see [official FAQ](https://docs.ollama.com/faq). The app does not silently change that environment setting.

**Your previous first reply succeeded but a later turn caused a Windows VIDEO_TDR_FAILURE GPU-driver crash. Its underlying trigger is unresolved.** This upgrade does not claim to fix the driver, and model availability does not prove stability. First run menu 2/3/4. Review the [existing crash record](../test-plans/2026-10-03-conversational-brain-v1-qwen3-first-multiturn.md) before another real-model test. Killing Rocky's inference client does not guarantee Ollama has released GPU resources.

Malformed JSON/settings → read the field-specific error, edit and restart. No speakers/device error → confirm Windows output device; `--audio-backend wav` diagnoses synthesis without claiming audible playback. Provider timeout → input commands stay available; inspect model/runtime before retrying. Backend render/player error → stop latches; read the error, correct the device/problem and explicitly reset. Do not use “it worked” as proof of real-model, disconnected-internet, Pi or hardware acceptance.

See the [manual test checklist and observed results](../test-plans/rocky-desktop-v1-1.md). Your first Windows action after fetching the review branch is **double-click Rocky.bat, choose 7, then 8**; use **2** for the first conversation check.
