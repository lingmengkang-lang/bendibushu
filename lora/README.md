# LoRA 微调配套（LLaMA-Factory）

本目录提供基于 [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) 的 LoRA/QLoRA 微调配套：配置模板、启动脚本、数据集注册与示例数据。

## 先读这个：训练模型 ≠ 推理模型

| 用途 | 格式 | 来源 |
|---|---|---|
| LoRA 微调 | HuggingFace / ModelScope 格式（safetensors 目录或在线 ID） | `huggingface.co` / `modelscope.cn` 下载 |
| Ollama 本地推理 | gguf（Ollama 专用格式） | `ollama pull` 拉取 |

两者**不通用**。训练产物（LoRA adapter 或合并后的完整模型）要用于 Ollama 推理，需经过「合并 LoRA → 导出 → Ollama 导入」流程。
该流程的具体命令随两个项目版本变化较大，**请以 LLaMA-Factory 与 Ollama 双方官方文档为准**，本工程不固化命令，避免给出过时指令。【⚠️需核实】

## 目录结构

```
lora/
├── README.md                 本说明
├── requirements.txt          微调依赖（llamafactory；torch 需另行按 CUDA 版本安装）
├── train.ps1                 训练启动器（CLI 模式 / -WebUI 模式）
├── configs/
│   └── qlora_sft.yaml        QLoRA SFT 配置模板（4bit 量化，显存友好）
└── dataset/
    ├── dataset_info.json     数据集注册表（把数据集名称映射到文件与格式）
    └── data/
        └── sample_sft.json   示例数据（alpaca 格式，3 条，仅演示结构）
```

## 安装（独立于核心环境）

```powershell
# 1. 先装 GPU 版 torch（命令以 pytorch.org 当前页面为准）
pip install torch --index-url https://download.pytorch.org/whl/cu121

# 2. 再装 LLaMA-Factory
pip install -r lora\requirements.txt
```

## 快速开始

```powershell
# 方式一：WebUI（图形界面，适合调参）
.\lora\train.ps1 -WebUI
# 然后浏览器打开 http://127.0.0.1:7860

# 方式二：命令行（按模板配置训练）
.\lora\train.ps1
# 等价于：venv\Scripts\llamafactory-cli.exe train lora\configs\qlora_sft.yaml
```

## 数据集准备

1. 数据文件为 alpaca 格式 JSON 数组：`instruction`（指令）/ `input`（可选输入）/ `output`（期望输出），可加 `system`；
2. 在 `dataset/dataset_info.json` 中注册（示例已含 `sample_sft`）；
3. 训练配置 `configs/qlora_sft.yaml` 的 `dataset` 字段填注册名；
4. 示例数据仅 3 条用于跑通流程，正式训练请替换为你自己的数据（建议千条量级起步）。

## 硬件与平台说明

- **显存**：7B 模型 QLoRA 4bit 约需 12GB 级显存；14B 约需 20GB 级【⚠️经验值，以实测为准】；显存不足时依次降 `lora_rank`、`cutoff_len`、`per_device_train_batch_size`；
- **bf16**：模板默认开启，需 Ampere（RTX 30 系）及以上 NVIDIA 显卡；老卡改为 `fp16: true`；
- **Windows**：LLaMA-Factory 在 Windows 原生环境可跑通单卡流程；多卡、量化内核、DeepSpeed 等场景在 Windows 上坑较多，生产训练建议 Linux 或 WSL2【⚠️社区经验，非官方承诺】。

## 常见报错速查

| 现象 | 优先检查 |
|---|---|
| CUDA out of memory | 降 batch / rank / cutoff_len，或确认安装的是 GPU 版 torch |
| `llamafactory-cli` 找不到 | venv 未安装依赖，见上文安装步骤 |
| template 报错 | `template` 与基座模型不匹配（qwen/llama/deepseek 需对应） |
| 数据集加载失败 | `dataset_info.json` 注册名与配置 `dataset` 不一致，或 JSON 格式错误 |
