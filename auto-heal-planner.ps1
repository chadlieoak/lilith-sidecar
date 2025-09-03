$ErrorActionPreference = 'Stop'
$planner = Join-Path $PSScriptRoot 'lilith\planner.py'

# --- Step 1: Backup ---
$stamp  = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = "$planner.bak-$stamp"
Copy-Item -LiteralPath $planner -Destination $backup -Force
Write-Host "[+] Backup created: $backup"

# --- Step 2: Read file ---
$content = Get-Content -Raw -LiteralPath $planner

# --- Step 3: Look for open triple-quoted strings ---
$tripleSingleCount = ([regex]::Matches($content, "'''")).Count
$tripleDoubleCount = ([regex]::Matches($content, '"""')).Count

$needsFix = $false
$fixText  = ""

if ($tripleSingleCount % 2 -ne 0) {
    $needsFix = $true
    $fixText = "'''"
}
elseif ($tripleDoubleCount % 2 -ne 0) {
    $needsFix = $true
    $fixText = '"""'
}

if ($needsFix) {
    Add-Content -LiteralPath $planner -Value $fixText
    Write-Host "[*] Appended missing $fixText to $planner"
} else {
    Write-Host "[√] No unterminated triple-quoted strings found."
}

# --- Step 4: Verify with py_compile ---
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python3 -ErrorAction SilentlyContinue }

if ($python) {
    & $python.Source - << 'PYCODE'
import py_compile, sys
try:
    py_compile.compile(r"lilith/planner.py", doraise=True)
    print("[√] planner.py compiles cleanly.")
except Exception as e:
    print("[!] py_compile error:", e)
    sys.exit(1)
PYCODE
} else {
    Write-Host "[!] Python not found on PATH — skipping compile check."
}
