# 《传颂之物：虚伪的假面》修改器制作 · 交接说明书

版本：2026-11-08 　面向对象：接手制作修改器（Trainer）的另一个模型 / 工程师
本文自包含。凡标注【实测】的都是本机验证过的事实；标注【未验证】的是推测或待办，不要当成结论。

---

## 0. 一页速览（先读这节）

**任务**：为 PC 版《传颂之物：虚伪的假面》（Utawarerumono: Mask of Deception）制作一个**单机修改器**（Trainer），典型功能：无限金钱、全道具、无限 BP/经验、战斗一击必杀、无限行动/技能、速度倍率等。

**游戏是什么**：Aquaplus（アクアプラス）出品的 SRPG/AVG 混合体，2015 年 PS 系首发，2020-04-15 的 PC 版（Steam 发行，含官方中文）。引擎为 Aquaplus 自研 **UT 引擎**（与同系列《致逝者的摇篮曲》HD 版同族，大量类名 RTTI、自研内存分配器 `Kernel::CAllocator`）。

**关键结论**：
- 32 位 PE（PE32, i386），**无任何反作弊**（未发现 EAC/BattlEye/VMProtect/Themida 导入或字符串）；有 `steam_emu.ini`（Steam 模拟器，纯离线）→ **普通的 ReadProcessMemory / WriteProcessMemory 方案可行**
- 战斗/成长/存档系统全部有 RTTI 类名可作锚点（见 §5），且**存档文件是明文结构、未加密**（§4）——存档编辑路线同样可行，可作为内存方案失败时的 Plan B
- 已有一个 2021 年的第三方修改器（§9），加壳无静态信息；本机另有 FLiNG Trainer 工具链（`D:\<LOCAL_TOOLCHAIN>\`）可参考

---

## 1. 游戏身份与环境（全部【实测】）

```text
安装目录（当前）：D:\<WORK_ROOT>\ChuanSongZhiWu\
  注意：原在 D:\Games\Utawarerumono_Mask_of_Deception\，2026-11-08 已搬迁到这里；
        若再移动，用 exe 名 "Utawarerumono Mask of Deception.exe" 全盘搜索即可重新定位。

主程序：Utawarerumono Mask of Deception.exe
  size = 6,130,176 B
  md5  = c02107b577a8e3be7965b5b50594abfc
  PE timestamp = 2019-12-23T06:08:01Z（2020-04-15 为文件分发时间）
  进程名 = "Utawarerumono Mask of Deception.exe"（含空格，写工具时注意引号转义）

运行库：avcodec/avformat/swscale 等 FFmpeg-4.x DLL + D3D11（dxgi/d3d11 导入）
       + steam_api.dll（配套 steam_emu.ini = Steam 模拟器，无需 Steam 在线）

存档目录：C:\Users\<用户>\Documents\AQUAPLUS\受讚頌者 虛偽的假面\
  Save\GAME-001.DAT   65,360 B   （第1号存档）
  Save\GAME-002.DAT   65,360 B   （第2号存档）
  Save\SYSTEM.DAT     82,656 B   （全局：系统进度/图鉴/设置等）
  Config\SETTING.DAT     176 B   （画面/按键等设置）

文本语言：官方繁体中文（CHN 包）。本机已安装简体字形补丁（见 §10），
          文本内容仍是繁体字符串，仅字库图集换成了简体字形。
```

---

## 2. PE 布局与地址换算【实测】

```text
imageBase = 0x400000（PE32，Machine=0x14C，Optional.Magic=0x10B）

节表：
  .text  va=0x001000  raw=0x000400  rawSize=0x16C600   → va = file + 0xC00
  .rdata va=0x16E000  raw=0x16CA00  rawSize=0x3A9600   → va = file + 0x1600
  .data  va=0x518000  raw=0x516000  rawSize=0x08B800   → va = file + 0x2000
  _RDATA va=0x18931000 raw=0x5A1800（小）
  .rsrc  va=0x18932000 raw=0x5A1E00

⚠ 与一代不同：一代全文件统一 va = file + 0x400C00；二代必须按节换算（上表）。
   例：BMF 字体表 file 0x51B830 → va = 0x51B830 + 0x2000 = 0x51D830。
```

**ASLR**：exe 带 `IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE` 的话，运行时模块基址会随机。
→ 修改器**永远用 模块基址 + RVA**，不要写死 0x400000。用 CE 的 "Pointer scan / Pointer map" 或自己写
`GetModuleHandle + RVA` 即可。CE 请用 **32 位版**（游戏是 32 位进程，64 位 CE 也能附但脚本要选对）。

---

## 3. 引擎技术档案（做修改器时用得上的部分）

```text
1) 引擎 = Aquaplus UT2（exe 内可见 "UT2OP"、"logo_DMMGAMES.TEX"，DMM Games 发行版）。特征：
   - 自研分配器 Kernel::CAllocator；对象大多 new 在引擎堆上（非 CRT 堆），
     CE 的 "普通堆扫描" 可能扫不到 → 用 "Value scan 全内存" 或直接走指针路径
   - 任务系统 CTaskManager（战斗/菜单/对话各是 Task 对象），战斗流程 = 一批 CBattle@@ 任务
   - 窗口标题不在明文里（资源段/运行时生成；且随语言变）→ 修改器认进程请用进程名，
     不要靠窗口标题匹配

2) 数据包 .sdat = 自研 "Filename" 容器：
   magic "Filename" + 索引表 + 名字表 + Pack 成员对表，成员偏移为**整文件绝对偏移**
   解析器现成：workspace/utawa/sdat.js（parse(buf) → 成员数组，含 name/off/size/abs）
   二代主要包：
     Data/DataBase2.sdat（8.7 MB，578 成员：NameText/ScriptText/BaseText/Battle*/Item* 等）
     Data/CHN/DataBase.sdat（2 MB，243 成员）、CHN/ScriptEvent.sdat（3.5 MB，353 成员）
     CHN/Grp1.sdat（1.6 GB 美术）、CHN/Grp2.sdat（548 MB）、CHN/Grp3.sdat（5 MB）
     Data/Model.sdat（482 MB）、Data/Voice.sdat（388 MB）、Data/SE.sdat、Data/BGM.sdat…

3) 贴图 .tex = 自研 LZSS（标签写 "LZ77" 但**不是** deflate/LZ4/LZMA）
   已完整破译，编解码器现成：workspace/utawa/lzdec_lib.js / lzenc.js
   （若修改器要做"换立绘/改 UI"之类，直接可用）

4) 文本槽位：每条记录含 3 个语言槽，顺序 JPN | KOR | ZH（比一代少 EN）。
   UTF-8、NUL 分隔。剧本 = ScriptEvent.sdat 的 *.BIN（字节码，结构未逆向）。

5) 字体：exe 内嵌 BMFont 表（va 0x51D830，"BMF\x03"，13,977 条 码位→x,y,w,h）。
   图集 = Data/CHN/Texture/font.tex（2688×5216 RGBA8，白字+alpha）。
```

---

## 4. 存档系统【实测，修改器的重要路线】

### 4.1 文件头结构（GAME-*.DAT / SYSTEM.DAT / SETTING.DAT 三者同构）

```text
偏移    类型      含义
0x00    u32       校验/哈希 A（疑似 CRC32，未验证）
0x04    u32       校验/哈希 B
0x08    u32       负载长度 = 文件长度 − 16      （GAME: 0xFF40, SYSTEM: 0x142D0）
0x0C    u32       校验/哈希 C
0x10    char[8]   "1.00\0\0\0\0"（存档格式版本）
0x18    char[8]   "GAME"/"SYSTEM"/"SETTING"（类型标签，NUL 补齐）
0x20    u32       文件总长度（GAME: 0xFF50=65360, SYSTEM: 0x142E0=82656, SETTING: 0xB0=176）
0x24    ...       类型相关的负载（GAME: 记录头 + 存档描述 + 数据区）
```

GAME-001.DAT 负载开头的实测样本（UTF-8 明文可见）：

```text
@0x28  "旅店（傍晚）"   ← 存档描述（玩家可见的档名信息）
再往后有 "哈克"（主角名）、"那接下來該做什麼呢"（当前进度摘要）等 UTF-8 字符串
```

### 4.2 两个存档的差异（用于反推数据区）

```text
GAME-001 vs GAME-002：65,360 B 中 18,207 B 不同，1563 个差异区段
→ 说明数据是【接近明文/未压缩】的结构化数据（不是整块加密），
  改数值后若校验和能重算，存档编辑完全可行
```

### 4.3 存档编辑路线的关键待办（交给接手者）

```text
① 校验和：header 里 A/B/C 三个 u32 极可能是 CRC32/其它。验证方法：
   把同一存档复制一份、只改 1 个字节 → 进游戏读档 →
   若游戏提示"存档损坏"，说明有校验；用反汇编找 CSave 的序列化函数
   （RTTI 有 .?AVCSave@@ / .?AVCSaveLoadBase@@ 可 xref）确认算法后重算。
② 定位金钱/BP/道具：两种办法
   - 内存法（推荐）：CE 找到数值 → 把该 u32 的字节模式在 GAME-*.DAT 里搜 → 得到存档偏移
   - 差分法：两个不同进度存档对比，找"通常是 4 字节小整数"的差异点
③ SYSTEM.DAT（82 KB）里大概率有：图鉴解锁、周目数、总击杀/总回合等统计——
   想改"全图鉴解锁"就看这里（负载 @0x24 起）
```

---

## 5. 修改器要改什么：功能清单与实现锚点

### 5.1 推荐的功能集（按实现难度排序）

| 功能 | 目标值 | 寻找路径 |
| --- | --- | --- |
| 金钱 | 4 字节整数（几十~几万量级） | CE 已知值扫描 → 买卖东西改变 → 重扫 → 指针 |
| BP（战斗点数，升级用） | 4 字节整数（战后结算） | 同上；RTTI 有 `CBattleBonusPointTask@Battle@@` |
| 单位等级/经验 | 4 字节 / 可能是 16 位 | 战后结算界面扫描；`CLevelUpTask@Battle@@` |
| 道具数量 | 4 字节（背包堆叠数） | `CItemList@Window@@`，先找数量后找数组基址 |
| 战斗 HP / 一击必杀 | float 或 int（HP 大概率 int） | 战斗中扫当前 HP → 被打变化 → 指针；`CDamageAct@@` |
| 行动力/技能使用 | 不明（可能每回合重置） | 战斗内多次行动前后扫描 |
| 移动/战斗速度 | 无直接字段 | `CBattleSpeed@Battle@@` 存在！可试写速度倍率 |
| 必定暴击/连击 | 判定逻辑 | `CCriticalRingTask@@` / `CChainRingTask@@`（圈圈判定） |

**注意**：以上"目标值类型"是同类游戏的常见形态，**必须实测确认**。不要相信任何未验证的偏移。

### 5.2 RTTI 类名锚点（exe 内字符串，用 xref 定位代码 / 结构）

已从 exe 提取 226 个 RTTI 名，关键的：

```text
战斗：  .?AVCBattle@Battle@@      .?AVCBattleMap@Battle@@   .?AVCStatusTask@Battle@@
        .?AVCLevelUpTask@Battle@@ .?AVCBattleBonusPointTask@Battle@@
        .?AVCDamageAct@@          .?AVCCriticalRingTask@Battle@@  .?AVCChainRingTask@Battle@@
        .?AVCBattleSpeed@Battle@@ .?AVCBattleResultTask@Battle@@ .?AVCGameOverTask@Battle@@
        .?AVCSimulateMode@Battle@@（战斗模拟模式，可能有额外入口）
        .?AVCPreViewMode@Battle@@
存档：  .?AVCSave@@  .?AVCSaveLoadBase@@  .?AVCSaveDataList@Window@@
事件：  .?AVCEventFlagBase@Kernel@@（剧情旗标基类！）  .?AVCEventMain@GameEvent@@
        .?AVCEvtMes@GameEvent@@（对话）  .?AVCEvtUnit@GameEvent@@
管理：  .?AVCTaskManager@@  .?AVCModelManager@@  .?AVCFaceManager@@  .?AVCSpriteManager@@
成长：  .?AVCLevelUpAct@@   .?AVCWinSimpleStatus@Window@@
```

**怎么用**：
1. 字符串在 exe 的 .rdata/data 段（file 偏移 = 字符串位置，va = file + 节 delta）
2. 找**谁引用这个 RTTI 字符串**（4 字节小端立即数 = va），那就是 vftable 构造函数附近 →
   顺着 vftable 找虚函数 → 找到 serialize / 战斗结算 / 数值更新
3. 本机 workspace 里已有完整的 capstone-wasm 反汇编工具链和套路脚本（见 §8），直接改路径复用

参考技巧（一代项目验证过）：`disasm*.js` 里 `va = file + DELTA`，二代需按节 delta（§2 表）。

---

## 6. 实现路线（三条，建议顺序 A → B → C）

### 路线 A：实时内存修改（推荐，用户习惯的形态）

```text
工具链：Cheat Engine 32 位（找值）→ 自己写 C# / C++ 32 位 trainer（稳定运行）
步骤：
1. 启动游戏到战斗/菜单，CE 附加 "Utawarerumono Mask of Deception.exe"
2. 扫描类型先试 "4 Bytes"，不行试 "2 Bytes"/"Float"
3. 找到稳定地址后做"基址+偏移"：
   内存里那个地址每次重开都会变（引擎堆）→ 必须找静态指针链
   做法：CE → Pointer scan（max level 3~5，max offset 0x2000）→ 重启游戏验证至少 3 次
4. 拿到指针链后写 trainer：
   c# Process.GetProcessById + 模块基址(Process.Modules) + 偏移链 + ReadProcessMemory
   热键：RegisterHotKey（F1 金钱、F2 BP、F3 道具…）
5. 数值写入建议：金钱类"锁定"用定时器轮询写；HP 类注意战斗对象会重建（每场战斗换对象），
   要在每场战斗开始时重新定位（hook 或特征扫描）
```

**注意**：
- 32 位目标 → 写 32 位 trainer（AnyCPU 也行但要用 32 位进程读写）
- 游戏窗口全屏时 CE 附加正常；WriteProcessMemory 无需管理员权限（除非游戏提权）
- 不要用"修改 exe 文件"的方案（游戏会校验自身？未验证；且升级/搬迁易失效）

### 路线 B：存档编辑（Plan B，或作为"一次性大改"功能）

```text
优点：不用处理指针链/ASLR，一次改完读档即生效
缺点：必须先解决校验和（§4.3①），否则游戏拒读
建议实现：读 GAME-*.DAT → 按 §4.1 头结构定位负载 → 在负载区搜目标值 u32 →
          改值 → 重算 header 三个哈希（算法待逆向）→ 写回
注意：改前必须备份原存档（工具里自动 .bak）
```

### 路线 C：DLL 注入 / Hook（进阶）

```text
适合做"必定暴击""无限行动"这类逻辑修改：
- 注入 DLL，hook CCriticalRingTask / CChainRingTask 的判定函数直接返回成功
- 或 hook CBattleBonusPointTask 的结算函数把 BP 改成固定值
前提：先用反汇编确认函数签名与调用约定（cdecl/thiscall）
风险：崩溃概率高，必须做"可关闭"开关
```

---

## 7. 接手第一天该做什么（照抄执行，1 小时内能出结论）

```text
STEP 1 定位游戏（可能又搬家）：
  全盘搜索 "Utawarerumono Mask of Deception.exe"，确认 md5 = c02107b577a8e3be7965b5b50594abfc
STEP 2 验证存档路径：
  C:\Users\<用户>\Documents\AQUAPLUS\受讚頌者 虛偽的假面\Save\
  先备份整个 Save 目录（改坏了能恢复）
STEP 3 启动游戏 → 进入有金钱/BP 的界面 → CE 32 位附加
  建议先找"金钱"：买/卖一次改变数值 → 变化量扫描 → 确认是 4 字节
STEP 4 找到地址后：CE → "找出是什么访问了这个地址" → 看是哪个函数在读写 →
  这个函数就是"金钱读写的代码"，RTTI/反汇编可以从这里反推结构
STEP 5 做指针扫描 → 重启游戏 3 次验证稳定 → 写成 trainer 骨架
STEP 6 若内存路线卡住：转存档路线（§4）先做"读档改钱"的最小闭环
```

---

## 8. 可复用的现成工具（都在 C:\Users\<USER_ID>\Documents\Qoder\2026-11-04\7a9fd51c\utawa\）

| 文件 | 用途 |
| --- | --- |
| `sdat.js` | sdat 容器解析（parse → 成员表）——读 DataBase2/ScriptEvent 等 |
| `lzdec_lib.js` / `lzenc.js` | tex 的 LZ77 解码/编码（做 UI/立绘替换时用） |
| `bmf.js` | exe 内 BMF 字体表解析（码位→图集坐标） |
| `disasm*.js` + `capstone-wasm` | 反汇编套路：读 PE、按 RVA 转文件偏移、线性反汇编、xref 搜索 |
| `g2_*.js` | 二代专项（BMF 定位、语料、字体烘焙）——改路径即可复用 |
| `trainer_recon.js` | exe 字符串+PE 段扫描（本说明书 §2/§5 数据的来源） |
| `rtti_scan.js` | RTTI 类名提取（可再筛） |

**坑（一代项目踩过，通用）**：
- 中文/非 ASCII 字符串**不要**通过 shell 参数或 `node -e` 传（Git Bash 会破坏编码）；
  一律写进 .js 文件里用 `\uXXXX` 转义
- 分析结果落文件（*.out）再读，不要靠 stdout 看中文
- 游戏运行时写游戏目录文件会 EBUSY——写文件前先关游戏
- exe 是 32 位：所有地址 4 字节，指针扫描别用 64 位模式

---

## 9. 已存在的第三方修改器（参考，不要盲信）

```text
D:\<WORK_ROOT>\传颂之物-虚伪的假面修改器 (3)\传颂之物-虚伪的假面修改器.exe
  size = 9,637,888 B（9.6 MB，2021-02-02）
  加壳（静态字符串全是压缩噪声），无法直接参考其偏移
  可能来源：国内修改器站的通用壳工具（如"某宝修改器"），
  风险：可能被杀软报毒、可能与新版存档/系统不兼容
  建议：只把它当"功能清单参考"，不复制其代码
D:\<LOCAL_TOOLCHAIN>\：FLiNG 通用修改器框架（本机已有），
  可用于研究 trainer 的 UI/热键框架（.NET）
```

---

## 10. 与字体补丁的关系（重要，别弄冲突）

本机已对游戏做过**繁体→简体字形替换**（只改 `Data/CHN/Texture/font.tex`，文本未改）：

```text
Data/CHN/Texture/font.tex      现为简体字形  md5 = a7dad69b6e2795a9  8,549,464 B
Data/CHN/Texture/font.tex.orig 原版繁体备份  md5 = ed47cf9c0ff96c98  8,386,360 B
```

修改器**不要**去动 font.tex；若用户要求"还原繁体"，跑
`node g2_install_font.js restore`（脚本在 workspace，路径按当前安装目录改）。

---

## 11. 纪律与风险

```text
1) 仅限单机离线使用；本游戏无联网对战，修改不影响他人
2) 分发时不要附带任何原游戏文件（sdat/tex/exe 都是版权内容）
3) 改存档前必须自动备份；提供"一键还原"按钮
4) 数值写入要防越界（道具数量别写成 99999 导致数组越界崩溃）
5) 战斗类修改在"战斗结束/读档/重开"后可能失效——这是引擎对象重建，不是 bug，
   要提示用户重新按热键
6) 不修改 exe 文件本体（保持可回滚）
```

---

## 12. 已知未解 / 交给接手者的开放问题

```text
① 存档校验算法（3 个 u32 哈希）——存档编辑路线的前置条件【最高优先级】
② 战斗 HP 与单位的对象布局（CBattle/CBattleMap 的成员偏移）——需要动态调试
③ 金钱/BP 的静态指针链——CE 指针扫描
④ ScriptEvent.sdat 的脚本字节码格式——做"剧情旗标修改/跳关"才需要
⑤ CBattleSpeed / CSimulateMode 是否可直接改——可能有意外功能（快速战斗/模拟）
⑥ SYSTEM.DAT 全局数据布局（图鉴/周目）——做"全解锁"需要
```

**接手者第一步：按 §7 跑 STEP 1~4，把"金钱"在内存里的地址、读取它的函数、以及该值在 GAME-*.DAT 里的偏移三者对齐——这三条信息一到手，其余功能都是同一套流程的复制。**
