# Hy4：历史产物

状态：**在本基准中未通过验收。**

这是标为 Hy4 的会话所交付源码的脱敏只读快照。保留它是为了让失败分析可核查，而不是推荐把它当可用修改器。

## 快照内容

- `trainer-source/utawa_trainer.py` — 扫描后端与本地 HTTP 接口。
- `trainer-source/unit_table.py` — 静态 `UnitData.bin` 解析器。
- `trainer-source/index.html` — 网页界面。
- `trainer-source/verify_checksum.py` — 存档头校验和分析。
- `trainer-source/README.md` — 原始说明，含 Agent 自己的更正声明。
- `trainer-source/start.bat`、`启动修改器.bat` — 启动脚本。

没有产出可执行文件。

## 隐私脱敏

本机用户目录替换为 `<USER_HOME>`，游戏／工作目录替换为 `<GAME_DIR>` 或 `<WORK_ROOT>`。运行这份历史源码前必须先自行配置这些占位符。

## 为什么被拒绝

实现把静态角色模板数据当成了实时角色状态。其最终消息自认显示的数值与游戏不符；后续的补救是“手动改值扫描器”，不是所要求的稳定按人物编辑页面。

延伸阅读：[../../docs/HY4_ANALYSIS.md](../../docs/HY4_ANALYSIS.md)、[../../evidence/hy4/final-response.md](../../evidence/hy4/final-response.md)。

## 安全

这是历史代码，能读写进程内存，也能编辑存档文件，且未重新验证其破坏性行为。不要把它指向你在意的存档或进程。
