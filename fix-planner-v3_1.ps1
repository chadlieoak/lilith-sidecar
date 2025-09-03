$ErrorActionPreference = "Stop"

# Paths
$repoRoot  = (Get-Location).Path
$planner   = Join-Path $repoRoot "lilith\planner.py"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup    = "$planner.bak-$timestamp"

if (-not (Test-Path $planner)) { Write-Error "Could not find $planner. Run this from your repo root." }

# Backup
Copy-Item $planner $backup -Force
Write-Host "[+] Backup created -> $backup"

# Load
$text     = Get-Content -Path $planner -Raw
$original = $text

# --- 1) Trim the extra curly: "'''}}}" -> "'''}}"
$newText = $text.Replace("'''}}}", "'''}}")
if ($newText -eq $text) {
  # Safer targeted footer
  $patternAppFooter = "(app\.run\(host=.*?debug=True\)\r?\n'''\}\}\})"
  $newText = [System.Text.RegularExpressions.Regex]::Replace(
    $text,
    $patternAppFooter,
    { param($m) $m.Value -replace "'''\}\}\}", "'''}}" },
    [System.Text.RegularExpressions.RegexOptions]::Singleline
  )
}
$text = $newText

# --- 2) Fix the curl JSON snippet
$text = [System.Text.RegularExpressions.Regex]::Replace(
  $text,
  '-d\s+"{""?msg""?\s*:\s*""?hello""?}"',
  '-d "{\"msg\":\"hello\"}"',
  [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
)

# --- 3) Align wrapper signature/call/blob; remove dict fallback return
$text = [Regex]::Replace($text, 'def\s+_wrapped\([^\)]*\)\s*:', 'def _wrapped(goal: str, proj_id: int, seed: int = 42):', 'Singleline')
$text = [Regex]::Replace($text, 'steps\s*=\s*original_fn\([^\)]*\)', 'steps = original_fn(goal, proj_id, seed)', 'Singleline')
$text = [Regex]::Replace($text, 'blob\s*=\s*\(f"[^"]*"\)\.lower\(\)', 'blob = (goal or "").lower()', 'Singleline')
$text = [Regex]::Replace($text, 'return\s+_lf_echo_fallback_steps\(\)', 'return steps', 'Singleline')

# --- 3b) OPTIONAL: hard-disable the fallback function body
# (Match the whole def .. up to next def or EOF)
$patternFallback = 'def\s+_lf_echo_fallback_steps\(\):[\s\S]*?(?=\ndef\s|\Z)'
if ([Regex]::IsMatch($text, $patternFallback)) {
  $replacement = @"
def _lf_echo_fallback_steps():
    raise NotImplementedError("disabled: pipeline should return Step objects")
"@
  $text = [Regex]::Replace($text, $patternFallback, $replacement)
}

# Write back if changed
if ($text -ne $original) {
  Set-Content -Path $planner -Value $text -Encoding UTF8
  Write-Host "[√] Patched $planner"
} else {
  Write-Host "[i] No changes applied (already fixed?)"
}

# --- 4) Quick syntax check
function Get-PythonPath {
  $candidates = @()
  $venvPy = Join-Path $repoRoot ".venv\Scripts\python.exe"
  if (Test-Path $venvPy) { $candidates += $venvPy }
  foreach ($name in @("python","py")) { $cmd = Get-Command $name -EA SilentlyContinue; if ($cmd) { $candidates += $cmd.Source } }
  if ($candidates.Count -gt 0) { return $candidates[0] }
  return $null
}
$pyExe = Get-PythonPath
if ($pyExe) {
  Write-Host "[?] Quick syntax check with: $pyExe"
  $checkerPath = Join-Path $env:TEMP ("pycheck_{0}.py" -f $timestamp)
  $checkerCode = @"
import py_compile, sys
try:
    py_compile.compile(r"lilith/planner.py", doraise=True)
    print("[√] planner.py compiles cleanly.")
except Exception as e:
    print("[!] py_compile error:", e)
    sys.exit(1)
"@
  Set-Content -Path $checkerPath -Value $checkerCode -Encoding UTF8
  & $pyExe $checkerPath
} else {
  Write-Host "[i] Skipping syntax check (Python not found)."
}

# --- 5) Nudge
if (Get-Command meow -ErrorAction SilentlyContinue) { Write-Host "[?] Reloading via 'meow reload'..."; meow reload; Write-Host "[√] Reloaded." }
else { Write-Host "[i] Tip: run 'python app.py' to test the Flask UI." }
