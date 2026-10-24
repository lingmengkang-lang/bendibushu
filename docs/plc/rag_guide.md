# PLC / 工控知识库（RAG）使用指引

本助手准确性的关键，不是盲目换更大模型，而是**把你们自己的资料喂给它**。
RAG（检索增强）让模型在回答时引用你提供的手册、样本与程序，显著降低幻觉。

## 一、把什么放进知识库
建议集中放到工程内的 `data/knowledge_base/docs/`（部署时该目录已存在）：

- **厂家编程手册 / 指令集**：西门子、台达、三菱、信捷、欧姆龙、汇川等；
- **产品样本 / 选型手册**：PLC、伺服电机、驱动器、变频电源（VFD）；
- **你们现有的程序片段**（**务必脱敏**：去掉真实 IP、账号、工艺机密、涉密图纸）；
- **通信协议说明**：Modbus RTU/TCP 寄存器表、EtherCAT/脉冲接线、参数地址映射；
- **故障代码表 / 排查经验**：把常见报警与处理写成文档，检索效果极佳。

> 多品牌混用时，建议按品牌建子目录（如 `docs/siemens/`、`docs/mitsubishi/`），
> 或在文件名/正文里写明品牌，便于模型区分指令差异。

## 二、支持的格式
`rag_manager.py` 支持 `.md` / `.txt`，PDF 用 `pypdf` 解析（见 `requirements.txt`）。
优先用 **Markdown**：结构清晰、分块检索效果更好。

## 三、导入与验证
```powershell
# 1) 把资料放好后，建立/更新向量库（递归 -r 含子目录）
python scripts\rag_manager.py add data\knowledge_base\docs -r

# 2) 检索验证（用工控相关提问）
python scripts\rag_manager.py search "西门子 S7-1200 怎么配置高速计数器" --top-k 5

# 3) 查看集合统计
python scripts\rag_manager.py stats
```

## 四、配置要点（见 config/rag.config.json）
- `chunk_size` / `chunk_overlap`：手册类长文档建议 500/50，避免截断语义；
- `provider`：默认 `chroma-default`（首次需联网下载 ONNX 嵌入权重）；
  完全离线机器请切 `ollama` 用本地嵌入模型（见 `config/workbuddy/knowledge-base.md`）。

## 五、注意事项
- **不要**把涉密/隐私信息提交进 Git 仓库（这些文件已被 `.gitignore` 排除，不会入库）；
- 资料更新后，重新执行一次 `add` 即可（脚本为幂等 upsert）；
- 若想彻底重建，慎用 `rag_manager.py clear`（会永久删除整个集合，需交互确认）。
