<#
.SYNOPSIS
Wrapper script for calling OraTAPI/controller/ora_tapi.py.

.DESCRIPTION
This script sets up the environment and executes the OraTAPI Python program.

For help, use:
    <OraTAPI-Home>\bin\ora_tapi.ps1 -h

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
$CONTROL_DIR = Join-Path $PROJECT_DIR "src\controller"
$ACTIVATE_SCRIPT = Join-Path $PROJECT_DIR "venv\Scripts\Activate.ps1"

# Activate the virtual environment if the script exists
if (Test-Path $ACTIVATE_SCRIPT) {
    Write-Host "Activating the virtual environment..."
    . $ACTIVATE_SCRIPT
    Write-Host "Virtual environment activated successfully."
} else {
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

# Execute the Python program
Write-Host "Executing Python script..."
& $PYTHON_INTERPRETER (Join-Path $CONTROL_DIR $ENTRY_POINT) @args
