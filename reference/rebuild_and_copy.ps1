Write-Host "Building RevitBridge..." -ForegroundColor Cyan
dotnet build "C:\Users\mitch\Autodesk-Revit-MCP-Server\packages\revit-bridge-addin\RevitBridge.csproj" -c Release -p:RevitVersion=2025

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build FAILED" -ForegroundColor Red
    exit 1
}

Write-Host "Copying DLL..." -ForegroundColor Cyan
Copy-Item "C:\Users\mitch\Autodesk-Revit-MCP-Server\packages\revit-bridge-addin\bin\Release\2025\net8.0-windows\RevitBridge.dll" "C:\ProgramData\RevitMCP\bin\RevitBridge.dll" -Force

Write-Host "Done - open Revit" -ForegroundColor Green
