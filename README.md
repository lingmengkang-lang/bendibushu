# bendibushu（本地离线工控 AI 助手）

> **仓库对应**：GitHub（lingmengkang-lang/bendibushu）与 CNB（gongyeyingyong/bendibushu）同名；工程目录名为 local-offline-assistant。

**Windows 本机离线 AI 助手，专做工控软件应用：PLC 编写、变频器（VFD）调试、伺服电机调试、触摸屏（HMI）/ 组态软件（组态王、MCGS、台达 DIAEntegro、WinCC 等）、编码器使用、上位机程序编写，以及"自动控制软件写程序"。离线推理（Ollama）+ 本地知识库（Chroma RAG）+ WorkBuddy 接入配置，数据不出域，覆盖西门子 / 台达 / 三菱 / 信捷 / 欧姆龙 / 汇川等多品牌及伺服、驱动器、变频电源等自动化配件。**

---

## ❓ 能办到吗——"自动控制软件写程序"

**能，但定位是"AI 辅助起草"，不是全自动代写。** 这一点必须先说清楚：

- 助手可为 **TIA Portal（SCL）、GX Works（ST）、InoProShop（ST/CODESYS）、ISPSoft、Sysmac Studio、CX-Programmer、各品牌 HMI / 组态软件（组态王、MCGS、台达 DIAEntegro、WinCC 等）、伺服/变频调试软件，以及上位机程序（C# / Python / LabVIEW 等）** 生成文本形式的程序、配置、参数表、变量点表、脚本与调试清单；
- 你把这些文本复制 / 导入对应的工控软件里编译、下装即可；
- 它**不能直接点击操作厂商软件的图形界面**（本工程不含 RPA / 无 GUI 自动化），但产出的就是软件能直接吃进去的源码 / 配置文件；
- 所有产出**仅供起草与教学**，必须经合格工程师审核 + 仿真验证（见 `docs/plc/SAFETY.md`）后才能下装到真实设备。

> 一句话：**本工程 = 工控软件应用的"离线编程/调试副驾"，不是自动下装机器人。**

---

## 一、覆盖的工控软件应用（8 大类）

| # | 应用 | 典型软件 / 语言 | 助手能帮你做的事 |
|---|---|---|---|
| 1 | **PLC 编写** | TIA Portal(SCL)、GX Works(ST)、InoProShop(ST)、ISPSoft、Sysmac、CX-P | IEC 61131-3 ST/LAD/FBD 逻辑起草、代码审查、报错分析、联锁/急停设计 |
| 2 | **变频器（VFD）调试** | 各品牌变频调试软件 / 面板 | 参数表起草（加减速、多段速、载波）、Modbus/模拟量/端子控制方案、故障排查 |
| 3 | **伺服电机调试** | 伺服调试软件（如 IS620P、MR-Config 等） | 三环增益、原点回归、电子齿轮比、惯量辨识、限位方案起草 |
| 4 | **触摸屏（HMI）使用** | WinCC / GT Designer / NB / EBPro / MCGS 等 | 画面组态思路、变量映射表、通信参数、报警/趋势配置草稿 |
| 5 | **编码器使用** | PLC 高速计数器 / 运动轴配置 | 增量/绝对式选型、A/B/Z 接线、SSI/EnDat/BiSS 读取逻辑、与 HSC 配合 |
| 6 | **自动控制软件写程序** | 上述各类软件的源码/配置文件 | 面向"自动控制"场景的程序/配置/参数集起草（见上方说明） |
| 7 | **组态软件（SCADA/HMI）** | 组态王、MCGS（昆仑通态）、台达 DIAEntegro、WinCC、力控、EBPro | 变量点表、设备通信参数、命令语言/脚本、画面组态草稿 |
| 8 | **上位机程序编写** | C#/.NET、Python、LabVIEW（Modbus / OPC UA / S7 / MC 等） | 读写寄存器代码、采集/日志、报警、曲线、异常/超时处理 |

---

## 二、方案定位（4 层本地能力）

面向 **Windows 本机**的离线 AI 助手工程，四层能力开箱即用；**全部重心为工控软件应用**：

```
┌─────────────────────────────────────────────────────────────┐
│  WorkBuddy / 任意客户端（你口述需求 → 助手出工控代码/配置）      │
│    └── MCP 配置片段（config/workbuddy/mcp.fragment.json）      │
├─────────────────────────────────────────────────────────────┤
│  ① 本地推理     Ollama（11434，OpenAI 兼容 /v1）               │
│  ② 本地 RAG     Chroma 向量库 + rag_manager.py（导入/检索）      │
│  ③ LoRA 微调    LLaMA-Factory（lora/，可选：用你的工控手册微调）  │
│  ④ 运维支撑     deploy/install.ps1、selfcheck.ps1、启停、日志管理 │
└─────────────────────────────────────────────────────────────┘
           全部组件本地运行，业务数据不出本机
```

**适用场景（工控向）**：
- PLC 编程辅助：IEC 61131-3 ST/LAD 思路、逻辑起草、代码审查、报错分析；
- 多品牌手册问答：西门子 / 台达 / 三菱 / 信捷 / 欧姆龙 / 汇川的指令集、参数、接线；
- 伺服电机、驱动器、变频电源（VFD）的选型 / 参数 / 通信（Modbus / EtherCAT / 脉冲）配置咨询；
- 触摸屏（HMI）/ 组态软件（组态王、MCGS、台达 DIAEntegro、WinCC 等）组态、编码器接入、上位机程序、自动控制程序草稿；
- 故障排查、联锁与急停逻辑、PID 整定等经验性问题的离线检索。

**边界声明（重要）**：
- 本工程是**部署与配置工程**，仓库不含模型文件；模型可由 `scripts/setup_ollama.ps1` 或 CI 自动拉取（见 `docs/deploy/ollama_setup.md`），也可你手动 `ollama pull`；
- 知识库、日志、向量库等运行时数据均被 `.gitignore` 排除，仓库只含代码与配置；
- AI 生成的 PLC / 工控代码**仅供起草与教学**，必须经由合格工程师审核并在仿真中验证（见 `docs/plc/SAFETY.md`）；
- LoRA 微调使用 HuggingFace/ModelScope 格式模型，与 Ollama 的 gguf 格式**不通用**（详见 `lora/README.md`）。

## 三、目录结构

```
local-offline-assistant/
├── README.md                       本文件
├── 启动.bat / 停止.bat             双击启动 / 停止（Windows 一键编排，推荐）
├── requirements.txt                核心依赖（chromadb 等）
├── .gitignore                      运行时数据排除规则
├── LICENSE                         MIT 许可证
├── config/
│   ├── rag.config.json             RAG 参数（向量库/嵌入/分块/支持格式/知识目录）
│   ├── ollama-models.txt           推荐模型清单（含 24G+CPU 卸载指引）
│   └── workbuddy/
│       ├── mcp.fragment.json       WorkBuddy MCP 接入配置片段
│       └── knowledge-base.md       接入说明 + 知识库结构
├── .github/
│   └── workflows/
│       └── setup-ollama.yml        GitHub Actions：云端校验 + 自托管节点装 Ollama/模型
├── .cnb.yml                        CNB 流水线：云端校验 + 自托管 Windows 节点装 Ollama/模型
├── deploy/
│   ├── install.ps1                 一键部署脚本（Windows PowerShell）
│   ├── bootstrap.py                跨平台一键部署（纯 Python，Linux/macOS/Windows 通用）
│   └── setup.sh                    Linux/macOS 便捷入口（调 bootstrap.py）
├── tests/                          零依赖测试套件（unittest；云端 CI 真跑）
│   ├── test_repo_structure.py      仓库结构/配置/PS1 BOM/文档链接
│   ├── test_ci_validate.py         在真实仓库上跑 ci_validate.py
│   ├── test_rag_manager.py         分块/收集/导入检索（含离线集成测试）
│   └── test_bootstrap.py           bootstrap 纯函数与目录初始化
├── app/
│   └── webui.py                    本地 Web 聊天界面（标准库，端口 8500，对接 Ollama + RAG）
├── scripts/
│   ├── start.ps1 / stop.ps1        服务启停（PID 文件精准停止，防误杀）
│   ├── setup_ollama.ps1            安装 Ollama + 拉模型（幂等；两平台 CI 共用）
│   ├── selfcheck.ps1               环境自检（PASS/WARN/FAIL 分级）
│   ├── ci_validate.py              仓库结构校验（云端 CI 门禁，零依赖）
│   ├── rag_manager.py              RAG 管理：add/add-all/scan/search/list/stats/clear
│   └── history_manager.ps1         历史记录管理：status/archive/export/clean
├── lora/
│   ├── README.md                   微调说明（含模型格式区别，可选组件）
│   ├── requirements.txt            微调依赖（torch 需另行按 CUDA 安装）
│   ├── train.ps1                   训练启动器（CLI / -WebUI）
│   ├── configs/qlora_sft.yaml      QLoRA 配置模板
│   └── dataset/                    数据集注册 + alpaca 示例数据
├── docs/
│   ├── plc/                        工控应用资料（本工程全部重心）
│   │   ├── SAFETY.md               安全红线（必读）
│   │   ├── st_template.st          IEC 61131-3 ST 示例集（厂商中立）
│   │   ├── rag_guide.md            把厂家手册/程序喂进 RAG 的指引
│   │   ├── brands.md               多品牌对照 + HMI/编码器速查
│   │   ├── commissioning.md        六类调试检查清单
│   │   ├── hmi_scada_host.md       组态软件与上位机程序编写指引
│   │   ├── how_to_extend.md        ⭐ 如何随时增加应用场景（新品牌/新器件）
│   │   ├── brand_onboarding_template.md  ⭐ 品牌/器件接入骨架模板（填空即用）
│   │   └── sample_plc_doc.md       知识库示例样板（也可作 RAG 导入测试）
│   ├── scada/                      ⭐ 组态软件 TOP5 自动编程能力（组态王/MCGS/WinCC/力控/威纶通）
│   ├── host/                       上位机程序样例（含 write_safety_template.md 写入安全模板）
│   ├── devices/                    ⭐ 常用电气件使用方法（你自己持续补充）
│   └── assistant/ROLE_RULES.md    助手角色铁律（10 条行为规则，已全部写进 webui SYSTEM_PROMPT）
│   ├── deploy/
│   │   └── ollama_setup.md         ⭐ 让 GitHub/CNB 自动帮你装 Ollama+模型（自托管节点）
│   └── review/                     ⭐ 双视角审查报告（资深 IT + 20 年电气自动化）
└── data/ logs/ models/ lora/output/   运行时目录（部署时自动创建，不入库）
```

## 四、快速开始（新机器 5 步）

```powershell
# 0. 前置：安装 Python 3.10+（python.org，勾选 Add to PATH）
git clone <你的仓库地址> local-offline-assistant
cd local-offline-assistant

# 1. 一键部署（创建 venv、装依赖、建目录、跑自检）
#    Windows：
.\deploy\install.ps1
#    Linux / macOS（跨平台等价入口）：
#    ./deploy/setup.sh
#    Python 直跑（可加 --dry-run 只预览不落盘；--install-ollama 尝试装 Ollama）：
#    python deploy/bootstrap.py
#   想自动尝试 winget 装 Ollama：.\deploy\install.ps1 -InstallOllama

# 2. 安装 Ollama 引擎 + 拉取模型（幂等，可反复跑；也可交给 CI 做，见下一步）
.\scripts\setup_ollama.ps1
#   只拉指定模型：.\scripts\setup_ollama.ps1 -Models "qwen2.5:14b,nomic-embed-text"

# 3. 启动服务
.\scripts\start.ps1

# 4. 一键导入知识库并验证（把你们的厂家手册/程序脱敏后放进 data\knowledge_base\docs\）
python scripts\rag_manager.py add-all
python scripts\rag_manager.py scan
python scripts\rag_manager.py search "西门子 S7-1200 高速计数器怎么配" --top-k 5

# 5. 接入 WorkBuddy（可选）
#    按 config\workbuddy\knowledge-base.md 合并 mcp.fragment.json 到 ~/.workbuddy/mcp.json
```

> **本机零预装验证**：本工程所有部署能力都收在仓库里，CI 也只依赖 Python 3.10+。
> 你也可以在部署前用 `python deploy/bootstrap.py --dry-run` 预览将要做的所有改动。

> **不想自己动手装 Ollama？** 把你的机器注册成 GitHub 自托管 runner 或 CNB 自托管
> Windows 构建节点，之后在网页上点一下「Run workflow」，两个平台就会自动把
> Ollama + 模型装到你本机。完整步骤见 `docs/deploy/ollama_setup.md`。

常用运维命令：环境自检 `.\scripts\selfcheck.ps1`｜停止服务 `.\scripts\stop.ps1`｜日志归档 `.\scripts\history_manager.ps1 archive`。

## 五、配置说明

| 配置 | 位置 | 要点 |
|---|---|---|
| RAG | `config/rag.config.json` | 集合名、嵌入方式（chroma-default / ollama）、分块大小与重叠、支持的文件格式 |
| 模型清单 | `config/ollama-models.txt` | 推理/嵌入模型推荐 + **24G 内存 + CPU 卸载**指引【⚠️显存数值为经验值】 |
| WorkBuddy | `config/workbuddy/mcp.fragment.json` | **仅结构示例**，真实 command/args 需按你选用的 MCP 服务器填写【⚠️需核实】，见同目录 knowledge-base.md |
| LoRA | `lora/configs/qlora_sft.yaml` | 字段随 LLaMA-Factory 版本演进，以官方文档为准（可选组件） |

## 六、安全与高危操作清单

| 操作 | 风险 | 保护措施 |
|---|---|---|
| `rag_manager.py clear` | **永久删除整个向量库集合** | 默认交互输入 yes 确认 |
| `history_manager.ps1 clean -Force` | **永久删除日志文件（不进回收站）** | 默认干跑只列出；-Force 时二次输入 DELETE 确认 |
| `stop.ps1` 停止进程 | 误杀风险 | 只停 PID 文件记录且进程名校验通过的进程；无 PID 文件不自动杀 |
| `install.ps1 -RecreateVenv` | 删除重建 venv | 需显式传参 |
| `install.ps1 -InstallOllama` | 联网安装 + 可能弹 UAC | 需显式传参，默认仅检测引导 |
| **注册自托管 runner / 构建节点** | **流水线可在你机器上执行任意代码**（公开仓库尤甚） | GitHub 侧默认仅 `workflow_dispatch` 触发；建议私有仓库或限制推送权限；不要把 token 写进仓库 |
| **PLC / 工控代码 / HMI / 组态软件 / 上位机 / 编码器配置** | **错误程序可能导致设备损坏/伤人** | **AI 输出仅作起草，必须工程师审核 + 仿真验证（见 `docs/plc/SAFETY.md`）** |

**生产/重要机器上执行任何删除类操作前，请先备份 `data/` 与 `logs/` 目录。**

## 七、FAQ

**Q：你标题说"自动控制软件写程序"，到底能不能办到？**
A：**能办到"起草"，不能办到"全自动代写"。** 本助手可为各品牌 PLC 编程软件、HMI/组态软件（组态王、MCGS、台达 DIAEntegro、WinCC 等）、伺服/变频调试软件、上位机程序（C#/Python）生成文本程序、配置与参数表，你导入软件即可编译下装；它不能代替你在软件里点鼠标（不含 GUI 自动化）。是否"自动"取决于你把它接进工作流的程度——例如通过 MCP 把本地 Ollama 接进 WorkBuddy，你口述需求它就出代码。但代码下装前必须人工审核 + 仿真。

**Q：Ollama 模型和 LoRA 训练的模型为什么不能通用？**
A：Ollama 用 gguf 格式，LLaMA-Factory 训练用 HuggingFace/ModelScope 格式。训练产物需合并 LoRA 后按双方官方文档转换才能在 Ollama 使用【⚠️转换命令随版本变化，以官方文档为准】。

**Q：完全离线的机器能用吗？**
A：可以，但有一次"联网预热"：Chroma 默认嵌入方式首次运行会自动下载 ONNX 模型权重。完全无网的机器请预先在联网机器下载放置，或切换 `provider=ollama` 用本地 Ollama 嵌入模型（见 `config/workbuddy/knowledge-base.md`、`docs/plc/rag_guide.md` 第 4.1 节）。

**Q：能不能让 GitHub / CNB 的自动运行助手帮我装 Ollama 和模型？**
A：**能，但要先把你的机器注册成"自托管节点"。** 两家的云端 runner 都是临时云机器，装完即销毁、也摸不到你的 `D:\` 盘；只有把本机注册成 GitHub 自托管 runner 或 CNB 自托管 Windows 构建节点，流水线才会在你机器上执行安装。本工程已配好两条流水线（`.github/workflows/setup-ollama.yml`、`.cnb.yml`），共用同一个幂等脚本 `scripts/setup_ollama.ps1`。⚠️ 公开仓库 + 自托管 runner 有安全风险（他人推代码即可在你机器执行），GitHub 侧已默认只允许网页手动触发。完整步骤见 `docs/deploy/ollama_setup.md`。

**Q：我想再加一个 PLC 品牌，或者加一个我常用的电气件，怎么办？**
A：**不用改代码，加文档就行。** 复制 `docs/plc/brand_onboarding_template.md` 的模板 → 填空 → 放进 `docs/devices/`（器件）或 `docs/plc/brands/<品牌>.md` → 跑一次 `python scripts\rag_manager.py add-all`。之后问 AI 相关问题，它就会引用你核对过的映射表和用法，而不是凭记忆编。详见 `docs/plc/how_to_extend.md`。

**Q：组态软件覆盖了哪些？**
A：锁定国内使用率 TOP5 深度支持——**组态王、MCGS（昆仑通态）、WinCC、力控、威纶通 EBPro**，每个都有专门的"AI 自动编程能力"文档（变量点表、设备配置、脚本、画面清单、提示词模板），见 `docs/scada/`。台达 DIAEntegro、紫金桥、inTouch/iFIX、Ignition 等在 `docs/scada/second_tier.md`。

**Q：没有 NVIDIA 显卡？**
A：Ollama 可 CPU 推理 7B（慢但可用）；LoRA 训练 7B 在 CPU 上基本不可行，仅建议用于跑通流程。

**Q：Windows 上训练稳吗？**
A：LLaMA-Factory 单卡流程在 Windows 原生环境可跑通；多卡/量化内核/DeepSpeed 场景建议 Linux 或 WSL2【⚠️社区经验】。

**Q：PLC 编程/伺服/变频/触摸屏/HMI/组态软件/上位机 这类专业问题，小模型够用吗？**
A：7B 偏弱、易幻觉；建议至少 **14B**（24G 内存可舒适跑）。但更关键的是把你们的手册/程序喂进 RAG（见 `docs/plc/rag_guide.md`）——领域准确性靠"模型 + 你的资料"双管齐下。

## 八、工控应用专章（本工程全部重心）

详见 `docs/plc/` 目录：
- **SAFETY.md** — 安全红线，**部署前必读**；
- **st_template.st** — IEC 61131-3 ST 示例集（电机启停/急停联锁、定时器、计数器、PID、伺服定位），厂商中立；
- **rag_guide.md** — 把西门子/台达/三菱/信捷/欧姆龙/汇川手册、HMI 软件手册、伺服/编码器资料与程序（脱敏）导入知识库的指引；
- **brands.md** — 多品牌软件/语言对照速查 + HMI/触摸屏、编码器要点；
- **commissioning.md** — 变频器/伺服/触摸屏(HMI)/编码器/组态软件/上位机 六类调试检查清单；
- **hmi_scada_host.md** — 组态软件（组态王/MCGS/台达 DIAEntegro/WinCC/力控等）与上位机程序编写（C#/Python/LabVIEW）指引、协议与示例代码；
- **how_to_extend.md** — ⭐ 如何随时增加应用场景（新 PLC 品牌 / 新电气件 / 新样例），三步即可；
- **brand_onboarding_template.md** — ⭐ 品牌/器件接入骨架模板，填空后 AI 即可按它"自动部署"；
- **sample_plc_doc.md** — 知识库资料整理样板（也可作 RAG 导入测试样例）。

**组态软件 TOP5 自动编程能力**（`docs/scada/`）：组态王、MCGS（昆仑通态）、WinCC、力控、威纶通 EBPro 各一份文档，
每份含"AI 能自动产出什么 + 变量点表 + 脚本样例 + 画面清单 + 提示词模板"；
第二梯队（台达 DIAEntegro、紫金桥、inTouch/iFIX、Ignition 等）见 `docs/scada/second_tier.md`。

**持续扩充**：`docs/devices/`（常用电气件使用方法）、`docs/host/`（上位机程序样例）由你按模板不断新增。

## 九、自动化：让两个平台替你装引擎、做校验

| 平台 | 流水线 / Job | 运行位置 | 作用 |
|---|---|---|---|
| GitHub | `validate` | 云端 ubuntu-latest | 仓库结构校验（`scripts/ci_validate.py`），公开仓库也安全 |
| GitHub | `test` | 云端 ubuntu-latest | 跑 `tests/` 零依赖测试套件（22 例全过） |
| GitHub | `setup-ollama` | **你的 Windows 本机**（自托管 runner） | 装 Ollama + 拉模型；默认仅网页手动触发 |
| CNB | `validate-repo` | 云端 amd64 | 仓库结构校验 **+** `tests/` 测试套件 |
| CNB | `setup-ollama-on-windows-node` | **你的 Windows 本机**（自托管构建节点） | 装 Ollama + 拉模型（`allowFailure`，装完需人工复核） |

两平台共用 `scripts/setup_ollama.ps1`（幂等：已装的跳过、已拉的模型跳过）。
注册自托管节点与安全注意事项（含"公开仓库 + 自托管 = 任意代码在你的电脑跑"的风险）见 `docs/deploy/ollama_setup.md` 与 `docs/plc/SAFETY.md` 第五节。

## 十、信息来源与存疑标注汇总

本仓库内容按三类来源组织：

- **【原生推理】**：工程结构、脚本逻辑、目录划分、文档组织——由方案设计直接推导；
- **需你核实的点（文中已逐处标注 ⚠️）**：
  1. `mcp.fragment.json` 中的 MCP 服务器 command/args（第三方实现需自行评估选型）；
  2. `ollama-models.txt` 中各模型在 Ollama library 的实际可用性与显存经验值；
  3. LLaMA-Factory 配置字段与训练产物转 Ollama 的具体命令（以双方官方文档为准）；
  4. PyTorch/CUDA 组合命令（以 pytorch.org 当前页面为准）；
  5. GitHub Actions runner 下载版本号（以仓库 Settings → Runners 页面当前显示的为准）；
  6. CNB 自托管节点的接入脚本与标签（以组织设置 → 构建节点 → 连接指引弹窗显示的为准）；
  7. `docs/scada/`、`docs/devices/` 中各品牌脚本语法与寄存器地址（随版本变化，必须按你所用版本手册核对）。

## 十一、测试与双视角质量审查

本工程自带质量门禁，且**严格不向本机安装任何东西**——CI 在云端真跑，本机只用既有 venv 复验：

- **`scripts/ci_validate.py`**：零依赖仓库结构校验（文件/目录/配置 JSON/PS1 BOM/文档链接），CI 门禁。
- **`tests/`**：零依赖 `unittest` 套件（22 例全过），含 `rag_manager` 分块/收集/导入检索的**离线集成测试**（用 `FakeEmbedding` 避免联网下载嵌入模型）。
- **本机复验**：`python -m unittest discover -s tests -v` 与 `python scripts/ci_validate.py`（均只用仓库内已有 venv，不装新包）。

**双视角审查报告**（`docs/review/`）：
- `it_review.md` —— 资深 30 年 IT 工程师视角：安全 / 健壮性 / 幂等 / 可观测 / CI 正确性，含 bug 清单与严重级；
- `automation_review.md` —— 20 年电气自动化工程师视角：Modbus 0基/1基偏移、各品牌脚本语法准确性、上位机写入校验/轮询/超时、安全红线充分性，给出"必须改/建议改/可不改"结论。
- `assistant/ROLE_RULES.md` —— 用户对本地离线助手定下的 **10 条行为铁律**（诚实/推理优先/来源标注/领域严谨/上下文管控/拒绝污染/输出自检/模式区分/格式/中文），已全部写进 `app/webui.py` 的 `SYSTEM_PROMPT`，作为 Web 聊天界面的实时约束（见第十一节本机复验的同一份代码）。

## 十二、许可

仓库采用 **MIT 许可证**（`LICENSE` 文件）。公开仓库，可自由使用、修改、分发，但按 MIT 条款须保留版权与许可声明；不提供任何担保。

## 十三、用户使用指南：下载压缩包 → 双击启动（最简）

> 目标：**使用者拿到一个 zip，解压，双击 `启动.bat`，浏览器自动打开就能用。** 下面把"会不会执行不起来、要不要全部下载、怎么操作"一次说清。

### 13.1 你提的要求都满足了，但有一处必须讲清楚的硬限制

- ✅ 双仓库（GitHub + CNB 同名）、本地离线 AI 助手工程、Ollama+Chroma+RAG、组态 TOP5、可扩展框架、CI 自动装引擎、测试套件、双视角审查——**全部已交付并三端一致**。
- ⚠️ **真正的硬限制**：一个能"离线对话"的助手必须有**推理引擎（Ollama）+ 至少一个模型权重（几 GB）**。这两样无法凭空出现在 zip 里——要么你本机装一次 Ollama（启动.bat 会尝试自动装），要么 zip 里塞进多 GB 模型（不现实）。
- 因此**首次运行必须联网一次**：拉 Python 依赖 + 装/确认 Ollama + 拉取默认模型。之后**完全离线**可用。这是离线 AI 助手的物理边界，不是工程缺陷。

### 13.2 两种拿到工程的方式（都不用"全部手动下载"）

**方式 A（推荐，最小）：下载发布 zip**
1. 维护者运行 `.\deploy\package.ps1` → 生成 `releases/local-offline-assistant-YYYYMMDD.zip`（仅含源码，几 MB，已排除 venv/模型/数据/日志）。
2. 把 zip 发给使用者；使用者解压到任意目录（如 `D:\assistant`）。
3. **双击 `启动.bat`** → 自动：检测/装 Python → 建 venv 装依赖 → 检测/装 Ollama → 拉默认模型 → 导入知识库 → 启动服务 → **打开浏览器 http://127.0.0.1:8500**。
4. 在网页里用中文提问即可；勾选"启用知识库"会用你导入的工控文档作答。
5. 停止：**双击 `停止.bat`**。

**方式 B：直接 git clone（开发者）**
```
git clone <你的仓库地址> local-offline-assistant
cd local-offline-assistant
.\启动.bat          # 一样的一键编排
```

### 13.3 会不会执行不起来？已做的健壮性

- `启动.bat` 全程幂等：venv/依赖/模型/知识库重复执行都安全（已装的跳过）。
- 缺 Python → 打开官网引导安装；缺 Ollama → 尝试自动装，失败则打开官网让你装一次（装完重跑即可）。
- 模型拉取失败 / 知识库嵌入模型下载失败 → **不致命**，聊天仍可用（只是没有 RAG 上下文，或提示改用 `provider=ollama` 后重跑）。
- 自带 `scripts/selfcheck.ps1` 与 `python scripts/ci_validate.py` 做环境自检与结构校验。

### 13.4 想"完全不装 Ollama"行不行？

不现实。Ollama 是本地推理引擎，必须在本机存在。可退而求其次：
- 用别人已装好 Ollama 的机器；或
- 云端/别机跑 Ollama、本机 Web 界面指向它（设环境变量 `OLLAMA_BASE=http://那台机:11434`，并把 `app/webui.py` 的 `ASSISTANT_HOST` 设为 `0.0.0.0` 仅在你信任的内网）。

### 13.5 关键文件速查

| 用途 | 文件 |
|---|---|
| 双击启动 | `启动.bat` |
| 双击停止 | `停止.bat` |
| 启动编排逻辑 | `scripts/launcher.ps1` |
| 本地聊天界面 | `app/webui.py`（端口 8500，标准库，零新增依赖） |
| 发发布包 | `deploy/package.ps1` → `releases/*.zip` |
| 模型清单 | `config/ollama-models.txt`（首个未注释项即默认模型） |
| 知识库配置 | `config/rag.config.json` |
