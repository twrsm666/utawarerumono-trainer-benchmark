# K3.1：通过验收的修改器

状态：**在本基准中通过验收。**

发布资产为 `k31-trainer-v1.1.exe`。`trainer-source/` 中的源码是从平台文件历史恢复的最终版本，2026-11-11 用它重建并重新验证了该可执行文件。

## 源码结构

```text
trainer-source/
├── app.py             PySide6 界面、逐项锁定、手动刷新
├── game_memory.py     Win32 进程读写与角色表解析
├── build.py           PyInstaller 打包 + 图标/版本资源生成
├── tests/             解析、实机读取、实机写入、界面回归测试
└── tools/recon.py     开发期使用的只读侦察工具
```

## 环境

- Windows 11
- Python 3.13.x x64
- PySide6 6.12.0
- PyInstaller 6.22.3
- 游戏 PE MD5 `c02107b577a8e3be7965b5b50594abfc`

## 构建

```powershell
python -m pip install PySide6-Essentials PyInstaller
python -m unittest discover -s tests -p "test_core.py" -v
python tests/ui_smoke_test.py
python tests/live_write_test.py
python build.py
```

产物输出到 `dist/`。

## 安全属性

- 不修改游戏文件。
- 不写存档文件。
- 写入前校验已知角色表与每个目标角色。
- 每次写入后回读。
- 字段获得焦点或处于待写入状态时不做自动刷新。
- 锁定是显式操作，可随时解除。

## 溯源

原始工作树在后来的清理中被删除，最终源码从平台文件历史恢复。发布的可执行文件是重建版，不是被删除的 2026-11-08 二进制的逐字节副本。详见 [../../docs/K31_ACCEPTANCE.md](../../docs/K31_ACCEPTANCE.md)。

## 限制

该修改器面向一个特定游戏版本与一种运行时角色表布局。未经重新验证，不能移植到其他补丁或重制版。
