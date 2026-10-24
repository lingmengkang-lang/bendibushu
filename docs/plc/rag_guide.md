# PLC / 工控知识库（RAG）使用指引

本助手准确性的关键，不是盲目换更大模型，而是**把你们自己的资料喂给它**。
RAG（检索增强）让模型在回答时引用你提供的手册、样本与程序，显著降低幻觉。

## 一、把什么放进知识库
建议集中放到工程内的 `data/knowledge_base/docs/`（部署时该目录已存在）：

- **PLC 编程手册 / 指令集**：西门子、台达、三菱、信捷、欧姆龙、汇川等；
- **HMI / 触摸屏软件手册**：WinCC、GT Designer、NB/CX-Designer、DOPSoft、InoProShop HMI、MCGS、EBPro 等（变量地址表、通信驱动、画面组态说明极有价值）；
- **组态软件手册 / 样例工程**：组态王（KingView）命令语言与变量点表、MCGS（昆仑通态）脚本与设备窗口、台达 DIAEntegro、WinCC、力控 等（变量点表、设备通信参数、命令语言/脚本样例极具参考价值）；
- **上位机程序样例**：C#（NModbus / S7.Net / OPC UA）、Python（pymodbus / python-snap7 / python-opcua）、LabVIEW 等读写下位机的源码与寄存器分配表（务必脱敏）；
- **伺服 / 驱动器手册**：IS620P、MR-Config、各品牌调试软件说明、参数表、三环整定笔记；
- **变频器 / 变频电源（VFD）手册**：参数说明、加减速/多段速/Modbus 寄存器表；
- **编码器资料**：选型样本、接线图、SSI/EnDat/BiSS 协议说明；
- **产品样本 / 选型手册**：PLC、伺服电机、驱动器、变频电源；
- **你们现有的程序片段**（**务必脱敏**：去掉真实 IP、账号、工艺机密、涉密图纸）；
- **通信协议说明**：Modbus RTU/TCP 寄存器表、EtherCAT/脉冲接线、参数地址映射；
- **故障代码表 / 排查经验**：把常见报警与处理写成文档，检索效果极佳。

> 多品牌混用时，建议按品牌 + 设备类型建子目录（如 `docs/siemens/`、`docs/mitsubishi/`、`docs/hmi/`、`docs/scada/`、`docs/host/`、`docs/encoder/`），
> 或在文件名/正文里写明品牌与型号，便于模型区分指令差异。

## 二、支持的格式
`rag_manager.py` 支持 `.md` / `.txt`，PDF 用 `pypdf` 解析（见 `requirements.txt`）。
优先用 **Markdown**：结构清晰、分块检索效果更好。

## 三、导入与验证

本工程已把知识目录配好（见 `config/rag.config.json` 的 `knowledge_dirs`），
新增场景文档放进去后**一条命令即可全部入库**：

```powershell
# 1) 一键导入所有知识目录（新增 PLC 品牌/电气件/组态样例后用这个）
python scripts\rag_manager.py add-all

# 2) 确认没有漏入库的文件
python scripts\rag_manager.py scan

# 3) 检索验证（用工控相关提问）
python scripts\rag_manager.py search "组态王 命令语言 定时 计时" --top-k 5

# 4) 查看集合统计
python scripts\rag_manager.py stats
```

> 只导单个目录/文件时仍可用：`python scripts\rag_manager.py add <路径> -r`

## 四、配置要点（见 config/rag.config.json）
- `chunk_size` / `chunk_overlap`：手册类长文档建议 500/50，避免截断语义；
- `knowledge_dirs`：`add-all` / `scan` 按此列表走；**新建目录后加到这里**；
- `provider`：默认 `ollama` + `bge-m3`（中文/多语言嵌入，约 1.2GB，中文检索明显优于
  Chroma 内置的英文向 ONNX 嵌入；需先 `ollama pull bge-m3`，`setup_ollama.ps1` 会自动拉）；
  备选 `chroma-default`（首次需联网下载 ONNX 嵌入权重，约 80MB，见 `config/workbuddy/knowledge-base.md`）。

### 4.1 ⚠️ 切换嵌入方式/模型 = 向量库必须重建（维度不兼容）

`chroma-default`（`all-MiniLM-L6-v2`，384 维）与 `bge-m3`（1024 维）产出的向量**维度不同**，
同一集合里混用会在检索时报维度错误。凡改动 `embedding.provider` 或 `embedding.ollama_model`：

```powershell
python scripts\rag_manager.py clear     # ⚠️ 永久删除整个集合，需交互输入 yes
python scripts\rag_manager.py add-all   # 用新嵌入模型重建
```

> 备份提示：`data/chroma` 为运行时数据（已被 `.gitignore` 排除），重建前如有重要导入结果，
> 先复制 `data\chroma` 目录留底。

### 4.2 首次运行要联网下载嵌入模型（chroma-default 路线的实测踩坑）

`chroma-default` 用的是 `all-MiniLM-L6-v2`，**第一次执行 add/search 会自动下载约 80MB 的
ONNX 权重**到 `%USERPROFILE%\.cache\chroma\onnx_models\`，之后才真正离线。

如果本机下载不了（表现为卡在 `onnx.tar.gz` 反复重试、最后报
`The read operation timed out in upsert`），三种解法：

1. **换本地嵌入模型（推荐，本工程默认已是此路线）**：确认 `config/rag.config.json` 的
   `embedding.provider` 为 `ollama`，并先 `ollama pull bge-m3`（`setup_ollama.ps1` 会自动拉）。
2. **预置缓存**：在能联网的机器上下载好权重，把整个
   `%USERPROFILE%\.cache\chroma\onnx_models\all-MiniLM-L6-v2` 目录拷到本机同路径。
3. **清掉半截文件再重试**：下载中断会留下不完整的 `onnx.tar.gz`，删掉它再在好网络下重跑
   （残留文件会被误判为"已缓存"而报损坏）。

## 五、注意事项
- **不要**把涉密/隐私信息提交进 Git 仓库（这些文件已被 `.gitignore` 排除，不会入库）；
- 资料更新后，重新执行一次 `add` 即可（脚本为幂等 upsert）；
- 若想彻底重建，慎用 `rag_manager.py clear`（会永久删除整个集合，需交互确认）。
