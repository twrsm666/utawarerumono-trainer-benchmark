#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立复现：验证存档头部 A 校验公式。

用法：python verify_checksum.py [存档根目录]
不依赖修改器后端，可直接用来核对新存档 / 其它机器上的存档。
"""
import glob
import os
import struct
import sys
import zlib

DEFAULT = os.path.join(os.path.expanduser("~"), "Documents", "AQUAPLUS",
                       "受讚頌者 虛偽的假面")


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    files = []
    for sub in ("Save", "Config"):
        files += sorted(glob.glob(os.path.join(root, sub, "*.DAT")))
    if not files:
        print("找不到存档：", root)
        return
    ok = 0
    print(f"{'文件':<18} {'大小':>8} {'A 存储':>10} {'A 计算':>10} {'CRC32(payload)':>16}  B")
    print("-" * 88)
    for p in files:
        with open(p, "rb") as f:
            d = f.read()
        a, b, ln, c = struct.unpack_from("<IIII", d, 0)
        calc = (sum(d[0x10:]) + ln) & 0xFFFFFFFF
        crc = zlib.crc32(d[0x10:]) & 0xFFFFFFFF
        good = calc == a
        ok += good
        print(f"{os.path.basename(p):<18} {len(d):>8} {a:>10X} {calc:>10X} "
              f"{crc:>16X}  {b:08X}  {'OK' if good else 'FAIL'}")
    print("-" * 88)
    print(f"A 公式验证：{ok}/{len(files)} 通过")
    print("A = sum(save[0x10:]) + (len(save) - 16)   [mod 2^32]")
    print("注意：B 不匹配此处 CRC32，也非 FNV/Adler/MD5/SHA + 常量偏移，算法未解。")
    print("      C 常见 0 或 0xBB80，是游戏数据而非校验和。")


if __name__ == "__main__":
    main()
