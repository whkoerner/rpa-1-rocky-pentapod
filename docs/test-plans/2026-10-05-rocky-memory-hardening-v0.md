# Rocky Memory hardening V0 — test evidence

**Date:** 2026-10-05  
**Branch:** `feat/rocky-memory-hardening-v0`  
**Base:** active translation acceptance stacked head

## Runtime hardening

Memory remains opt-in, user-statement-only, bounded, inspectable, editable, deletable, and outside model write authority.

This follow-up tightens the local file boundary:

- existing memory path must be a regular non-symlink file;
- immediate memory parent directory must not be a symlink during writes;
- writes use an OS-created unpredictable temporary file in the same directory;
- temporary output is flushed and fsync is attempted before atomic replace;
- a symlink appearing at the target before replace fails closed;
- temporary files are cleaned after success/failure.

## Automated cases

- disabled memory cannot be written;
- save/reopen/update/forget/clear;
- 512-byte value bound;
- case-insensitive key update remains one logical memory;
- duplicate case-colliding file rows rejected;
- secret-like keys/control characters rejected;
- unsupported provenance rejected;
- unsupported schema version rejected;
- file symlink rejected where supported;
- stored prompt injection remains JSON data below the hard-coded safety constitution;
- portable backup can be verified/staged without overwriting live memory.

## Schema migration

Memory schema V1 is the first committed persistent schema. There is no legitimate V0 file format to migrate. Unknown versions therefore remain fail-closed until a real schema transition is designed with explicit one-way migration and fixtures from actual old data.

## Manual NOT RUN

- enable memory on the user's Windows PC;
- save a real fact;
- restart Rocky and retrieve it through the real local model;
- edit/delete/clear through the real UI;
- stage a real backup and manually import memory;
- future real schema migration.
