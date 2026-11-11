"""Capture the evidence used to compare the Qwen4 save editor with live game state.

Requires:
  - The tested 32-bit game process running.
  - The Qwen4 save editor listening on 127.0.0.1:8765 (GET-only requests).

The script never writes to game memory or save files.
"""
from __future__ import annotations

import csv
import ctypes
import json
import struct
import urllib.request
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

PROCESS_NAME = "Utawarerumono Mask of Deception.exe"
TABLE_RVA = 0x6CE4A4
STRIDE = 0x278
COUNT = 18
QWEN_URL = "http://127.0.0.1:8765/api/save/10"

ACTUAL_NAMES = {
    0: "Haku", 20: "Kuon", 25: "Maroro", 28: "Rulutieh", 32: "Uruuru/Saraana",
    33: "Nosuri", 35: "Ougi", 36: "Nekone", 37: "Kiwru", 38: "Atuy", 42: "Anju",
    43: "Jachdwalt", 47: "Munechika", 50: "Fumirul", 102: "Itaku", 103: "Yuri",
    112: "Tamaki", 114: "Sasara",
}

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD), ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * 256), ("szExePath", wintypes.WCHAR * 260),
    ]


kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.OpenProcess.restype = wintypes.HANDLE


def find_game() -> tuple[int, int]:
    snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    pid = None
    ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
    while ok:
        if entry.szExeFile.casefold() == PROCESS_NAME.casefold():
            pid = entry.th32ProcessID
            break
        ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    kernel32.CloseHandle(snapshot)
    if not pid:
        raise RuntimeError("game process not found")
    module_snapshot = kernel32.CreateToolhelp32Snapshot(0x18, pid)
    module_entry = MODULEENTRY32W()
    module_entry.dwSize = ctypes.sizeof(module_entry)
    base = None
    ok = kernel32.Module32FirstW(module_snapshot, ctypes.byref(module_entry))
    while ok:
        if module_entry.szModule.casefold() == PROCESS_NAME.casefold():
            base = ctypes.cast(module_entry.modBaseAddr, ctypes.c_void_p).value
            break
        ok = kernel32.Module32NextW(module_snapshot, ctypes.byref(module_entry))
    kernel32.CloseHandle(module_snapshot)
    if not base:
        raise RuntimeError("game module not found")
    return pid, base


def read_live() -> list[dict]:
    pid, base = find_game()
    process = kernel32.OpenProcess(0x0010 | 0x0400, False, pid)
    buffer = ctypes.create_string_buffer(STRIDE * COUNT)
    read = ctypes.c_size_t()
    ok = kernel32.ReadProcessMemory(process, ctypes.c_void_p(base + TABLE_RVA), buffer, len(buffer), ctypes.byref(read))
    kernel32.CloseHandle(process)
    if not ok or read.value != len(buffer):
        raise RuntimeError("ReadProcessMemory failed")
    data = buffer.raw
    characters = []
    for index in range(COUNT):
        offset = index * STRIDE
        unit_id = struct.unpack_from("<H", data, offset + 0x74)[0]
        level, xp = struct.unpack_from("<HH", data, offset + 0x7C)
        max_hp = struct.unpack_from("<I", data, offset + 0x88)[0]
        attack, defense, speed, unknown_92, move, jump = struct.unpack_from("<6H", data, offset + 0x8C)
        bp = struct.unpack_from("<H", data, offset + 0xA8)[0]
        characters.append({
            "slot": index, "unit_id": unit_id, "name": ACTUAL_NAMES.get(unit_id, f"Unit {unit_id}"),
            "level": level, "experience": xp, "max_hp": max_hp,
            "attack": attack, "defense": defense, "speed": speed,
            "field_0x92": unknown_92, "move": move, "jump": jump, "bp": bp,
        })
    return characters


def main():
    repo = Path(__file__).resolve().parents[1]
    qwen = json.load(urllib.request.urlopen(QWEN_URL, timeout=5))
    actual = read_live()
    qwen_rows = qwen["chars"]
    output = []
    for index, q in enumerate(qwen_rows):
        a = actual[index]
        expected = actual[(index + 1) % COUNT]
        core = {
            "level": q["fields"]["level"] == a["level"],
            "experience": q["fields"]["exp"] == a["experience"],
            "attack": q["fields"]["atk"] == a["attack"],
            "defense": q["fields"]["def"] == a["defense"],
            "move": q["fields"]["mov"] == a["move"],
            "jump": q["fields"]["jump"] == a["jump"],
        }
        output.append({
            "qwen_slot": index,
            "qwen_unit_id": q["unitId"],
            "qwen_declared_name": q["name"],
            "qwen_fields": q["fields"],
            "actual_same_slot": a,
            "declared_name_matches_same_slot": q["unitId"] == a["unit_id"],
            "next_slot_unit_id": expected["unit_id"],
            "declared_id_equals_next_slot": q["unitId"] == expected["unit_id"],
            "numeric_core_matches_same_slot": core,
        })
    evidence = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "game_process": "Utawarerumono Mask of Deception.exe",
        "qwen_endpoint": QWEN_URL,
        "qwen_save_valid_checksum": qwen["valid"],
        "qwen_character_rows": len(qwen_rows),
        "name_matches_same_slot": sum(x["declared_name_matches_same_slot"] for x in output),
        "id_equals_next_slot": sum(x["declared_id_equals_next_slot"] for x in output),
        "numeric_core_field_matches": sum(sum(x["numeric_core_matches_same_slot"].values()) for x in output),
        "numeric_core_field_total": len(output) * 6,
        "rows": output,
    }
    evidence_dir = repo / "evidence" / "qwen4"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "comparison.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    with (evidence_dir / "comparison.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "slot", "qwen_unit_id", "qwen_name", "actual_unit_id", "actual_name",
            "level_qwen", "level_actual", "exp_qwen", "exp_actual",
            "atk_qwen", "atk_actual", "def_qwen", "def_actual",
            "move_qwen", "move_actual", "jump_qwen", "jump_actual",
            "name_matches_same_slot", "id_equals_next_slot",
        ])
        for item in output:
            q = item["qwen_fields"]
            a = item["actual_same_slot"]
            writer.writerow([
                item["qwen_slot"], item["qwen_unit_id"], item["qwen_declared_name"],
                a["unit_id"], a["name"],
                q["level"], a["level"], q["exp"], a["experience"],
                q["atk"], a["attack"], q["def"], a["defense"],
                q["mov"], a["move"], q["jump"], a["jump"],
                item["declared_name_matches_same_slot"], item["declared_id_equals_next_slot"],
            ])
    print(json.dumps({k: v for k, v in evidence.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
