# Security and safe use

## Scope

This repository documents a local, single-player game trainer and a benchmark of agent sessions. It is not a service and has no server component exposed to the internet.

## Do not use rejected tools on valuable data

The Qwen4 source snapshot is archived for audit only. Its character mapping is known to be wrong. Do not run it against a real save file.

The Hy4 snapshot is historical and not part of the accepted build. It has not been revalidated for destructive behavior.

## Accepted trainer

The accepted trainer:

- attaches to one named local process;
- reads and writes process memory;
- does not modify the game executable;
- does not modify save files;
- validates the known character table and target character before writing;
- reads back each write;
- exposes explicit locking so game-recomputed values can be held.

Back up your save before using any third-party trainer, even when the trainer does not write save files.

## Credentials

There are no API keys, GitHub tokens, passwords, session cookies, or other credentials in this repository. A publication token included in a private planning transcript was deliberately excluded and should be revoked by the operator.

## Reporting

If you find sensitive data, a game file, or a credential in the repository, open a private security advisory or contact the repository owner rather than posting it publicly.
