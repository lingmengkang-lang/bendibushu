# install.ps1 — local-offline-assistant 一键部署脚本
# 用法（工程根目录执行）：
#   .\deploy\install.ps1                 标准部署（不自动安装 Ollama，只检测+引导）
#   .\deploy\install.ps1 -InstallOllama  额外尝试通过 winget 安装 Ollama（需联网+管理员）
#   .\deploy\install.ps1 -RecreateVenv   删除并重建 venv（依赖重装）
#
# 本脚本做什么：
#   1) 检查 Python 3.10+
#   2) 创建 venv 并安装 requirements.txt
#   3) 初始化目录结构
#   4) 检测 Ollama（可选安装）
#   5) 运行 selfcheck.ps1 汇总环境状态
# 本脚本不做什么（遵守"只做工程产出"约定）：
#   - 不拉取任何模型（模型清单在 config\ollama-models.txt，由你手动 ollama pull）
#
# 幂等性：重复执行安全；已存在的 venv 默认跳过创建（除非 -RecreateVenv）。

param(
    [switch]$InstallOllama,
    [switch]$RecreateVenv
)

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent

Write-Host "===== local-offline-assistant 一键部署 =====" -ForegroundColor Cyan
Write-Host ("工程目录: {0}" -f $root)
Write-Host ""

# ---------- 1. Python 检测 ----------
$pyCmd = $null
foreach ($c in @("python", "py")) {
    try {
        $ver = & $c --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $ver -match "3\.(\d+)" -and [int]$Matches[1] -ge 10) {
            $pyCmd = $c; break
        }
    } catch { }
}
if (-not $pyCmd) {
    Write-Host "[FAIL] 未检测到 Python 3.10+。请先从 https://www.python.org/downloads/ 安装（安装时勾选 Add to PATH）。" -ForegroundColor Red
    exit 1
}
Write-Host ("[1/5] Python 检测通过: {0}" -f (& $pyCmd --version 2>&1)) -ForegroundColor Green

# ---------- 2. venv + 依赖 ----------
$venvDir = Join-Path $root "venv"
if ($RecreateVenv -and (Test-Path $venvDir)) {
    Write-Host "      正在删除旧 venv ..."
    Remove-Item $venvDir -Recurse -Force
}
if (-not (Test-Path $venvDir)) {
    Write-Host "[2/5] 创建 venv ..."
    & $pyCmd -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] venv 创建失败" -ForegroundColor Red; exit 1 }
} else {
    Write-Host "[2/5] venv 已存在，跳过创建（-RecreateVenv 可重建）。" -ForegroundColor Yellow
}
$pip = Join-Path $venvDir "Scripts\pip.exe"
Write-Host "      安装依赖（chromadb 等，耗时取决于网络）..."
& $pip install --upgrade pip
& $pip install -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { Write-Host "[FAIL] 依赖安装失败，请检查网络与 pip 源。" -ForegroundColor Red; exit 1 }
Write-Host "      依赖安装完成。" -ForegroundColor Green

# ---------- 3. 目录结构 ----------
Write-Host "[3/5] 初始化目录结构 ..."
$dirs = @(
    "data\chroma",
    "data\knowledge_base\docs",
    "logs",
    "models",
    "lora\output",
    "lora\dataset\data"
)
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Path (Join-Path $root $d) -Force | Out-Null
}
foreach ($gk in @("data\knowledge_base\docs\.gitkeep", "lora\dataset\data\.gitkeep")) {
    $p = Join-Path $root $gk
    if (-not (Test-Path $p)) { New-Item -ItemType File -Path $p -Force | Out-Null }
}
Write-Host "      目录就绪。" -ForegroundColor Green

# ---------- 4. Ollama 检测 / 可选安装 ----------
Write-Host "[4/5] 检测 Ollama ..."
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCmd) {
    Write-Host ("      Ollama 已安装: {0}" -f $ollamaCmd.Source) -ForegroundColor Green
} elseif ($InstallOllama) {
    Write-Host "      尝试通过 winget 安装 Ollama（需要联网，可能弹出 UAC）..."
    try {
        winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
        Write-Host "      winget 安装流程结束，请重开终端后验证 'ollama --version'。" -ForegroundColor Green
    } catch {
        Write-Host ("      [WARN] winget 安装失败: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
        Write-Host "      请手动下载安装: https://ollama.com/download" -ForegroundColor Yellow
    }
} else {
    Write-Host "      [WARN] 未检测到 Ollama。" -ForegroundColor Yellow
    Write-Host "             手动安装: https://ollama.com/download" -ForegroundColor Yellow
    Write-Host "             或加 -InstallOllama 参数让本脚本尝试 winget 安装。" -ForegroundColor Yellow
}

# ---------- 5. 自检 ----------
Write-Host "[5/5] 运行环境自检 ..."
& (Join-Path $root "scripts\selfcheck.ps1")
$sc = $LASTEXITCODE

Write-Host ""
Write-Host "===== 部署完成 =====" -ForegroundColor Cyan
Write-Host "后续步骤（按顺序）：" -ForegroundColor Cyan
Write-Host "  1) 重开一个终端（刷新 PATH），启动服务:  .\scripts\start.ps1"
Write-Host "  2) 拉取模型（首次必须）:           ollama pull qwen2.5:7b"
Write-Host "  3) 放入知识库文档到 data\knowledge_base\docs\，然后导入:"
Write-Host "     python scripts\rag_manager.py add data\knowledge_base\docs -r"
Write-Host "  4) WorkBuddy 接入配置:             见 config\workbuddy\knowledge-base.md"
Write-Host "  5) LoRA 微调（可选）:              见 lora\README.md"
if ($sc -ne 0) { Write-Host "`n注意：自检存在 FAIL 项（见上），请先修复。" -ForegroundColor Red; exit 1 }
exit 0
