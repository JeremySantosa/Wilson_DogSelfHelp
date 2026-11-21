$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$buildEnvironment = Join-Path $projectRoot ".build-venv"
$pythonExe = Join-Path $buildEnvironment "Scripts\python.exe"
$appScript = Join-Path $projectRoot "app.py"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    & py -3.11 -m venv $buildEnvironment
    if ($LASTEXITCODE -ne 0) {
        throw "Couldn't create the build environment. Install Python 3.11 and try again."
    }
}

& $pythonExe -m pip install -r (Join-Path $projectRoot "requirements-build.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Couldn't install build dependencies. Check your Python installation and try again."
}

& $pythonExe -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name WilsonDogSelfHelp $appScript

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

Write-Host "Built: $(Join-Path $projectRoot 'dist\WilsonDogSelfHelp.exe')"
