from __future__ import annotations

import argparse
import ctypes
import json
import re
import struct
import sys
from ctypes import wintypes
from pathlib import Path

PROCESS_NAME = "Utawarerumono Mask of Deception.exe"
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
MEM_MAPPED = 0x40000
MEM_IMAGE = 0x1000000
PAGE_NOACCESS = 0x01
PAGE_GUARD = 0x100
READABLE_PROTECTIONS = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}
WRITABLE_PROTECTIONS = {0x04, 0x08, 0x40, 0x80}

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * 256),
        ("szExePath", wintypes.WCHAR * 260),
    ]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("PartitionId", wintypes.WORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]
    else:
        _fields_ = [
            ("BaseAddress", ctypes.c_void_p),
            ("AllocationBase", ctypes.c_void_p),
            ("AllocationProtect", wintypes.DWORD),
            ("RegionSize", ctypes.c_size_t),
            ("State", wintypes.DWORD),
            ("Protect", wintypes.DWORD),
            ("Type", wintypes.DWORD),
        ]


kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wintypes.BOOL
kernel32.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
kernel32.Module32FirstW.restype = wintypes.BOOL
kernel32.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
kernel32.Module32NextW.restype = wintypes.BOOL
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]
kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.VirtualQueryEx.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
    ctypes.c_size_t,
]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t


def find_process(name: str = PROCESS_NAME) -> int:
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        found = []
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.casefold() == name.casefold():
                found.append(entry.th32ProcessID)
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
        if not found:
            raise RuntimeError(f"未找到进程: {name}")
        return found[0]
    finally:
        kernel32.CloseHandle(snapshot)


def module_base(pid: int, name: str = PROCESS_NAME) -> tuple[int, int]:
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snapshot == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = kernel32.Module32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            if entry.szModule.casefold() == name.casefold():
                return ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value, entry.modBaseSize
            ok = kernel32.Module32NextW(snapshot, ctypes.byref(entry))
        raise RuntimeError(f"未找到模块: {name}")
    finally:
        kernel32.CloseHandle(snapshot)


class ProcessMemory:
    def __init__(self, pid: int, write: bool = False):
        access = PROCESS_VM_READ | PROCESS_QUERY_INFORMATION
        if write:
            access |= PROCESS_VM_WRITE | PROCESS_VM_OPERATION
        self.pid = pid
        self.handle = kernel32.OpenProcess(access, False, pid)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def read(self, address: int, size: int) -> bytes:
        buffer = (ctypes.c_ubyte * size)()
        read = ctypes.c_size_t()
        ok = kernel32.ReadProcessMemory(self.handle, address, buffer, size, ctypes.byref(read))
        if not ok:
            error = ctypes.get_last_error()
            if error == 299 and read.value:
                return bytes(buffer[: read.value])
            raise ctypes.WinError(error)
        return bytes(buffer[: read.value])

    def regions(self, writable_only: bool = False):
        result = []
        address = 0
        mbi = MEMORY_BASIC_INFORMATION()
        while address < 0x80000000:
            count = kernel32.VirtualQueryEx(self.handle, address, ctypes.byref(mbi), ctypes.sizeof(mbi))
            if not count:
                address += 0x10000
                continue
            base = mbi.BaseAddress or 0
            size = mbi.RegionSize
            if size <= 0:
                break
            protection = mbi.Protect & 0xFF
            readable = protection in READABLE_PROTECTIONS and not (mbi.Protect & PAGE_GUARD)
            writable = protection in WRITABLE_PROTECTIONS
            if mbi.State == MEM_COMMIT and readable and (not writable_only or writable):
                result.append({
                    "base": base,
                    "size": size,
                    "protect": mbi.Protect,
                    "type": mbi.Type,
                })
            address = base + size
        return result


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def plausible_character(data: bytes, offset: int = 0) -> bool:
    if offset < 0 or offset + 0x130 > len(data):
        return False
    level = u16(data, offset + 0x7C)
    hp = u32(data, offset + 0x88)
    attack = u16(data, offset + 0x8C)
    defense = u16(data, offset + 0x8E)
    speed = u16(data, offset + 0x90)
    move = u16(data, offset + 0x94)
    jump = u16(data, offset + 0x96)
    bp = u16(data, offset + 0xA8)
    current_hp = u32(data, offset + 0xB8)
    zeal = u32(data, offset + 0xBC)
    team = u32(data, offset + 0x12C)
    return (
        1 <= level <= 99
        and 1 <= hp <= 99999
        and attack <= 9999
        and defense <= 9999
        and speed <= 9999
        and 1 <= move <= 30
        and 1 <= jump <= 30
        and bp <= 99999
        and current_hp <= 99999
        and zeal <= 10000
        and team in (0, 1)
    )


def character_summary(data: bytes, offset: int = 0) -> dict:
    return {
        "level": u16(data, offset + 0x7C),
        "xp": u16(data, offset + 0x7E),
        "total_xp": u32(data, offset + 0x84),
        "max_hp": u32(data, offset + 0x88),
        "attack": u16(data, offset + 0x8C),
        "defense": u16(data, offset + 0x8E),
        "speed": u16(data, offset + 0x90),
        "move": u16(data, offset + 0x94),
        "jump": u16(data, offset + 0x96),
        "bp": u16(data, offset + 0xA8),
        "current_hp": u32(data, offset + 0xB8),
        "zeal": u32(data, offset + 0xBC),
        "team": u32(data, offset + 0x12C),
        "words_00_7c": [u16(data, offset + i) for i in range(0, 0x7C, 2)],
    }


def scan_characters(memory: ProcessMemory):
    candidates = {}
    overlap = 0x200
    move_jump_pattern = re.compile(rb"[\x01-\x1e]\x00[\x01-\x1e]\x00")
    for region in memory.regions(writable_only=True):
        base = region["base"]
        size = region["size"]
        if size > 512 * 1024 * 1024:
            continue
        position = 0
        while position < size:
            chunk_size = min(4 * 1024 * 1024, size - position)
            try:
                chunk = memory.read(base + position, chunk_size)
            except OSError:
                position += chunk_size
                continue
            for match in move_jump_pattern.finditer(chunk):
                offset = match.start() - 0x94
                if offset < 0 or offset + 0x130 > len(chunk):
                    continue
                address = base + position + offset
                if address % 4 or address in candidates or not plausible_character(chunk, offset):
                    continue
                candidates[address] = {
                    "address": address,
                    "region_type": region["type"],
                    **character_summary(chunk, offset),
                }
            if position + chunk_size >= size:
                break
            position += max(0x1000, chunk_size - overlap)
    return list(candidates.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["summary", "scan", "dump"])
    parser.add_argument("--address", type=lambda x: int(x, 0))
    parser.add_argument("--size", type=lambda x: int(x, 0), default=0x180)
    parser.add_argument("--output")
    args = parser.parse_args()
    pid = find_process()
    base, image_size = module_base(pid)
    with ProcessMemory(pid) as memory:
        if args.command == "summary":
            regions = memory.regions(writable_only=True)
            print(json.dumps({
                "pid": pid,
                "module_base": hex(base),
                "image_size": image_size,
                "writable_regions": len(regions),
                "writable_bytes": sum(r["size"] for r in regions),
                "largest_regions": sorted(regions, key=lambda r: r["size"], reverse=True)[:12],
            }, indent=2))
        elif args.command == "scan":
            candidates = scan_characters(memory)
            text = json.dumps(candidates, indent=2)
            if args.output:
                Path(args.output).write_text(text, encoding="utf-8")
            print(f"candidates={len(candidates)}")
            for candidate in candidates:
                print(hex(candidate["address"]), {k: v for k, v in candidate.items() if k not in ("address", "words_00_7c", "region_type")})
        elif args.command == "dump":
            if args.address is None:
                parser.error("dump requires --address")
            data = memory.read(args.address, args.size)
            if args.output:
                Path(args.output).write_bytes(data)
            for offset in range(0, len(data), 16):
                row = data[offset:offset + 16]
                print(f"{args.address + offset:08X}  {row.hex(' '):<47}  {''.join(chr(x) if 32 <= x < 127 else '.' for x in row)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
