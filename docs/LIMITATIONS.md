# Limitations and interpretation guardrails

## 1. This is not a model leaderboard

The study contains one task, one machine, one game build, one save environment, and one operator. It cannot establish general coding, reasoning, or reverse-engineering ability. The result is an acceptance record for this artifact.

## 2. Session labels are not certified model IDs

- **Hy4** is a WorkBuddy session title. The session metadata available at export reports `kimi-k3.1-pro`.
- **K3.1** is a WorkBuddy session title. The operator attributes the initial build to K3.1 and the final small fix to DeepSeek. The live session metadata at export reports `deepseek-v4.1-flash` after fallback.
- **Qwen4** is an operator-supplied Qoder session label. Its chat transcript was not available to the audit.

Provider-side model routing, revision, quantization, and fallback conditions are not independently verified. Report labels, not universal model claims.

## 3. The prompts were not identical

- K3.1 received the complete per-character requirement in its first prompt.
- Hy4 started with a shorter request. The explicit per-character requirement arrived 40 minutes later, after substantial work had already been done.
- Qwen4's original prompt was not available with the artifact.

This asymmetry materially affects any head-to-head interpretation.

## 4. Tooling and human steering differed

The sessions had different tools, web-search access, package availability, UI automation, screenshots, and human interventions. The K3.1 window includes a dependency download that took several minutes. Timing is not inference latency.

## 5. The handoff document reduced difficulty

The operator supplied a reverse-engineering handoff containing RTTI class names, save layout notes, PE details, and open questions. This is not a from-scratch reverse-engineering task.

The accepted run also used public research to locate a community field map, then validated the final memory layout independently. No third-party code, binary, or cheat table is redistributed.

## 6. Artifact timestamps are not full conversation times

The Qwen4 duration is computed from the first and last artifact writes. The chat may have started earlier or continued later. Qwen4's human-turn count and tool-call count are unknown.

## 7. The accepted build is version-specific

The trainer validates one game executable by MD5 and character-table shape. It is not claimed to work with a different patch, language build, executable revision, anti-cheat layer, or 64-bit remaster.

## 8. Testing was targeted, not exhaustive

The accepted build was tested for:

- process attachment;
- 18-page load;
- character field layout;
- one real BP write/read/restore;
- UI input preservation;
- packaged launch/read.

It was not exhaustively tested through every story chapter, every battle transition, every menu, every save slot, or every possible stat combination. Save-file editing is outside its scope.

## 9. Rebuilt binary provenance

The original final source was deleted in a later cleanup. It was recovered from the agent platform's file history and rebuilt on 2026-11-11. The release binary is validated by the tests in this repository, but it is not claimed to be byte-identical to the deleted original. Source-file versions and timestamps are documented in [K31_ACCEPTANCE.md](K31_ACCEPTANCE.md).

## 10. Qwen4 was not write-tested

The save editor exposes a write endpoint, but no real save was modified during the audit. The mapping failure was already demonstrated with read-only evidence. This avoids an unnecessary destructive test.

## 11. Raw logs are withheld

Publishing raw logs would expose unrelated private conversations, local usernames, absolute paths, and authentication material. Counts, timestamps, source, tests, and focused excerpts are published instead. This necessarily limits independent verification of conversational details.

## 12. No game assets

No game executable, archive, save, texture, text, audio, or third-party trainer is included. Reproduction requires the user to own and install the correct game build.

## 13. Correct interpretation

Reasonable conclusion:

> For this specific task and acceptance contract, the K3.1-labeled deliverable was the only one that provided a working per-character live editor. Hy4 did not deliver the requested stable editor, and Qwen4's editor systematically assigned character data to the wrong names.

Unreasonable conclusions include:

- "Model X is always better than model Y."
- "Hy4/Qwen4 cannot write code."
- "The timing is a controlled inference benchmark."
- "The accepted trainer works on every game version."
