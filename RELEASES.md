# 发布物

## v1.1-k31 — 通过验收的产物与失败样本

GitHub Release：`releases/tag/v1.1-k31`

### 资产一：K3.1 修改器（通过验收）

- 文件名：`k31-trainer-v1.1.exe`
- 大小：36,407,921 字节
- SHA-256：`fc56b3ca386e4823b0fe32ec11b3a957611ac3f094e592bdfaeea666380573da`
- 构建：2026-11-11，由恢复的最终源码在中性路径重建，PE 资源版本 1.1.0
- 运行环境：Windows 10/11 x64；需要 README 中所述的确切 32 位游戏版本

这是**可复现的重建版**，不声称与 2026-11-08 被删除的二进制逐字节一致。

功能：

- 以读写权限附加 `Utawarerumono Mask of Deception.exe`；
- 读取 18 个核心人物页，并校验角色表形状；
- 编辑 13 项：等级、当前经验、累计经验、BP、最大／当前 HP、攻击、防御、速度、移动、跳跃、最大／当前气力；
- 写入后回读，支持逐项锁定；
- 不修改游戏可执行文件，不修改存档文件。

### 资产二：Qwen4 存档修改器（失败样本，中性路径重建版）

- 文件名：`qwen4-save-editor-rebuilt.exe`
- 大小：87,227,904 字节
- SHA-256：`f01ce4fc20e557175e04f7bb17a554ad2c002065ef9e520299e144b898478460`
- 来源：Qwen4 自带的 `build_exe.js` + `trainer-sea.js` + `public/index.html`
- 改动：仅把硬编码的存档目录 `C:/Users/<本机账号>/Documents/AQUAPLUS/…` 改为按当前用户目录解析（可用环境变量 `UTAWA_SAVE_DIR` 覆盖），其余逻辑与其源码一致

**警告：这是已知映射错误的存档写入器，不要用它修改真实存档。** 它在这里只作为失败证据存在：界面显示 18 行、存档校验和有效，但角色 ID 与数值整体错开一个槽位。

为什么发布重建版而不是原始版：原始 EXE 内嵌了操作者的本机绝对路径，直接公开等同于泄露账号名。原始版的大小与哈希仍被记录，可用于证明“评测的确实是这个文件”：

| 版本 | 大小 | SHA-256 |
| --- | ---: | --- |
| 原始版（不公开） | 93,733,376 | `4a6525a2c8657eb598cc18aa9b5ba5d005797ee428b9a55237b58427a3d2e4dd` |
| 中性路径重建版（公开） | 87,227,904 | `f01ce4fc20e557175e04f7bb17a554ad2c002065ef9e520299e144b898478460` |

两者在角色映射上的错误表现一致（见 [Qwen4 分析](docs/QWEN4_ANALYSIS.md) 与界面截图 [docs/assets/qwen4-ui.png](docs/assets/qwen4-ui.png)）。

### 不包含

- 游戏可执行文件与任何游戏资源。
- 存档文件与存档备份。
- Hy4 的可执行文件（它没有产出）。
- 第三方修改器或 Cheat Engine 表。
- 原始私人会话全文。

### 被取代／被拒绝的产物

| 会话 | 原始可执行文件 | SHA-256 | 状态 |
| --- | --- | --- | --- |
| Hy4 | 无 | 不适用 | 无打包产物 |
| Qwen4 | 93,733,376 字节 | `4a6525a2c8657eb598cc18aa9b5ba5d005797ee428b9a55237b58427a3d2e4dd` | 原始版不公开；已发布中性路径重建版 |
| K3.1 v1.0（已被取代） | 36,409,143 字节 | `90e94d8801efd72382d63db23fc8fafb1c5e86bd93c9e4ba3f40fa5bccf11273` | 输入覆盖缺陷修复后被 v1.1 取代 |

### 校验

```powershell
Get-FileHash .\k31-trainer-v1.1.exe -Algorithm SHA256
Get-FileHash .\qwen4-save-editor-rebuilt.exe -Algorithm SHA256
```

预期：

```text
FC56B3CA386E4823B0FE32EC11B3A957611AC3F094E592BDFAEEA666380573DA
F01CE4FC20E557175E04F7BB17A554AD2C002065EF9E520299E144B898478460
```

### 测试证据

- [测试日志](evidence/k31/test-results.txt)
- [打包自检输出](evidence/k31/packaged-smoke/packaged-smoke.txt)
- [修改器运行截图](docs/assets/k31-running.png)
- [游戏内对照截图](docs/assets/k31-game-truth.png)
- [源码溯源](evidence/k31/source-provenance.json)
- [Qwen4 逐行对照](evidence/qwen4/comparison.csv)
