# Chạy train DDPG nền (CPU) — tự resume khi có mạng
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }

$env:CUDA_VISIBLE_DEVICES = "-1"
$env:TF_CPP_MIN_LOG_LEVEL = "2"

# Train đầy đủ paper (đổi TRAIN_EPISODES=200 để test nhanh)
if (-not $env:TRAIN_EPISODES) { $env:TRAIN_EPISODES = "5000" }
if (-not $env:DAYS_PER_MONTH) { $env:DAYS_PER_MONTH = "30" }

Start-Process python `
    -ArgumentList "-u", "train_daemon.py" `
    -WorkingDirectory $Root `
    -WindowStyle Hidden

Write-Host "Da khoi dong train nen. Xem log:"
Write-Host "  logs\train_daemon.log"
Write-Host "  logs\train_stdout.log"
Write-Host "Tien do: checkpoints\train_progress.json"
