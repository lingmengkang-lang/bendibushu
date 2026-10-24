# start.ps1 — 启动本地离线助手服务
# 用法（工程根目录执行）：
#   .\scripts\start.ps1            # 启动 Ollama（11434）
#   .\scripts\start.ps1 -WebUI     # 同时启动 LLaMA-Factory WebUI（7860）
#   .\scripts\start.ps1 -NoOllama  # 跳过 Ollama（例如已在系统服务中运行）
#
# 说明：启动的进程 PID 会写入 logs\*.pid，stop.ps1 按 PID 文件停止，
#       避免按进程名误杀其他 Python/Node 进程。

param(
    [switch]$WebUI,
    [switch]$NoOllama
)

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

function Wait-HttpOk([string]$Url, [int]$Retries) {
    for ($i = 1; $i -le $Retries; $i++) {
        try {
            Invoke-RestMethod -Uri $Url -TimeoutSec 3 -ErrorAction Stop | Out-Null
            return $true
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

# ---------- Ollama ----------
if (-not $NoOllama) {
    $already = Get-NetTCPConnection -LocalPort 11434 -ErrorAction SilentlyContinue
    if ($already) {
        Write-Host "[SKIP] Ollama 已在运行（11434 监听中）。" -ForegroundColor Yellow
    } else {
        $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
        if (-not $ollamaCmd) {
            Write-Host "[WARN] 未检测到 ollama 命令。请先安装 Ollama（https://ollama.com）或将其加入 PATH。" -ForegroundColor Yellow
        } else {
            Write-Host "正在启动 Ollama ..."
            $proc = Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -PassThru
            $proc.Id | Out-File -FilePath (Join-Path $logDir "ollama.pid") -Encoding ASCII
            if (Wait-HttpOk "http://127.0.0.1:11434/api/version" 20) {
                Write-Host ("[OK] Ollama 就绪 (PID {0}, http://127.0.0.1:11434)" -f $proc.Id) -ForegroundColor Green
            } else {
                Write-Host "[WARN] Ollama 已启动但 20 秒内未响应，请检查 logs 或手动运行 'ollama serve' 查看输出。" -ForegroundColor Yellow
            }
        }
    }
}

# ---------- LLaMA-Factory WebUI ----------
if ($WebUI) {
    $already = Get-NetTCPConnection -LocalPort 7860 -ErrorAction SilentlyContinue
    if ($already) {
        Write-Host "[SKIP] WebUI 已在运行（7860 监听中）。" -ForegroundColor Yellow
    } else {
        $cli = Join-Path $root "venv\Scripts\llamafactory-cli.exe"
        if (-not (Test-Path $cli)) {
            Write-Host "[WARN] 未找到 venv\Scripts\llamafactory-cli.exe。LLaMA-Factory 未安装（可选组件），安装见 lora\README.md。" -ForegroundColor Yellow
        } else {
            Write-Host "正在启动 LLaMA-Factory WebUI ..."
            $proc = Start-Process -FilePath $cli -ArgumentList "webui" -WorkingDirectory $root -WindowStyle Hidden -PassThru
            $proc.Id | Out-File -FilePath (Join-Path $logDir "webui.pid") -Encoding ASCII
            Start-Sleep -Seconds 3
            Write-Host ("[OK] WebUI 启动中 (PID {0})，访问 http://127.0.0.1:7860" -f $proc.Id) -ForegroundColor Green
        }
    }
}

# ---------- 状态与下一步 ----------
Write-Host ""
Write-Host "===== 服务状态 =====" -ForegroundColor Cyan
$s11434 = if (Get-NetTCPConnection -LocalPort 11434 -ErrorAction SilentlyContinue) { "运行中" } else { "未运行" }
$s7860  = if (Get-NetTCPConnection -LocalPort 7860 -ErrorAction SilentlyContinue) { "运行中" } else { "未运行" }
Write-Host ("  Ollama  (11434): {0}" -f $s11434)
Write-Host ("  WebUI   ( 7860): {0}" -f $s7860)
Write-Host ""
Write-Host "下一步提示：" -ForegroundColor Cyan
Write-Host "  1) 拉取模型（首次必须，清单见 config\ollama-models.txt）: ollama pull qwen2.5:7b"
Write-Host "  2) 导入知识库: python scripts\rag_manager.py add data\knowledge_base\docs -r"
Write-Host "  3) 检索测试  : python scripts\rag_manager.py search ""测试问题"""
Write-Host "  4) 停止服务  : .\scripts\stop.ps1"
