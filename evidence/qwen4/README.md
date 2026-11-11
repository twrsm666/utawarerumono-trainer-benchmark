# Qwen4 evidence

## `comparison.json`

Per-row comparison of:

- the Qwen4 save editor's parsed row (GET-only);
- the actual live character at the same slot;
- the actual live character at the next slot;
- six numeric field matches.

Summary:

- name matches at same slot: `0/18`
- unit ID equals next slot: `18/18`
- sampled numeric field matches at same slot: `108/108`
- Qwen4 save checksum: valid

## `comparison.csv`

The same data in spreadsheet form.

## `artifact-inventory.json`

Product files, sizes, and SHA-256 values. It also records excluded files: save backups, extracted game data, analysis dumps, the generated blob, and the 93.7 MB executable.

## Reproduction

Run [../../scripts/capture_runtime_comparison.py](../../scripts/capture_runtime_comparison.py) while the game and Qwen4 server are running. The script sends GET requests only and reads game memory; it does not write either target.

## Privacy

No `.DAT` file, extracted game text, or Qwen4 binary is present.
