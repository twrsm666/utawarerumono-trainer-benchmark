#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人物属性表：从游戏自身的 .sdat 数据包解析单位名与基础属性，
并在游戏进程内存里定位同一张表的运行时副本，实现按人物直接改数值。

【已在本机实测确认的结构】
  Data/CHN/DataBase.sdat -> UnitData.bin   (399126 B)
      @0 u32 count = 307
      属性块 i 位于 file offset 0xD8 + i*0x208，每块为 u16 数组
      i=0 哈克: 300 600 100 60 32 110 105 150 150 200 1536 1024
  Data/DataBase2.sdat    -> UnitTextData.bin (10912 B)
      @0 u32 count = 307，随后 307 个 u32 指向 UTF-8 名字串；
      每 3 个槽为一组（JPN | KOR | ZH），可从完整组建立 日/韩 -> 中文 映射。

【内存副本】
  游戏把 UnitData.bin 整表载入内存，并把文件内所有 u32 偏移重定位为
  「表基址 + 文件偏移」；属性数值保持原样。实测：
      特征码 UnitData[0xD0:0x100] 在 ~1GB 可读内存中唯一命中，
      base = hit - 0xD0；base + 0xD8 + i*0x208 的值与文件 9/9 一致。

本模块只在运行时读取游戏目录中的数据包，不复制、不分发任何原游戏文件。
"""
from __future__ import annotations

import os
import re
import struct

STRIDE = 0x208
ATTR_OFF = 0xD8
SIG_OFF = 0xD0
SIG_LEN = 0x30
FIELDS = 12

# 字段语义为「按数值形态推测」，界面允许重命名并持久化。
DEFAULT_LABELS = [
    "HP / 生命", "上限 / 气力", "攻击", "防御", "魔力 / 抗性",
    "命中", "回避", "速度 / 行动", "参数 8", "参数 9",
    "标志位 1", "标志位 2",
]

CJK = re.compile(r"[\u4e00-\u9fff]")
KANA_HANGUL = re.compile(r"[\u3040-\u30ff\uac00-\ud7af]")


def parse_sdat(path):
    """解析 Aquaplus 'Filename' 容器，返回 {name: bytes}。"""
    with open(path, "rb") as f:
        d = f.read()
    if d[:8] != b"Filename":
        raise RuntimeError("不是 sdat 容器：" + path)
    ptr = struct.unpack_from("<I", d, 12)[0]
    n0 = -1
    for i in range(ptr, min(ptr + 8, len(d) - 4)):
        if d[i:i + 4] == b"Pack":
            n0 = i
            break
    if n0 < 0:
        raise RuntimeError("找不到 Pack 索引：" + path)
    idx_size, count = struct.unpack_from("<II", d, n0 + 12)
    names_at = 16 + 4 * count
    parts = [x for x in d[names_at:n0].split(b"\0") if x]
    out = {}
    for i in range(count):
        off, size = struct.unpack_from("<II", d, n0 + 20 + i * 8)
        name = parts[i].decode("latin1") if i < len(parts) else ""
        if name and 0 <= off and off + size <= len(d):
            out[name] = d[off:off + size]
    return out


def _is_zh(s):
    return bool(CJK.search(s)) and not KANA_HANGUL.search(s)


def build_names(text_bin):
    """返回 307 个单位的可读中文名。"""
    n = struct.unpack_from("<I", text_bin, 0)[0]
    offs = struct.unpack_from("<%dI" % n, text_bin, 4)

    def s(o):
        e = text_bin.find(b"\0", o)
        return text_bin[o:e].decode("utf-8", "replace") if e > o else ""

    slots = [s(o) for o in offs]
    # 307 个槽 = 每 3 个语言槽(JPN|KOR|ZH)对应 1 个单位条目；
    # 多数条目只有日文槽（中文/韩文为空），故从完整组学 日/韩 -> 中文。
    groups = [slots[i:i + 3] for i in range(0, len(slots), 3)]
    alt2zh = {}
    for g in groups:
        if len(g) >= 3 and _is_zh(g[2]):
            if g[0]:
                alt2zh[g[0]] = g[2]
            if g[1]:
                alt2zh[g[1]] = g[2]
    names = []
    for i in range(n):
        g = groups[i // 3] if i // 3 < len(groups) else []
        cand = next((x for x in g if x), "")
        if _is_zh(cand):
            names.append(cand)
        elif cand in alt2zh:
            names.append(alt2zh[cand])
        else:
            names.append(cand)
    return names


class UnitTable:
    def __init__(self, game_dir=None):
        self.game_dir = game_dir or ""
        self.unit_data = b""
        self.names = []
        self.count = 0
        self.base = 0
        self.error = ""
        self.source = {}
        self.labels = list(DEFAULT_LABELS)
        self.custom_names = {}

    def load(self, game_dir=None):
        self.game_dir = game_dir or self.game_dir
        if not self.game_dir:
            raise RuntimeError("未指定游戏目录")
        p1 = os.path.join(self.game_dir, "Data", "CHN", "DataBase.sdat")
        p2 = os.path.join(self.game_dir, "Data", "DataBase2.sdat")
        for p in (p1, p2):
            if not os.path.isfile(p):
                raise RuntimeError("找不到数据表：" + p)
        m1 = parse_sdat(p1)
        m2 = parse_sdat(p2)
        if "UnitData.bin" not in m1:
            raise RuntimeError("CHN/DataBase.sdat 中缺少 UnitData.bin")
        if "UnitTextData.bin" not in m2:
            raise RuntimeError("DataBase2.sdat 中缺少 UnitTextData.bin")
        self.unit_data = m1["UnitData.bin"]
        self.names = build_names(m2["UnitTextData.bin"])
        self.count = struct.unpack_from("<I", self.unit_data, 0)[0]
        self.source = {
            "gameDir": self.game_dir,
            "unitDataSize": len(self.unit_data),
            "unitCount": self.count,
            "textSlots": len(self.names),
        }
        return self.source

    def file_attrs(self, i):
        off = ATTR_OFF + i * STRIDE
        if off + FIELDS * 2 > len(self.unit_data):
            return None
        return list(struct.unpack_from("<%dH" % FIELDS, self.unit_data, off))

    def name_of(self, i):
        if i in self.custom_names:
            return self.custom_names[i]
        if 0 <= i < len(self.names) and self.names[i]:
            return self.names[i]
        return "单位 #%d" % i

    def signature(self):
        return self.unit_data[SIG_OFF:SIG_OFF + SIG_LEN]

    def locate(self, proc):
        """在目标进程内存里定位表基址；返回 (base, hits)。"""
        if not self.unit_data:
            raise RuntimeError("请先加载数据表")
        if not proc or not proc.h:
            raise RuntimeError("请先附加游戏进程")
        sig = self.signature()
        hits = []
        for start, size in proc.regions():
            off = 0
            while off < size:
                want = min(1 << 20, size - off)
                data = proc.read(start + off, want)
                if data:
                    pos = data.find(sig)
                    while pos >= 0:
                        hits.append(start + off + pos)
                        pos = data.find(sig, pos + 1)
                        if len(hits) > 32:
                            break
                if len(hits) > 32:
                    break
                off += 1 << 20
            if len(hits) > 32:
                break
        # 用属性数值校验候选，排除巧合命中
        valid = []
        for h in hits:
            base = h - SIG_OFF
            raw = proc.read(base + ATTR_OFF, FIELDS * 2)
            if len(raw) == FIELDS * 2 and struct.unpack("<%dH" % FIELDS, raw)[:10] == tuple(self.file_attrs(0)[:10]):
                valid.append(base)
        self.base = valid[0] if valid else 0
        return self.base, len(hits)

    def addr_of(self, i, field):
        return self.base + ATTR_OFF + i * STRIDE + field * 2

    def read(self, proc, i):
        if not self.base:
            raise RuntimeError("尚未定位人物属性表")
        raw = proc.read(self.addr_of(i, 0), FIELDS * 2)
        if len(raw) != FIELDS * 2:
            return None
        return list(struct.unpack("<%dH" % FIELDS, raw))

    def write(self, proc, i, field, value):
        if not self.base:
            raise RuntimeError("尚未定位人物属性表")
        if not (0 <= i < self.count and 0 <= field < FIELDS):
            raise RuntimeError("单位或字段越界")
        v = int(value)
        if not 0 <= v <= 65535:
            raise RuntimeError("数值须在 0 ~ 65535 之间")
        return proc.write(self.addr_of(i, field), struct.pack("<H", v))

    def restore(self, proc, i, fields=None):
        orig = self.file_attrs(i)
        if orig is None:
            raise RuntimeError("单位越界")
        for f in (fields if fields is not None else range(FIELDS)):
            proc.write(self.addr_of(i, f), struct.pack("<H", orig[f]))
        return orig
