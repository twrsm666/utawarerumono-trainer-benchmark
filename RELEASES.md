# Releases

## v1.1-k31 — accepted benchmark artifact

GitHub release: `releases/tag/v1.1-k31`

Asset:

- `k31-trainer-v1.1.exe`
- Size: 36,407,921 bytes
- SHA-256: `fc56b3ca386e4823b0fe32ec11b3a957611ac3f094e592bdfaeea666380573da`
- SHA-1: not provided
- Built: 2026-11-11 from recovered final source; version 1.1.0 in the PE resource
- Runtime: Windows 10/11 x64, requires the exact 32-bit game build documented in the README

This is a **reproducible rebuild**, not a claim of bit-identical reproduction of the deleted 2026-11-08 binary.

### What the asset does

- Attaches to `Utawarerumono Mask of Deception.exe` with read/write process access.
- Reads 18 core character pages and validates the character-table shape.
- Edits 13 fields: level, current EXP, total EXP, BP, max/current HP, ATK, DEF, SPD, MOVE, JUMP, max/current zeal.
- Verifies reads/writes and supports explicit per-field locks.
- Does not alter the game executable or save files.

### Not included

- Game executable or any game asset.
- Save files.
- Qwen4's defective executable.
- Third-party trainer binaries or cheat tables.
- Raw private agent transcripts.

### Rejected artifacts

| Run | Original executable | SHA-256 | Status |
| --- | --- | --- | --- |
| Hy4 | none | n/a | no packaged deliverable |
| Qwen4 | 93,733,376 bytes | `4a6525a2c8657eb598cc18aa9b5ba5d005797ee428b9a55237b58427a3d2e4dd` | withheld; bad character mapping |
| K3.1 v1.0 (superseded) | 36,409,143 bytes | `90e94d8801efd72382d63db23fc8fafb1c5e86bd93c9e4ba3f40fa5bccf11273` | replaced after input-overwrite fix |

### Verify

```powershell
Get-FileHash .\k31-trainer-v1.1.exe -Algorithm SHA256
```

Expected:

```text
FC56B3CA386E4823B0FE32EC11B3A957611AC3F094E592BDFAEEA666380573DA
```

### Test evidence

- [test-results.txt](evidence/k31/test-results.txt)
- [packaged self-test](evidence/k31/packaged-smoke/packaged-smoke.txt)
- [UI screenshot](evidence/k31/ui.png)
- [source provenance](evidence/k31/source-provenance.json)
