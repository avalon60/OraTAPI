#------------------------------------------------------------------------------

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
# Author: Clive Bostock
#   Date: 16 December 2024
#   Name: setup.ps1
#  Descr: Script to set up the application environment, including creating a
#         virtual environment, checking/installing pip, installing dependencies,
#         and configuring scripts.
#------------------------------------------------------------------------------

# Initialize step counter
$step = 0
$PROG_PATH = $MyInvocation.MyCommand.Path
$APP_HOME = Split-Path -Parent $PROG_PATH

# Change to the application directory
Push-Location -Path $APP_HOME

# Define variables
$VENV_DIR = "venv"  # Change this if you want a different name for the virtual environment
$BIN_DIR = "bin"    # Directory containing shell scripts

# Step 1: Check if pip is installed
$step++
$step_desc = "Check if pip is installed"
Write-Host "Step ${step}: ${step_desc}..."
if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
    Write-Host "pip not found. Installing pip..."
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "get-pip.py"
    python get-pip.py
    Remove-Item -Path "get-pip.py" -Force
} else {
    Write-Host "pip is already installed."
}

# Step 2: Create virtual environment (recreate if it exists)
$step++
$step_desc = "Create virtual environment (recreate if it exists)"
Write-Host "Step ${step}: ${step_desc}..."
if (Test-Path $VENV_DIR) {
    Write-Host "Recreating virtual environment in: $VENV_DIR"
    Remove-Item -Recurse -Force -Path $VENV_DIR
} else {
    Write-Host "Creating virtual environment in: $VENV_DIR"
}
python -m venv $VENV_DIR

# Step 3: Activate the virtual environment
$step++
$step_desc = "Activate the virtual environment"
Write-Host "Step ${step}: ${step_desc}..."
$venvPython = Join-Path -Path $VENV_DIR -ChildPath "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Error: Python not found in the virtual environment. Exiting."
    Exit 1
}
Write-Host "Activating virtual environment..."

# Step 4: Upgrade pip to ensure you're using the latest version
Write-Host "Upgrading pip..."
& $venvPython -m pip install --upgrade pip

# Step 5: Install deployment dependencies
$step++
$step_desc = "Install deployment dependencies"
Write-Host "Step ${step}: ${step_desc}..."
& $venvPython -m pip install -r requirements.txt
& $venvPython -m pip install --no-deps .

Write-Host "Setup completed successfully!"

# Return to the original directory
Pop-Location
