# K3.1 acceptance record

## Scope

This document records the accepted implementation and the independent rebuild performed for publication. "Accepted" means it satisfies this task's acceptance contract, not that it is universally correct for every build or save state.

## Environment

| Item | Value |
| --- | --- |
| OS | Windows 11, build 10.0.26200 |
| Python | 3.13.14, 64-bit |
| UI | PySide6 6.12.0 |
| Packager | PyInstaller 6.22.3 |
| Game | `Utawarerumono Mask of Deception.exe` |
| Game PE | 32-bit, 6,130,176 bytes |
| Game MD5 | `c02107b577a8e3be7965b5b50594abfc` |
| Output | `k31-trainer-v1.1.exe`, one-file Windows GUI |
| Rebuilt release SHA-256 | `fc56b3ca386e4823b0fe32ec11b3a957611ac3f094e592bdfaeea666380573da` |

## Runtime model

The accepted tool reads a stable character table from the running 32-bit process:

- Character table RVA: `0x6CE4A4`
- Record stride: `0x278`
- Core player slots: 18; reserved player/guest slots are scanned up to 30
- Team field: `+0x12C` (`1` for player side)

Verified field offsets:

| Field | Offset | Type |
| --- | ---: | --- |
| Unit ID | `0x74` | u16 |
| Level | `0x7C` | u16 |
| Current EXP | `0x7E` | u16 |
| Max zeal | `0x80` | u32 |
| Total EXP | `0x84` | u32 |
| Max HP | `0x88` | u32 |
| ATK | `0x8C` | u16 |
| DEF | `0x8E` | u16 |
| SPD | `0x90` | u16 |
| MOVE | `0x94` | u16 |
| JUMP | `0x96` | u16 |
| BP | `0xA8` | u16 |
| Current HP | `0xB8` | u32 |
| Current zeal | `0xBC` | u32 |

The tool verifies the known unit-ID sequence at connection time. It also rereads each character's unit ID and team before every write, then reads back every written value.

## UI behavior

- One direct page per character.
- 13 editable fields per page.
- Per-row write, whole-page write, per-row lock, heal-all, and all-BP shortcuts.
- No automatic refresh during editing.
- Typed text is marked dirty immediately.
- Enter writes the current field.
- Lock writes the selected value every 500 ms.

## Defect found in v1.0

The first packaged build used a 1.5 s UI refresh. `QSpinBox` had keyboard tracking disabled, so typed text that had not yet been committed did not emit `valueChanged`; the refresh replaced it with the old value.

Timeline:

- First EXE: 18:33:45.
- User report: 18:37:02.
- Fixed EXE: 18:40:42.
- Fix time: 3.67 minutes.

Fix:

- Removed the automatic refresh timer.
- Bound `QLineEdit.textEdited` to mark a field dirty immediately.
- Skipped refresh for focused, dirty, or locked fields.
- Called `interpretText()` before writing.
- Added Enter-to-write.
- Kept a manual refresh button that still preserves pending edits.

This defect is included because omitting it would make the acceptance record less credible. It was real, reproduced, fixed, and retested.

## Automated checks

### Structural tests

Command:

```powershell
python -m unittest discover -s tests -p "test_core.py" -v
```

Result: **5/5 passed**, including live process attachment, character-table parse, field bounds, and expected roster order.

### UI smoke test

Command:

```powershell
python tests/ui_smoke_test.py
```

Result:

```text
UI_TEST_OK pages=18 fields=13
```

The test reproduces the important editing case: type `300` without committing, trigger refresh, and verify the text remains `300`; then verify the entered value can be committed.

### Live write/read/restore

Command:

```powershell
python tests/live_write_test.py
```

Observed during the publication audit:

```text
LIVE_WRITE_OK name=哈克 original_bp=31 test_bp=32 restored_bp=31
```

This is a real process write followed by a read-back, then a separate restore.

### Packaged executable

Command:

```powershell
k31-trainer-v1.1.exe --self-test
```

Observed:

```text
status=OK
pages=18
fields=13
pid=<current game process>
```

Screenshot: [ui.png](../evidence/k31/ui.png). Raw smoke output: [evidence/k31/packaged-smoke](../evidence/k31/packaged-smoke/).

## Provenance and rebuild

The working tree was deleted during an earlier cleanup. Final source versions were recovered from the agent platform's file-history store:

- `app.py` v5, 30,413 bytes
- `game_memory.py` v2, 15,079 bytes
- `build.py` v3, 3,817 bytes
- tests and `tools/recon.py`

Those files were copied into [artifacts/k31/trainer-source](../artifacts/k31/trainer-source/), compiled, tested against the running game, and packaged into the release asset on 2026-11-11. The release is therefore a **reproducible rebuild**. It is not claimed to be byte-identical to the deleted 2026-11-08 binary.

The superseded v1.0 binary is not published. Its SHA-256 is recorded in the artifact checksums for provenance.

## Attachments and third-party material

The accepted tool does not include any game executable, archive, texture, save file, third-party binary, or cheat table. A public community Cheat Engine table was used during research to identify field candidates; its code is not redistributed. The final implementation reads and writes the live process directly.

## Remaining limits

- Only the exact game build above was validated.
- Only the tested save and battle-independent character table state were exercised.
- The `+0x88` field is the base max-HP field used by the accepted model. The game can derive a larger effective maximum from upgrades or equipment, so current HP may exceed this base value. The UI labels the field “max HP”; it is not a complete derived-stat calculator.
- It does not claim that every field persists through every menu or battle transition; the UI provides locks for values the game recomputes.
- It writes process memory only. It does not edit the game executable or save files.
