# stop.ps1 — 停止本地离线助手服务
# 用法（工程根目录执行）：
#   .\scripts\stop.ps1          # 停止 Ollama（及 WebUI，如已启动）
#
# 安全设计：只停止 start.ps1 启动时记录的 PID（logs\ollama.pid / logs\webui.pid），
#           并在停止前校验进程名，绝不按进程名批量杀，防止误杀其他 Python/Node 进程。
#           无 PID 文件时不自动杀进程，只列出手动处理指引。

param()

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
$logDir = Join-Path $root "logs"

function Stop-ByPidFile([string]$PidFile, [string]$ExpectName) {
    if (-not (Test-Path $PidFile)) {
        Write-Host "[INFO] 无 PID 文件（$PidFile），跳过 $ExpectName。" -ForegroundColor Yellow
        return
    }
    $pidValue = (Get-Content $PidFile -Raw).Trim()
    try { $proc = Get-Process -Id $pidValue -ErrorAction Stop } catch {
        Write-Host "[INFO] PID $pidValue 对应进程已不存在，清理 PID 文件。"
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return
    }
    if ($proc.ProcessName -ne $ExpectName) {
        Write-Host "[WARN] PID $pidValue 进程名为 $($proc.ProcessName)，与预期 $ExpectName 不符，已跳过（防止误杀）。" -ForegroundColor Yellow
        return
    }
    Write-Host "正在停止 $ExpectName (PID $pidValue, 启动于 $($proc.StartTime)) ..."
    Stop-Process -Id $pidValue -Force
    Start-Sleep -Seconds 1
    if (-not (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] $ExpectName 已停止。" -ForegroundColor Green
    } else {
        Write-Host "[WARN] $ExpectName 仍在运行，请人工确认。" -ForegroundColor Yellow
    }
}

Write-Host "===== 停止服务 =====" -ForegroundColor Cyan
Stop-ByPidFile (Join-Path $logDir "assistant.pid") "python"
Stop-ByPidFile (Join-Path $logDir "webui.pid")   "python"
Stop-ByPidFile (Join-Path $logDir "ollama.pid")  "ollama"

Write-Host ""
$s11434 = if (Get-NetTCPConnection -LocalPort 11434 -ErrorAction SilentlyContinue) { "仍在监听" } else { "已释放" }
Write-Host ("端口 11434: {0}" -f $s11434)
if ($s11434 -eq "仍在监听") {
    Write-Host "提示：11434 仍有进程监听但无 PID 文件——可能是你手动启动的 Ollama。" -ForegroundColor Yellow
    Write-Host "      请人工确认后处理（如任务管理器结束 ollama 进程），本脚本不按进程名批量杀。" -ForegroundColor Yellow
}
