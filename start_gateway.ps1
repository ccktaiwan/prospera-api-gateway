# start_gateway.ps1
# Prospera API Gateway 啟動腳本 v1.0

$GATEWAY_ROOT = "C:\AI_WorkDir\GitHub\prospera-api-gateway"
Set-Location $GATEWAY_ROOT
Write-Host "[Gateway] Starting Prospera API Gateway v1.1 on http://localhost:9000" -ForegroundColor Cyan
python gateway.py