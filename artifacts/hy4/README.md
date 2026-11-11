# Hy4 historical artifact

Status: **not accepted for this benchmark.**

This is a sanitized, read-only snapshot of the source delivered by the session labeled Hy4. It is preserved to make the failure analysis auditable, not recommended as a working trainer.

## Snapshot

- `trainer-source/utawa_trainer.py` — backend scanner and local HTTP API.
- `trainer-source/unit_table.py` — static `UnitData.bin` parser.
- `trainer-source/index.html` — web UI.
- `trainer-source/verify_checksum.py` — save-header checksum analysis.
- `trainer-source/README.md` — original README, including the agent's own correction notice.
- `trainer-source/start.bat`, `启动修改器.bat` — launch scripts.

No executable was produced.

## Privacy redaction

Local profile paths were replaced with `<USER_HOME>`. The game/work directory was replaced with `<GAME_DIR>` or `<WORK_ROOT>`. These placeholders must be configured before the historical source can run.

## Why it is rejected

The implementation treats static character-template data as live character state. Its own final message acknowledges that the displayed values did not match the game. The later fallback is a manual value-change scanner, not the requested stable per-character editor.

Read [../../docs/HY4_ANALYSIS.md](../../docs/HY4_ANALYSIS.md) and [../../evidence/hy4/final-response.md](../../evidence/hy4/final-response.md).

## Safety

This is historical code that can read and write process memory and edit save files. It has not been revalidated for destructive behavior. Do not point it at a save or process you care about.
