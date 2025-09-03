$ErrorActionPreference = "Stop"

# Paths
$repoRoot  = (Get-Location).Path
$planner   = Join-Path $repoRoot "lilith\planner.py"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup    = "$planner.bak-$timestamp"

if (-not (Test-Path $planner)) {
  Write-Error "Could not find $planner. Run this from your repo root."
}

# Backup
Copy-Item $planner $backup -Force
Write-Host "[+] Backup created -> $backup"

# Load
$text     = Get-Content -Path $planner -Raw
$original = $text

# --- 1) Trim the extra curly: "'''}}}" -> "'''}}"
# Do a conservative pass first (exact substring), then a targeted footer pass if needed.
$newText = $text.Replace("'''}}}", "'''}}")

if ($newText -eq $text) {
  # Target right after an app.run(...) line to be safer if the exact substring wasn't found
  $patternAppFooter = @'
(app\.run\(host=.*?debug=True\)\r?\n'''\}\}\})
