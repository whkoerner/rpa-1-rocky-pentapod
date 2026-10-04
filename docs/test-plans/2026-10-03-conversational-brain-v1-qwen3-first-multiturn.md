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
- Computer RAM: later baseline capture reported approximately 31.43 GB physical RAM. GPU was later identified after reboot as NVIDIA GeForce RTX 5070 Ti Laptop GPU; see diagnostic follow-up.
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
- RAM/GPU utilization at failure: UNKNOWN. A later post-reboot GPU snapshot is recorded below and must not be substituted for crash-time utilization.
- Immediate failure mechanism: later WinDbg analysis establishes a Windows VIDEO_TDR_FAILURE in the NVIDIA display-driver recovery path; see diagnostic follow-up. Underlying/root trigger remains UNKNOWN. Do not attribute that trigger to Rocky, Ollama, Qwen, Python, a specific driver defect, GPU hardware, thermal limits, or memory exhaustion without further evidence.

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
  - Underlying trigger of the NVIDIA/Windows TDR failure.
  - Model format/quantization or Ollama version.
  - Acceptable RAM/GPU/thermal behavior.
  - Offline operation.
  - Raspberry Pi suitability.
- Acceptance status:
  - “Real local AI gives useful, original, multi-turn replies”: **FAIL** for this session because the second turn caused a full-system crash.
  - “Favorite-color recall succeeds within the session”: **NOT TESTED**.
- Required changes: none made; application repair is outside this documentation-only authorization.
- Next diagnostic step: inspect `server-1.log` and `app-1.log` for model, GPU, resource, and error lines before deciding on any Qwen3 8B retest.

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

## Diagnostic follow-up: GPU and display-driver snapshot

After reboot, the operator ran the requested GPU/driver inventory command.

### Exact diagnostic command

```powershell
Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,DriverDate,AdapterRAM; nvidia-smi
```

### Observed GPU/driver information

Windows/WMI reported:

```text
Name                               DriverVersion  DriverDate              AdapterRAM
Intel(R) Graphics                  32.0.101.8991  8/23/2026 5:00:00 PM   4293918720
NVIDIA GeForce RTX 5070 Ti Laptop GPU
                                   32.0.16.1062   6/10/2026 5:00:00 PM   4293918720
```

`nvidia-smi` reported at `Sat Oct 3 17:45:18 2026`:

```text
NVIDIA-SMI 610.62
KMD Version: 610.62
CUDA UMD Version: 13.3
GPU: NVIDIA GeForce RTX 5070 Ti Laptop GPU
Driver model: WDDM
Bus-Id: 00000000:01:00.0
Display active: On
Temperature: 50 C
Performance state: P5
Power: 20 W / 70 W
Memory usage: 2068 MiB / 12227 MiB
GPU utilization: 5%
Compute mode: Default
```

The process table showed many ordinary desktop processes using the GPU through Windows graphics, including ChatGPT, VS Code, Explorer, browser/WebView processes, NVIDIA Overlay, and other applications. Per-process GPU memory was displayed as `N/A` in this WDDM snapshot.

### Interpretation

- The discrete GPU is an **NVIDIA GeForce RTX 5070 Ti Laptop GPU**.
- The NVIDIA driver was reported as `610.62` by `nvidia-smi` and `32.0.16.1062` by Windows WMI. These are two representations of the installed driver stack, not two separately proven installed drivers.
- `nvidia-smi` reported approximately 12 GB of addressable GPU memory (`12227 MiB` total) in the post-reboot snapshot.
- WMI reported `AdapterRAM=4293918720` for both Intel and NVIDIA adapters. Because this conflicts with the NVIDIA-specific `12227 MiB` value, do not use the WMI AdapterRAM field as the authoritative VRAM capacity for this test.
- At the time of this **post-reboot diagnostic**, the NVIDIA GPU was at 50 C, 20 W of 70 W, 5% utilization, and 2068 MiB / 12227 MiB memory use.
- Those temperature, power, utilization, and memory values were collected after the crash and **must not be treated as measurements from the crash itself**.
- Combined with the earlier bugcheck `0x00000116` and the Windows note that `nvlddmkm.sys` was a possibly related driver, the environment evidence is consistent with a Windows/NVIDIA graphics timeout/crash path. It still does not prove whether the trigger was the driver, GPU hardware, model workload, another application, power/thermal behavior, or a software interaction.

### Updated next diagnostic step

Inspect the saved minidump `C:\Windows\Minidump\100326-20515-01.dmp` before another Qwen3 8B multi-turn run. Preserve the original failed session regardless of later retest outcome.

## Diagnostic follow-up: targeted crash-window event query

The operator then queried only the crash window for providers matching `Display`, `nvlddmkm`, `WHEA`, or `Kernel-Power`.

### Exact diagnostic command

```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=[datetime]'10/3/2026 5:30 PM'; EndTime=[datetime]'10/3/2026 5:41 PM'} | Where-Object {$_.ProviderName -match 'Display|nvlddmkm|WHEA|Kernel-Power'} | Select-Object TimeCreated,Id,LevelDisplayName,ProviderName,Message | Format-List
```

### Exact visible output

```text
TimeCreated      : 10/3/2026 5:40:12 PM
Id               : 521
LevelDisplayName : Information
ProviderName     : Microsoft-Windows-Kernel-Power
Message          : Active battery count change.

TimeCreated      : 10/3/2026 5:40:12 PM
Id               : 521
LevelDisplayName : Information
ProviderName     : Microsoft-Windows-Kernel-Power
Message          : Active battery count change.

TimeCreated      : 10/3/2026 5:40:06 PM
Id               : 41
LevelDisplayName : Critical
ProviderName     : Microsoft-Windows-Kernel-Power
Message          : The system has rebooted without cleanly shutting down first. This error could be caused if the system
                   stopped responding, crashed, or lost power unexpectedly.

TimeCreated      : 10/3/2026 5:40:06 PM
Id               : 125
LevelDisplayName : Information
ProviderName     : Microsoft-Windows-Kernel-Power
Message          : ACPI thermal zone \\_TZ.TZ01 has been enumerated.
                   _PSV = 0K
                   _TC1 = 2
                   _TC2 = 3
                   _TSP = 4000ms
                   _AC0 = 0K
                   _AC1 = 0K
                   _AC2 = 0K
                   _AC3 = 0K
                   _AC4 = 0K
                   _AC5 = 0K
                   _AC6 = 0K
                   _AC7 = 0K
                   _AC8 = 0K
                   _AC9 = 0K
                   _CRT = 393K
                   _HOT = 0K
                   minimum throttle = 0
                   _CR3 = 0K
```

The prompt returned after these entries. No visible `Display`, `nvlddmkm`, or `WHEA` provider entry appeared in this targeted result.

### Interpretation

- This filtered query corroborates the unclean restart through Kernel-Power event 41.
- It did **not** surface a separate Display, `nvlddmkm`, or WHEA event in the specified 5:30–5:41 PM window.
- Absence from this query does not disprove the earlier Windows Error Reporting record that named `nvlddmkm.sys` as a possibly related driver.
- The ACPI thermal-zone event is an enumeration record created during/after restart. Its `_CRT = 393K` value is a firmware critical-trip threshold (about 120 C), **not a measured crash-time temperature**. Do not use it as evidence that the machine reached 393 K.
- No crash-time GPU temperature, GPU utilization, GPU memory use, CPU temperature, or system RAM use has been recovered.
- Root cause remains **UNKNOWN**.

### Updated next diagnostic step

WinDbg is now installed; open the saved Windows minidump and run `!analyze -v` before another Qwen3 8B multi-turn run.

## Diagnostic follow-up: WinDbg installation

The operator installed Microsoft WinDbg to prepare for minidump analysis.

### Exact command

```powershell
winget install --id Microsoft.WinDbg -e
```

### Relevant observed output

```text
Found WinDbg [Microsoft.WinDbg] Version 1.2606.22001.0
Successfully verified installer hash
Starting package install...
100%
Successfully installed
```

The Microsoft Store source displayed its normal source-agreement prompt and the operator accepted it.

### Interpretation

- Microsoft WinDbg version `1.2606.22001.0` was successfully installed according to winget.
- Successful debugger installation does **not** analyze the crash and does not change the test result.
- Bugcheck root cause remains **UNKNOWN** until the saved dump is opened and analyzed.

### Updated next diagnostic step

Open `C:\Windows\Minidump\100326-20515-01.dmp` in WinDbg and run `!analyze -v`. Preserve the full analysis output, especially `BUGCHECK_CODE`, `MODULE_NAME`, `IMAGE_NAME`, `FAILURE_BUCKET_ID`, and stack information.

## Diagnostic follow-up: WinDbg `!analyze -v`

The operator opened `C:\Windows\Minidump\100326-20515-01.dmp` in WinDbg and ran `!analyze -v`.

### Key exact output

```text
VIDEO_TDR_FAILURE (116)
Attempt to reset the display driver and recover from timeout failed.

Arg1: ffffe18ec79701d0, Optional pointer to internal TDR recovery context (TDR_RECOVERY_CONTEXT).
Arg2: fffff80364198210, The pointer into responsible device driver module (e.g. owner tag).
Arg3: ffffffffc000009a, Optional error code (NTSTATUS) of the last failed operation.
Arg4: 0000000000000004, Optional internal context dependent data.

Unable to load image nvlddmkm.sys, Win32 error 0n2
*** WARNING: Unable to verify timestamp for nvlddmkm.sys

BUGCHECK_CODE:  116
FILE_IN_CAB:  100326-20515-01.dmp
DUMP_FILE_ATTRIBUTES: 0x21808
  Kernel Generated Triage Dump

PROCESS_NAME:  System

IP_IN_PAGED_CODE:
nvlddmkm+1958210

STACK_TEXT:
... nt!KeBugCheckEx
... dxgkrnl!TdrBugcheckOnTimeout+0x101
... dxgkrnl!ADAPTER_RENDER::Reset+0x12d
... dxgkrnl!DXGADAPTER::Reset+0x58a
... dxgkrnl!TdrResetFromTimeout+0x15
... dxgkrnl!TdrResetFromTimeoutWorkItem+0x22
... nt!ExpWorkerThread+0x3db
... nt!PspSystemThreadStartup+0x5a
... nt!KiStartSystemThread+0x34

SYMBOL_NAME:  nvlddmkm+1958210
MODULE_NAME:  nvlddmkm
IMAGE_NAME:  nvlddmkm.sys

FAILURE_BUCKET_ID:  0x116_IMAGE_nvlddmkm.sys
OSPLATFORM_TYPE:  x64
OSNAME:  Windows 10
Followup:  MachineOwner
```

The debugger also reported that it could not load/verify the `nvlddmkm.sys` image timestamp. That symbol/image limitation is preserved and means the dump should not be used to claim a verified NVIDIA binary timestamp from this analysis.

### Interpretation

- The minidump confirms **VIDEO_TDR_FAILURE (0x116)**.
- WinDbg's own description is: the attempt to reset the display driver and recover from a timeout failed.
- The stack shows Windows graphics-kernel TDR recovery functions (`dxgkrnl!TdrBugcheckOnTimeout`, adapter reset, and timeout-reset work item), rather than an application exception stack in Rocky/Python.
- The failing module/image identified by WinDbg is `nvlddmkm.sys`, with failure bucket `0x116_IMAGE_nvlddmkm.sys`.
- `PROCESS_NAME: System` means the bugcheck was recorded in the Windows System context; it does **not** identify Rocky, Python, or Ollama as the crashing process.
- `Arg3` was `0xffffffffc000009a`, which WinDbg labels as the optional NTSTATUS of the last failed operation. Its symbolic meaning has not yet been resolved in this record.
- The dump is a **Kernel Generated Triage Dump**, so it does not contain every possible crash-time measurement.
- The debugger displayed `OSNAME: Windows 10`; retain that as raw debugger output only. The separately captured host environment is Windows 11 Home, so this debugger label is not used to revise the recorded operating-system version.
- This analysis establishes the immediate failure path substantially better than the event logs: Windows graphics TDR recovery failed with `nvlddmkm.sys` identified in the failure bucket.
- The **underlying trigger remains UNKNOWN**. The dump does not by itself distinguish among an NVIDIA driver defect, GPU hardware instability, resource exhaustion, power/thermal conditions, workload interaction, or another cause that made the driver stop responding.

### Updated diagnostic status

- Immediate failure mechanism: **ESTABLISHED — Windows VIDEO_TDR_FAILURE during NVIDIA display-driver timeout recovery**.
- Underlying/root trigger: **UNKNOWN**.
- Rocky V1 multi-turn result: remains **FAIL**.
- No application code change is authorized or made by this test-history update.

### Updated next diagnostic step

Resolve bugcheck Arg3 `0xC000009A` in WinDbg before deciding whether to retest or change the local model/runtime.

## Diagnostic follow-up: decode bugcheck Arg3

The operator ran WinDbg's error decoder for the `Arg3` NTSTATUS reported by `!analyze -v`.

### Exact command

```text
!error c000009a
```

### Exact observed output

```text
Error code: (NTSTATUS) 0xc000009a (3221225626) - Insufficient system resources exist to complete the API.
```

### Interpretation

- Bugcheck Arg3 `0xC000009A` resolves to **“Insufficient system resources exist to complete the API.”**
- In the context of this dump, that status belongs to the last failed operation reported during the Windows/NVIDIA TDR recovery path.
- This strengthens a **resource-failure hypothesis during display-driver recovery**, but it does **not** identify which resource was insufficient.
- It does not, by itself, prove exhaustion of system RAM, committed virtual memory/pagefile, GPU VRAM, kernel pools, a driver-internal resource, or any other specific resource.
- No crash-time resource counters were captured, so ordinary RAM/VRAM exhaustion remains unverified.
- Immediate failure mechanism remains **ESTABLISHED — VIDEO_TDR_FAILURE (0x116) in the NVIDIA display-driver recovery path**.
- Underlying trigger remains **UNKNOWN**.

### Updated next diagnostic step

Capture installed physical memory and current pagefile/virtual-memory configuration before any real-model retest. This is environment evidence only; current free memory after reboot must not be treated as crash-time memory availability.

## Diagnostic follow-up: physical RAM and pagefile baseline

The operator reported the physical-memory value from the preceding memory command as:

```text
TotalPhysicalRAM_GB: 31.43
```

The operator then ran:

```powershell
Get-CimInstance Win32_PageFileUsage | Format-List Name,AllocatedBaseSize,CurrentUsage,PeakUsage
```

### Exact observed pagefile output

```text
Name              : C:\pagefile.sys
AllocatedBaseSize : 2048
CurrentUsage      : 42
PeakUsage         : 42
```

### Interpretation

- Installed/visible physical-memory baseline from the user-reported command output is approximately **31.43 GB**.
- The currently allocated Windows pagefile is **2048 MB (2 GB)** at `C:\pagefile.sys`.
- At the time of this **post-reboot diagnostic**, pagefile current usage and reported peak usage for the current boot/session were both **42 MB**.
- This post-reboot pagefile snapshot does **not** show current pagefile pressure.
- It also does **not** establish pagefile, physical-RAM, committed-memory, or VRAM usage at the time of the Qwen crash because those crash-time counters were not captured.
- The relatively small 2 GB pagefile is relevant configuration context for a dump whose TDR recovery Arg3 decoded to `STATUS_INSUFFICIENT_RESOURCES`, but this evidence is insufficient to conclude that pagefile sizing caused the crash.
- Immediate failure mechanism remains **VIDEO_TDR_FAILURE (0x116) in the NVIDIA display-driver recovery path**.
- Underlying trigger remains **UNKNOWN**.

### Updated next diagnostic step

Determine whether Windows is automatically managing the pagefile or whether the 2 GB pagefile is a fixed/manual configuration before considering any retest.

## Diagnostic follow-up: automatic pagefile management

The operator ran the pagefile-management query and reported:

```text
AutomaticManagedPagefile: True
```

The `Win32_PageFileSetting` values were not supplied, so `InitialSize` and `MaximumSize` remain UNKNOWN.

### Interpretation

- Windows automatic pagefile management is enabled.
- The previously observed `AllocatedBaseSize = 2048 MB` therefore must not be described as a user-fixed 2 GB pagefile cap based on the current evidence.
- Automatic management does not prove that the pagefile had already expanded, could expand quickly enough, or that committed-memory pressure was absent at crash time.
- The earlier `STATUS_INSUFFICIENT_RESOURCES (0xC000009A)` remains a resource-failure signal during TDR recovery, but the specific insufficient resource remains UNKNOWN.
- Immediate failure mechanism remains **VIDEO_TDR_FAILURE (0x116) in the NVIDIA display-driver recovery path**.
- Underlying trigger remains **UNKNOWN**.

### Updated next diagnostic step

Check the crash window for Windows Resource-Exhaustion-Detector events before any real-model retest.

## Diagnostic follow-up: Resource-Exhaustion/Memory event query

The operator ran:

```powershell
Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=[datetime]'10/3/2026 5:30 PM'; EndTime=[datetime]'10/3/2026 5:41 PM'} | Where-Object {$_.ProviderName -match 'Resource-Exhaustion|Memory'} | Select-Object TimeCreated,Id,ProviderName,Message | Format-List
```

### Observed result

No output was returned.

### Interpretation

- No System-log event whose provider name matched `Resource-Exhaustion` or `Memory` was returned for the queried 5:30–5:41 PM crash window.
- This is useful negative evidence: Windows did not surface an obvious matching resource-exhaustion event through this query.
- It does **not** negate WinDbg's decoded `0xC000009A` status: **“Insufficient system resources exist to complete the API.”**
- It also does not prove that RAM, commit, VRAM, kernel pools, or driver-internal resources were healthy at the instant of the crash.
- Immediate failure mechanism remains **VIDEO_TDR_FAILURE (0x116) in the NVIDIA display-driver recovery path**.
- Underlying trigger remains **UNKNOWN**.

### Updated next diagnostic step

Inspect Ollama's own logs around the failed run before choosing a lower-risk real-model retest.

## Diagnostic follow-up: Ollama log inventory

The operator listed files under `$env:LOCALAPPDATA\Ollama` after the crash/reboot.

### Exact command

```powershell
Get-ChildItem "$env:LOCALAPPDATA\Ollama" -File | Sort-Object LastWriteTime -Descending | Select-Object Name,LastWriteTime,Length
```

### Relevant observed output

```text
Name            LastWriteTime              Length
ollama.pid      10/3/2026 5:41:27 PM       4
server.log      10/3/2026 5:41:26 PM       0
db.sqlite-shm   10/3/2026 5:41:26 PM       32768
app.log         10/3/2026 5:41:26 PM       0
app-1.log       10/3/2026 4:42:04 PM       10484
server-1.log    10/3/2026 4:42:04 PM       23373
server-2.log    10/3/2026 4:42:04 PM       0
db.sqlite-wal   10/3/2026 4:42:04 PM       177192
server-3.log    10/3/2026 4:42:04 PM       6174
server-4.log    10/3/2026 3:17:47 PM       3037
app-3.log       10/3/2026 3:17:46 PM       861
server-5.log    10/2/2026 3:08:31 PM       2679
app-4.log       10/2/2026 3:08:18 PM       598
upgrade.log     10/2/2026 3:08:15 PM       422903
app-5.log       10/2/2026 3:07:11 PM       1329
db.sqlite       10/2/2026 1:40:33 AM       4096
```

### Interpretation

- The current `server.log` and `app.log` were created/updated after reboot at about 5:41 PM and were both **0 bytes** in this inventory.
- The immediately previous nonempty rotated logs are `server-1.log` (23,373 bytes) and `app-1.log` (10,484 bytes), both with `LastWriteTime` 4:42:04 PM.
- That timestamp is earlier than the approximately 5:34 PM crash. File modification time alone does not establish whether those files contain the failed request, because logging may be buffered, sparse, rotated, or not emit per-request lines.
- The existence of a new `ollama.pid` at 5:41:27 PM is consistent with Ollama having restarted after the system reboot, but this inventory does not prove the exact pre-crash Ollama process lifetime.
- No Ollama error, CUDA error, model unload, allocation failure, or request failure is established by this file listing alone.
- Immediate Windows failure mechanism remains **VIDEO_TDR_FAILURE (0x116) in the NVIDIA display-driver recovery path**; underlying trigger remains **UNKNOWN**.

### Updated next diagnostic step

Inspect the nonempty rotated Ollama logs for model/GPU/resource/error lines before any real-model retest.
