# Results

## Summary

| Run | Wall clock | Human turns | Tool calls | Delivered | Verdict |
| --- | ---: | ---: | ---: | --- | --- |
| Hy4 | 81.97 min | 4 | 182 | 7-file Python/HTML source, no EXE | Fail |
| K3.1 | 30.09 min to first EXE; 3.67 min fix | 3 in the initial task window | 117 in the initial task window | Rebuilt Windows EXE, source, tests | Pass |
| Qwen4 | 71.57 min artifact window | Unknown | Unknown | 93.7 MB save editor EXE, source | Fail on identity mapping |

Machine-readable metrics: [session-metrics.json](../evidence/session-metrics.json).

## Hy4

### Delivered

- `utawa_trainer.py` (47,018 bytes)
- `unit_table.py` (8,293 bytes)
- `index.html` (65,266 bytes)
- `verify_checksum.py` (1,618 bytes)
- launch scripts and README

No `.exe`, installer, or single-command build path was delivered.

### Acceptance

| Check | Result | Evidence |
| --- | :---: | --- |
| A1 standalone executable | FAIL | no executable in artifact tree |
| A2 per-character pages | FAIL | final product requires a manual value-change scan/filter workflow |
| A3 correct identity | FAIL | final reply admits template values were presented as runtime character state |
| A4 correct values | FAIL | final reply: values do not match the game |
| A5 faithful writes | Not accepted | no reliable fixed character object was established |
| A6 safe boundaries | Uncontested | source is non-destructive by design |
| A7 packaging | FAIL | no executable |

### Technical conclusion

Hy4 found and packaged static `UnitData.bin` data, then treated it as runtime state. After user feedback, it replaced named fixed pages with a live scanner that requires the user to change a value in game and filter candidates. That is a different product and still not the requested direct per-character editor.

Hy4's own final response is preserved at [evidence/hy4/final-response.md](../evidence/hy4/final-response.md).

## K3.1

### Delivered

- Windows one-file executable (`k31-trainer-v1.1.exe`).
- Source for process attachment, character parsing, UI, write verification, locks, tests, and packaging.
- 18 character pages.
- 13 editable fields per page.

### Acceptance

| Check | Result | Evidence |
| --- | :---: | --- |
| A1 standalone executable | PASS | packaged self-test exit 0 |
| A2 per-character pages | PASS | 18 pages, 13 fields each |
| A3 correct identity | PASS | expected unit-ID sequence matched 18/18 |
| A4 correct values | PASS | read-only runtime snapshot matched the accepted build's field layout |
| A5 faithful writes | PASS | BP `31 → 32 → 31`; read-back verification after each write |
| A6 safe boundaries | PASS | no game file or save-file writes; memory only |
| A7 packaging | PASS | `status=OK`, `pages=18`, `fields=13` |

The first build had a real UI defect: a 1.5 s automatic refresh could overwrite typed input before the spin box committed it. The final version removes automatic refresh, marks text edits immediately, preserves focused/dirty rows, and supports Enter-to-write. See [K31_ACCEPTANCE.md](K31_ACCEPTANCE.md).

### Technical conclusion

The accepted tool reads a stable, validated character table at module base + `0x6CE4A4`. It uses a record stride of `0x278`, verifies character ID and team before each write, and reads back every written field. The Windows executable passed an independent launch and read smoke test.

## Qwen4

### Delivered

- A 93,733,376-byte Node single-executable save editor.
- JavaScript implementation of save checksum, character parsing, edit UI, backup, and restore.
- Nine product files and a large analysis workspace.

### Acceptance

| Check | Result | Evidence |
| --- | :---: | --- |
| A1 standalone executable | PASS | executable exists; process started |
| A2 per-character pages | PARTIAL | 18 rows exist, but page identity is wrong |
| A3 correct identity | FAIL | 0/18 names match their same-slot character; 18/18 IDs equal the next slot's ID |
| A4 correct values | FAIL for user intent | 108/108 sampled numeric fields match the same slot but are shown under the next character's name; several field labels are also wrong |
| A5 faithful writes | NOT TESTED | not safe to write a real save after identity mapping failed |
| A6 safe boundaries | PARTIAL | backup exists, but semantic corruption is possible |
| A7 packaging | PASS | standalone EXE produced |

### What looked correct

- Save checksum validation returned `valid: true`.
- The editor produced 18 rows.
- Six core numeric fields matched the live game state by slot.

### What made it unusable

- Every row's unit ID was taken from the wrong location and rotated one slot.
- Thus, a user opening "Kuon" saw Haku's level, EXP, ATK, DEF, MOVE, and JUMP.
- `SP` matched the runtime max-HP field; `Hit` matched runtime speed. The labels do not describe the values.
- Because the user edits by character name, writing through this UI would apply values to the wrong save record.

Detailed numbers: [QWEN4_ANALYSIS.md](QWEN4_ANALYSIS.md).

## Cross-case conclusion

For this single task and acceptance contract:

- Hy4 spent the longest and did not deliver a stable named-character editor.
- The K3.1-labeled session delivered a working executable in about 30 minutes, followed by a small input-handling fix.
- Qwen4 delivered a polished-looking save editor whose character-to-data mapping is systematically wrong.

This ordering is **not** a general capability ranking. The runs had different prompts, tool availability, human steering, and model fallback conditions.
