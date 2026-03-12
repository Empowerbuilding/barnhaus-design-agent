Set-Location "C:\Users\mitch\Autodesk-Revit-MCP-Server\packages\revit-bridge-addin"
dotnet restore -p:RevitVersion=2025
dotnet build RevitBridge.csproj -c Release -p:RevitVersion=2025
if ($LASTEXITCODE -ne 0) { Write-Host "Build failed!" -ForegroundColor Red; exit 1 }
$dll = Get-ChildItem "bin\Release\2025" -Recurse -Filter "RevitBridge.dll" | Select-Object -First 1
Copy-Item $dll.FullName "C:\ProgramData\RevitMCP\bin\RevitBridge.dll" -Force
Write-Host "Done - open Revit" -ForegroundColor Green
