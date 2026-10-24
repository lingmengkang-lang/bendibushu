# local-offline-assistant

**Windows 本地离线 AI 助手一体化部署工程：Ollama 本地推理 + Chroma 本地 RAG 知识库 + LLaMA-Factory LoRA 微调训练 + WorkBuddy 接入配置，数据不出域，支持运维/办公/工控等多场景离线使用。**

---

## 一、方案定位

面向 **Windows 本机**的离线 AI 助手工程，四层能力开箱即用：

```
┌─────────────────────────────────────────────────────────────┐
│  WorkBuddy / 任意客户端                                       │
│    └── MCP 配置片段（config/workbuddy/mcp.fragment.json）      │
├─────────────────────────────────────────────────────────────┤
│  ① 本地推理     Ollama（11434，OpenAI 兼容 /v1）               │
│  ② 本地 RAG     Chroma 向量库 + rag_manager.py（导入/检索）      │
│  ③ LoRA 微调    LLaMA-Factory（lora/，可选组件）                 │
│  ④ 运维支撑     deploy/install.ps1、selfcheck.ps1、启停、日志管理 │
└─────────────────────────────────────────────────────────────┘
           全部组件本地运行，业务数据不出本机
```

**边界声明（重要）**：
- 本工程是**部署与配置工程**，不含模型文件、不自动拉取模型（Ollama 模型需你手动 `ollama pull`）；
- 知识库、日志、向量库等运行时数据均被 `.gitignore` 排除，仓库只含代码与配置；
- LoRA 微调使用 HuggingFace/ModelScope 格式模型，与 Ollama 的 gguf 格式**不通用**（详见 `lora/README.md`）。

## 二、目录结构

```
local-offline-assistant/
├── README.md                       本文件
├── requirements.txt                核心依赖（chromadb 等）
├── .gitignore                      运行时数据排除规则
├── config/
│   ├── rag.config.json             RAG 参数（向量库/嵌入/分块/支持格式）
│   ├── ollama-models.txt           推荐模型清单（仅清单，不自动拉取）
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
│   ├── README.md                   微调说明（含模型格式区别）
│   ├── requirements.txt            微调依赖（torch 需另行按 CUDA 安装）
│   ├── train.ps1                   训练启动器（CLI / -WebUI）
│   ├── configs/qlora_sft.yaml      QLoRA 配置模板
│   └── dataset/                    数据集注册 + alpaca 示例数据
├── docs/
│   └── sample_test_doc.md          RAG 导入测试示例文档
└── data/ logs/ models/ lora/output/   运行时目录（部署时自动创建，不入库）
```

## 三、快速开始（新机器 5 步）

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

# 3. 拉取模型（首次必须；清单与显存参考见 config\ollama-models.txt）
ollama pull qwen2.5:7b

# 4. 导入知识库并验证（把文档放进 data\knowledge_base\docs\）
python scripts\rag_manager.py add data\knowledge_base\docs -r
python scripts\rag_manager.py search "测试问题" --top-k 5

# 5. 接入 WorkBuddy（可选）
#    按 config\workbuddy\knowledge-base.md 合并 mcp.fragment.json 到 ~/.workbuddy/mcp.json
```

常用运维命令：环境自检 `.\scripts\selfcheck.ps1`｜停止服务 `.\scripts\stop.ps1`｜日志归档 `.\scripts\history_manager.ps1 archive`。

## 四、配置说明

| 配置 | 位置 | 要点 |
|---|---|---|
| RAG | `config/rag.config.json` | 集合名、嵌入方式（chroma-default / ollama）、分块大小与重叠、支持的文件格式 |
| 模型清单 | `config/ollama-models.txt` | 推理/嵌入模型推荐 + 显存参考【⚠️显存数值为经验值】 |
| WorkBuddy | `config/workbuddy/mcp.fragment.json` | **仅结构示例**，真实 command/args 需按你选用的 MCP 服务器填写【⚠️需核实】，见同目录 knowledge-base.md |
| LoRA | `lora/configs/qlora_sft.yaml` | 字段随 LLaMA-Factory 版本演进，以官方文档为准 |

## 五、安全与高危操作清单

| 操作 | 风险 | 保护措施 |
|---|---|---|
| `rag_manager.py clear` | **永久删除整个向量库集合** | 默认交互输入 yes 确认 |
| `history_manager.ps1 clean -Force` | **永久删除日志文件（不进回收站）** | 默认干跑只列出；-Force 时二次输入 DELETE 确认 |
| `stop.ps1` 停止进程 | 误杀风险 | 只停 PID 文件记录且进程名校验通过的进程；无 PID 文件不自动杀 |
| `install.ps1 -RecreateVenv` | 删除重建 venv | 需显式传参 |
| `install.ps1 -InstallOllama` | 联网安装 + 可能弹 UAC | 需显式传参，默认仅检测引导 |

**生产/重要机器上执行任何删除类操作前，请先备份 `data/` 与 `logs/` 目录。**

## 六、FAQ

**Q：Ollama 模型和 LoRA 训练的模型为什么不能通用？**
A：Ollama 用 gguf 格式，LLaMA-Factory 训练用 HuggingFace/ModelScope 格式。训练产物需合并 LoRA 后按双方官方文档转换才能在 Ollama 使用【⚠️转换命令随版本变化，以官方文档为准】。

**Q：完全离线的机器能用吗？**
A：可以，但有一次“联网预热”：Chroma 默认嵌入方式首次运行会自动下载 ONNX 模型权重。完全无网的机器请预先在联网机器下载放置，或切换 `provider=ollama` 用本地 Ollama 嵌入模型（见 `config/workbuddy/knowledge-base.md`）。

**Q：没有 NVIDIA 显卡？**
A：Ollama 可 CPU 推理 7B（慢但可用）；LoRA 训练 7B 在 CPU 上基本不可行，仅建议用于跑通流程。

**Q：Windows 上训练稳吗？**
A：LLaMA-Factory 单卡流程在 Windows 原生环境可跑通；多卡/量化内核/DeepSpeed 场景建议 Linux 或 WSL2【⚠️社区经验】。

## 七、信息来源与存疑标注汇总

本仓库内容按三类来源组织：

- **【原生推理】**：工程结构、脚本逻辑、目录划分、文档组织——由方案设计直接推导；
- **需你核实的点（文中已逐处标注 ⚠️）**：
  1. `mcp.fragment.json` 中的 MCP 服务器 command/args（第三方实现需自行评估选型）；
  2. `ollama-models.txt` 中各模型在 Ollama library 的实际可用性与显存经验值；
  3. LLaMA-Factory 配置字段与训练产物转 Ollama 的具体命令（以双方官方文档为准）；
  4. PyTorch/CUDA 组合命令（以 pytorch.org 当前页面为准）。

## 八、许可

仓库当前**未附加 LICENSE 文件**。公开仓库建议补充许可证（默认建议 MIT），需要添加请告知。
