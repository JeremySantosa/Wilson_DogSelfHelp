$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$buildEnvironment = Join-Path $projectRoot ".build-venv"
$pythonExe = Join-Path $buildEnvironment "Scripts\python.exe"
$appScript = Join-Path $projectRoot "app.py"
$buildRoot = Join-Path $projectRoot "build"
$workPath = Join-Path $buildRoot "pyinstaller-work"
$specPath = Join-Path $buildRoot "spec"
$configPath = Join-Path $buildRoot "pyinstaller-config"
$buildLog = Join-Path $buildRoot "pyinstaller-output.log"
$distPath = Join-Path $projectRoot "dist"
$outputFolder = Join-Path $distPath "WilsonDogSelfHelp"
$outputExe = Join-Path $outputFolder "WilsonDogSelfHelp.exe"

if (Get-Process -Name "WilsonDogSelfHelp" -ErrorAction SilentlyContinue) {
    throw "Close WilsonDogSelfHelp.exe before rebuilding, then run this script again."
}
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Build Python is missing. Create .build-venv in this folder and install requirements-build.txt."
}

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $pythonExe -c "import PyInstaller, PySide6" 2>&1 | Out-Null
$dependencyCheckExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference
if ($dependencyCheckExitCode -ne 0) {
    throw "The .build-venv environment is missing PyInstaller or PySide6. Install requirements-build.txt there, then retry."
}

New-Item -ItemType Directory -Path $buildRoot, $workPath, $specPath, $configPath, $distPath -Force | Out-Null

$previousConfigPath = $env:PYINSTALLER_CONFIG_DIR
$env:PYINSTALLER_CONFIG_DIR = $configPath
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    & $pythonExe -m PyInstaller --noconfirm --onedir --windowed `
        --name WilsonDogSelfHelp --distpath $distPath `
        --workpath $workPath --specpath $specPath `
        $appScript 2>&1 | Tee-Object -FilePath $buildLog
    $pyinstallerExitCode = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $previousErrorActionPreference
    if ($null -eq $previousConfigPath) {
        Remove-Item Env:PYINSTALLER_CONFIG_DIR -ErrorAction SilentlyContinue
    } else {
        $env:PYINSTALLER_CONFIG_DIR = $previousConfigPath
    }
}

if ($pyinstallerExitCode -ne 0) {
    Write-Host "PyInstaller output is saved to $buildLog"
    Get-Content -LiteralPath $buildLog -Tail 80
    throw "PyInstaller failed with exit code $pyinstallerExitCode."
}

if (-not (Test-Path -LiteralPath $outputExe)) {
    throw "PyInstaller completed, but the expected executable wasn't created at $outputExe."
}

$oldSingleFileExe = Join-Path $distPath "WilsonDogSelfHelp.exe"
if (Test-Path -LiteralPath $oldSingleFileExe) {
    Remove-Item -LiteralPath $oldSingleFileExe -Force
}

$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$currentStartup = (Get-ItemProperty -Path $runKey -Name "WilsonDogSelfHelp" -ErrorAction SilentlyContinue).WilsonDogSelfHelp
if ($currentStartup) {
    try {
        Set-ItemProperty -Path $runKey -Name "WilsonDogSelfHelp" -Value ('"' + $outputExe + '"')
    } catch {
        Write-Warning "The app was built, but Windows startup couldn't be updated. Run the new executable once to refresh it."
    }
}

Write-Host "Built: $outputExe"
Write-Host "Keep all files in dist\WilsonDogSelfHelp together."
Write-Host "All configured build paths are inside $projectRoot."
