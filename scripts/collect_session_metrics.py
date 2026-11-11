"""Build a privacy-preserving metrics file from locally available agent logs.

Raw conversation logs are intentionally not copied into the repository. This
script emits only counts, timestamps, and high-level tool usage.
"""
from __future__ import annotations

import collections
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKBUDDY_ROOT = Path.home() / ".workbuddy" / "projects"
HY4_DIR = next(WORKBUDDY_ROOT.glob("*2026-11-08-16-38-36"))
K31_DIR = next(WORKBUDDY_ROOT.glob("*2026-11-08-18-03-40"))
HY4_TRANSCRIPT = next(HY4_DIR.glob("93071ce1-*.jsonl"))
K31_TRANSCRIPT = next(K31_DIR.glob("ba32e60d-*.jsonl"))


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]


def iso_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000).astimezone().isoformat(timespec="milliseconds")


def summarize(path: Path, cutoff_ms: int | None = None) -> dict:
    records = load(path)
    if cutoff_ms is not None:
        records = [record for record in records if (record.get("timestamp") or 0) <= cutoff_ms]
    messages = [record for record in records if record.get("type") == "message"]
    users = []
    for message in messages:
        if message.get("role") != "user":
            continue
        text = "\n".join(part.get("text", "") for part in message.get("content", []) if isinstance(part, dict))
        if "<task-notification>" not in text:
            users.append(message)
    tool_counts = collections.Counter(record.get("name") for record in records if record.get("type") == "function_call")
    timestamps = [record["timestamp"] for record in records if record.get("timestamp")]
    return {
        "record_count": len(records),
        "start": iso_ms(min(timestamps)),
        "end": iso_ms(max(timestamps)),
        "human_turn_count": len(users),
        "assistant_message_count": sum(1 for message in messages if message.get("role") == "assistant"),
        "tool_call_count": sum(tool_counts.values()),
        "tool_calls": dict(tool_counts.most_common()),
        "wall_clock_minutes": round((max(timestamps) - min(timestamps)) / 60000, 2),
    }


def main():
    cutoff = int(datetime.fromisoformat("2026-11-08T18:40:42").astimezone().timestamp() * 1000)
    metrics = {
        "generated_for": "single-task agent benchmark, Utawarerumono trainer",
        "timezone": datetime.now().astimezone().tzinfo.tzname(None),
        "hy4": {
            "session_label": "Hy4",
            "platform": "WorkBuddy",
            "configured_model_label_at_export": "kimi-k3.1-pro",
            "attribution_note": "The session title is Hy4; the model value is the session metadata available at export. It is not independently verified.",
            **summarize(HY4_TRANSCRIPT),
        },
        "k31_initial_task_window": {
            "session_label": "K3.1",
            "platform": "WorkBuddy",
            "model_label_current_after_switch": "deepseek-v4.1-flash",
            "attribution_note": "The operator attributes the initial build to K3.1 and the final small fix to DeepSeek. The live session metadata reports deepseek-v4.1-flash after fallback; split attribution is not independently verifiable.",
            "cutoff_local": "2026-11-08T18:40:42+08:00",
            **summarize(K31_TRANSCRIPT, cutoff),
        },
        "qwen4": {
            "session_label": "Qwen4",
            "platform": "Qoder",
            "artifact_id": "dd671415",
            "attribution_note": "Model name is the operator-provided session label; Qoder chat transcript was not available to this audit.",
            "artifact_first_write": "2026-11-11T20:33:07+08:00",
            "artifact_last_write": "2026-11-11T21:44:42+08:00",
            "artifact_window_minutes": 71.57,
            "raw_product_file_count": 9,
            "excluded_sensitive_or_game_data_file_count": 90,
        },
        "withheld_raw_logs": {
            "reason": "Raw agent logs contain local usernames, absolute paths, environment details, and unrelated personal context.",
            "published_equivalent": "Counts, timestamps, final self-correction excerpt, source snapshots, and runtime comparison evidence.",
        },
    }
    (ROOT / "evidence" / "session-metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
