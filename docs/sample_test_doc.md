# 示例测试文档：本地离线助手工程速查

> 本文档为 RAG 知识库的**导入测试样例**，内容与本工程实际结构一致。
> 用途：放入 `data/knowledge_base/docs/` 后用 `rag_manager.py` 导入，再通过 `search` 子命令验证检索链路是否正常工作。
> 你可以在掌握测试方法后，用自己的一手资料替换本目录下的文档。

## 一、工程是做什么的

本工程（local-offline-assistant）是 Windows 本机的一体化离线 AI 部署方案，包含四层能力：

1. **本地推理**：Ollama 运行本地大模型（如 qwen2.5:7b），默认监听 127.0.0.1:11434，提供 OpenAI 兼容 API；
2. **本地 RAG**：文档经 `scripts/rag_manager.py` 分块后进入 Chroma 向量库（`data/chroma/`），检索全程不联网；
3. **LoRA 微调**：`lora/` 目录提供 LLaMA-Factory 配置与启动脚本，训练使用 HuggingFace 格式模型，与 Ollama 的 gguf 格式不通用；
4. **WorkBuddy 接入**：`config/workbuddy/` 提供 MCP 配置片段与本地知识库说明。

## 二、常用命令速查（PowerShell，工程根目录执行）

| 目的 | 命令 |
|---|---|
| 一键部署 | `.\deploy\install.ps1` |
| 环境自检 | `.\scripts\selfcheck.ps1` |
| 启动服务 | `.\scripts\start.ps1` |
| 停止服务 | `.\scripts\stop.ps1` |
| 启动训练 WebUI | `.\lora\train.ps1 -WebUI` |
| 拉取模型 | `ollama pull qwen2.5:7b` |
| 导入知识库 | `python scripts\rag_manager.py add data\knowledge_base\docs -r` |
| 检索测试 | `python scripts\rag_manager.py search "关键词" --top-k 5` |
| 查看集合状态 | `python scripts\rag_manager.py stats` |
| 日志归档 | `.\scripts\history_manager.ps1 archive` |
| 日志清理（先干跑） | `.\scripts\history_manager.ps1 clean -Days 30` |

## 三、端口一览

| 端口 | 服务 | 说明 |
|---|---|---|
| 11434 | Ollama API | 本地推理入口，OpenAI 兼容端点为 `/v1` |
| 7860 | LLaMA-Factory WebUI | 仅在执行 `.\lora\train.ps1 -WebUI` 时监听 |

## 四、目录结构速查

- `config/` — 全局配置：RAG 参数（`rag.config.json`）、模型清单（`ollama-models.txt`）、WorkBuddy 接入（`workbuddy/`）
- `data/` — 运行时数据：知识库源文档（`knowledge_base/docs/`）、Chroma 向量库（`chroma/`）
- `deploy/` — 一键部署脚本
- `scripts/` — 启停、自检、RAG 管理、历史记录管理脚本
- `lora/` — LoRA 微调配套
- `docs/` — 文档与测试样例（本文件）
- `logs/` — 运行日志（`history_manager.ps1` 的管理对象）

## 五、三条重要提醒

1. **首次运行 RAG 会联网一次**：Chroma 默认嵌入方式首次使用时会自动下载 ONNX 模型权重，之后完全离线；
2. **模型不会自动拉取**：部署脚本只检测 Ollama 是否安装，模型需你手动 `ollama pull`（清单见 `config/ollama-models.txt`）；
3. **删除类操作都是高危**：`rag_manager.py clear`、`history_manager.ps1 clean -Force` 会永久删除数据，执行前务必确认清单。
