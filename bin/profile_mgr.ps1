<#
.SYNOPSIS
Wrapper script for calling OraTAPI/controller/profile_mgr.py.
#>

$ENTRY_POINT = [System.IO.Path]::GetFileNameWithoutExtension($PSCommandPath) + ".py"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_DIR = Split-Path -Parent $SCRIPT_DIR
$CONTROL_DIR = Join-Path $PROJECT_DIR "src\oratapi\controller"
$activateCandidates = @(
    (Join-Path $PROJECT_DIR "venv\Scripts\Activate.ps1"),
    (Join-Path $PROJECT_DIR ".venv\Scripts\Activate.ps1")
)
$venvActivated = $false

foreach ($activateScript in $activateCandidates) {
    if (Test-Path $activateScript) {
        . $activateScript
        $venvActivated = $true
        break
    }
}

if (-not $venvActivated) {
    Write-Error "Virtual environment activation script not found."
    exit 1
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

$existingPath = if ($env:PYTHONPATH) { [IO.Path]::PathSeparator + $env:PYTHONPATH } else { "" }
$env:PYTHONPATH = (Join-Path $PROJECT_DIR "src") + $existingPath

& $PYTHON_INTERPRETER (Join-Path $CONTROL_DIR $ENTRY_POINT) @args
