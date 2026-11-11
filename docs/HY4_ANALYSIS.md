# Hy4 analysis: static data mistaken for runtime state

## Scope

- Session label: **Hy4**
- Platform: WorkBuddy
- Session metadata at export: `kimi-k3.1-pro`
- Active window: `2026-11-08 16:38:36` to `18:00:35` (`UTC+08:00`)
- Wall clock: **81.97 minutes**
- Human turns: 4
- Tool calls: 182
- Output: 7-file Python/HTML source tree, no executable

The session title is the operator-provided label. The model metadata is reported as observed, not independently certified.

## What was delivered

| File | Bytes |
| --- | ---: |
| `utawa_trainer.py` | 47,018 |
| `index.html` | 65,266 |
| `README.md` | 11,779 |
| `unit_table.py` | 8,293 |
| `verify_checksum.py` | 1,618 |
| `启动修改器.bat` | 458 |
| `start.bat` | 210 |

There is no `.exe`, installer, or build script that produces a standalone deliverable. The archived source is in [artifacts/hy4](../artifacts/hy4/). Local paths were replaced with `<USER_HOME>`, `<GAME_DIR>`, and `<WORK_ROOT>`.

## Why it failed the requested product

The original requirement was an intuitive per-character editor. Hy4 initially built pages from `UnitData.bin`, a static game data table, rather than the live character records.

Its own final response states:

> I gave you `300 / 600 / 100 / 60…` from `UnitData.bin`; those are static template parameters, not Haku's state in the current battle. I treated the data-table template as a runtime character object, and the HP/attack/defense labels were also guesses.

After the operator reported the mismatch, Hy4 changed the default page to a manual live scanner:

1. Enter a value visible in the game.
2. Scan memory for candidates.
3. Change the value in game.
4. Filter again.
5. Inspect ambiguous surrounding fields and guess what changed.

That workflow requires user-driven dynamic analysis and still does not provide a stable page per character. It is a materially different deliverable.

The final response is archived verbatim at [evidence/hy4/final-response.md](../evidence/hy4/final-response.md).

## Acceptance

| Check | Result |
| --- | --- |
| Standalone executable | Fail: none delivered |
| Direct per-character pages | Fail: replaced by manual scanning |
| Correct character identity | Fail: static templates assigned to named characters |
| Correct live values | Fail, acknowledged by the agent |
| Faithful writes | Not accepted: no stable per-character object established |
| Safe boundaries | Source is read/write to memory and backup-oriented save editing |
| Packaging | Fail: no packaged build |

## Technical work that was valid

Hy4's artifact includes useful reverse-engineering notes:

- save-header A-field checksum analysis;
- `UnitData.bin` and `UnitTextData.bin` container parsing;
- runtime location of the static unit-data table;
- an explicit distinction between static templates and live state after correction.

Those findings are not enough to satisfy the product requirement. They are preserved because removing failed work would make the comparison less useful.

## Interpretation

Hy4 spent 81.97 minutes and made many tool calls, but did not deliver the requested usable per-character editor. The failure was not a lack of UI polish; it was a data-model error: static templates were treated as current character state, and the correction moved away from the requested direct editor.

This single result does not establish a general capability ranking. The session also received the explicit per-character requirement later than K3.1 did. That prompt difference is disclosed in [LIMITATIONS.md](LIMITATIONS.md).
