param(
  [ValidateSet("process","user","dotenv")]
  [string]$Persist = "process",
  [string]$DotEnvPath = ".env",
  [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info($msg){ Write-Host "[i] $msg" -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-OK($msg){ Write-Host "[✓] $msg" -ForegroundColor Green }
function Write-Err($msg){ Write-Host "[x] $msg" -ForegroundColor Red }

function Get-PlainFromSecure([securestring]$sec) {
  if (-not $sec) { return "" }
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
  try { [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

function Ensure-DotEnvLine {
  param([string]$Path,[string]$Name,[string]$Value)
  if (-not (Test-Path $Path)) { New-Item -ItemType File -Path $Path | Out-Null }
  $lines = Get-Content $Path -ErrorAction SilentlyContinue
  $kept = @()
  foreach($ln in $lines){ if($ln -notmatch "^\s*${Name}\s*="){ $kept += $ln } }
  $kept + ("{0}={1}" -f $Name,$Value) | Set-Content -Path $Path -Encoding UTF8
}

function Get-EnvVar {
  param([string]$Name)
  $proc = [Environment]::GetEnvironmentVariable($Name, "Process")
  if ($proc) { return $proc }
  $user = [Environment]::GetEnvironmentVariable($Name, "User")
  if ($user) {
    # mirror into process for immediate use
    [Environment]::SetEnvironmentVariable($Name, $user, "Process")
    return $user
  }
  return $null
}

function Set-EnvVar {
  param(
    [string]$Name, [string]$Value,
    [ValidateSet("process","user","dotenv")] [string]$Mode,
    [string]$DotEnvPath
  )
  switch ($Mode) {
    "process" {
      [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
      Write-OK "Set (process) $Name"
    }
    "user" {
      [Environment]::SetEnvironmentVariable($Name, $Value, "User")
      [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
      Write-OK "Set (user) $Name"
    }
    "dotenv" {
      Ensure-DotEnvLine -Path $DotEnvPath -Name $Name -Value $Value
      [Environment]::SetEnvironmentVariable($Name, $Value, "Process")
      Write-OK "Wrote $Name to $DotEnvPath"
    }
  }
}

function Require-Or-Prompt {
  param(
    [string]$Name,
    [string]$PromptText,
    [switch]$Secret,
    [ValidateSet("process","user","dotenv")] [string]$Persist,
    [string]$DotEnvPath
  )
  $current = Get-EnvVar -Name $Name
  if (($null -eq $current) -or $current -eq "" -or $Force) {
    if ($Secret) {
      $sec = Read-Host -AsSecureString -Prompt $PromptText
      $plain = Get-PlainFromSecure $sec
      if ([string]::IsNullOrWhiteSpace($plain)) { throw "Empty value for $Name" }
      Set-EnvVar -Name $Name -Value $plain -Mode $Persist -DotEnvPath $DotEnvPath
      return $plain
    } else {
      $plain = Read-Host -Prompt $PromptText
      if ([string]::IsNullOrWhiteSpace($plain)) { throw "Empty value for $Name" }
      Set-EnvVar -Name $Name -Value $plain -Mode $Persist -DotEnvPath $DotEnvPath
      return $plain
    }
  } else {
    Write-OK "$Name already set"
    return $current
  }
}

Write-Host "=== Lilith LLM Preflight ===" -ForegroundColor Magenta
Write-Info "Persist values to: process (this shell), user (profile), or dotenv (.env file)."
if (-not $PSBoundParameters.ContainsKey("Persist")) {
  $Persist = Read-Host -Prompt "Persist mode [process | user | dotenv] (default: process)"
  if ([string]::IsNullOrWhiteSpace($Persist)) { $Persist = "process" }
}

# 1) Provider
$provider = Require-Or-Prompt -Name "LLM_PROVIDER" -PromptText "LLM provider (openai | anthropic | ollama)" -Persist $Persist -DotEnvPath $DotEnvPath
switch ($provider.ToLower()) {
  "openai"   { $needKey = "OPENAI_API_KEY"; $needUrl = $null; $defaultModel = "gpt-4o-mini" }
  "anthropic"{ $needKey = "ANTHROPIC_API_KEY"; $needUrl = $null; $defaultModel = "claude-3-5-sonnet-latest" }
  "ollama"   { $needKey = $null; $needUrl = "OLLAMA_BASE_URL"; $defaultModel = "llama3.1" }
  default    { throw "Unsupported LLM_PROVIDER: $provider" }
}

# 2) Model
$model = Get-EnvVar -Name "LLM_MODEL"
if (-not $model -or $Force) {
  $model = Read-Host -Prompt "LLM model (default: $defaultModel)"
  if ([string]::IsNullOrWhiteSpace($model)) { $model = $defaultModel }
  Set-EnvVar -Name "LLM_MODEL" -Value $model -Mode $Persist -DotEnvPath $DotEnvPath
} else {
  Write-OK "LLM_MODEL already set"
}

# 3) Provider-specific credential/url
if ($needKey) {
  $null = Require-Or-Prompt -Name $needKey -PromptText "$needKey (input hidden)" -Secret -Persist $Persist -DotEnvPath $DotEnvPath
}
if ($needUrl) {
  $url = Get-EnvVar -Name $needUrl
  if (-not $url -or $Force) {
    $url = Read-Host -Prompt "$needUrl (default: http://localhost:11434)"
    if ([string]::IsNullOrWhiteSpace($url)) { $url = "http://localhost:11434" }
    Set-EnvVar -Name $needUrl -Value $url -Mode $Persist -DotEnvPath $DotEnvPath
  } else {
    Write-OK "$needUrl already set"
  }
}

# 4) Optional knobs
function Set-If-Empty([string]$name, [string]$prompt, [string]$default){
  $cur = Get-EnvVar -Name $name
  if (-not $cur -or $Force) {
    $val = Read-Host -Prompt "$prompt (default: $default)"
    if ([string]::IsNullOrWhiteSpace($val)) { $val = $default }
    Set-EnvVar -Name $name -Value $val -Mode $Persist -DotEnvPath $DotEnvPath
  } else {
    Write-OK "$name already set"
  }
}
Set-If-Empty -name "LLM_TEMPERATURE" -prompt "LLM temperature" -default "0.2"
Set-If-Empty -name "LLM_TIMEOUT_S"  -prompt "LLM timeout seconds" -default "40"
Set-If-Empty -name "LLM_STEPS_MAX"  -prompt "Max planning steps" -default "12"

Write-Host "`nSummary:" -ForegroundColor Cyan
"{0,-20} {1}" -f "LLM_PROVIDER:", (Get-EnvVar -Name "LLM_PROVIDER")
"{0,-20} {1}" -f "LLM_MODEL:", (Get-EnvVar -Name "LLM_MODEL")
switch ((Get-EnvVar -Name "LLM_PROVIDER").ToLower()) {
  "openai"   { "{0,-20} {1}" -f "OPENAI_API_KEY:", ("*" * 8 + " (set)") }
  "anthropic"{ "{0,-20} {1}" -f "ANTHROPIC_API_KEY:", ("*" * 8 + " (set)") }
  "ollama"   { "{0,-20} {1}" -f "OLLAMA_BASE_URL:", (Get-EnvVar -Name "OLLAMA_BASE_URL") }
}

Write-Host "`nPreflight complete. Launch your server in THIS shell so it inherits the env:" -ForegroundColor Green
Write-Host "  python app.py" -ForegroundColor Green
Write-Warn "Tip: re-run with -Persist dotenv to save values into .env for future sessions."
