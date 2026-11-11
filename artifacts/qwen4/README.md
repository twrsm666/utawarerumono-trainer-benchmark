# Qwen4：被拒绝的存档修改器

状态：**就所要求的产品而言未通过验收。**

> 不要用这份源码处理真实存档。它的角色到 ID 的映射已被证明错误。原始可执行文件不直接公开。

## 为什么保留它

保留源码是为了让失败可复现、可审阅。它实现了：

- 存档头校验和的验证与重算；
- 角色行解析；
- 本地网页界面；
- 存档备份与还原；
- 单文件打包。

## 失败在哪里

同槽位的数值是对的，但每个角色的 ID／名称都取自下一槽位：

- 0/18 名称与同槽位真实角色一致；
- 18/18 的 ID 等于下一槽位的 ID；
- 108/108 抽样数值属于同一槽位。

结果是一个看起来完整、却会在熟悉的名字下改到另一个角色数值的编辑器。详见 [../../docs/QWEN4_ANALYSIS.md](../../docs/QWEN4_ANALYSIS.md)。

## 快照内容

`save-editor-source/` 为产品源码：

- `saveengine.js`
- `server.js`
- `trainer-sea.js`
- `trainer-bundle.js`
- `build_exe.js`
- `sea-config.json`
- `unit_names.json`
- `ui-index.html`
- `启动修改器.bat`

以下内容被有意排除：

- 存档文件与存档备份；
- 抽取出的 `NameTextData.bin`、`UnitTextData.bin` 与游戏数据；
- 分析用反汇编转储；
- `trainer.blob`；
- 93,733,376 字节的原始可执行文件（内嵌本机用户路径）。

## 脱敏

源码快照把本机路径替换为 `<USER_HOME>`。在测试者自行提供存档目录前，它不能就地运行。原始产物清单与哈希见 [../../evidence/qwen4/artifact-inventory.json](../../evidence/qwen4/artifact-inventory.json)。

## 原始可执行文件

- 大小：93,733,376 字节
- SHA-256：`4a6525a2c8657eb598cc18aa9b5ba5d005797ee428b9a55237b58427a3d2e4dd`

不公开是出于隐私与安全考虑，而非操作者拿不到该文件。

## 公开的重建版

为便于复现其错误表现，Release 中附带了用其自带构建脚本在中性路径下重建的单文件程序：

- 文件名：`qwen4-save-editor-rebuilt.exe`
- 大小：87,227,904 字节
- SHA-256：`f01ce4fc20e557175e04f7bb17a554ad2c002065ef9e520299e144b898478460`

它仍会写存档且映射仍然错误，仅用于复核。
