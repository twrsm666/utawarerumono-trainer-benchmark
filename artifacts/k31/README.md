# K3.1 accepted trainer

Status: **accepted for this benchmark.**

The release asset is `k31-trainer-v1.1.exe`. The source in `trainer-source/` is the recovered final source used to rebuild and revalidate the executable on 2026-11-11.

## Source layout

```text
trainer-source/
├── app.py             PySide6 UI, edit locks, manual refresh
├── game_memory.py     typed Win32 process reader/writer and table parser
├── build.py           PyInstaller build + icon/version resource generation
├── tests/             parser, live read, live write, and UI regression tests
└── tools/recon.py     read-only reconnaissance utility used during development
```

## Environment

- Windows 11
- Python 3.13.x x64
- PySide6 6.12.0
- PyInstaller 6.22.3
- Game PE MD5 `c02107b577a8e3be7965b5b50594abfc`

## Build

```powershell
python -m pip install PySide6-Essentials PyInstaller
python -m unittest discover -s tests -p "test_core.py" -v
python tests/ui_smoke_test.py
python tests/live_write_test.py
python build.py
```

The built executable is written to `dist/`.

## Safety properties

- Does not modify game files.
- Does not write save files.
- Validates the known character table and each target character before writing.
- Reads back every write.
- Does not auto-refresh while a field is focused or dirty.
- Locking is explicit and can be disabled.

## Provenance

The original working tree was deleted during a later cleanup. Final source versions were recovered from platform file history. The release executable is a rebuild, not a byte-identical copy of the deleted 2026-11-08 binary. See [../../docs/K31_ACCEPTANCE.md](../../docs/K31_ACCEPTANCE.md).

## Limitation

This trainer targets one game build and one runtime character-table layout. It is not portable to a different patch or remaster without revalidation.
