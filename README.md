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
- 本工程是**部署与配置工程**，不含模型文件、不自动拉取模型（Ollama 模型需你手动 `ollama pull`）；
- 知识库、日志、向量库等运行时数据均被 `.gitignore` 排除，仓库只含代码与配置；
- AI 生成的 PLC / 工控代码**仅供起草与教学**，必须经由合格工程师审核并在仿真中验证（见 `docs/plc/SAFETY.md`）；
- LoRA 微调使用 HuggingFace/ModelScope 格式模型，与 Ollama 的 gguf 格式**不通用**（详见 `lora/README.md`）。

## 三、目录结构

```
local-offline-assistant/
├── README.md                       本文件
├── requirements.txt                核心依赖（chromadb 等）
├── .gitignore                      运行时数据排除规则
├── LICENSE                         MIT 许可证
├── config/
│   ├── rag.config.json             RAG 参数（向量库/嵌入/分块/支持格式）
│   ├── ollama-models.txt           推荐模型清单（含 24G+CPU 卸载指引，不自动拉取）
│   └── workbuddy/
│       ├── mcp.fragment.json       WorkBuddy MCP 接入配置片段
│       └── knowledge-base.md       接入说明 + 知识库结构
├── deploy/
│   └── install.ps1                 一键部署脚本
├── scripts/
│   ├── start.ps1 / stop.ps1        服务启停（PID 文件精准停止，防误杀）
│   ├── selfcheck.ps1               环境自检（PASS/WARN/FAIL 分级）
│   ├── rag_manager.py              RAG 管理：add/search/list/stats/clear
│   └── history_manager.ps1         历史记录管理：status/archive/export/clean
├── lora/
│   ├── README.md                   微调说明（含模型格式区别，可选组件）
│   ├── requirements.txt            微调依赖（torch 需另行按 CUDA 安装）
│   ├── train.ps1                   训练启动器（CLI / -WebUI）
│   ├── configs/qlora_sft.yaml      QLoRA 配置模板
│   └── dataset/                    数据集注册 + alpaca 示例数据
├── docs/
│   └── plc/                        工控应用资料（本工程全部重心）
│       ├── SAFETY.md               安全红线（必读）
│       ├── st_template.st          IEC 61131-3 ST 示例集（厂商中立）
│       ├── rag_guide.md            把厂家手册/程序喂进 RAG 的指引
│       ├── brands.md               多品牌对照 + HMI/编码器速查
│       ├── commissioning.md        变频器/伺服/触摸屏/编码器/组态软件/上位机调试检查清单
│       ├── hmi_scada_host.md       组态软件(组态王/MCGS/台达/WinCC)与上位机程序编写指引
│       └── sample_plc_doc.md       知识库示例样板（也可作 RAG 导入测试）
└── data/ logs/ models/ lora/output/   运行时目录（部署时自动创建，不入库）
```

## 四、快速开始（新机器 5 步）

```powershell
# 0. 前置：安装 Python 3.10+（python.org，勾选 Add to PATH）；
#    可选安装 Ollama（https://ollama.com/download），或让 install.ps1 用 winget 尝试安装
git clone <你的仓库地址> local-offline-assistant
cd local-offline-assistant

# 1. 一键部署（创建 venv、装依赖、建目录、跑自检；不自动装 Ollama、不拉模型）
.\deploy\install.ps1
#   想自动尝试 winget 装 Ollama：.\deploy\install.ps1 -InstallOllama

# 2. 启动服务（新开终端，刷新 PATH）
.\scripts\start.ps1

# 3. 拉取模型（首次必须；工控专业场景建议 14B，见 config\ollama-models.txt）
ollama pull qwen2.5:14b

# 4. 导入知识库并验证（把你们的厂家手册/程序脱敏后放进 data\knowledge_base\docs\）
python scripts\rag_manager.py add data\knowledge_base\docs -r
python scripts\rag_manager.py search "西门子 S7-1200 高速计数器怎么配" --top-k 5

# 5. 接入 WorkBuddy（可选）
#    按 config\workbuddy\knowledge-base.md 合并 mcp.fragment.json 到 ~/.workbuddy/mcp.json
```

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
| **PLC / 工控代码 / HMI / 组态软件 / 上位机 / 编码器配置** | **错误程序可能导致设备损坏/伤人** | **AI 输出仅作起草，必须工程师审核 + 仿真验证（见 `docs/plc/SAFETY.md`）** |

**生产/重要机器上执行任何删除类操作前，请先备份 `data/` 与 `logs/` 目录。**

## 七、FAQ

**Q：你标题说"自动控制软件写程序"，到底能不能办到？**
A：**能办到"起草"，不能办到"全自动代写"。** 本助手可为各品牌 PLC 编程软件、HMI/组态软件（组态王、MCGS、台达 DIAEntegro、WinCC 等）、伺服/变频调试软件、上位机程序（C#/Python）生成文本程序、配置与参数表，你导入软件即可编译下装；它不能代替你在软件里点鼠标（不含 GUI 自动化）。是否"自动"取决于你把它接进工作流的程度——例如通过 MCP 把本地 Ollama 接进 WorkBuddy，你口述需求它就出代码。但代码下装前必须人工审核 + 仿真。

**Q：Ollama 模型和 LoRA 训练的模型为什么不能通用？**
A：Ollama 用 gguf 格式，LLaMA-Factory 训练用 HuggingFace/ModelScope 格式。训练产物需合并 LoRA 后按双方官方文档转换才能在 Ollama 使用【⚠️转换命令随版本变化，以官方文档为准】。

**Q：完全离线的机器能用吗？**
A：可以，但有一次"联网预热"：Chroma 默认嵌入方式首次运行会自动下载 ONNX 模型权重。完全无网的机器请预先在联网机器下载放置，或切换 `provider=ollama` 用本地 Ollama 嵌入模型（见 `config/workbuddy/knowledge-base.md`）。

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
- **sample_plc_doc.md** — 知识库资料整理样板（也可作 RAG 导入测试样例）。

## 九、信息来源与存疑标注汇总

本仓库内容按三类来源组织：

- **【原生推理】**：工程结构、脚本逻辑、目录划分、文档组织——由方案设计直接推导；
- **需你核实的点（文中已逐处标注 ⚠️）**：
  1. `mcp.fragment.json` 中的 MCP 服务器 command/args（第三方实现需自行评估选型）；
  2. `ollama-models.txt` 中各模型在 Ollama library 的实际可用性与显存经验值；
  3. LLaMA-Factory 配置字段与训练产物转 Ollama 的具体命令（以双方官方文档为准）；
  4. PyTorch/CUDA 组合命令（以 pytorch.org 当前页面为准）。

## 十、许可

仓库采用 **MIT 许可证**（`LICENSE` 文件）。公开仓库，可自由使用、修改、分发，但按 MIT 条款须保留版权与许可声明；不提供任何担保。
