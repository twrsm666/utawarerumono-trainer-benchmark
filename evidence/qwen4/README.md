# Qwen4 证据

## `comparison.json`

逐行对照以下四项：

- Qwen4 存档修改器解析出的行（仅 GET）；
- 同槽位的真实运行角色；
- 下一槽位的真实运行角色；
- 六个数值字段的命中情况。

汇总：

- 同槽位名称命中：`0/18`
- 單位ID 等于下一槽位：`18/18`
- 同槽位数值字段命中：`108/108`
- Qwen4 存档校验和：有效

## `comparison.csv`

同样的数据，表格形式。

## `artifact-inventory.json`

产品文件、大小与 SHA-256。同时记录被排除的文件：存档备份、抽取出的游戏数据、分析转储、生成的 blob，以及 93.7 MB 的可执行文件。

## 复现

在游戏与 Qwen4 服务同时运行时执行 [../../scripts/capture_runtime_comparison.py](../../scripts/capture_runtime_comparison.py)。脚本只发 GET 请求并读取游戏内存，不写入任何一侧。

## 隐私

本目录不含任何 `.DAT` 文件、抽取出的游戏文本或 Qwen4 二进制。
