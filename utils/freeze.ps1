##############################################################################
# Author: Clive Bostock
#   Date: 27 Jan 2024
#   Name: freeze.ps1
#  Descr: Generates a Python requirements.txt 
##############################################################################

# Resolve the script's path and directories
$PROG_PATH = (Get-Item -Path $MyInvocation.MyCommand.Definition).FullName
$PROG_DIR = Split-Path -Path $PROG_PATH -Parent
$APP_HOME = Split-Path -Path $PROG_DIR -Parent

# Change to APP_HOME directory
Set-Location -Path $APP_HOME

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

# Generate the requirements.txt file, excluding "apt-clone"
pip freeze | Select-String -NotMatch "apt-clone" | Set-Content -Path "requirements.txt"

# Notify the user
Write-Host "requirements.txt has been generated successfully." -ForegroundColor Green

