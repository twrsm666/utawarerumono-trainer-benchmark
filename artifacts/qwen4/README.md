# Qwen4 rejected save editor

Status: **rejected for the requested product.**

> Do not use this source snapshot on a real save file. Its character-to-ID mapping is demonstrably wrong. The original executable is intentionally not redistributed.

## Why it is here

The source is retained to make the failure reproducible and reviewable. It implements:

- save-header checksum verification and recomputation;
- character-row parsing;
- a local web UI;
- save backup and restore;
- single-executable packaging.

## What failed

The same-slot numeric data is correct, but every character ID/name is taken from the next slot:

- 0/18 names match the actual same-slot character;
- 18/18 IDs equal the next slot's ID;
- 108/108 sampled numeric fields belong to the same slot.

The result is a polished editor that changes the wrong character's values under a familiar name. See [../../docs/QWEN4_ANALYSIS.md](../../docs/QWEN4_ANALYSIS.md).

## Snapshot contents

`save-editor-source/` contains the product source files:

- `saveengine.js`
- `server.js`
- `trainer-sea.js`
- `trainer-bundle.js`
- `build_exe.js`
- `sea-config.json`
- `unit_names.json`
- `ui-index.html`
- `启动修改器.bat`

The following were deliberately excluded:

- save files and save backups;
- extracted `NameTextData.bin`, `UnitTextData.bin`, and game data;
- analysis disassembly dumps;
- `trainer.blob`;
- the 93,733,376-byte executable, which embeds a local user path.

## Sanitization

The source snapshot replaces local paths with `<USER_HOME>`. It is not runnable in place until a tester supplies a local save directory. The original artifact inventory and hashes are in [../../evidence/qwen4/artifact-inventory.json](../../evidence/qwen4/artifact-inventory.json).

## Original executable

- Size: 93,733,376 bytes
- SHA-256: `4a6525a2c8657eb598cc18aa9b5ba5d005797ee428b9a55237b58427a3d2e4dd`

The binary is withheld for privacy and safety, not because it is unavailable to the operator.
