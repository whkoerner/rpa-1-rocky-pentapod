# Rocky portability and provisioning v0

**Date:** 2026-10-05  
**Status:** Draft implementation on `feat/rocky-portability-v0`, stacked on Voice Input V0 PR #21.

## Goals

Portability V0 makes a Rocky installation easier to reproduce and move without pretending multi-gigabyte AI assets belong in Git or a tiny installer.

The package is split conceptually into:

```text
small Rocky source/bootstrap
+ Python environment created locally
+ user settings/personality/memory
+ explicitly provisioned external model/voice/STT assets
```

No virtual environment, model weight, OAuth token or API credential is committed or packed into the user backup.

## External asset manifest

`software/rocky/config/assets.example.json` defines schema `rocky-assets-v1`.

Supported asset kinds:

- `file`: a locally provisioned file such as whisper-cli or a Whisper model; when a path is configured, a SHA-256 checksum is mandatory and verified;
- `ollama_model`: a runtime-managed model identity such as `qwen3:8b`; recorded as a runtime reference and explicitly **not** claimed file-checksum verified;
- `windows_voice`: an installed local voice identity; recorded as a runtime reference.

Rocky does not download any asset while verifying the manifest.

An editable copy is created as `%USERPROFILE%\.rpa1\settings\assets.json` during normal Windows setup when it does not already exist.

## Portable user backup

`python -m rocky backup` or Windows menu option 11 creates a small ZIP containing only existing allowlisted user files:

- `settings/rocky.json`;
- active personality JSON or text;
- `memory/memory-v1.json`, when present.

The ZIP contains `manifest.json` with SHA-256 and byte size for every included file. Export immediately re-verifies the completed archive.

Deliberately excluded:

- model weights;
- voice/STT model files;
- `.venv` or other virtual environments;
- conversation WAV/log output;
- arbitrary neighboring files;
- OAuth/API credentials.

Backup sources are bounded and symbolic links are rejected. Archive verification rejects path traversal, duplicate/unlisted members, checksum/size mismatch and oversized archives.

This milestone verifies backups but does not automatically restore/overwrite a live profile. Safe restore/migration can be added separately after the export format has real user evidence.

## Windows launcher

Menu additions:

- **11 — Export portable user backup**
- **12 — Verify external asset manifest**

Setup creates the editable asset manifest without replacing an existing one.

## Portable configuration examples

The Pi-standalone and PC-assisted examples now follow current reviewed language/audio defaults:

- EXP-003;
- `vocal-v1`;
- duration multiplier 2;
- memory OFF;
- STT OFF;
- spoken English translation OFF on these pygame/Linux-oriented examples.

The hardware/model choice remains illustrative rather than a benchmark claim.

## Reproducibility boundary

File asset checksums prove the exact file bytes selected by the user. Runtime-managed Ollama/Windows voice references are listed as references, not falsely described as checksum verified. Rocky's normal provider checks remain responsible for confirming the selected Ollama model is local rather than remote/cloud-backed.

## Safe restore staging follow-up

Portable backup V0 now has an explicit **staging restore**, not an automatic live-profile overwrite.

`python -m rocky restore-backup --backup-input BACKUP.zip --restore-output NEW_DIR --restore-confirm`:

1. verifies the complete archive before extraction;
2. requires an explicit confirmation flag;
3. refuses any destination that already exists;
4. extracts only the already-allowlisted Rocky settings/personality/memory members into a newly created temporary staging directory;
5. rechecks size and SHA-256 after writing each staged file;
6. atomically renames the completed temporary directory into the requested new destination;
7. deletes the partial temporary directory on failure;
8. reports `live_profile_modified=False`.

The active Rocky settings, personality, and memory paths are never overwritten by the restore command. This deliberately keeps schema/config migration separate from archive extraction: the user can inspect a staged backup before deciding what to import.

Windows launcher option **17 — Verify and stage a portable backup restore** creates a new timestamped directory under `~/.rpa1/restore-staging`.

This is a safer foundation for future guided migrations than writing ZIP members directly into the live profile.
