# One-command local setup + launch for Granite Lifeline (Windows).
#
# Installs dashboard dependencies, installs the Model Layer's dedicated
# dependencies, installs Ollama if missing, pulls the Granite LLM, and
# starts the dashboard. Safe to re-run - every step is idempotent.
#
# Usage (PowerShell): .\setup.ps1
# If script execution is blocked, run once as admin:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$OllamaModel = "granite4.1:8b"

Write-Host "==> Installing dashboard Python dependencies..."
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
pip install --upgrade pip --quiet
pip install -r requirements.txt
pip install -r requirements-local.txt

Write-Host "==> Installing Model Layer Python dependencies (includes torch - this can take a few minutes on first run)..."
if (-not (Test-Path "model_layer\ttm-related\.venv")) {
    python -m venv model_layer\ttm-related\.venv
}
& .\model_layer\ttm-related\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .\model_layer\ttm-related\.venv\Scripts\python.exe -m pip install -r model_layer\ttm-related\requirements.txt

Write-Host "==> Checking Ollama..."
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Ollama not found - installing via winget..."
        winget install --id Ollama.Ollama -e --silent
        # winget installs to a new PATH entry; refresh this session's PATH.
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("Path", "User")
    } else {
        Write-Host "Ollama not found and winget is unavailable."
        Write-Host "Install it manually first: https://ollama.com/download"
        exit 1
    }
}

Write-Host "==> Starting Ollama server (if not already running)..."
$ollamaUp = $false
try {
    Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -UseBasicParsing | Out-Null
    $ollamaUp = $true
} catch {
    $ollamaUp = $false
}
if (-not $ollamaUp) {
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

Write-Host "==> Pulling $OllamaModel (~5.3GB on first run; skips if already present)..."
ollama pull $OllamaModel

Write-Host "==> Setup complete. Starting the dashboard..."
streamlit run dashboard\app.py
