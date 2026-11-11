"""Run the accepted trainer's non-destructive acceptance suite and save its output.

Requires the correct game build to be running and a save to be loaded.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "artifacts" / "k31" / "trainer-source"
OUTPUT = ROOT / "evidence" / "k31" / "test-results.txt"


def run(label: str, args: list[str]) -> tuple[bool, str]:
    command = [sys.executable, *args]
    result = subprocess.run(command, cwd=SOURCE, text=True, capture_output=True)
    body = (result.stdout + result.stderr).strip()
    shown = "python " + " ".join(args)
    body = body.replace(str(Path.home()), "<USER_HOME>").replace(str(ROOT), "<REPO_ROOT>")
    return result.returncode == 0, f"$ {shown}\n{body}\n"


def main():
    checks = []
    outputs = [f"Acceptance run: {datetime.now().astimezone().isoformat(timespec='seconds')}", ""]
    for label, args in [
        ("structure", ["-m", "unittest", "discover", "-s", "tests", "-p", "test_core.py", "-v"]),
        ("ui", ["tests/ui_smoke_test.py"]),
        ("live-write-restore", ["tests/live_write_test.py"]),
    ]:
        ok, text = run(label, args)
        checks.append((label, ok))
        outputs.append(f"[{label}] {'PASS' if ok else 'FAIL'}")
        outputs.append(text)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(outputs), encoding="utf-8")
    print(OUTPUT.read_text(encoding="utf-8"))
    sys.exit(0 if all(ok for _, ok in checks) else 1)


if __name__ == "__main__":
    main()
