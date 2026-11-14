$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$venvPath = Join-Path $projectRoot ".venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Host "Création de l'environnement Python..."
    python -m venv $venvPath
}

Write-Host "Installation des dépendances..."
& $pythonPath -m pip install -r (Join-Path $projectRoot "requirements.txt")

$envPath = Join-Path $projectRoot ".env"
if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath (Join-Path $projectRoot ".env.example") -Destination $envPath
    Write-Host "Fichier .env créé. Les clés IA restent facultatives."
}

Write-Host "Ouverture de Cap Marchés sur http://localhost:8501"
& $pythonPath -m streamlit run (Join-Path $projectRoot "app.py")

