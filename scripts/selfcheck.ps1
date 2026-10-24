# selfcheck.ps1 — local-offline-assistant 环境自检
# 用法：在工程根目录执行  .\scripts\selfcheck.ps1
# 退出码：0 = 全部通过（允许 WARN）；1 = 存在 FAIL
# 兼容：Windows PowerShell 5.1（无 ?? / ?: 语法）

param(
    [switch]$VerboseOutput
)

$ErrorActionPreference = "Continue"
$root = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
$results = @()

function Add-Result([string]$Name, [string]$Status, [string]$Detail) {
    $script:results += [pscustomobject]@{ Name = $Name; Status = $Status; Detail = $Detail }
    $color = switch ($Status) { "PASS" { "Green" } "WARN" { "Yellow" } default { "Red" } }
    Write-Host ("[{0}] {1} - {2}" -f $Status, $Name, $Detail) -ForegroundColor $color
}

Write-Host "===== local-offline-assistant 环境自检 =====" -ForegroundColor Cyan
Write-Host ("工程目录: {0}" -f $root)
Write-Host ""

# ---- 1. Python 版本 ----
$pyCmd = $null
foreach ($c in @("python", "py")) {
    try {
        $ver = & $c --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $ver -match "3\.(\d+)") {
            if ([int]$Matches[1] -ge 10) { $pyCmd = $c; break }
        }
    } catch { }
}
if ($pyCmd) {
    Add-Result "Python 3.10+" "PASS" (& $pyCmd --version 2>&1)
} else {
    Add-Result "Python 3.10+" "FAIL" "未检测到 Python 3.10+，请先安装（python.org 或 Microsoft Store）"
}

# ---- 2. venv 与核心依赖 ----
$venvPy = Join-Path $root "venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    Add-Result "venv 存在" "PASS" "venv\"
    try {
        & $venvPy -c "import chromadb; print('chromadb', chromadb.__version__)" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Add-Result "chromadb 已安装" "PASS" (& $venvPy -c "import chromadb; print(chromadb.__version__)" 2>&1)
        } else {
            Add-Result "chromadb 已安装" "FAIL" "venv 内未安装 chromadb，执行: venv\Scripts\pip install -r requirements.txt"
        }
    } catch {
        Add-Result "chromadb 已安装" "FAIL" "检测异常: $_"
    }
} else {
    Add-Result "venv 存在" "WARN" "未创建 venv，请先执行 deploy\install.ps1"
}

# ---- 3. Ollama 安装与服务 ----
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCmd) {
    Add-Result "Ollama 已安装" "PASS" $ollamaCmd.Source
    $svc = $null
    try {
        $svc = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 5 -ErrorAction Stop
        Add-Result "Ollama 服务(11434)" "PASS" ("version: " + $svc.version)
    } catch {
        Add-Result "Ollama 服务(11434)" "WARN" "未运行，执行 scripts\start.ps1 启动"
    }
} else {
    Add-Result "Ollama 已安装" "WARN" "未检测到 ollama 命令（未安装或未加入 PATH），下载: https://ollama.com"
}

# ---- 4. 目录结构 ----
foreach ($d in @("data\chroma", "data\knowledge_base\docs", "logs", "config")) {
    if (Test-Path (Join-Path $root $d)) {
        Add-Result ("目录 " + $d) "PASS" "存在"
    } else {
        Add-Result ("目录 " + $d) "WARN" "缺失，执行 deploy\install.ps1 初始化"
    }
}

# ---- 5. 配置文件 JSON 有效性 ----
foreach ($j in @("config\rag.config.json", "config\workbuddy\mcp.fragment.json")) {
    $p = Join-Path $root $j
    if (-not (Test-Path $p)) { Add-Result $j "WARN" "文件缺失"; continue }
    try {
        Get-Content $p -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null
        Add-Result $j "PASS" "JSON 合法"
    } catch {
        Add-Result $j "FAIL" ("JSON 解析失败: " + $_.Exception.Message)
    }
}

# ---- 6. 端口占用 ----
foreach ($port in @(11434, 7860)) {
    $name = switch ($port) { 11434 { "Ollama" } 7860 { "LLaMA-Factory WebUI" } }
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($conn) { Add-Result ("端口 " + $port) "PASS" ($name + " 监听中") }
    else { Add-Result ("端口 " + $port) "WARN" ($name + " 未监听（未启动时为正常）") }
}

# ---- 7. GPU（可选参考） ----
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    try {
        $gpu = (& nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1 | Select-Object -First 1)
        Add-Result "NVIDIA GPU" "PASS" $gpu
    } catch { Add-Result "NVIDIA GPU" "WARN" "nvidia-smi 执行异常" }
} else {
    Add-Result "NVIDIA GPU" "WARN" "未检测到 nvidia-smi（无独显或驱动未装，仅 CPU 推理可用但慢）"
}

# ---- 8. WorkBuddy MCP 配置（提示级）----
$wbCfg = Join-Path $env:USERPROFILE ".workbuddy\mcp.json"
if (Test-Path $wbCfg) { Add-Result "WorkBuddy mcp.json" "PASS" $wbCfg }
else { Add-Result "WorkBuddy mcp.json" "WARN" "未发现 ~/.workbuddy/mcp.json（未使用 WorkBuddy 或未配置时为正常）" }

# ---- 汇总 ----
Write-Host ""
$fail = ($results | Where-Object { $_.Status -eq "FAIL" }).Count
$warn = ($results | Where-Object { $_.Status -eq "WARN" }).Count
$pass = ($results | Where-Object { $_.Status -eq "PASS" }).Count
Write-Host ("===== 汇总: PASS {0} / WARN {1} / FAIL {2} =====" -f $pass, $warn, $fail) -ForegroundColor Cyan
if ($fail -gt 0) {
    Write-Host "存在 FAIL 项，请根据上方提示修复后重跑。" -ForegroundColor Red
    exit 1
}
Write-Host "自检通过（WARN 项请按需处理）。" -ForegroundColor Green
exit 0
