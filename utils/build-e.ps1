##############################################################################
# Author: Clive Bostock
#   Date: 16 Dec 2024 (A Merry Christmas to one and all! :o)
#   Name: build.ps1
#  Descr: Performs a build and install of the project as packages in edit mode).
##############################################################################

# Function to emulate 'realpath' behavior
function Get-RealPath {
    param (
        [string]$Path
    )
    # Resolve the full path
    if (Test-Path $Path) {
        return (Resolve-Path $Path).Path
    } else {
        throw "Path not found: $Path"
    }
}

# Get script path and directories
$ScriptPath = Get-RealPath $MyInvocation.MyCommand.Path
$ScriptDir = Split-Path -Parent $ScriptPath
$AppHome = Split-Path -Parent $ScriptDir

# Navigate to the application home directory
Push-Location $AppHome
Write-Output "App home: $AppHome"

# Activate Python virtual environment and install the project
# Check for the virtual environment directory
if (Test-Path "venv/bin/activate") {
    # Activate the virtual environment for Linux/macOS style
    . "venv/bin/activate"
} elseif (Test-Path "venv/Scripts/activate") {
    # Activate the virtual environment for Windows style
    . "venv/Scripts/activate"
 elseif (Test-Path ".venv/Scripts/activate") {
    # Activate the virtual environment for Windows style
    . ".venv/bin/activate"
}
 elseif (Test-Path ".venv/Scripts/activate") {
    # Activate the virtual environment for Windows style
    . ".venv/Scripts/activate"
} else {
    Write-Host "Cannot locate activate script from venv directory!" -ForegroundColor Red
    Exit 1
}
python -m pip install -e .

