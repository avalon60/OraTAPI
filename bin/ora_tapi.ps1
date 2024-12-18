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
#    chmod 750 ora_tapi.sh
#
#------------------------------------------------------------------------------
#>

# Constants
$EntryPoint = "ora_tapi.py"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectDir = Split-Path -Parent $ScriptDir
$BinDir = Join-Path $ProjectDir "bin"
$ControlDir = Join-Path $ProjectDir "controller"
$VenvDir = Join-Path $ProjectDir "venv"

# Detect OS and activate virtual environment
if ($env:OS -match "Windows") {
    $ActivateScript = Join-Path $VenvDir "Scripts\activate.ps1"
} else {
    $ActivateScript = Join-Path $VenvDir "bin/activate"
}

# Attempt to activate virtual environment
if (-Not (Test-Path $ActivateScript)) {
    Write-Host "WARNING: Unable to locate a venv directory or activate script; no virtual environment activated."
} else {
    # For Windows PowerShell
    if ($ActivateScript -match "activate.ps1") {
        & $ActivateScript
    } else {
        # For Linux/Mac (requires `source` equivalent)
        . $ActivateScript
    }
}

# Detect Python interpreter
$PythonInterpreter = ""
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonInterpreter = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonInterpreter = "py"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonInterpreter = "python3"
}

# Error handling if no interpreter found
if (-Not $PythonInterpreter) {
    Write-Host "Error: No compatible Python interpreter found (python3, python, or py)!"
    exit 1
}

# Configure PYTHONPATH
$Libs = Join-Path $ProjectDir "lib"
$Ctl = Join-Path $ProjectDir "controller"
$View = Join-Path $ProjectDir "view"
$Model = Join-Path $ProjectDir "model"
$env:PYTHONPATH = "$ProjectDir;$Libs;$Ctl;$View;$Model;$env:PYTHONPATH"

# Execute the Python script
$Arguments = $args -join " "  # Combine passed arguments
& $PythonInterpreter (Join-Path $ControlDir $EntryPoint) $Arguments

