# Test Result: CV1-QWEN-001 — Qwen3 real-model first-turn and multi-turn stability

## Configuration

- Date/time: 2026-10-03; exact execution time UNKNOWN; timezone UTC-07:00.
- Operator: project owner/user.
- Launch command from the prescribed test procedure:
  `.\.venv-rocky\Scripts\python.exe -m rocky --provider local --model qwen3:8b`
- Local branch: UNKNOWN for this invocation. The last directly captured branch earlier in the same test session was `feat/rocky-conversation-v1`.
- Local commit: UNKNOWN for this invocation. The last directly captured local HEAD earlier in the same test session was `2f6eae7cb3a17087ad1cd9d35bf4196367a889b1`; later GitHub documentation commits must not be treated as the version run locally.
- Working tree: UNKNOWN for this invocation. The earlier captured state was dirty.
- Operating system: not re-queried during this invocation. The immediately preceding environment record captured Microsoft Windows 11 Home `10.0.26300`, 64-bit.
- Python: not re-queried during this invocation. The immediately preceding environment record captured Python `3.13.16`.
- Runtime/provider: Rocky Conversational Brain V1 with local Ollama provider.
- Requested model tag: `qwen3:8b`.
- Pre-test Ollama inventory: `qwen3:8b` was listed with ID `500a1f067a9f` and displayed size `5.2 GB`. The ID was not re-read during the inference invocation.
- Ollama version: UNKNOWN.
- Model format/quantization: UNKNOWN.
- Audio backend: not captured in the user report for this invocation.
- Digital volume: no per-run override was prescribed; the most recently observed tracked configuration used `0.12`.
- Translation mode: automatic English display was expected from the V1 default but was not explicitly recorded in the supplied evidence.
- Audio speed: no configurable speed value was recorded; user reported the tones were still too fast.
- Computer RAM/GPU: UNKNOWN.
- Test-plan source: `docs/build-guides/conversational-brain-v1-build.md`, real-model first conversation and acceptance checklist.
- Safety controls/exclusion zone: no actuators or physical robot hardware were involved.

## Requirement under test

Relevant Conversational Brain V1 acceptance criteria:

- Real local AI gives useful, original, multi-turn replies.
- Favorite-color recall succeeds within the session.
- Record actual model behavior and any delay before calling V1 VERIFIED.

The first-turn result is supporting evidence for real-model inference and response quality. The overall multi-turn criterion is **not verified** because the computer crashed during the second turn before any second response was produced.

## Procedure deviations

- Exact terminal text from the real-model replies was not supplied, so no model answer is reconstructed or paraphrased as if it were raw output.
- Exact inference duration was not measured with a timer. The user reported the first response took “30+ seconds to load.”
- Branch, commit, OS, Python version, Ollama version, RAM, GPU, backend, and working-tree status were not re-collected in the same invocation.
- The intended third prompt was never reached because the system crashed on the second turn.

## Raw evidence

### Prescribed launch command

```powershell
.\.venv-rocky\Scripts\python.exe -m rocky --provider local --model qwen3:8b
```

### Test inputs

The user described “first response” and “second response” immediately after running the three-message procedure supplied for this test. The corresponding prescribed inputs were:

```text
Hello Rocky. How are you?
My favorite color is blue.
What color did I tell you I liked?
```

Only the first two were reached. The third was not tested.

### User-reported observations

> “First response worked, took 30+ seconds to load though, still too fast for tones. Responded well. Second response froze the laptop then the whole computer crashed. No respond was given.”

This is user-reported observational evidence. No exact first model reply text, stack trace, Windows event log, Ollama log, memory reading, temperature, or GPU-driver error was supplied.

## Results

| Trial | Input | Expected | Observed | Result | Notes |
|---:|---|---|---|---|---|
| 1 | `Hello Rocky. How are you?` | Real local model returns a useful reply; reply can be delivered through the V1 conversation/audio path. | User reported the first response worked, responded well, took more than 30 seconds to load, and produced tones that were still too fast. | **PASS** for first-turn real-model response; performance **PARTIAL** | Exact reply text and measured latency are unavailable. The tone-speed comment is subjective user feedback. |
| 2 | `My favorite color is blue.` | Model returns a second reply and session continues without destabilizing the computer. | User reported the laptop froze and the entire computer crashed. No response was produced. | **FAIL** | Full-system failure prevented continuation. Cause is UNKNOWN. |
| 3 | `What color did I tell you I liked?` | Model recalls the color from prior session history. | Not reached because the computer crashed during Trial 2. | **NOT TESTED** | Favorite-color recall remains unverified. |

## Faults, interventions, and near misses

### Full-system crash during second real-model turn

- Severity: high for desktop usability/reliability testing.
- Observed behavior: laptop froze, then the whole computer crashed.
- Application response: none was observed for the second prompt.
- Terminal error text: UNKNOWN; the later Windows System log recorded a bugcheck and saved a minidump.
- Windows event evidence: collected after reboot; see diagnostic follow-up below.
- Ollama/runtime log evidence: not yet collected.
- RAM/GPU utilization at failure: UNKNOWN.
- Root cause: UNKNOWN. Do not attribute the crash to Rocky, Ollama, Qwen, Python, GPU drivers, thermal limits, or memory exhaustion without diagnostic evidence.

The initial successful turn must be retained even though the later turn failed. Likewise, the failure must remain in history if a later retest passes.

### Audio/user-experience observation

The user again reported the tones were too fast. The first reply's content quality was reported positively (“Responded well”). These are user-reported qualitative observations. No code or timing change is authorized by this test-record task.

## Conclusion

- Overall result: **FAIL**
- Supported claims:
  - A real `qwen3:8b` request produced at least one successful first-turn response through the tested Rocky V1 session.
  - The user judged that first response positively.
  - The first response took more than 30 seconds by user observation; no exact latency measurement is available.
  - Audible tones were produced for the successful turn, and the user considered them too fast.
  - The second prompt did not receive a response because the laptop froze and the entire computer crashed.
- Claims not supported:
  - Stable multi-turn real-model conversation.
  - Favorite-color memory/recall.
  - Exact response latency.
  - Exact first model reply content.
  - Cause of the system crash.
  - Model format/quantization or Ollama version.
  - Acceptable RAM/GPU/thermal behavior.
  - Offline operation.
  - Raspberry Pi suitability.
- Acceptance status:
  - “Real local AI gives useful, original, multi-turn replies”: **FAIL** for this session because the second turn caused a full-system crash.
  - “Favorite-color recall succeeds within the session”: **NOT TESTED**.
- Required changes: none made; application repair is outside this documentation-only authorization.
- Next diagnostic step: collect GPU identity and display-driver version, then analyze the saved minidump before attempting another heavy real-model retest.

## Diagnostic follow-up: Windows crash events

After reboot, the operator ran the requested Windows System event query. The supplied output provides direct OS-level evidence that the failure was a Windows bugcheck rather than only an application hang.

### Exact diagnostic command

```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=(Get-Date).AddHours(-3); Level=1,2} | Select-Object -First 25 TimeCreated,Id,ProviderName,Message | Format-List
```

### Relevant observed events

```text
TimeCreated  : 10/3/2026 5:40:19 PM
Id           : 1019
ProviderName : Microsoft-Windows-WER-SystemErrorReporting
Message      : The computer has rebooted from a bugcheck. Possibly related driver: nvlddmkm.sys.

TimeCreated  : 10/3/2026 5:40:19 PM
Id           : 1001
ProviderName : Microsoft-Windows-WER-SystemErrorReporting
Message      : The computer has rebooted from a bugcheck. The bugcheck was: 0x00000116 (...). A dump was saved in:
               C:\Windows\Minidump\100326-20515-01.dmp.

TimeCreated  : 10/3/2026 5:40:06 PM
Id           : 41
ProviderName : Microsoft-Windows-Kernel-Power
Message      : The system has rebooted without cleanly shutting down first. This error could be caused if the system stopped
               responding, crashed, or lost power unexpectedly.

TimeCreated  : 10/3/2026 5:40:02 PM
Id           : 162
ProviderName : volmgr
Message      : Dump file generation succeeded.

TimeCreated  : 10/3/2026 5:40:22 PM
Id           : 6008
ProviderName : EventLog
Message      : The previous system shutdown at 5:34:47 PM on 10/3/2026 was unexpected.
```

The screenshot also showed DistributedCOM, Wi-Fi Direct virtual-adapter, BitLocker, and Epic Online Services errors at earlier times. They are preserved as observed background events but are not treated as causal for the 5:34:47 PM crash.

### Interpretation

- Windows recorded bugcheck `0x00000116`.
- Windows Error Reporting explicitly named `nvlddmkm.sys` as a **possibly related driver**.
- A minidump was successfully written to `C:\Windows\Minidump\100326-20515-01.dmp`.
- Kernel-Power 41 and EventLog 6008 corroborate an unclean system failure/restart.
- These events strengthen the evidence that the second Qwen turn coincided with a system-level graphics/driver failure path.
- They do **not** prove that Rocky, Ollama, Qwen3, the NVIDIA driver, GPU hardware, thermals, or memory pressure was the root cause. Root cause remains **UNKNOWN** until the dump and hardware/driver state are analyzed.

### Updated next diagnostic step

Collect the installed GPU identity and display-driver version before any further real-model retest. Do not overwrite this failure if a later driver update or smaller-model retest passes.
