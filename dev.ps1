# dev.ps1 — environment bootstrap for lilith-sidecar
param([switch]$UserScope)

$ErrorActionPreference = "Stop"

$ROOT = Get-Location
$venvScripts = Join-Path $ROOT ".venv\Scripts"

# Ensure workspace/checkpoints exist
$ws  = Join-Path $ROOT "workspace"
$cks = Join-Path $ROOT "checkpoints"
New-Item -ItemType Directory -Force -Path $ws, $cks | Out-Null

# Prepend venv Scripts to PATH if not already present
if (-not ($env:PATH -like "*$venvScripts*")) {
    $env:PATH = "$venvScripts;$env:PATH"
}

# Common environment variables
$envs = @{
    "LILITH_ROOT" = $ROOT
    "PYTHONPATH"  = (Join-Path $ROOT "lilith")
    "WORKSPACE"   = $ws
    "CHECKPOINTS" = $cks
}

# Helper to set env for chosen scope and reflect in current process
function Set-Env {
    param([string]$Name, [string]$Value, [string]$Scope)
    [Environment]::SetEnvironmentVariable($Name, $Value, $Scope)
    # Also reflect immediately in this shell via the Env: provider
    Set-Item -Path ("Env:{0}" -f $Name) -Value $Value
}

$scope = if ($UserScope) { "User" } else { "Process" }
foreach ($k in $envs.Keys) {
    Set-Env -Name $k -Value $envs[$k] -Scope $scope
}

Write-Host "[√] dev environment initialized."
Write-Host "    ROOT=$($ROOT)"
Write-Host "    PATH updated with $venvScripts"
Write-Host "    Scope=$scope"

# --- Sanity check ---
Write-Host "[?] Running planner.py sanity check..."
# Prefer venv python.exe if present, else fall back to python on PATH
$py = Join-Path $venvScripts "python.exe"
if (-not (Test-Path $py)) { $py = "python" }

try {
    & $py -m py_compile (Join-Path $ROOT "lilith\planner.py")
    Write-Host "[√] planner.py compiles cleanly."
}
catch {
    Write-Host "[!] planner.py sanity check failed:"
    Write-Host "    $($_.Exception.Message)"
    exit 1
}
