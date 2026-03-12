$file = "C:\Users\mitch\Autodesk-Revit-MCP-Server\packages\revit-bridge-addin\src\Bridge\BridgeCommandFactory.cs"
$content = Get-Content $file -Raw

# Patch: if no roof type specified, use first available
$old = @'
            RoofType roofType = null;
            if (!string.IsNullOrEmpty(roofTypeName))
            {
                roofType = GetRoofTypeByName(doc, roofTypeName);
            }
'@

$new = @'
            RoofType roofType = null;
            if (!string.IsNullOrEmpty(roofTypeName))
            {
                roofType = GetRoofTypeByName(doc, roofTypeName);
            }
            else
            {
                // Fall back to first available roof type
                roofType = new FilteredElementCollector(doc)
                    .OfClass(typeof(RoofType))
                    .Cast<RoofType>()
                    .FirstOrDefault();
                if (roofType == null)
                    throw new InvalidOperationException("No roof types found in project. Load a roof type first.");
            }
'@

$content = $content.Replace($old, $new)
$content | Set-Content $file -Encoding UTF8 -NoNewline
Write-Host "Patched roof type fallback" -ForegroundColor Green

# Rebuild
Set-Location "C:\Users\mitch\Autodesk-Revit-MCP-Server\packages\revit-bridge-addin"
dotnet restore -p:RevitVersion=2025
dotnet build RevitBridge.csproj -c Release -p:RevitVersion=2025
if ($LASTEXITCODE -ne 0) { Write-Host "Build failed!" -ForegroundColor Red; exit 1 }

$dll = Get-ChildItem "bin\Release\2025" -Recurse -Filter "RevitBridge.dll" | Select-Object -First 1
Copy-Item $dll.FullName "C:\ProgramData\RevitMCP\bin\RevitBridge.dll" -Force
Write-Host "Reinstalled. Close and reopen Revit." -ForegroundColor Green
