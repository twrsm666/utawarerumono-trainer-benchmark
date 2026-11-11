# K3.1 evidence

- `ui.png` — native Windows screenshot captured by the packaged self-test.
- `test-results.txt` — parser, live attach, UI input preservation, and live BP write/restore results.
- `packaged-smoke/` — raw output and screenshot from the released executable's `--self-test`.

The live tests ran against the game process identified by the exact PE MD5 in the top-level README. Character names and levels are shown solely to prove that the parsed table matches the running game; no save file is published. The screenshot is a UI capture of a live process, not a redistributed save state.
