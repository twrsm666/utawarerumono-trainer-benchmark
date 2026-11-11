# Qwen4 analysis: a one-slot character mapping error

## Artifact under test

- Session label: **Qwen4**
- Platform: Qoder
- Artifact directory: `2026-11-11/dd671415/trainer`
- Product: Node.js local web UI plus a 93,733,376-byte Windows single executable
- Original executable SHA-256: `4a6525a2c8657eb598cc18aa9b5ba5d005797ee428b9a55237b58427a3d2e4dd`
- Save checksum check: valid
- Public source snapshot: [artifacts/qwen4](../artifacts/qwen4/)
- Runtime comparison: [evidence/qwen4/comparison.json](../evidence/qwen4/comparison.json)

The executable is not redistributed. It embeds a local username path and is a save-file writer with a known bad mapping.

## What the tool does

Qwen4 chose a save-file editor rather than live process editing. Its character parser is in `saveengine.js`:

```js
const CHAR_BASE = 0xa4f8;      // character array start
const CHAR_STRIDE = 0x278;     // record size
const CHAR_SLOTS = 24;

const unitId = buf.readUInt32LE(off + 0x270);
const level = buf.readUInt16LE(off);
const hp = buf.readUInt32LE(off + 8);
```

Field definitions map `level` to `+0x00`, `exp` to `+0x02`, `hp` to `+0x08`, `sp` to `+0x0C`, `atk` to `+0x10`, `def` to `+0x12`, `hit` to `+0x14`, `avoid` to `+0x16`, `move` to `+0x18`, and `jump` to `+0x1A`.

The checksum code and backup path are technically coherent: checksum verification returned `valid: true`, and the tool preserves the original save before an edit. Those facts do not validate the character semantics.

## Reproduction

The game was running with the Qwen4 editor listening at `127.0.0.1:8765`. The audit:

1. Requested Qwen4's parsed save slot 10 with GET only.
2. Read the live 18-slot character table with `ReadProcessMemory`.
3. Compared each Qwen4 row to the same index and to the next index.
4. Wrote no memory and no save file.

Script: [scripts/capture_runtime_comparison.py](../scripts/capture_runtime_comparison.py).

## Result

| Metric | Result |
| --- | ---: |
| Qwen4 character rows | 18 |
| Qwen4 name matches actual same-slot character | **0 / 18** |
| Qwen4 unit ID equals next slot's actual unit ID | **18 / 18** |
| Level/EXP/ATK/DEF/MOVE/JUMP matches actual same slot | **108 / 108** |
| Save checksum valid | yes |

In other words, the numeric data was not random. Qwen4 read Haku's progression and displayed it under Kuon's name; it read Kuon's progression and displayed it under Maroro's name, and so on through all 18 slots.

## Representative rows

| Qwen4 page | Qwen4 level / EXP / ATK / DEF / MOVE / JUMP | Actual same-slot character | Actual values | Interpretation |
| --- | --- | --- | --- | --- |
| 久遠 | 14 / 68 / 24 / 23 / 4 / 1 | Haku | 14 / 68 / 24 / 23 / 4 / 1 | Haku's values under Kuon's name |
| 麻呂呂 | 14 / 8 / 30 / 25 / 4 / 2 | Kuon | 14 / 8 / 30 / 25 / 4 / 2 | Kuon's values under Maroro's name |
| 露露緹耶 | 5 / 30 / 24 / 15 / 3 / 1 | Maroro | 5 / 30 / 24 / 15 / 3 / 1 | Maroro's values under Rulutieh's name |
| 哈克（最后一行） | 1 / 0 / 19 / 16 / 4 / 1 | Sasara (slot 17) | 1 / 0 / 19 / 16 / 4 / 1 | Sasara's values under Haku's name |

The full 18-row table is in [comparison.csv](../evidence/qwen4/comparison.csv).

## Secondary semantic errors

Even if the names were fixed, several labels would still be wrong:

- Qwen4's `sp` at `+0x0C` equals the runtime max-HP value used in this test. For example, Qwen4 shows `SP=223` for the Haku row, while the live Haku `max_hp` is 223.
- Qwen4's `hit` at `+0x14` equals runtime speed. The Haku row shows `hit=100`, and live Haku speed is 100.
- Qwen4's `hp` at `+0x08` is not the runtime max-HP field used by the accepted tool (`+0x88`). This audit does not assert what that save field means.

The core failure is therefore not a single mistyped offset: the unit identity and several display labels form an inconsistent save-layout model.

## Why the checksum did not catch it

A checksum validates file integrity, not semantics. Qwen4's computed checksum matched the header, so the file was structurally intact while the editor still associated the values with the wrong character IDs.

## Why no write test was performed

Qwen4 exposes a POST endpoint that rewrites the selected save and recomputes its checksum. Because the same-slot values were already assigned to the wrong character name, writing through the UI would modify another character's record under a misleading label. The audit stopped at read-only evidence.

This is not a claim that every write would corrupt the file. It is a refusal to perform an unnecessary destructive test after a semantic mapping failure had been demonstrated.

## Rejected evidence

Qwen4's `_analysis` directory contains extracted `NameTextData.bin`, `UnitTextData.bin`, disassembly, and save backups. Those are not published because they contain game-derived data, private save content, or both. Their presence and hashes are recorded in [artifact-inventory.json](../evidence/qwen4/artifact-inventory.json).

## Conclusion

For the requested product, Qwen4's result is unusable for a precise reason: **the per-character pages map each character's real values to the next character's identity.** A user editing “Kuon” would actually be editing Haku's record. The UI looks complete, and the checksum is valid, but the character semantics are wrong.
