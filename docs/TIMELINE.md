# Timeline

All timestamps are local time (`UTC+08:00`) as recorded by the agent platform, transcript event timestamps, or filesystem metadata.

## Hy4: 2026-11-08

| Time | Event |
| --- | --- |
| 16:38:36 | Session `Hy4` starts; first task prompt asks for a game trainer. |
| 16:47:15 | Operator supplies the reverse-engineering handoff document. |
| 17:18:44 | Operator adds the requirement for intuitive per-character pages. |
| 17:42:14 | Operator reports that displayed values do not match the game. |
| 18:00:35 | Final self-correction acknowledges static templates were mistaken for runtime character state. |

Measured span: **81.97 minutes**. Result: Python/HTML source only; no standalone build.

Tool histogram: Bash 71, Edit 71, TaskUpdate 14, Write 8, TaskCreate 7, Read 4, DeferExecuteTool 3, present_files 3, ToolSearch 1. Total: **182 calls**.

## K3.1: 2026-11-08

| Time | Event |
| --- | --- |
| 18:03:40 | First prompt includes the complete per-character requirement and handoff document. |
| 18:33:45 | First one-file EXE generated. Elapsed: **30.09 min**. |
| 18:37:02 | Operator reports typed values being overwritten before write. |
| 18:40:42 | Fixed v1.1 EXE generated. Elapsed after report: **3.67 min**. |
| 18:40:43 | Build completion event recorded. |

Measured initial-task span through the fixed build: **37.02 minutes**.

Tool histogram inside the initial task window (ending 18:40:42): Bash 50, Edit 27, Write 8, Read 7, ViewImage 6, TaskUpdate 5, PowerShell 4, TaskCreate 3, TaskOutput 3, WebSearch 1, WebFetch 1, Grep 1, present_files 1. Total: **117 calls**.

The first request and fixed-build timestamps are also corroborated by filesystem metadata from the platform file history.

## Qwen4: 2026-11-11

The Qoder conversation transcript was not available to this audit. The timeline below comes from artifact filesystem timestamps in `dd671415/trainer`.

| Time | Event |
| --- | --- |
| 20:33:07 | Save snapshots written; analysis workspace begins. |
| 20:33:23 | Save analysis script produced. |
| 20:41:48 | Character block analysis script produced. |
| 21:06:01 | Character detail analysis script produced. |
| 21:20:11 | Character map script produced. |
| 21:25:55 | UI HTML last written. |
| 21:28:09 | Save engine last written. |
| 21:42:37 | Executable build script produced. |
| 21:44:42 | Final 93.7 MB executable timestamp. |

Artifact window: **71.57 minutes**. The Qwen4 chat itself may have started earlier or ended later; this is an artifact-only lower-bound window, not a full conversation duration.

## 2026-11-11: audit and restoration

These events are not part of any model's original performance time.

- The K3.1 working tree was recovered from platform file history.
- The final v1.1 source was rebuilt and ran the complete test suite against the running game.
- Qwen4's save editor was queried read-only on localhost and compared with live game memory.
- No save file was written by the audit.

## Interpretation

Elapsed time includes tool waits, dependency installation, screenshots, edits, retries, and human steering. It is not inference latency and should not be presented as a controlled throughput measurement.
