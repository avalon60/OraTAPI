<#
.SYNOPSIS
Wrapper script for calling OraTAPI/controller/quick_config.py.

.DESCRIPTION
This script sets up the environment and executes the initialisation routines - a Python program.

This utility copies `.sample` files from the resources directory to
target locations, based on the template_category, and specific copying rules.
We only initialise, if specific files does not exist, we avoid clobbering them.

For help, use:
    <OraTAPI-Home>\bin\quick_config.ps1 -h

.AUTHOR
Clive Bostock
.DATE
5 August 2024
#>

# Define the entry point and directories
$ENTRY_POINT = [System.IO.Path]::GetFileNameWithoutExtension($PSCommandPath) + ".py"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_DIR = Split-Path -Parent $SCRIPT_DIR
$BIN_DIR = Join-Path $PROJECT_DIR "bin"
$CONTROL_DIR = Join-Path $PROJECT_DIR "src\oratapi\controller"
$activateCandidates = @(
    (Join-Path $PROJECT_DIR "venv\Scripts\Activate.ps1"),
    (Join-Path $PROJECT_DIR ".venv\Scripts\Activate.ps1")
)
$venvActivated = $false

foreach ($activateScript in $activateCandidates) {
    if (Test-Path $activateScript) {
        Write-Host "Activating the virtual environment..."
        . $activateScript
        Write-Host "Virtual environment activated successfully."
        $venvActivated = $true
        break
    }
}

if (-not $venvActivated) {
    Write-Warning "Virtual environment activation script not found. Exiting..."
    exit 1
}

# Determine the Python interpreter
$PYTHON_INTERPRETER = ""
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PYTHON_INTERPRETER = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PYTHON_INTERPRETER = "py"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PYTHON_INTERPRETER = "python3"
}

# Error handling if no interpreter found
if (-not $PYTHON_INTERPRETER) {
    Write-Error "Error: No compatible Python interpreter found (python3, python, or py)!"
    exit 1
}

$existingPath = if ($env:PYTHONPATH) { [IO.Path]::PathSeparator + $env:PYTHONPATH } else { "" }
$env:PYTHONPATH = (Join-Path $PROJECT_DIR "src") + $existingPath

# Execute the Python program
Write-Host "Executing Python script..."
& $PYTHON_INTERPRETER (Join-Path $CONTROL_DIR $ENTRY_POINT) @args
