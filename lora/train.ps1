# train.ps1 — LLaMA-Factory 训练启动器
# 用法（工程根目录执行）：
#   .\lora\train.ps1                          # 按 configs\qlora_sft.yaml 训练
#   .\lora\train.ps1 -Config configs\xxx.yaml # 指定其他配置
#   .\lora\train.ps1 -WebUI                   # 改为启动 WebUI（http://127.0.0.1:7860）
#
# 前置条件（本脚本只检查，不自动安装）：
#   1. venv 中已安装 llamafactory（见 lora\requirements.txt）
#   2. 已按 PyTorch 官网指引安装 GPU 版 torch
#   3. 训练模型为 HuggingFace/ModelScope 格式（与 Ollama gguf 不通用）

param(
    [string]$Config = "configs\qlora_sft.yaml",
    [switch]$WebUI
)

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
$loraDir = Join-Path $root "lora"
$cli = Join-Path $root "venv\Scripts\llamafactory-cli.exe"

if (-not (Test-Path $cli)) {
    Write-Host "[FAIL] 未找到 $cli" -ForegroundColor Red
    Write-Host "请先安装：pip install torch（GPU版，见 lora\requirements.txt 注释）后 pip install -r lora\requirements.txt" -ForegroundColor Yellow
    exit 1
}

# GPU 检查（仅提示，不阻断——CPU 可跑但极慢）
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    Write-Host "[WARN] 未检测到 nvidia-smi，将使用 CPU 训练（7B 模型基本不可行，仅作流程验证）。" -ForegroundColor Yellow
}

if ($WebUI) {
    Write-Host "启动 LLaMA-Factory WebUI: http://127.0.0.1:7860"
    Start-Process -FilePath $cli -ArgumentList "webui" -WorkingDirectory $loraDir
    exit 0
}

$cfgPath = Join-Path $loraDir $Config
if (-not (Test-Path $cfgPath)) {
    Write-Host ("[FAIL] 配置不存在: {0}" -f $cfgPath) -ForegroundColor Red
    exit 1
}

# 数据集文件存在性提示
$dsFile = Join-Path $loraDir "dataset\data\sample_sft.json"
if (-not (Test-Path $dsFile)) {
    Write-Host "[WARN] 未找到示例数据集 $dsFile，请确认配置中的 dataset 已备好数据。" -ForegroundColor Yellow
}

Write-Host ("训练配置: {0}" -f $cfgPath) -ForegroundColor Cyan
Write-Host "产物目录: lora\output\ （已配置为 git 忽略）" -ForegroundColor Cyan
Write-Host "开始训练 ...（中断用 Ctrl+C，日志同时写入 logs\ 可由 history_manager.ps1 管理）`n"
& $cli train $cfgPath
$code = $LASTEXITCODE
if ($code -ne 0) {
    Write-Host ("`n[FAIL] 训练退出码 {0}，请检查上方报错（常见：显存不足->降 lora_rank/cutoff_len/batch；bf16 不支持->改 fp16）。" -f $code) -ForegroundColor Red
    exit $code
}
Write-Host "`n[OK] 训练完成。产物在 lora\output\ 下。" -ForegroundColor Green
