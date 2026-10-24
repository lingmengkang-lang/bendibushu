# WorkBuddy 接入配置说明（MCP + 本地知识库）

本目录包含两份配置产物：

| 文件 | 用途 |
|---|---|
| `mcp.fragment.json` | WorkBuddy MCP 接入配置**片段**，用于让 WorkBuddy 通过 MCP 协议调用本地 Ollama |
| 本说明 | 本地 RAG 知识库的目录结构与导入方法 |

---

## 一、mcp.fragment.json 合并方法（重要）

WorkBuddy 的 MCP 配置文件位于 `~/.workbuddy/mcp.json`（Windows 下通常为 `C:\Users\<你的用户名>\.workbuddy\mcp.json`）。

**合并规则：只合并 `mcpServers` 键下的条目，不要覆盖整个文件**，否则会丢失其他已连接的 MCP 服务器配置。

1. 打开 `~/.workbuddy/mcp.json`
2. 将本目录 `mcp.fragment.json` 中 `mcpServers` 下的条目（如 `ollama-local`）合并进去
3. 重启 WorkBuddy 使配置生效

### ⚠️ 关于 mcp.fragment.json 内的参数【信息存疑，需你核实】

本地 Ollama **本身不是 MCP 服务器**，它对外提供 OpenAI 兼容 API（`http://127.0.0.1:11434/v1`）。
要通过 MCP 接入，需要一个"把 Ollama 包装成 MCP 服务器"的中间程序（社区有若干第三方实现）。

因此 `mcp.fragment.json` 中的 `command` / `args` 为**结构占位示例**，不是已验证可用的真实包名。
你需要：

1. 选定一个 Ollama MCP 包装实现（自行检索社区项目，评估其维护状态与安全性）；
2. 按其文档把真实的 `command` / `args` 填进片段；
3. `OLLAMA_BASE_URL` 环境变量是 Ollama 官方约定的变量名，可直接沿用。

在未接入 MCP 的情况下，本地 Ollama 的 OpenAI 兼容端点依然可以被任何支持自定义端点的客户端直接使用。

---

## 二、本地 RAG 知识库结构

```
local-offline-assistant/
└── data/
    └── knowledge_base/
        └── docs/            ← 把你的一手资料（.md/.txt/.pdf）放在这里
```

数据流：

```
docs/ 原始文档 ──rag_manager.py add──▶ 分块 ──▶ Chroma 向量库（data/chroma/）
                                                      │
 WorkBuddy / 命令行 ──rag_manager.py search──▶ 检索结果
```

### 导入与检索命令（PowerShell，工程根目录执行）

```powershell
# 导入单个文件
python scripts\rag_manager.py add data\knowledge_base\docs\示例文档.md

# 导入整个目录（递归）
python scripts\rag_manager.py add data\knowledge_base\docs --recursive

# 检索测试
python scripts\rag_manager.py search "你的问题关键词" --top-k 5

# 查看集合状态
python scripts\rag_manager.py stats
```

### 与 WorkBuddy 云端资料库的区别

- 本工程知识库 = **纯本地 Chroma 向量库**，数据不出本机，适合涉密/离线场景；
- WorkBuddy 云端 Library（资料库）适合跨设备协作；
- 两者可并用：机密资料进本地库，可公开资料进云端库。

### ⚠️ 首次运行注意

本工程默认 `provider=ollama` + `bge-m3`（约 1.2GB，需先 `ollama pull bge-m3`，导入/检索时 Ollama 需在运行），**首次需联网拉取一次**，之后完全离线。

若切到 `provider=chroma-default`：Chroma 首次运行会自动下载一次内置 ONNX 嵌入模型权重（约 80MB 级），**需要联网**；下载完成后永久离线可用。如运行环境完全无网，请预先在联网机器上下载并放置到用户缓存目录。

⚠️ 两种 provider 的向量维度不同（bge-m3=1024 维，MiniLM=384 维），切换后必须 `rag_manager.py clear` 再重新 `add-all`（见 `docs/plc/rag_guide.md` 第 4.1 节）。
