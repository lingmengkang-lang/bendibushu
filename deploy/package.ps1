# package.ps1 — 打包发布用 zip（仅含已提交源码，自动排除 venv/数据/模型/日志等）
# 用法（工程根目录执行）：
#   .\deploy\package.ps1
#
# 原理：用 `git archive HEAD` 导出——只包含已提交的文件，
#       所有被 .gitignore 排除的（venv/ data/chroma/* / logs/* / models/* 等）都不会进包，
#       因此发布包体积小、且不会把你的本地数据/模型/凭据带出去。
# 要求：打包前请确保最新改动已 git commit（git archive 基于 HEAD）。

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
$outDir = Join-Path $root "releases"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$stamp = Get-Date -Format "yyyyMMdd"
$zip = Join-Path $outDir ("local-offline-assistant-" + $stamp + ".zip")
if (Test-Path $zip) {
    $zip = Join-Path $outDir ("local-offline-assistant-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".zip")
}

# 定位 git（兼容不同安装位置，避免依赖 PATH）：
# PowerShell 下 git 可能不在 PATH；逐项探测常见安装路径。
function Find-Git {
    $cands = @(
        "git",
        (Join-Path $env:ProgramFiles "Git\cmd\git.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Git\cmd\git.exe"),
        "$env:LOCALAPPDATA\Programs\Git\bin\git.exe",
        "C:\Program Files\Git\cmd\git.exe"
    )
    # WorkBuddy 自带 PortableGit（沙箱/便携环境常见）
    try {
        $wb = Join-Path $env:USERPROFILE ".workbuddy\binaries\PortableGit\versions"
        if (Test-Path $wb) {
            foreach ($d in Get-ChildItem $wb -Directory -ErrorAction SilentlyContinue) {
                $cands += Join-Path $d.FullName "cmd\git.exe"
            }
        }
    } catch { }
    foreach ($c in $cands) {
        try {
            if ($c -eq "git") {
                $p = (Get-Command git -ErrorAction SilentlyContinue).Source
                if ($p) { return $p }
            } elseif (Test-Path $c) {
                return $c
            }
        } catch { }
    }
    # 最后退回 cmd 的 where
    try {
        $r = cmd /c "where git" 2>$null
        if ($r) { return $r.Split([Environment]::NewLine)[0].Trim() }
    } catch { }
    return $null
}
$git = Find-Git
if (-not $git) {
    Write-Host "[FAIL] 未找到 git。请先安装 Git（https://git-scm.com/downloads）。" -ForegroundColor Red
    exit 1
}

Write-Host "正在用 git archive 打包（仅已提交文件，自动排除 .gitignore 项）..." -ForegroundColor Cyan
# 注意：直接调用 git，不用 Start-Process —— PowerShell 5.1 的 Start-Process 在遇到
# 环境中同时存在 HTTPS_PROXY / https_proxy（大小写不同）时会抛“字典关键字重复”异常。
Push-Location $root
& $git archive --format=zip -o $zip HEAD
$rc = $LASTEXITCODE
Pop-Location
if ($rc -ne 0) {
    Write-Host "[FAIL] git archive 失败。请确认：在仓库目录内、且最新改动已 git commit。" -ForegroundColor Red
    exit 1
}

$sizeMB = [math]::Round((Get-Item $zip).Length / 1MB, 2)
Write-Host ("[OK] 已生成: {0}  ({1} MB)" -f $zip, $sizeMB) -ForegroundColor Green
Write-Host ""
Write-Host "===== 发布包使用说明 =====" -ForegroundColor Cyan
Write-Host "1) 把该 zip 发给使用者（体积小，不含 venv / 模型 / 本地数据）；"
Write-Host "2) 使用者解压到任意目录，双击 启动.bat；"
Write-Host "3) 首次运行会联网：装 Python 依赖 + Ollama 引擎 + 拉取默认模型；之后完全离线；"
Write-Host "4) 浏览器自动打开 http://127.0.0.1:8500 即可对话；"
Write-Host "5) 停止：双击 停止.bat。"
Write-Host ""
Write-Host "注意：唯一需要‘安装一次’的是 Ollama（启动.bat 会尝试自动装；失败则打开官网手动装）。"
