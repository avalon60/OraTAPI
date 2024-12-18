<#
#------------------------------------------------------------------------------
# Author: Clive Bostock
#   Date: 5 August 2024
#   Name: ora_tapi.sh
#  Descr: Wrapper shell for calling OraTAPI/controller/ora_tapi.py
#
#    For help, use:
#
#      <OraTAPI-Home>/bin/ora_tapi.sh -h
#
#    For Mac or Linux, before the first execution, ensure you set the
#    execute permissions:
#
#    cd <OraTAPI-Home>/bin
#    chmod 750 conn_mgr.sh
#
#------------------------------------------------------------------------------
#>
$ENTRY_POINT = "conn_mgr.py"
$SCRIPT_DIR = (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$PROJECT_DIR = (Split-Path -Parent $SCRIPT_DIR)
$BIN_DIR = "${PROJECT_DIR}\bin"
$CONTROL_DIR = "${PROJECT_DIR}\controller"
$E = "-e"

# Virtual environment activation (adjust based on your setup)
$VENV_DIR = "$PROJECT_DIR\venv"  # Assuming venv directory is in the parent folder

if ($env:OS -match "Windows") {  # Check for windows systems
    $ACTIVATE_SCRIPT = "$VENV_DIR\Scripts\Activate.ps1"  # Windows path
} else {
    $ACTIVATE_SCRIPT = "$VENV_DIR\bin\activate"  # Linux/Mac path
}

if (-Not (Test-Path $ACTIVATE_SCRIPT)) {
    Write-Warning "Unable to locate a venv directory or activate script; no virtual environment activated."
} else {
    # Source virtual environment if it exists
    . $ACTIVATE_SCRIPT
}

# Detect operating system (Linux, Mac, or Windows)
$OS = [System.Environment]::OSVersion.Platform

# Choose Python interpreter based on user's PATH
$PYTHON_INTERPRETER = ""

if (Get-Command python -ErrorAction SilentlyContinue) {
    $PYTHON_INTERPRETER = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PYTHON_INTERPRETER = "py"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PYTHON_INTERPRETER = "python3"
}

# Error handling if no interpreter found
if (-Not $PYTHON_INTERPRETER) {
    Write-Error "Error: No compatible Python interpreter found (python3, python, or py)!"
    exit 1
}

$LIBS = (Get-Item "${PROJECT_DIR}\lib").FullName
$CTL = (Get-Item "${PROJECT_DIR}\controller").FullName
$VIEW = (Get-Item "${PROJECT_DIR}\view").FullName
$MDL = (Get-Item "${PROJECT_DIR}\model").FullName
$env:PYTHONPATH = "${PROJECT_DIR};${LIBS};${CTL};${VIEW};${MDL}" + $env:PYTHONPATH

# Execute the Python program
& $PYTHON_INTERPRETER "${CONTROL_DIR}\${ENTRY_POINT}" $args

