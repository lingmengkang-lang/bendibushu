# history_manager.ps1 — 历史记录（日志）管理
# 用法（工程根目录执行）：
#   .\scripts\history_manager.ps1 status                         统计 logs\ 目录
#   .\scripts\history_manager.ps1 archive                        按月打包归档到 logs\archive\
#   .\scripts\history_manager.ps1 export -Name 2026-10.log -To D:\backup\
#   .\scripts\history_manager.ps1 clean -Days 30                 干跑：仅列出将被删除的文件
#   .\scripts\history_manager.ps1 clean -Days 30 -Force          实际删除（高危，执行前会完整列出清单）
#
# 管理范围：logs\*.log（Ollama/服务/训练日志）。conversations\ 目录如存在也一并纳入统计。
# 兼容：Windows PowerShell 5.1

param(
    [Parameter(Mandatory=$true)][ValidateSet("status","archive","export","clean")][string]$Action,
    [string]$Name,
    [string]$To,
    [int]$Days = 30,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent
$logDir = Join-Path $root "logs"

function Get-SizeText([long]$bytes) {
    if ($bytes -ge 1GB) { return ("{0:N2} GB" -f ($bytes/1GB)) }
    if ($bytes -ge 1MB) { return ("{0:N2} MB" -f ($bytes/1MB)) }
    return ("{0:N1} KB" -f ($bytes/1KB))
}

if (-not (Test-Path $logDir)) {
    Write-Host "logs 目录不存在，无历史记录可管理。" -ForegroundColor Yellow
    exit 0
}

switch ($Action) {

    "status" {
        $files = Get-ChildItem $logDir -File -Filter *.log -ErrorAction SilentlyContinue
        if (-not $files) { Write-Host "logs 目录下无 .log 文件。" ; exit 0 }
        $total = ($files | Measure-Object Length -Sum).Sum
        $oldest = ($files | Sort-Object LastWriteTime | Select-Object -First 1).LastWriteTime
        $newest = ($files | Sort-Object LastWriteTime | Select-Object -Last 1).LastWriteTime
        Write-Host ("日志文件数 : {0}" -f $files.Count)
        Write-Host ("总大小     : {0}" -f (Get-SizeText $total))
        Write-Host ("时间范围   : {0} ~ {1}" -f $oldest, $newest)
        Write-Host ""
        $files | Sort-Object LastWriteTime | ForEach-Object {
            Write-Host ("  {0,-40} {1,10}  {2}" -f $_.Name, (Get-SizeText $_.Length), $_.LastWriteTime)
        }
        $archDir = Join-Path $logDir "archive"
        if (Test-Path $archDir) {
            $zips = Get-ChildItem $archDir -Filter *.zip
            Write-Host ("`n归档文件   : {0} 个" -f $zips.Count)
        }
    }

    "archive" {
        $archDir = Join-Path $logDir "archive"
        New-Item -ItemType Directory -Path $archDir -Force | Out-Null
        $groups = Get-ChildItem $logDir -File -Filter *.log | Group-Object { $_.LastWriteTime.ToString("yyyyMM") }
        if (-not $groups) { Write-Host "无可归档日志。" ; exit 0 }
        foreach ($g in $groups) {
            $zip = Join-Path $archDir ("logs-{0}.zip" -f $g.Name)
            $tmp = Join-Path $env:TEMP ("hist-{0}" -f $g.Name)
            New-Item -ItemType Directory -Path $tmp -Force | Out-Null
            $g.Group | Copy-Item -Destination $tmp
            if (Test-Path $zip) { Remove-Item $zip -Force }
            Compress-Archive -Path (Join-Path $tmp "*") -DestinationPath $zip
            Remove-Item $tmp -Recurse -Force
            $g.Group | Remove-Item -Force
            Write-Host ("[OK] {0} -> {1}（{2} 个文件，源文件已移除）" -f $g.Name, $zip, $g.Count) -ForegroundColor Green
        }
        Write-Host "`n注意：归档 zip 内的源日志已从 logs\ 移除，zip 请另行备份。" -ForegroundColor Yellow
    }

    "export" {
        if (-not $Name) { Write-Host "export 需要 -Name <日志文件名>" -ForegroundColor Red; exit 1 }
        $src = Join-Path $logDir $Name
        if (-not (Test-Path $src)) { Write-Host ("文件不存在: {0}" -f $src) -ForegroundColor Red; exit 1 }
        $destDir = if ($To) { $To } else { $root }
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
        Copy-Item $src -Destination $destDir
        Write-Host ("[OK] 已导出到: {0}" -f (Join-Path $destDir $Name)) -ForegroundColor Green
    }

    "clean" {
        $cutoff = (Get-Date).AddDays(-$Days)
        $targets = Get-ChildItem $logDir -File -Filter *.log | Where-Object { $_.LastWriteTime -lt $cutoff }
        if (-not $targets) {
            Write-Host ("没有超过 {0} 天的日志，无需清理。" -f $Days)
            exit 0
        }
        Write-Host ("以下 {0} 个文件将被删除（修改时间早于 {1}）：" -f $targets.Count, $cutoff) -ForegroundColor Yellow
        $targets | ForEach-Object { Write-Host ("  {0}  ({1}, {2})" -f $_.Name, (Get-SizeText $_.Length), $_.LastWriteTime) }
        if (-not $Force) {
            Write-Host "`n[干跑模式] 未删除任何文件。确认无误后加 -Force 参数实际执行。" -ForegroundColor Cyan
            exit 0
        }
        Write-Host "`n⚠️ 高危操作：即将永久删除上述文件（不进回收站）。" -ForegroundColor Red
        $confirm = Read-Host "输入 DELETE 确认执行"
        if ($confirm -ne "DELETE") { Write-Host "已取消。" ; exit 0 }
        $targets | Remove-Item -Force
        Write-Host ("[OK] 已删除 {0} 个文件。" -f $targets.Count) -ForegroundColor Green
    }
}
