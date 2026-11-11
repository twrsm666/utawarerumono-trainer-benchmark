#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《传颂之物：虚伪的假面》单机修改器 · 本地后端

设计要点（依据 TRAINER-二代修改器制作说明书.md）：
  * 目标为 32 位 PE32 进程、有 ASLR、无反作弊 → 走 ReadProcessMemory/WriteProcessMemory，
    地址一律以「模块基址 + RVA」持久化，绝不写死 0x400000。
  * 引擎用自研 Kernel::CAllocator，对象在引擎堆上，普通堆扫描会漏 → 全内存区域扫描。
  * 不注入 DLL、不 hook、不改 exe、不碰任何启动校验/Steam 组件。
  * 存档：A 校验已逆向（A = Σ(payload[0x10:]) + payloadLen，27/27 样本验证）；
    B 未逆向，提供保留/清零/自定义三种策略，改档必自动备份。

仅使用 Python 标准库，无需 pip 安装任何东西。
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import datetime
import glob
import http.server
import json
import os
import shutil
import struct
import sys
import threading
import time
import webbrowser
from array import array
from urllib.parse import urlparse, parse_qs

import unit_table

IS_WIN = sys.platform == "win32"
HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(HERE, "web")
TABLE_FILE = os.path.join(HERE, "address_table.json")
GAME_EXE = "utawarerumono mask of deception.exe"
SAVE_DIRNAME = "受讚頌者 虛偽的假面"

# --------------------------------------------------------------------------
# Win32 封装
# --------------------------------------------------------------------------
if IS_WIN:
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010
    PROCESS_VM_WRITE = 0x0020
    PROCESS_VM_OPERATION = 0x0008
    TH32CS_SNAPPROCESS = 0x00000002
    TH32CS_SNAPMODULE = 0x00000008
    TH32CS_SNAPMODULE32 = 0x00000010
    MEM_COMMIT = 0x1000
    PAGE_GUARD = 0x100
    PAGE_NOCACHE = 0x200
    READABLE_PROTECT = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}  # R/RW/WC/ER/ERW/EWC

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
            ("th32DefaultHeapID", ctypes.c_ulonglong), ("th32ModuleID", wt.DWORD),
            ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
            ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
            ("szExeFile", wt.WCHAR * 260),
        ]

    class MODULEENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
            ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD),
            ("modBaseAddr", ctypes.c_void_p), ("modBaseSize", wt.DWORD),
            ("hModule", ctypes.c_void_p), ("szModule", wt.WCHAR * 256),
            ("szExePath", wt.WCHAR * 260),
        ]

    class MEMORY_BASIC_INFORMATION64(ctypes.Structure):
        _fields_ = [
            ("BaseAddress", ctypes.c_ulonglong),
            ("AllocationBase", ctypes.c_ulonglong),
            ("AllocationProtect", wt.DWORD),
            ("PartitionId", wt.DWORD),
            ("RegionSize", ctypes.c_ulonglong),
            ("State", wt.DWORD),
            ("Protect", wt.DWORD),
            ("Type", wt.DWORD),
            ("Align2", wt.DWORD),
        ]

    k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k32.OpenProcess.restype = wt.HANDLE
    k32.CloseHandle.argtypes = [wt.HANDLE]
    k32.CloseHandle.restype = wt.BOOL
    k32.ReadProcessMemory.argtypes = [wt.HANDLE, wt.LPCVOID, wt.LPVOID,
                                      ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    k32.ReadProcessMemory.restype = wt.BOOL
    k32.WriteProcessMemory.argtypes = [wt.HANDLE, wt.LPVOID, wt.LPCVOID,
                                       ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    k32.WriteProcessMemory.restype = wt.BOOL
    k32.VirtualQueryEx.argtypes = [wt.HANDLE, wt.LPCVOID, wt.LPVOID, ctypes.c_size_t]
    k32.VirtualQueryEx.restype = ctypes.c_size_t
    k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
    k32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32FirstW.restype = wt.BOOL
    k32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32NextW.restype = wt.BOOL
    k32.Module32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(MODULEENTRY32W)]
    k32.Module32FirstW.restype = wt.BOOL

    INVALID_HANDLE = ctypes.c_void_p(-1).value
else:
    k32 = None

# 数值类型表：name -> (struct fmt, size, 是否整数)
TYPES = {
    "i8": ("b", 1, True), "u8": ("B", 1, True),
    "i16": ("h", 2, True), "u16": ("H", 2, True),
    "i32": ("i", 4, True), "u32": ("I", 4, True),
    "i64": ("q", 8, True), "u64": ("Q", 8, True),
    "f32": ("f", 4, False), "f64": ("d", 8, False),
}
MAX_RESULTS = 300000
CHUNK = 1 << 20


def parse_value(text, typ):
    fmt, size, is_int = TYPES[typ]
    text = str(text).strip()
    if is_int:
        return int(text, 0) if text.lower().startswith(("0x", "-0x")) else int(text, 10)
    return float(text)


def pack_value(value, typ):
    if isinstance(value, str):
        value = parse_value(value, typ)
    return struct.pack("<" + TYPES[typ][0], value)


def unpack_value(data, off, typ):
    return struct.unpack_from("<" + TYPES[typ][0], data, off)[0]


class WinProcess:
    """一个附加中的目标进程。"""

    def __init__(self, pid, name):
        self.pid = pid
        self.name = name
        self.base = 0
        self.base_size = 0
        self.exe_path = ""
        self.h = None

    def open(self):
        if not IS_WIN:
            raise RuntimeError("进程内存功能仅支持 Windows")
        self.h = k32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION,
            False, self.pid)
        if not self.h:
            raise OSError(ctypes.get_last_error(), "OpenProcess 失败，请以管理员身份重试")
        self._find_base()
        return self

    def _find_base(self):
        for flag in (TH32CS_SNAPMODULE32, TH32CS_SNAPMODULE):
            snap = k32.CreateToolhelp32Snapshot(flag, self.pid)
            if not snap or snap == INVALID_HANDLE:
                continue
            try:
                me = MODULEENTRY32W()
                me.dwSize = ctypes.sizeof(me)
                if k32.Module32FirstW(snap, ctypes.byref(me)):
                    self.base = me.modBaseAddr or 0
                    self.base_size = me.modBaseSize
                    self.exe_path = me.szExePath or ""
                    return
            finally:
                k32.CloseHandle(snap)

    def close(self):
        if self.h:
            try:
                k32.CloseHandle(self.h)
            except Exception:
                pass
        self.h = None

    def regions(self):
        """枚举所有可读、已提交、非 GUARD 的内存区域。"""
        if not self.h:
            return
        mbi = MEMORY_BASIC_INFORMATION64()
        addr = 0x10000
        limit = 0x7FFFFFFF0000
        fails = 0
        while addr < limit:
            n = k32.VirtualQueryEx(self.h, ctypes.c_void_p(addr),
                                   ctypes.byref(mbi), ctypes.sizeof(mbi))
            if not n:
                fails += 1
                if fails >= 8:      # 越过目标进程地址空间后不再空转
                    break
                addr += 0x10000
                continue
            fails = 0
            size = mbi.RegionSize
            if size == 0:
                addr += 0x1000
                continue
            good = (mbi.State == MEM_COMMIT
                    and (mbi.Protect & 0xFF) in READABLE_PROTECT
                    and not (mbi.Protect & PAGE_GUARD)
                    and not (mbi.Protect & PAGE_NOCACHE))
            if good:
                yield int(mbi.BaseAddress), int(size)
            addr = int(mbi.BaseAddress) + size

    def read(self, addr, size):
        buf = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t(0)
        ok = k32.ReadProcessMemory(self.h, ctypes.c_void_p(addr), buf, size, ctypes.byref(got))
        if not ok:
            return b""
        return buf.raw[:got.value]

    def write(self, addr, data):
        wrote = ctypes.c_size_t(0)
        ok = k32.WriteProcessMemory(self.h, ctypes.c_void_p(addr), data,
                                    len(data), ctypes.byref(wrote))
        return bool(ok) and wrote.value == len(data)


def list_processes():
    if not IS_WIN:
        return []
    out = []
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snap or snap == INVALID_HANDLE:
        return out
    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(pe)
        ok = k32.Process32FirstW(snap, ctypes.byref(pe))
        while ok:
            name = pe.szExeFile
            if name and (GAME_EXE in name.lower() or "utawa" in name.lower()):
                out.insert(0, {"pid": pe.th32ProcessID, "name": name, "game": True})
            elif name and name.lower().endswith(".exe"):
                out.append({"pid": pe.th32ProcessID, "name": name, "game": False})
            ok = k32.Process32NextW(snap, ctypes.byref(pe))
    finally:
        k32.CloseHandle(snap)
    return out


# --------------------------------------------------------------------------
# 状态与扫描
# --------------------------------------------------------------------------
class TrainerState:
    def __init__(self):
        self.lock = threading.RLock()
        self.proc = None
        self.scan_type = "i32"
        self.align = True
        self.addrs = array("Q")
        self.prev = array("d")   # 上一轮扫描时的值（用于变化判定）
        self.orig = array("d")   # 首次扫描的初始值（展示用）
        self.first_done = False
        self.scan_info = ""
        self.table = []
        self.next_id = 1
        self.log = []
        self.load_table()

    def note(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {msg}")
        if len(self.log) > 200:
            self.log.pop(0)

    # -------- 地址表 --------
    def load_table(self):
        try:
            with open(TABLE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.table = data.get("table", [])
            self.next_id = data.get("next_id", 1)
        except Exception:
            self.table = []
            self.next_id = 1

    def save_table(self):
        with open(TABLE_FILE, "w", encoding="utf-8") as f:
            json.dump({"table": self.table, "next_id": self.next_id},
                      f, ensure_ascii=False, indent=2)

    def rebase_table(self):
        """附加成功后，把用 RVA 保存的条目还原成实际地址（对抗 ASLR）。"""
        if not self.proc:
            return
        for t in self.table:
            if t.get("rva") is not None and self.proc.base:
                t["addr"] = self.proc.base + t["rva"]

    # -------- 扫描 --------
    def first_scan(self, value, typ, align=True):
        with self.lock:
            if not self.proc:
                raise RuntimeError("尚未附加游戏进程")
            fmt, size, _ = TYPES[typ]
            pat = pack_value(value, typ)
            step = size if align else 1
            self.addrs = array("Q")
            self.prev = array("d")
            self.orig = array("d")
            self.scan_type = typ
            self.align = align
            overlap = size - 1
            t0 = time.time()
            regions = 0
            for start, rsize in self.proc.regions():
                regions += 1
                off = 0
                while off < rsize:
                    want = min(CHUNK + overlap, rsize - off)
                    data = self.proc.read(start + off, want)
                    if not data:
                        off += CHUNK
                        continue
                    limit = min(CHUNK, len(data))
                    pos = 0
                    while True:
                        i = data.find(pat, pos, limit + overlap)
                        if i < 0 or i >= limit:
                            break
                        if align and (i % step):
                            pos = i + 1
                            continue
                        self.addrs.append(start + off + i)
                        self.prev.append(value)
                        self.orig.append(value)
                        pos = i + step
                        if len(self.addrs) >= MAX_RESULTS:
                            break
                    if len(self.addrs) >= MAX_RESULTS:
                        break
                    off += CHUNK
                if len(self.addrs) >= MAX_RESULTS:
                    break
            self.first_done = True
            elapsed = time.time() - t0
            self.scan_info = f"首次扫描：{regions} 个区域，{elapsed:.2f}s"
            self.note(f"{self.scan_info}，命中 {len(self.addrs)} 个地址")
            return len(self.addrs)

    def next_scan(self, mode, value=None, extra=None):
        with self.lock:
            if not self.first_done:
                raise RuntimeError("请先做一次首次扫描")
            if not self.proc:
                raise RuntimeError("游戏进程已断开")
            typ = self.scan_type
            size = TYPES[typ][1]
            target = parse_value(value, typ) if value not in (None, "") else None
            extra_v = parse_value(extra, typ) if extra not in (None, "") else None
            new_a = array("Q")
            new_p = array("d")
            new_o = array("d")
            cache = {}
            for idx, addr in enumerate(self.addrs):
                if len(cache) > 4096:
                    cache.clear()
                page = addr >> 12
                if page not in cache:
                    cache[page] = self.proc.read(page << 12, 4096)
                buf = cache[page]
                o = addr - (page << 12)
                if o + size > len(buf):
                    raw = self.proc.read(addr, size)
                    if len(raw) != size:
                        continue
                    cur = unpack_value(raw, 0, typ)
                else:
                    cur = unpack_value(buf, o, typ)
                old = self.prev[idx]
                keep = False
                if mode == "equal":
                    keep = cur == target
                elif mode == "not_equal":
                    keep = cur != target
                elif mode == "greater":
                    keep = cur > target
                elif mode == "less":
                    keep = cur < target
                elif mode == "changed":
                    keep = cur != old
                elif mode == "unchanged":
                    keep = cur == old
                elif mode == "increased":
                    keep = cur > old
                elif mode == "decreased":
                    keep = cur < old
                elif mode == "increased_by":
                    keep = (cur - old) == target
                elif mode == "decreased_by":
                    keep = (old - cur) == target
                elif mode == "between":
                    keep = target <= cur <= extra_v
                else:
                    raise RuntimeError("未知扫描模式：" + str(mode))
                if keep:
                    new_a.append(addr)
                    new_p.append(cur)
                    new_o.append(self.orig[idx])
            self.addrs, self.prev, self.orig = new_a, new_p, new_o
            self.scan_info = f"再次扫描（{mode}）"
            self.note(f"{self.scan_info}，剩余 {len(self.addrs)} 个地址")
            return len(self.addrs)

    def results(self, offset=0, count=200):
        with self.lock:
            if not self.proc or not self.first_done:
                return {"total": 0, "items": [], "base": self.proc.base if self.proc else 0}
            typ = self.scan_type
            size = TYPES[typ][1]
            out = []
            cache = {}
            for idx in range(offset, min(offset + count, len(self.addrs))):
                addr = self.addrs[idx]
                page = addr >> 12
                if page not in cache:
                    cache[page] = self.proc.read(page << 12, 4096)
                buf = cache[page]
                o = addr - (page << 12)
                if o + size <= len(buf):
                    cur = unpack_value(buf, o, typ)
                else:
                    raw = self.proc.read(addr, size)
                    cur = unpack_value(raw, 0, typ) if len(raw) == size else None
                # 本作 SizeOfImage 约 412MB（.rsrc 段 VA 高达 0x18932000），
                # 必须用实际模块大小判断，不能假定模块只有十几 MB。
                span = self.proc.base_size or 0x1000000
                rva = (addr - self.proc.base) if (self.proc.base
                       and 0 <= addr - self.proc.base < span) else None
                out.append({
                    "addr": addr,
                    "hex": f"0x{addr:08X}",
                    "value": cur,
                    "prev": self.orig[idx],
                    "rva": rva,
                })
            return {"total": len(self.addrs), "items": out,
                    "base": self.proc.base, "scan_type": typ, "info": self.scan_info}

    def write_addr(self, addr, value, typ=None):
        typ = typ or self.scan_type
        with self.lock:
            if not self.proc:
                raise RuntimeError("尚未附加游戏进程")
            data = pack_value(parse_value(value, typ), typ)
            if not self.proc.write(int(addr), data):
                raise OSError(ctypes.get_last_error(), "写入失败：内存可能不可写或进程已退出")
            self.note(f"写入 {pack_value(parse_value(value, typ), typ).hex()} → 0x{int(addr):08X}")
            return True

    def read_addr(self, addr, typ=None):
        typ = typ or self.scan_type
        size = TYPES[typ][1]
        raw = self.proc.read(int(addr), size)
        if len(raw) != size:
            return None
        return unpack_value(raw, 0, typ)

    # -------- 锁定线程 --------
    def lock_loop(self):
        while True:
            time.sleep(0.12)
            try:
                with self.lock:
                    if not self.proc:
                        continue
                    items = [(t["addr"], t["typ"], t["lock_value"])
                             for t in self.table if t.get("locked")]
                for addr, typ, val in items:
                    try:
                        self.proc.write(addr, pack_value(val, typ))
                    except Exception:
                        pass
                # 人物属性表锁定（防止游戏重载数据表时覆盖）
                for i, vals in list(UNIT_LOCKS.items()):
                    if not UNIT.base:
                        continue
                    for f, v in enumerate(vals):
                        try:
                            self.proc.write(UNIT.addr_of(i, f), struct.pack("<H", v))
                        except Exception:
                            pass
            except Exception:
                pass


STATE = TrainerState()

# ---- 人物属性表 ------------------------------------------------------------
UNIT = unit_table.UnitTable()
UNIT_CONFIG = os.path.join(HERE, "unit_config.json")
UNIT_LOCKS = {}          # unit index -> [12 个锁定值]


def load_unit_config():
    try:
        with open(UNIT_CONFIG, "r", encoding="utf-8") as f:
            c = json.load(f)
        if isinstance(c.get("labels"), list) and len(c["labels"]) == unit_table.FIELDS:
            UNIT.labels = [str(x) for x in c["labels"]]
        if isinstance(c.get("names"), dict):
            UNIT.custom_names = {int(k): str(v) for k, v in c["names"].items()}
    except Exception:
        pass


def save_unit_config():
    with open(UNIT_CONFIG, "w", encoding="utf-8") as f:
        json.dump({"labels": UNIT.labels, "names": UNIT.custom_names},
                  f, ensure_ascii=False, indent=2)


load_unit_config()


# ---- 实时角色定位：用「数值变化」找当前战斗中的真实地址 ------------------
# 只用区分度高的数值；1/3/4 这类小值在 1GB 内存里到处都是，绝不拿来自动命名。
UI_HINTS = [
    (66, "体力 / 当前 HP"), (15, "攻击力"), (18, "防御力"),
    (120, "敏捷度"), (70, "气力"),
]


class LiveScanner:
    """独立于数值扫描页的定位器：多种数值类型一起扫，用变化收敛到真实地址。"""

    def __init__(self):
        self.addrs = array("Q")
        self.typs = []
        self.stage = 0
        self.info = ""
        self.anchor = 0
        self._last_addr = {}

    def scan(self, proc, value, types=("u16", "u32", "f32")):
        if not proc:
            raise RuntimeError("请先附加游戏进程")
        pats = []
        for typ in types:
            try:
                pats.append((typ, pack_value(value, typ), TYPES[typ][1]))
            except (ValueError, struct.error):
                continue
        if not pats:
            raise RuntimeError("数值无法按所选类型编码")
        self.addrs = array("Q")
        self.typs = []
        seen = set()
        initial = {}
        for typ, _pat, _size in pats:
            initial[typ] = parse_value(value, typ)
        t0 = time.time()
        for start, size in proc.regions():
            off = 0
            while off < size:
                data = proc.read(start + off, min(CHUNK, size - off))
                if data:
                    for typ, pat, step in pats:
                        pos = data.find(pat)
                        while pos >= 0:
                            a = start + off + pos
                            key = (a, typ)
                            if key not in seen and len(self.addrs) < 400000:
                                seen.add(key)
                                self.addrs.append(a)
                                self.typs.append(typ)
                                self._last_addr[a] = initial[typ]
                            pos = data.find(pat, pos + 1)
                off += CHUNK
        self.stage = 1
        self.anchor = 0
        self.info = f"扫描 {value}（{','.join(types)}）→ {len(self.addrs)} 个候选，{time.time()-t0:.2f}s"
        STATE.note(self.info)
        return len(self.addrs)

    def _values(self, proc):
        cache = {}
        out = []
        for idx, a in enumerate(self.addrs):
            typ = self.typs[idx]
            size = TYPES[typ][1]
            page = a >> 12
            if page not in cache:
                if len(cache) > 4096:
                    cache.clear()
                cache[page] = proc.read(page << 12, 4096)
            buf = cache[page]
            o = a - (page << 12)
            if o + size <= len(buf):
                out.append(unpack_value(buf, o, typ))
            else:
                raw = proc.read(a, size)
                out.append(unpack_value(raw, 0, typ) if len(raw) == size else None)
        return out

    def filter(self, proc, value=None, mode="equal"):
        if not self.stage:
            raise RuntimeError("请先做首次扫描")
        target = float(value) if value not in (None, "") else None
        cur = self._values(proc)
        old = getattr(self, "_last_addr", {})
        na = array("Q")
        nt = []
        for i, v in enumerate(cur):
            if v is None:
                continue
            a = self.addrs[i]
            if mode == "equal":
                keep = target is not None and v == target
            elif mode == "changed":
                keep = a in old and v != old[a]
            elif mode == "increased":
                keep = a in old and v > old[a]
            elif mode == "decreased":
                keep = a in old and v < old[a]
            else:
                keep = False
            if keep:
                na.append(a)
                nt.append(self.typs[i])
        self.addrs, self.typs = na, nt
        # 更新基准，支持连续多轮「变化 / 新值」筛选
        self._last_addr = {a: v for a, v in zip(self.addrs, self._values(proc)) if v is not None}
        self.stage = 2
        self.info = f"筛选（{mode} {value if value is not None else ''}）→ 剩余 {len(na)} 个"
        STATE.note(self.info)
        return len(na)

    def snapshot(self, proc):
        vals = self._values(proc)
        self._last_addr = {a: v for a, v in zip(self.addrs, vals) if v is not None}
        return len(self._last_addr)

    def results(self, proc, offset=0, count=100):
        vals = self._values(proc)
        items = []
        for i in range(offset, min(offset + count, len(self.addrs))):
            items.append({"addr": self.addrs[i], "addrHex": "0x%08X" % self.addrs[i],
                          "typ": self.typs[i], "value": vals[i]})
        return {"total": len(self.addrs), "items": items, "info": self.info,
                "stage": self.stage}

    def fields(self, proc, addr, span=0x100):
        """以命中地址为锚，列出附近所有数值型字段。

        只有窗口内同时出现 >=3 个不同的高区分度 UI 数值（且含 66 或 120）
        才判定为「像角色对象」，此时才自动命名，避免把随机内存误标成属性。
        """
        base = addr - span
        raw = proc.read(base, span * 2 + 8)
        rows = []
        seen_vals = set()
        for i in range(0, len(raw) - 4, 2):
            u16 = struct.unpack_from("<H", raw, i)[0]
            u32 = struct.unpack_from("<I", raw, i)[0]
            f32 = struct.unpack_from("<f", raw, i)[0]
            hit = None
            for v, name in UI_HINTS:
                if u16 == v or u32 == v or (f32 == f32 and abs(f32 - v) < 0.001):
                    hit = (v, name)
                    break
            if hit:
                seen_vals.add(hit[0])
            rows.append((base + i, i - span, u16, u32, f32, hit))
        # 只做中性的「数值恰好相同」标记，绝不声称这个字段就是该属性：
        # 15/18/66/70/120 在 1GB 内存里大量出现，自动命名必然误导。
        out = []
        for a, off, u16, u32, f32, hit in rows:
            label = ("= 界面数值 %d" % hit[0]) if hit else ""
            plausible = (0 < u16 < 10000) or (0 < u32 < 10000) or label
            if label or plausible:
                out.append({"addr": a, "addrHex": "0x%08X" % a,
                            "off": off, "u16": u16, "u32": u32,
                            "f32": round(f32, 3) if f32 == f32 and abs(f32) < 1e6 else None,
                            "label": label})
        self.anchor = addr
        return {"anchor": addr, "anchorHex": "0x%08X" % addr,
                "fields": out, "hints": [n for _, n in UI_HINTS],
                "matched": sorted(seen_vals),
                "matchCount": len(seen_vals)}


LIVE = LiveScanner()


def unit_payload(only_active=True, query=""):
    p = STATE.proc
    out = []
    q = (query or "").strip().lower()
    for i in range(UNIT.count):
        orig = UNIT.file_attrs(i)
        if orig is None:
            continue
        name = UNIT.name_of(i)
        active = orig[0] > 0 or orig[2] > 0
        if only_active and not active:
            continue
        if q and q not in name.lower() and q != str(i) and not q.lstrip("#") == str(i):
            continue
        cur = UNIT.read(p, i) if (UNIT.base and p) else None
        out.append({"i": i, "name": name, "number": "#%d" % i,
                    "attrs": cur, "orig": orig, "active": active,
                    "addr": UNIT.addr_of(i, 0) if UNIT.base else 0,
                    "addrHex": ("0x%08X" % UNIT.addr_of(i, 0)) if UNIT.base else ""})
    return out


# --------------------------------------------------------------------------
# 存档编辑（路线 B）
# --------------------------------------------------------------------------
def default_save_dir():
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    for root in (docs, os.path.join(os.path.expanduser("~"), "OneDrive", "Documents"),
                 r"C:\Users\Public\Documents"):
        p = os.path.join(root, "AQUAPLUS", SAVE_DIRNAME)
        if os.path.isdir(p):
            return p
    return os.path.join(docs, "AQUAPLUS", SAVE_DIRNAME)


def parse_save(path):
    with open(path, "rb") as f:
        d = f.read()
    if len(d) < 0x24:
        raise RuntimeError("文件太短，不是有效存档")
    a, b, ln, c = struct.unpack_from("<IIII", d, 0)
    total = struct.unpack_from("<I", d, 0x20)[0]
    ver = d[0x10:0x18].split(b"\0")[0].decode("ascii", "replace")
    tag = d[0x18:0x20].split(b"\0")[0].decode("ascii", "replace")
    calc_a = (sum(d[0x10:]) + ln) & 0xFFFFFFFF
    return {
        "path": path, "name": os.path.basename(path), "size": len(d),
        "A": a, "B": b, "L": ln, "C": c, "total": total,
        "ver": ver, "tag": tag,
        "calcA": calc_a, "aValid": a == calc_a,
        "lenValid": ln == len(d) - 16,
        "backups": sorted(glob.glob(path + ".bak-*"), reverse=True)[:10],
    }


def list_saves(root=None):
    root = root or default_save_dir()
    out = []
    for sub in ("Save", "Config"):
        p = os.path.join(root, sub)
        if not os.path.isdir(p):
            continue
        for f in sorted(glob.glob(os.path.join(p, "*.DAT"))):
            try:
                out.append(parse_save(f))
            except Exception as e:
                out.append({"path": f, "name": os.path.basename(f), "error": str(e)})
    return {"root": root, "exists": os.path.isdir(root), "saves": out}


def save_search(path, value, typ):
    with open(path, "rb") as f:
        d = f.read()
    pat = pack_value(parse_value(value, typ), typ)
    hits = []
    pos = 0
    while len(hits) < 300:
        i = d.find(pat, pos)
        if i < 0:
            break
        hits.append(i)
        pos = i + 1
    return {"offsets": hits, "count": len(hits), "pattern": pat.hex()}


def save_patch(path, edits, b_mode="keep", b_value="0"):
    with open(path, "rb") as f:
        d = bytearray(f.read())
    original_a, original_b, ln, _ = struct.unpack_from("<IIII", d, 0)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{path}.bak-{ts}"
    shutil.copy2(path, bak)
    applied = []
    for e in edits:
        off = int(e["offset"])
        typ = e.get("typ", "u32")
        val = parse_value(e["value"], typ)
        if off < 0 or off + TYPES[typ][1] > len(d):
            raise RuntimeError(f"偏移 0x{off:X} 越界")
        struct.pack_into("<" + TYPES[typ][0], d, off, val)
        applied.append({"offset": off, "value": val, "typ": typ})
    # A 校验已完整逆向：A = Σ(payload[0x10:]) + payloadLen
    new_a = (sum(d[0x10:]) + ln) & 0xFFFFFFFF
    struct.pack_into("<I", d, 0, new_a)
    # B 未逆向，按用户策略处理
    if b_mode == "zero":
        struct.pack_into("<I", d, 4, 0)
    elif b_mode == "custom":
        struct.pack_into("<I", d, 4, int(str(b_value), 0) & 0xFFFFFFFF)
    # else keep 原值
    with open(path, "wb") as f:
        f.write(d)
    STATE.note(f"存档已修改 {path}（备份 {os.path.basename(bak)}）")
    return {"backup": bak, "applied": applied, "oldA": original_a, "newA": new_a, "B": struct.unpack_from("<I", d, 4)[0], "bMode": b_mode}


def save_restore(path, backup=None):
    if not backup:
        baks = sorted(glob.glob(path + ".bak-*"), reverse=True)
        if not baks:
            raise RuntimeError("没有找到备份文件")
        backup = baks[0]
    if not os.path.isfile(backup):
        raise RuntimeError("备份文件不存在")
    shutil.copy2(backup, path)
    STATE.note(f"已从备份还原 {path}")
    return {"restored": backup}


def save_bytes(path, offset=0, length=256):
    with open(path, "rb") as f:
        d = f.read()
    offset = max(0, min(int(offset), max(0, len(d) - 16)))
    chunk = d[offset:offset + int(length)]
    rows = []
    for i in range(0, len(chunk), 16):
        part = chunk[i:i + 16]
        rows.append({
            "off": offset + i,
            "hex": " ".join(f"{x:02X}" for x in part),
            "ascii": "".join(chr(x) if 32 <= x < 127 else "." for x in part),
        })
    return {"offset": offset, "rows": rows, "size": len(d)}


# --------------------------------------------------------------------------
# HTTP API
# --------------------------------------------------------------------------
class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "UtawaTrainer/1.0"

    def log_message(self, *_):
        pass

    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, name, ctype):
        path = os.path.join(WEB_DIR, name)
        if not os.path.isfile(path):
            self.send_error(404)
            return
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path in ("/", "/index.html"):
                return self._file("index.html", "text/html; charset=utf-8")
            if u.path == "/api/processes":
                return self._send({"processes": list_processes()})
            if u.path == "/api/status":
                p = STATE.proc
                return self._send({
                    "attached": bool(p and p.h),
                    "pid": p.pid if p else None,
                    "name": p.name if p else None,
                    "base": p.base if p else 0,
                    "baseHex": f"0x{p.base:08X}" if p and p.base else "",
                    "baseSize": p.base_size if p else 0,
                    "win": IS_WIN,
                    "scanCount": len(STATE.addrs),
                    "scanInfo": STATE.scan_info,
                    "log": STATE.log[-30:],
                })
            if u.path == "/api/results":
                off = int(q.get("offset", ["0"])[0])
                cnt = min(500, int(q.get("count", ["100"])[0]))
                return self._send(STATE.results(off, cnt))
            if u.path == "/api/table":
                return self._send({"table": STATE.table, "file": TABLE_FILE})
            if u.path == "/api/saves":
                return self._send(list_saves(q.get("root", [None])[0]))
            if u.path == "/api/save/info":
                return self._send(parse_save(q["path"][0]))
            if u.path == "/api/save/bytes":
                return self._send(save_bytes(q["path"][0],
                                             q.get("offset", ["0"])[0],
                                             q.get("length", ["256"])[0]))
            if u.path == "/api/units/status":
                active = sum(1 for i in range(UNIT.count)
                             if (lambda a: a and (a[0] > 0 or a[2] > 0))(UNIT.file_attrs(i)))
                return self._send({
                    "loaded": bool(UNIT.unit_data), "located": bool(UNIT.base),
                    "base": UNIT.base, "baseHex": ("0x%08X" % UNIT.base) if UNIT.base else "",
                    "count": UNIT.count, "activeCount": active,
                    "source": UNIT.source, "labels": UNIT.labels,
                    "gameDir": UNIT.game_dir, "locks": list(UNIT_LOCKS),
                    "attached": bool(STATE.proc and STATE.proc.h),
                    "exePath": STATE.proc.exe_path if STATE.proc else "",
                })
            if u.path == "/api/units/list":
                only = q.get("onlyActive", ["1"])[0] != "0"
                return self._send({"units": unit_payload(only, q.get("q", [""])[0]),
                                   "labels": UNIT.labels, "located": bool(UNIT.base),
                                   "locked": list(UNIT_LOCKS)})
            if u.path == "/api/units/config":
                return self._send({"labels": UNIT.labels, "names": UNIT.custom_names})
            if u.path == "/api/live/status":
                return self._send({"stage": LIVE.stage, "total": len(LIVE.addrs),
                                   "info": LIVE.info, "anchor": LIVE.anchor,
                                   "anchorHex": ("0x%08X" % LIVE.anchor) if LIVE.anchor else "",
                                   "attached": bool(STATE.proc and STATE.proc.h)})
            if u.path == "/api/live/results":
                off = int(q.get("offset", ["0"])[0])
                cnt = min(200, int(q.get("count", ["60"])[0]))
                return self._send(LIVE.results(STATE.proc, off, cnt))
            if u.path == "/api/live/fields":
                return self._send(LIVE.fields(STATE.proc, int(q["addr"][0], 0),
                                              int(q.get("span", ["256"])[0])))
        except Exception as e:
            return self._send({"ok": False, "error": f"{type(e).__name__}: {e}"}, 200)
        self.send_error(404)

    def do_POST(self):
        u = urlparse(self.path)
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
            r = self.dispatch(u.path, body)
            return self._send(r if isinstance(r, dict) else {"ok": True, "data": r})
        except Exception as e:
            return self._send({"ok": False, "error": f"{type(e).__name__}: {e}"})

    def dispatch(self, path, b):
        if path == "/api/attach":
            pid = int(b["pid"])
            name = b.get("name", "")
            if STATE.proc:
                STATE.proc.close()
            p = WinProcess(pid, name)
            p.open()
            STATE.proc = p
            STATE.rebase_table()
            STATE.first_done = False
            STATE.addrs = array("Q")
            STATE.prev = array("d")
            STATE.orig = array("d")
            STATE.note(f"已附加 PID {pid}，模块基址 0x{p.base:08X}")
            return {"ok": True, "base": p.base, "baseHex": f"0x{p.base:08X}",
                    "baseSize": p.base_size}
        if path == "/api/detach":
            if STATE.proc:
                STATE.proc.close()
            STATE.proc = None
            return {"ok": True}
        if path == "/api/scan/first":
            cnt = STATE.first_scan(parse_value(b["value"], b.get("typ", "i32")),
                                   b.get("typ", "i32"), bool(b.get("align", True)))
            return {"ok": True, "count": cnt, "info": STATE.scan_info}
        if path == "/api/scan/next":
            cnt = STATE.next_scan(b["mode"], b.get("value"), b.get("extra"))
            return {"ok": True, "count": cnt}
        if path == "/api/scan/reset":
            STATE.first_done = False
            STATE.addrs = array("Q")
            STATE.prev = array("d")
            STATE.orig = array("d")
            STATE.scan_info = ""
            return {"ok": True}
        if path == "/api/write":
            STATE.write_addr(b["addr"], b["value"], b.get("typ"))
            return {"ok": True}
        if path == "/api/read":
            return {"ok": True, "value": STATE.read_addr(b["addr"], b.get("typ"))}
        if path == "/api/table/add":
            t = {
                "id": STATE.next_id, "name": b.get("name", "新地址"),
                "addr": int(b["addr"]), "typ": b.get("typ", "i32"),
                "value": b.get("value", 0), "locked": False,
                "lock_value": b.get("value", 0),
                "rva": None,
            }
            if STATE.proc and STATE.proc.base:
                d = t["addr"] - STATE.proc.base
                if 0 <= d < (STATE.proc.base_size or 0x1000000):
                    t["rva"] = d
            STATE.next_id += 1
            STATE.table.append(t)
            STATE.save_table()
            return {"ok": True, "table": STATE.table}
        if path == "/api/table/update":
            tid = int(b["id"])
            for t in STATE.table:
                if t["id"] == tid:
                    for k in ("name", "value", "locked", "lock_value", "typ", "addr"):
                        if k in b:
                            t[k] = b[k]
                    break
            STATE.save_table()
            return {"ok": True, "table": STATE.table}
        if path == "/api/table/remove":
            STATE.table = [t for t in STATE.table if t["id"] != int(b["id"])]
            STATE.save_table()
            return {"ok": True, "table": STATE.table}
        if path == "/api/table/apply":
            tid = int(b["id"])
            for t in STATE.table:
                if t["id"] == tid:
                    STATE.write_addr(t["addr"], t["value"], t["typ"])
                    break
            return {"ok": True}
        if path == "/api/save/search":
            return {"ok": True, **save_search(b["path"], b["value"], b.get("typ", "u32"))}
        if path == "/api/save/patch":
            return {"ok": True, **save_patch(b["path"], b["edits"],
                                             b.get("bMode", "keep"), b.get("bValue", "0"))}
        if path == "/api/save/restore":
            return {"ok": True, **save_restore(b["path"], b.get("backup"))}
        # ---------------- 实时角色定位 ----------------
        if path == "/api/live/scan":
            if not STATE.proc:
                raise RuntimeError("请先附加游戏进程")
            n = LIVE.scan(STATE.proc, b["value"],
                          tuple(b.get("types", ["u16", "u32", "f32"])))
            return {"ok": True, "count": n, "info": LIVE.info}
        if path == "/api/live/filter":
            n = LIVE.filter(STATE.proc, b.get("value"), b.get("mode", "equal"))
            return {"ok": True, "count": n, "info": LIVE.info}
        if path == "/api/live/snapshot":
            LIVE.snapshot(STATE.proc)
            return {"ok": True, "count": len(LIVE._last_addr)}
        if path == "/api/live/reset":
            LIVE.addrs = array("Q")
            LIVE.typs = []
            LIVE.stage = 0
            LIVE.anchor = 0
            LIVE.info = ""
            return {"ok": True}
        if path == "/api/live/write":
            STATE.write_addr(b["addr"], b["value"], b.get("typ", "u32"))
            return {"ok": True}
        # ---------------- 数据表模板（实验性） ----------------
        if path == "/api/units/prepare":
            if not STATE.proc:
                raise RuntimeError("请先在「内存修改」页附加游戏进程")
            gd = b.get("gameDir") or os.path.dirname(STATE.proc.exe_path or "")
            if not gd:
                raise RuntimeError("无法推断游戏目录，请手动指定 gameDir")
            src = UNIT.load(gd)
            base, hits = UNIT.locate(STATE.proc)
            if not base:
                raise RuntimeError("已在 %d 处找到特征码，但属性校验未通过；请确认游戏已载入战斗数据" % hits)
            STATE.note(f"人物属性表已定位：{('0x%08X' % base)}（特征码命中 {hits} 处）")
            return {"ok": True, "base": base, "baseHex": "0x%08X" % base,
                    "hits": hits, "source": src}
        if path == "/api/units/write":
            i, f = int(b["i"]), int(b["field"])
            if not UNIT.write(STATE.proc, i, f, b["value"]):
                raise OSError(ctypes.get_last_error(), "写入失败：内存不可写或进程已退出")
            STATE.note(f"属性写入 {UNIT.name_of(i)} 字段{f+1} = {b['value']}")
            return {"ok": True, "attrs": UNIT.read(STATE.proc, i)}
        if path == "/api/units/writebatch":
            i = int(b["i"])
            vals = b["values"]
            for f, v in enumerate(vals):
                if v is None or v == "":
                    continue
                UNIT.write(STATE.proc, i, f, v)
            STATE.note(f"批量写入 {UNIT.name_of(i)} 的属性")
            return {"ok": True, "attrs": UNIT.read(STATE.proc, i)}
        if path == "/api/units/restore":
            i = int(b["i"])
            orig = UNIT.restore(STATE.proc, i)
            UNIT_LOCKS.pop(i, None)
            return {"ok": True, "attrs": orig}
        if path == "/api/units/lock":
            i = int(b["i"])
            if b.get("on"):
                cur = UNIT.read(STATE.proc, i) or UNIT.file_attrs(i)
                UNIT_LOCKS[i] = cur
            else:
                UNIT_LOCKS.pop(i, None)
            return {"ok": True, "locked": list(UNIT_LOCKS)}
        if path == "/api/units/labels":
            labs = b["labels"]
            if not isinstance(labs, list) or len(labs) != unit_table.FIELDS:
                raise RuntimeError("字段名数量不正确")
            UNIT.labels = [str(x) for x in labs]
            save_unit_config()
            return {"ok": True, "labels": UNIT.labels}
        if path == "/api/units/rename":
            i, name = int(b["i"]), str(b["name"]).strip()
            if name:
                UNIT.custom_names[i] = name
            else:
                UNIT.custom_names.pop(i, None)
            save_unit_config()
            return {"ok": True, "name": UNIT.name_of(i)}
        raise RuntimeError("未知接口：" + path)


def main():
    if not os.path.isdir(WEB_DIR):
        print("找不到 web 目录")
        return
    threading.Thread(target=STATE.lock_loop, daemon=True).start()
    port = 18765
    srv = None
    for _ in range(20):
        try:
            srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            port += 1
    if not srv:
        print("无法绑定本地端口")
        return
    url = f"http://127.0.0.1:{port}/"
    print("=" * 58)
    print("  《传颂之物：虚伪的假面》单机修改器")
    print(f"  界面地址：{url}")
    print("  关闭此窗口即可退出修改器")
    print("=" * 58)
    if "--no-browser" not in sys.argv:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if STATE.proc:
            STATE.proc.close()


if __name__ == "__main__":
    main()
