<#
.SYNOPSIS
Wrapper script for calling OraTAPI/controller/profile_mgr.py.
#>

$ENTRY_POINT = [System.IO.Path]::GetFileNameWithoutExtension($PSCommandPath) + ".py"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_DIR = Split-Path -Parent $SCRIPT_DIR
$CONTROL_DIR = Join-Path $PROJECT_DIR "src\controller"
$ACTIVATE_SCRIPT = Join-Path $PROJECT_DIR "venv\Scripts\Activate.ps1"

if (Test-Path $ACTIVATE_SCRIPT) {
    . $ACTIVATE_SCRIPT
}

$PYTHON_INTERPRETER = ""
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PYTHON_INTERPRETER = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PYTHON_INTERPRETER = "py"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PYTHON_INTERPRETER = "python3"
}

if (-not $PYTHON_INTERPRETER) {
    Write-Error "Error: No compatible Python interpreter found (python3, python, or py)!"
    exit 1
}

& $PYTHON_INTERPRETER (Join-Path $CONTROL_DIR $ENTRY_POINT) @args
