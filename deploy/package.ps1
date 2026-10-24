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

Write-Host "正在用 git archive 打包（仅已提交文件，自动排除 .gitignore 项）..." -ForegroundColor Cyan
$proc = Start-Process -FilePath "git" -ArgumentList ("archive","--format=zip","-o",$zip,"HEAD") `
    -WorkingDirectory $root -Wait -PassThru -NoNewWindow
if ($proc.ExitCode -ne 0) {
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
