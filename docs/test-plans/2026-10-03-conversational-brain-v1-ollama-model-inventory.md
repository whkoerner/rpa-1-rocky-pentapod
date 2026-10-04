# Test Result: CV1-MODEL-001 — Ollama local model inventory

## Configuration

- Date/time: 2026-10-03; exact execution time UNKNOWN; timezone UTC-07:00.
- Operator: project owner/user.
- Local repository path: project root shown in PowerShell; account-specific path is redacted below.
- Local branch: UNKNOWN for this invocation. The immediately preceding captured test session showed `feat/rocky-conversation-v1`, but branch state was not re-queried here.
- Local commit: UNKNOWN for this invocation. The immediately preceding captured test session showed `2f6eae7cb3a17087ad1cd9d35bf4196367a889b1`; this model-inventory command did not re-run `git rev-parse HEAD`.
- Working tree status: UNKNOWN for this invocation.
- Operating system: UNKNOWN for this invocation; the immediately preceding test session recorded Windows 11 Home `10.0.26300` 64-bit.
- Python version: not exercised by this command.
- Runtime: Ollama CLI/local model inventory.
- Ollama version: UNKNOWN.
- Rocky runtime/model under test: not launched.
- Audio settings: not exercised.
- Translation mode: not exercised.
- Hardware/firmware/CAD/electronics revision: N/A for this inventory step.
- Test-plan source: `docs/build-guides/conversational-brain-v1-build.md`, which requires recording the installed model ID before manual real-model acceptance.

## Requirement under test

Purpose: capture the exact locally installed Ollama model tag and ID before real-model testing.

This inventory is prerequisite evidence only. It does not by itself verify real local AI conversation, response quality, model-backed memory, audio, translation, or offline behavior.

## Procedure deviations

- `ollama --version` was not captured.
- `ollama show qwen3:8b` was not run, so format/quantization details remain UNKNOWN.
- Git branch/commit and working-tree status were not re-queried in the same command.
- No inference request was sent.

## Raw evidence

### Exact command

```powershell
ollama list
```

### Exact observed output

```text
NAME         ID            SIZE    MODIFIED
qwen3:8b     500a1f067a9f  5.2 GB  39 hours ago
gemma4:26b   001e5dafc3c7  18 GB   40 hours ago
```

The relative `MODIFIED` values are preserved exactly as displayed and are not converted into inferred timestamps.

## Results

| Trial | Input | Expected | Observed | Result | Notes |
|---:|---|---|---|---|---|
| 1 | `ollama list` | Enumerate locally installed Ollama models and capture the exact model ID intended for V1 testing. | `qwen3:8b` ID `500a1f067a9f`, size `5.2 GB`; `gemma4:26b` ID `001e5dafc3c7`, size `18 GB`. | **PASS** | PASS applies only to model-inventory capture. No model inference was tested. |

## Faults, interventions, and near misses

No error was visible in the supplied terminal output.

A successful `ollama list` is not treated as proof that `qwen3:8b` can complete Rocky's structured conversation request, that the model is currently loaded, or that operation will succeed without internet access.

## Conclusion

- Overall result: **PASS**
- Supported claims:
  - Ollama reported `qwen3:8b` in the local model inventory with ID `500a1f067a9f` and displayed size `5.2 GB`.
  - Ollama reported `gemma4:26b` with ID `001e5dafc3c7` and displayed size `18 GB`.
  - The exact Qwen model ID required for the upcoming V1 manual test has been captured.
- Claims not supported:
  - Successful real-model inference through Rocky.
  - Qwen response quality, latency, memory behavior, or schema compatibility.
  - Model format or quantization.
  - Ollama version.
  - Audio/translation behavior.
  - Offline operation or proof that no network service was used.
  - Raspberry Pi suitability.
- Required changes: none.
- Next cheapest experiment: launch Rocky with `qwen3:8b` and perform the documented real-model multi-turn conversation while preserving exact prompts and replies.
