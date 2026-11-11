# Evidence and publication policy

## Goals

1. Preserve enough evidence for another engineer to challenge the conclusions.
2. Avoid publishing unrelated private data, credentials, game assets, or save files.
3. Distinguish measured facts from operator attribution and inference.

## Published

- Session titles/labels, timestamps, wall-clock durations.
- Counts of human turns, assistant messages, and tool calls.
- Sanitized source snapshots.
- The accepted standalone executable, attached to a GitHub Release rather than committed to Git.
- Read-only runtime snapshots and field comparisons.
- Checksums and artifact sizes.
- Focused excerpts of the evaluated agents' own conclusions.

## Withheld

- Raw agent conversations. They contain unrelated private context and local account identifiers.
- The user's `.DAT` save files and all save backups.
- The game executable, data archives, textures, text, and extracted data.
- Third-party trainer binaries and Cheat Engine tables used only as research references.
- The Qwen4 executable. It embeds a local user path and is a save writer with a defective mapping.

## Sanitization

Local identities and directories were replaced with:

- `<USER_HOME>`
- `<USER_ID>`
- `<GAME_DIR>`
- `<WORK_ROOT>`
- `<LOCAL_TOOLCHAIN>`

The replacements are textual. Sanitized historical code is not claimed to run without restoring local paths.

## Checksums

Where a withheld artifact is relevant, its size and SHA-256 are published in an inventory JSON. This proves what was evaluated without redistributing it.

## Recorded measurements vs. interpretation

Measured:

- event counts and timestamps;
- file sizes and hashes;
- runtime character values;
- Qwen4 mapping counts;
- test and self-test outputs.

Operator attribution:

- which model produced which session;
- the claim that a quota forced a model switch.

The repository labels these separately and does not upgrade attribution into fact.

## No cherry-picked failed outputs

Failed runs are included with their source and own explanations. The accepted run's own bug (v1.0 auto-refresh overwrite) is also included and dated. Removing either would reduce the value of the evidence.

## Rights

No game assets are included. The repository is a technical audit of user-generated tooling. Character names and game references remain the property of their respective rights holders.
