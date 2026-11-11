# Method

## 1. Research question

Can an agent produce a usable Windows trainer for a specific 32-bit single-player game, with one page per character and editable attributes that correspond to the running game?

This is an acceptance-based case study. It asks whether each delivered artifact worked, not whether a model is generally better.

## 2. Task inputs

- A legally installed PC build of *Utawarerumono: Mask of Deception*.
- A 17 KB reverse-engineering handoff note supplied by the operator.
- A written requirement for an intuitive per-character editor.

The full K3.1 prompt included the per-character requirement from the beginning. The Hy4 session began with a shorter prompt and received the per-character requirement 40 minutes later. The Qwen4 conversation record was not available; only its session label and artifacts could be audited. These differences are material and are disclosed in [LIMITATIONS.md](LIMITATIONS.md).

## 3. Session attribution

| Label | Platform | Evidence of identity | What can be verified |
| --- | --- | --- | --- |
| Hy4 | WorkBuddy | Session title/custom title `Hy4`; metadata at export reports `kimi-k3.1-pro` | Session events, source tree, timestamps |
| K3.1 | WorkBuddy | Session title/custom title `K3.1`; current metadata after fallback reports `deepseek-v4.1-flash` | Events, file history, builds, source, executable |
| Qwen4 | Qoder | Operator-supplied session label; artifact directory `dd671415` | Files, timestamps, source, parser output |

A session title is not a provider-issued model identity. Where the operator's attribution and metadata differ or cannot be reconciled, both are reported.

## 4. Timing definition

Times are wall-clock timestamps in the operator's local timezone (`UTC+08:00`). They include model inference, tool execution, package installation, screenshots, tests, retries, and human steering. They are not per-token latency or pure generation time.

Artifact timestamps are filesystem `mtime`/`ctime`. Conversation timestamps come from the local JSONL event stream. All retain millisecond precision where available.

## 5. Acceptance contract

An artifact passes only if all applicable checks pass.

| ID | Check | Operational test |
| --- | --- | --- |
| A1 | Stable artifact | The delivered program starts without an IDE or agent session. |
| A2 | Per-character pages | There is a direct entry point for every supported character; no manual memory scan is required to reach a named page. |
| A3 | Correct identity | Displayed character IDs/names resolve to the same character in the running game. |
| A4 | Correct values | Displayed level, experience, HP-related fields, ATK, DEF, SPD, MOVE, and JUMP correspond to the same character in the running game. |
| A5 | Faithful writes | A changed value is read back from the target, remains after a short delay, and can be restored. |
| A6 | Safe boundaries | The tool does not modify the game executable or unrelated files without an explicit user action. |
| A7 | Usable packaging | A standalone executable exists and passes a launch/read smoke test. |

The checks are pass/fail. No weighted score is invented.

## 6. Evidence collection

### WorkBuddy sessions

Local JSONL event streams were parsed read-only. The audit counted:

- human turns, excluding automated task notifications;
- assistant messages;
- tool calls by tool name;
- first and last timestamps;
- wall-clock duration.

Final source versions were recovered from the platform's file-history records, copied to the repository, sanitized, rebuilt, and retested. The final accepted binary was produced from that recovered source on 2026-11-11.

### Qwen4 artifact

The artifact directory was inventoried read-only. Files were hashed. Qwen4's local server was queried with GET-only endpoints while the game was running. Its parsed slot-10 output was compared to a read-only `ReadProcessMemory` snapshot of the live character table.

No Qwen4 write endpoint was called and no save file was modified during the audit. The comparison script is [scripts/capture_runtime_comparison.py](../scripts/capture_runtime_comparison.py).

### Rejected material

The following were deliberately excluded from publication:

- game executable, archives, textures, audio, text, and extracted game data;
- `.DAT` save files and save backups;
- third-party trainer binaries or cheat tables;
- raw agent transcripts containing unrelated private context and local identity;
- Qwen4's generated executable, which embeds a local absolute path and is a defective save writer.

Original artifact hashes and sizes are retained where they do not expose file contents.

## 7. Runtime comparison method for Qwen4

For each of the 18 rows returned by Qwen4:

1. Compare the row's declared unit ID/name with the live character in the **same index**.
2. Compare the same row with the **next index** to test the observed one-slot rotation.
3. Compare six numeric fields: level, experience, attack, defense, move, jump.
4. Record matches in [evidence/qwen4/comparison.json](../evidence/qwen4/comparison.json).

This distinguishes three different failure modes:

- random or fabricated numeric data;
- correct data assigned to the wrong character;
- a UI-only naming defect.

The evidence shows the second mode: numeric data belongs to the same slot, while IDs/names are rotated to the next slot.

## 8. Reproduction boundaries

- Same game build required: PE MD5 `c02107b577a8e3be7965b5b50594abfc`.
- Same live process name required: `Utawarerumono Mask of Deception.exe`.
- Results may differ with another game build, language package, save state, process bitness, or modified executable.
- The accepted trainer uses a validated static table address for this exact build and refuses connection if its character-table checks fail.
