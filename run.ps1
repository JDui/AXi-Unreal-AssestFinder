# UE Asset Path Finder - PowerShell 启动脚本
# 使用方法: .\run.ps1

# 检查执行策略
$currentPolicy = Get-ExecutionPolicy
if ($currentPolicy -eq "Restricted") {
    Write-Host "⚠️  PowerShell 执行策略受限" -ForegroundColor Yellow
    Write-Host "请运行: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Cyan
    exit 1
}

# 获取脚本所在目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $scriptDir "dist\UEAssetPathFinder.exe"

# 验证 EXE 文件
if (-not (Test-Path $exePath)) {
    Write-Host "❌ 错误: 未找到应用程序文件" -ForegroundColor Red
    Write-Host "预期路径: $exePath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "请确保应用已编译到 dist 文件夹" -ForegroundColor Cyan
    Read-Host "按 Enter 键退出"
    exit 1
}

# 启动应用
Write-Host "🚀 正在启动 UE Asset Path Finder..." -ForegroundColor Green
try {
    Start-Process -FilePath $exePath -NoNewWindow
    Write-Host "✅ 应用已启动" -ForegroundColor Green
} catch {
    Write-Host "❌ 启动失败: $_" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}

exit 0
