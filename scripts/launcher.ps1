# launcher.ps1 — 本地离线工控助手 · 一键首次部署与启动编排
# 由根目录 启动.bat 调用（已带 -ExecutionPolicy Bypass）。
# 职责（全部在本机执行，满足"离线助手"定位；首次运行需联网拉取依赖/引擎/模型）：
#   1) 检测 Python 3.10+
#   2) 创建 venv 并安装 requirements.txt（核心依赖 chromadb 等）
#   3) 检测 / 安装 Ollama（唯一必须装一次的系统组件；装完请重开本脚本）
#   4) 拉取默认模型（config/ollama-models.txt 第一个未注释项，首次较大）
#   5) 导入知识库（best-effort；chroma-default 首次需联网下载嵌入模型，失败则降级）
#   6) 启动 Ollama 服务 + 本地 Web 聊天界面（自动打开浏览器 http://127.0.0.1:8500）
# 幂等：venv / 依赖 / 模型 / 知识库均重复执行安全。

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

function Write-Step([string]$m){ Write-Host ("[==] " + $m) -ForegroundColor Cyan }
function Write-Ok([string]$m){ Write-Host ("[OK] " + $m) -ForegroundColor Green }
function Write-Warn([string]$m){ Write-Host ("[WARN] " + $m) -ForegroundColor Yellow }
function Write-Fail([string]$m){ Write-Host ("[FAIL] " + $m) -ForegroundColor Red }

function Open-Url([string]$u){
    try { Start-Process $u } catch { }
}

function Get-TotalRamGB {
    # 返回物理内存总量（GB）；读不到返回 0（表示跳过内存护栏）
    try {
        $m = Get-CimInstance Win32_PhysicalMemory
        $sum = ($m | Measure-Object Capacity -Sum).Sum
        if ($sum -gt 0) { return [math]::Round($sum/1GB, 1) }
    } catch { }
    return 0
}

function Get-ModelMinRamGB([string]$name) {
    # 按模型 tag 估算"能跑起来"的最小内存（经验值，偏保守；CPU 卸载虽能突破但速度不可接受）
    $n = $name.ToLower()
    if ($n -match "72b") { return 48 }
    if ($n -match "32b") { return 24 }
    if ($n -match "14b") { return 12 }
    if ($n -match "7b")  { return 8 }
    if ($n -match "3b")  { return 4 }
    if ($n -match "bge-m3|nomic|minicpm") { return 2 }
    return 8
}

function Test-RamForModel([string]$name) {
    # 内存够返回 $true；不够打印警告并返回 $false（调用方跳过拉取）
    $ram = Get-TotalRamGB
    $need = Get-ModelMinRamGB $name
    if ($ram -le 0) { return $true }   # 读不到内存信息时不阻拦
    if ($ram -ge $need) { return $true }
    Write-Warn ("内存不足，已跳过拉取 {0}（本机 {1}GB < 约需 {2}GB）。" -f $name, $ram, $need)
    Write-Warn "内存不足时大模型不是'慢'，而是磁盘交换卡死。两个选择："
    Write-Warn "  A) 升级内存后重跑 启动.bat（32B 档约需 24GB+，72B 档约需 48GB+）"
    Write-Warn "  B) 暂不升级：把 config\ollama-models.txt 第一个未注释项改成 qwen2.5:14b-instruct-q6_K（16GB 可跑）"
    return $false
}

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "   本地离线工控助手 · 一键部署与启动" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ("工程目录: {0}" -f $root)
Write-Host ""

# ---------- 1. Python 检测 ----------
Write-Step "检测 Python 3.10+ ..."
$py = $null
foreach ($c in @("python","python3","py")) {
    try {
        $ver = & $c --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $ver -match "3\.(\d+)") {
            if ([int]$Matches[1] -ge 10) { $py = $c; break }
        }
    } catch { }
}
if (-not $py) {
    Write-Fail "未检测到 Python 3.10+。"
    Write-Host "   请先安装：https://www.python.org/downloads/  （安装时务必勾选 Add to PATH）"
    Open-Url "https://www.python.org/downloads/"
    exit 1
}
Write-Ok ("Python 就绪: " + (& $py --version 2>&1))

# ---------- 2. venv + 依赖 ----------
Write-Step "准备 venv 与依赖 ..."
$venvPy = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    & $py -m venv $root/venv
    if ($LASTEXITCODE -ne 0) { Write-Fail "venv 创建失败"; exit 1 }
}
$pip = Join-Path $root "venv\Scripts\pip.exe"
& $pip install --upgrade pip | Out-Null
& $pip install -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { Write-Warn "依赖安装失败（检查网络与 pip 源），后续步骤可能受影响。" }
else { Write-Ok "依赖安装完成。" }

# ---------- 3. Ollama 检测 / 安装 ----------
Write-Step "检测 Ollama ..."
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Warn "未检测到 Ollama。尝试通过 winget 安装（需要管理员权限，可能弹 UAC）..."
    try {
        winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements | Out-Null
    } catch { }
    # 刷新当前进程 PATH（winget 装完不会自动刷新）
    $env:Path = "$env:Path;$(Join-Path $env:LOCALAPPDATA 'Programs\Ollama');$(Join-Path ${env:ProgramFiles} 'Ollama')"
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
}
if (-not $ollama) {
    Write-Fail "仍未检测到 Ollama。请手动安装：https://ollama.com/download ，装完重新双击 启动.bat。"
    Open-Url "https://ollama.com/download"
    exit 1
}
Write-Ok ("Ollama 就绪: " + $ollama.Source)

# ---------- 4. 拉取默认模型 ----------
Write-Step "拉取默认模型（首次较大，请耐心等待）..."
$model = "qwen2.5:32b-instruct-q4_K_M"
$mf = Join-Path $root "config\ollama-models.txt"
if (Test-Path $mf) {
    foreach ($line in Get-Content $mf) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith("#")) { continue }
        $model = ($t -split "#")[0].Trim(); break
    }
}
Write-Host ("   模型: {0}" -f $model)
if (Test-RamForModel $model) {
    & ollama pull $model
    if ($LASTEXITCODE -ne 0) { Write-Warn ("模型拉取失败（网络/磁盘？）。可稍后手动: ollama pull {0}" -f $model) }
    else { Write-Ok ("模型就绪: {0}" -f $model) }
}

# ---------- 4b. 拉取视觉/图片解析模型（best-effort，用于“看图”）----------
Write-Step "拉取视觉/图片解析模型（可选，首次较大）..."
$vmodel = "qwen2.5vl:32b-q4_K_M"
$vf = Join-Path $root "config\ollama-vision-model.txt"
if (Test-Path $vf) {
    foreach ($line in Get-Content $vf) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith("#")) { continue }
        $vmodel = ($t -split "#")[0].Trim(); break
    }
}
Write-Host ("   视觉模型: {0}" -f $vmodel)
if (Test-RamForModel $vmodel) {
    & ollama pull $vmodel
    if ($LASTEXITCODE -ne 0) { Write-Warn ("视觉模型拉取失败（网络/磁盘？）。图片解析功能暂不可用；可稍后手动: ollama pull {0}" -f $vmodel) }
    else { Write-Ok ("视觉模型就绪: {0}" -f $vmodel) }
}

# ---------- 5. 导入知识库（best-effort）----------
Write-Step "导入知识库（best-effort，首次可能需联网下载嵌入模型）..."
try {
    & $venvPy (Join-Path $root "scripts\rag_manager.py") add-all
    Write-Ok "知识库导入完成（失败项见上方；若嵌入模型下载失败，可改用 config 中 provider=ollama 后重跑）。"
} catch {
    Write-Warn ("知识库导入异常: {0}" -f $_.Exception.Message)
}

# ---------- 6. 启动 Ollama + Web 界面 ----------
Write-Step "启动 Ollama 服务与本地 Web 聊天界面 ..."
& (Join-Path $root "scripts\start.ps1") -Assistant

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Green
Write-Host "  完成：浏览器应已打开 http://127.0.0.1:8500" -ForegroundColor Green
Write-Host "  若未自动打开，请手动访问该地址。" -ForegroundColor Green
Write-Host "  停止服务：双击 停止.bat" -ForegroundColor Green
Write-Host "  说明：首次需联网；之后完全离线。Ollama/模型只需装/拉一次。" -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green
