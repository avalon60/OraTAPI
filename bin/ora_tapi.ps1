<#
.SYNOPSIS
Wrapper script for calling OraTAPI/controller/ora_tapi.py.

.DESCRIPTION
This script sets up the environment and executes the OraTAPI Python program.

For help, use:
    <OraTAPI-Home>\bin\ora_tapi.ps1 -h

Before the first execution, ensure you set the execution policy:
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

.AUTHOR
Clive Bostock
.DATE
5 August 2024
#>


# Define the entry point and directories
$ENTRY_POINT = "ora_tapi.py"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_DIR = Split-Path -Parent $SCRIPT_DIR
$BIN_DIR = Join-Path $PROJECT_DIR "bin"
$CONTROL_DIR = Join-Path $PROJECT_DIR "src\controller"

# Virtual environment directory
$VENV_DIR = Join-Path $PROJECT_DIR "venv"  # Assuming venv directory is in the parent folder

# Determine activation script based on OS
if ($IsWindows) {
    $ACTIVATE_SCRIPT = Join-Path $VENV_DIR "Scripts\activate.ps1"  # Windows path
} else {
    $ACTIVATE_SCRIPT = Join-Path $VENV_DIR "bin\activate"  # Linux/Mac path
}

# Check if the virtual environment activation script exists
if (!(Test-Path $ACTIVATE_SCRIPT)) {
    Write-Host "WARNING: Unable to locate a venv directory or activate script; no virtual environment activated."
}

# Activate the virtual environment if the script exists
if (Test-Path $ACTIVATE_SCRIPT) {
    if ($IsWindows) {
        & $ACTIVATE_SCRIPT
    } else {
        source $ACTIVATE_SCRIPT
    }
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

# Set up PYTHONPATH
$LIBS = Join-Path $PROJECT_DIR "lib"
$CTL = Join-Path $PROJECT_DIR "controller"
$VIEW = Join-Path $PROJECT_DIR "view"
$MDL = Join-Path $PROJECT_DIR "model"
$env:PYTHONPATH = "$PROJECT_DIR;$LIBS;$CTL;$VIEW;$MDL;$env:PYTHONPATH"

# Execute the Python program
Write-Host "Executing Python script..."
& $PYTHON_INTERPRETER (Join-Path $CONTROL_DIR $ENTRY_POINT) @args
