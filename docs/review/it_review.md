# 双视角审查报告（一）：资深 IT 工程师视角

> 审查对象：`local-offline-assistant` 仓库（GitHub `lingmengkang-lang/bendibushu` 与 CNB `gongyeyingyong/bendibushu` 同名）
> 审查维度：安全 / 健壮性 / 幂等性 / 可观测性 / CI 正确性
> 审查方式（严格遵守"本机不装任何东西"约束）：
> - 不向本机安装 Ollama、模型或任何新运行时；
> - 仅用仓库内既有 venv（Python 3.13.14，已含 chromadb 1.5.9 / numpy / pypdf / onnxruntime）跑验证；
> - 部署能力全部收进仓库（`deploy/bootstrap.py` 跨平台 + `deploy/install.ps1`、`deploy/setup.sh`、CI 流水线）；
> - 云端 CI（GitHub Actions ubuntu-latest / CNB python:3.12-slim）负责真跑校验与测试。
> 验证结果：**22 个单元测试全部通过**（`python -m unittest discover -s tests`）；`ci_validate.py` 在真实仓库上返回 0（PASS 38 / WARN 0 / FAIL 0）。

---

## 0. 结论速览

**可以交付，但建议按本报告"仍需处理"项做一轮收口。** 已在本轮修复 4 处真实 bug + 1 处运营坑，剩余项多为加固建议，不阻塞使用。

严重级定义：**🔴 致命（会导致错误结果或安全事件）｜🟠 严重（会导致失败/误判）｜🟡 一般（健壮性/可维护性）｜🟢 提示（优化）**

---

## 1. 已发现并修复的问题（Bug 清单）

### 1.1 🟠 严重 — `scripts/setup_ollama.ps1` 模型"已存在"判断子串误匹配（已修复）
- **现象**：原逻辑用 `$have -match [regex]::Escape($m)` 做子串匹配。当本地已装 `qwen2.5:7b-instruct-q4_K_M` 时，`qwen2.5:7b` 会被误判为"已存在"而**跳过拉取**，导致按 `config/ollama-models.txt` 期望的 `qwen2.5:7b` 实际未就位，下游检索/推理静默降级。
- **根因**：把"包含"当"相等"。Ollama 的 tag 体系里 `qwen2.5:7b` 与 `qwen2.5:7b-instruct-q4_K_M` 是不同模型。
- **修复**：新增 `Get-InstalledModels` 精确解析 `ollama list` 的 NAME 列首字段，用 `-contains` 精确匹配；兼容 `library/` 命名空间。
- **复核**：单元化验证困难（依赖 `ollama list` 实时输出），已通过代码走查确认逻辑闭合。

### 1.2 🟠 严重 — `scripts/setup_ollama.ps1` 转录（Transcript）可能不关闭导致 CI 误判成功（已修复）
- **现象**：多处 `Stop-Transcript` 在 `exit 1` 前未闭合；未捕获的终止性异常会让转录句柄一直挂着，且脚本可能**以非零原因失败却被 CI 当成成功**。
- **根因**：`$ErrorActionPreference="Stop"` 下，未兜底未预期异常；部分分支 `exit 1` 前漏写 `Stop-Transcript`。
- **修复**：加全局 `trap { ...; Stop-Transcript; exit 1 }`，保证任何未预期终止性错误都关闭转录并以非零退出。
- **复核**：对 PowerShell 5.1 行为为合理防护；`trap` 在 `Stop` 模式下能拦截未处理异常。

### 1.3 🟡 一般 — `scripts/ci_validate.py` 代码块内示例链接被误报为失效（已修复）
- **现象**：原实现对整篇 Markdown 文本 `findall` 链接，会把 ``` 代码围栏内作为示例出现的 URL（如 `https://...`）误判，但更关键的是把"相对链接示例"当真实失败；也曾存在把示例路径当失效。
- **根因**：未区分正文与代码块。
- **修复**：逐行解析、`^\s*(```|~~~)` 检测围栏，处于代码块内则跳过链接检查（外链/http/锚点本就跳过）。
- **复核**：已在真实仓库跑 `ci_validate.py` 验证无误报。

### 1.4 🟢 提示 — `scripts/ci_validate.py` 死代码（已修复）
- **现象**：存在未使用的 `width = max(...)`。
- **修复**：删除。

### 1.5 🟠 严重（运营坑）— 嵌入模型首次联网下载超时残留（已缓解）
- **现象**：`chroma-default` 使用的 `all-MiniLM-L6-v2` 首次运行需联网下载约 80MB 到 `%USERPROFILE%\.cache\chroma\onnx_models\`。沙箱网络弱时下了 3.9MB 就超时（`The read operation timed out in upsert`），并在缓存目录留下**残片**。残片会让 Chroma 误判"已缓存"而跳过重下，进而后续全部嵌入失败。
- **缓解**：已删除残片，并在 `docs/plc/rag_guide.md` 第 4.2 节写入绕法：`provider` 切到 `ollama`（用本地嵌入模型，完全离线）或预先把缓存目录拷贝到位。
- **建议**（见 2.3）：在 `rag_manager.py` 启动嵌入前**显式检测并清理损坏缓存 / 捕获超时给清晰报错**，避免静默降级。

---

## 2. 仍需处理 / 加固建议

### 2.1 🟠 严重 — 公开仓库 + 自托管 runner 的代码执行风险（已做基础防护，仍需巡检）
- **现状**：GitHub 侧 `setup-ollama` job 已锁成 `workflow_dispatch` 手动触发（公开仓库安全默认）；CNB 侧 `setup-ollama-on-windows-node` 已加 `allowFailure: true`。
- **风险**：若使用者为"省事"把自托管 job 改成 push/PR 自动触发，任何能提 PR 的人都能在该机器执行任意代码。
- **建议**：
  1. 文档明确"只允许手动触发"；若要自动化，把仓库设为私有或将 runner 限制到受保护分支 + 必要审查。
  2. 自托管节点注册在**专用开发机**而非产线控制主机（见 `docs/plc/SAFETY.md` 第五节）。

### 2.2 🟡 一般 — 凭据管理（已补 `.gitignore`）
- **已补**：`.gitignore` 增加 `*.token`、`.cnb/`、`*credentials*.json`、`.env`，防止令牌/凭据误提交。CNB token 本体在 `~/.cnb/token`（用户家目录，本就在仓库外）。
- **建议**：在 `docs/deploy/ollama_setup.md` 增加"令牌用后即废、定期轮换、勿贴聊天/工单"的显式提示。

### 2.3 🟡 一般 — 嵌入缓存损坏的显式处理（建议增强）
- 在 `rag_manager.py` 的 `get_embedding_fn`/`get_client` 处，对 `chroma-default` 首次下载增加 try/except，命中超时或 onnx 模型加载失败时，**打印明确指引**（指向 `rag_guide.md` 4.1）而非抛出晦涩的 `read operation timed out`。

### 2.4 🟢 提示 — 可观测性 / 日志轮转
- `logs/` 无大小上限、无轮转，长时间运行可能膨胀。建议 `setup_ollama.ps1` 转录写入带日期文件名（已实现），并在文档提示定期清理；可在 `selfcheck.ps1` 增加"日志目录体积"告警。

### 2.5 🟢 提示 — CI 语法静态检查
- 建议在云端 `validate` 阶段增加 `yamllint`（校验 `.cnb.yml` / workflow）与 `powershell -Command Invoke-ScriptAnalyzer`（校验 `*.ps1`），把"脚本质量门禁"前移。当前靠 `ci_validate.py` 做结构校验，已覆盖 BOM/JSON/链接，但没覆盖 PS1 逻辑 lint。

### 2.6 🟢 提示 — `bootstrap.py` 健壮性增强
- 已具备 `--dry-run`（不落盘预览）。建议再加 `--check`（仅校验环境：Python 版本、目录可写、Ollama 可达），方便 CI 在"不安装"前提下做环境断言。当前 `detect_python`/`parse_requirements`/`ensure_dirs` 已可单测覆盖（见 `tests/test_bootstrap.py`）。

---

## 3. 架构与可维护性评价

| 项 | 评价 |
|---|---|
| **部署能力是否完全收进仓库** | ✅ 是。`deploy/bootstrap.py`（跨平台 Python）+ `install.ps1`（Windows）+ `setup.sh`（Linux/macOS）+ 两套 CI 流水线，clone + 一条命令即可部署，本机除 Python 外零预装。 |
| **幂等性** | ✅ `setup_ollama.ps1`、`install.ps1`、`bootstrap.py` 均支持重复执行；`rag_manager` 导入用 `md5(内容)` 做幂等键，重复导入不重复入库（已用集成测试验证）。 |
| **零依赖校验/测试** | ✅ `ci_validate.py` 与 `tests/` 仅用 stdlib + 已有 chromadb；chromadb 集成用例用 `skipUnless` + `FakeEmbedding` 离线跑，不触发联网下载。 |
| **跨平台一致性** | ✅ Windows 走 PS1，Linux/macOS 走 `setup.sh`→`bootstrap.py`，能力对齐。 |
| **安全默认** | ✅ 自托管安装仅手动触发；`.gitignore` 覆盖敏感信息；SAFETY.md 单列 CI/节点风险。 |

---

## 4. 是否改动 —— 结论

- **本轮已改动**：`setup_ollama.ps1`（1.1/1.2）、`ci_validate.py`（1.3/1.4）、`.gitignore`（2.2）、`SAFETY.md`（新增第五节）、新增 `deploy/bootstrap.py` + `deploy/setup.sh`、新增 `tests/`、CI 增加 test job。
- **建议下一轮改动**：2.3（嵌入缓存显式处理）、2.5（CI lint 门禁）、2.6（`--check`）。
- **整体判定**：通过资深 IT 视角深挖，工程结构稳健、部署闭环完整、关键 bug 已修复；剩余为加固项，不阻塞交付。三端（本机工作区 / GitHub / CNB）在本轮提交后保持一致。
