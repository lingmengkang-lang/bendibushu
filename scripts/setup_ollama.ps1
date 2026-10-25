# setup_ollama.ps1 — 安装 Ollama 并拉取模型（幂等，可重复执行）
# 用途：
#   1) 本机手动执行：            .\scripts\setup_ollama.ps1
#   2) GitHub Actions 自托管 runner 调用：见 .github\workflows\setup-ollama.yml
#   3) CNB 自托管 Windows 构建节点调用：见 .cnb.yml
#
# 为什么需要"自托管"：GitHub / CNB 的云端 runner 是临时云机器，
#   装完即销毁、也摸不到你的 D:\ 盘。要"让平台自动助手把引擎装到本机"，
#   必须把你的机器注册成自托管 runner/构建节点（见 docs\deploy\ollama_setup.md）。
#
# 参数：
#   -Models "qwen2.5:14b,nomic-embed-text"  指定要拉的模型；缺省解析 config\ollama-models.txt
#   -SkipPull                               只安装 Ollama 引擎，不拉模型
#   -PullVision                             额外拉取视觉/图片解析模型（config\ollama-vision-model.txt；best-effort，失败不致命）
#   -NoServe                                装完不启动 ollama serve
#   -InstallerPath <本地 OllamaSetup.exe>   有本地安装包时直接静默安装（跳过 winget）
#
# 幂等性：已安装的 Ollama 跳过；已拉取的模型跳过；重复执行安全。
# 网络：本脚本不设置代理。若你在代理环境，请在调用前设置 HTTP_PROXY / HTTPS_PROXY。

param(
    [string]$Models = "",
    [switch]$SkipPull,
    [switch]$NoServe,
    [switch]$PullVision,
    [string]$InstallerPath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
$modelsFile = Join-Path $root "config\ollama-models.txt"
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logFile = Join-Path $logDir ("setup_ollama_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
try { Start-Transcript -Path $logFile -Force | Out-Null } catch { }

# 兜底：任何未预期的终止性错误（含 $ErrorActionPreference=Stop 触发）都必须关闭转录
# 并非 0 退出；否则转录一直挂着、且 CI 可能把失败当成功。
trap {
    try { Write-Err ("未预期的异常: {0}" -f $_) } catch { }
    try { Stop-Transcript | Out-Null } catch { }
    exit 1
}

function Write-Step([string]$msg) { Write-Host ("[==] {0}" -f $msg) -ForegroundColor Cyan }
function Write-Ok([string]$msg)   { Write-Host ("[OK] {0}" -f $msg) -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host ("[WARN] {0}" -f $msg) -ForegroundColor Yellow }
function Write-Err([string]$msg)  { Write-Host ("[FAIL] {0}" -f $msg) -ForegroundColor Red }

# 内存护栏：模型所需最小内存（经验值）超过本机物理内存时跳过拉取，
# 避免"下完 20GB 却因内存不足跑不动"。读不到内存信息时不阻拦。
function Get-TotalRamGB {
    try {
        $m = Get-CimInstance Win32_PhysicalMemory
        $sum = ($m | Measure-Object Capacity -Sum).Sum
        if ($sum -gt 0) { return [math]::Round($sum/1GB, 1) }
    } catch { }
    return 0
}

function Get-ModelMinRamGB([string]$name) {
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
    $ram = Get-TotalRamGB
    $need = Get-ModelMinRamGB $name
    if ($ram -le 0 -or $ram -ge $need) { return $true }
    Write-Warn ("内存不足，跳过拉取 {0}（本机 {1}GB < 约需 {2}GB）。" -f $name, $ram, $need)
    Write-Warn "升级内存后重跑本脚本即可（幂等）；或把模型清单改成本机能跑的档位。"
    return $false
}

Write-Host "===== Ollama 引擎安装 / 模型拉取 =====" -ForegroundColor Cyan
Write-Host ("工程目录: {0}" -f $root)
Write-Host ("日志文件 : {0}" -f $logFile)

# ---------- 1. 定位或安装 Ollama ----------
function Resolve-OllamaExe {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"),
        (Join-Path ${env:ProgramFiles} "Ollama\ollama.exe")
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    return $null
}

Write-Step "检测 Ollama ..."
$ollamaExe = Resolve-OllamaExe
if ($ollamaExe) {
    Write-Ok ("Ollama 已安装: {0}" -f $ollamaExe)
} else {
    # winget 安装完不会刷新当前进程 PATH，这里补一下常见安装目录
    if ($InstallerPath) {
        if (-not (Test-Path $InstallerPath)) {
            Write-Err ("指定的安装包不存在: {0}" -f $InstallerPath); Stop-Transcript | Out-Null; exit 1
        }
        Write-Step ("使用本地安装包静默安装: {0}" -f $InstallerPath)
        # OllamaSetup.exe 基于 Inno Setup，支持 /VERYSILENT
        $p = Start-Process -FilePath $InstallerPath -ArgumentList "/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART" -Wait -PassThru
        Write-Host ("      安装包退出码: {0}" -f $p.ExitCode)
    } else {
        Write-Step "尝试通过 winget 安装 Ollama（可能需要 UAC 授权）..."
        $wg = Get-Command winget -ErrorAction SilentlyContinue
        if (-not $wg) {
            Write-Err "未找到 winget。请手动安装: https://ollama.com/download"
            Stop-Transcript | Out-Null; exit 1
        }
        try {
            & winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements --disable-interactivity
            Write-Host ("      winget 退出码: {0}" -f $LASTEXITCODE)
        } catch {
            Write-Warn ("winget 安装异常: {0}" -f $_.Exception.Message)
        }
    }
    # 安装后刷新当前进程 PATH（winget/静默包都不会自动刷新）
    $paths = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Ollama"),
        (Join-Path ${env:ProgramFiles} "Ollama")
    )
    foreach ($p in $paths) { if ((Test-Path $p) -and ($env:Path -notlike "*$p*")) { $env:Path = "$env:Path;$p" } }
    Start-Sleep -Seconds 2
    $ollamaExe = Resolve-OllamaExe
    if (-not $ollamaExe) {
        Write-Err "Ollama 安装后仍未检测到。请重开终端执行 'ollama --version' 验证；或手动安装 https://ollama.com/download"
        Stop-Transcript | Out-Null; exit 1
    }
    Write-Ok ("Ollama 安装完成: {0}" -f $ollamaExe)
}

# ---------- 2. 验证引擎版本 ----------
try {
    $ver = & $ollamaExe --version 2>&1
    Write-Ok ("ollama 版本: {0}" -f ($ver -join " "))
} catch {
    Write-Err ("ollama --version 失败: {0}" -f $_.Exception.Message)
    Stop-Transcript | Out-Null; exit 1
}

# ---------- 3. 确保服务在跑（拉模型需要） ----------
function Test-OllamaUp {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/version" -TimeoutSec 3 -ErrorAction Stop | Out-Null
        return $true
    } catch { return $false }
}

if (-not $NoServe -and -not $SkipPull) {
    if (Test-OllamaUp) {
        Write-Ok "Ollama 服务已在运行 (11434)。"
    } else {
        Write-Step "启动 Ollama 服务 (ollama serve) ..."
        $proc = Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden -PassThru
        $ok = $false
        for ($i = 1; $i -le 20; $i++) {
            Start-Sleep -Seconds 1
            if (Test-OllamaUp) { $ok = $true; break }
        }
        if ($ok) { Write-Ok ("Ollama 服务就绪 (PID {0})。" -f $proc.Id) }
        else { Write-Warn "服务 20 秒内未响应；继续尝试拉取（若失败请手动运行 'ollama serve' 查看输出）。" }
    }
}

# ---------- 4. 解析模型清单 ----------
$modelList = @()
if ($Models) {
    $modelList = $Models.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ }
} elseif (-not $SkipPull) {
    if (Test-Path $modelsFile) {
        foreach ($line in Get-Content $modelsFile) {
            $t = $line.Trim()
            if (-not $t) { continue }
            if ($t.StartsWith("#")) { continue }
            # 去掉行内注释
            $name = ($t -split "#")[0].Trim()
            if ($name) { $modelList += $name }
        }
    } else {
        Write-Warn ("未找到模型清单 {0}，跳过拉取。" -f $modelsFile)
    }
}
$modelList = $modelList | Select-Object -Unique

# ---------- 5. 拉取模型（幂等） ----------
function Get-InstalledModels {
    """解析 `ollama list` 的 NAME 列，返回已安装模型名集合（精确匹配用）"""
    param([string]$Exe)
    $names = @()
    try {
        $lines = & $Exe list 2>$null
        foreach ($l in $lines) {
            if (-not $l) { continue }
            $t = "$l".Trim()
            # 跳过表头与空行
            if ($t -eq "" -or $t -like "NAME*") { continue }
            $first = ($t -split "\s+")[0]
            if ($first) {
                $names += $first
                # 兼容带 library/ 命名空间的显示形式
                if ($first -like "library/*") { $names += ($first -replace "^library/", "") }
            }
        }
    } catch {
        # list 失败时返回空集合，后续 pull 会暴露真实错误
    }
    return ,$names
}

if ($SkipPull) {
    Write-Step "指定了 -SkipPull，跳过模型拉取。"
} elseif ($modelList.Count -eq 0) {
    Write-Warn "模型清单为空，无需拉取。"
} else {
    Write-Step ("待拉取模型 {0} 个: {1}" -f $modelList.Count, ($modelList -join ", "))
    $installed = Get-InstalledModels -Exe $ollamaExe
    foreach ($m in $modelList) {
        # 精确匹配 NAME 列：避免 "qwen2.5:7b" 被 "qwen2.5:7b-instruct-q4_K_M" 误判为已存在
        if ($installed -contains $m) {
            Write-Ok ("已存在，跳过: {0}" -f $m)
            continue
        }
        if (-not (Test-RamForModel $m)) { continue }
        Write-Step ("拉取 {0} （体积较大，耗时取决于网络）..." -f $m)
        & $ollamaExe pull $m
        if ($LASTEXITCODE -ne 0) {
            Write-Err ("拉取失败: {0}。可重试或手动执行: ollama pull {0}" -f $m)
            exit 1
        }
        Write-Ok ("拉取完成: {0}" -f $m)
    }
}

# ---------- 5b. 视觉/图片解析模型（-PullVision 时；best-effort，失败不致命）----------
if ($PullVision -and -not $SkipPull) {
    $visionFile = Join-Path $root "config\ollama-vision-model.txt"
    $visionModel = "qwen2.5vl:7b-q4_K_M"
    if (Test-Path $visionFile) {
        foreach ($line in Get-Content $visionFile) {
            $t = $line.Trim()
            if (-not $t -or $t.StartsWith("#")) { continue }
            $visionModel = ($t -split "#")[0].Trim(); break
        }
    }
    $installed = Get-InstalledModels -Exe $ollamaExe
    if ($installed -contains $visionModel) {
        Write-Ok ("视觉模型已存在，跳过: {0}" -f $visionModel)
    } elseif (-not (Test-RamForModel $visionModel)) {
        # 内存不足：跳过（图片解析暂不可用，文本问答不受影响）
    } else {
        Write-Step ("拉取视觉/图片解析模型 {0} （体积较大，best-effort）..." -f $visionModel)
        & $ollamaExe pull $visionModel
        if ($LASTEXITCODE -ne 0) {
            Write-Warn ("视觉模型拉取失败: {0}。图片解析功能暂不可用；可稍后手动: ollama pull {0}" -f $visionModel)
        } else {
            Write-Ok ("视觉模型就绪: {0}" -f $visionModel)
        }
    }
}

# ---------- 6. 汇总 ----------
Write-Host ""
Write-Host "===== 完成 =====" -ForegroundColor Cyan
try {
    Write-Host "当前已安装模型："
    & $ollamaExe list
} catch { }
Write-Host ""
Write-Host "后续步骤：" -ForegroundColor Cyan
Write-Host "  启动服务    : .\scripts\start.ps1"
Write-Host "  导入知识库  : python scripts\rag_manager.py add-all"
Write-Host "  检索测试    : python scripts\rag_manager.py search ""三菱FX5U Modbus 地址"""
Stop-Transcript | Out-Null
exit 0
