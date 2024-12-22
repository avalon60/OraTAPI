#------------------------------------------------------------------------------
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
Write-Host "Step $step: $step_desc..."
if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
    Write-Host "pip not found. Installing pip..."
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile "get-pip.py"
    python3 get-pip.py
    Remove-Item -Path "get-pip.py" -Force
} else {
    Write-Host "pip is already installed."
}

# Step 2: Create virtual environment if it doesn't exist
$step++
$step_desc = "Create virtual environment if it doesn't exist"
Write-Host "Step $step: $step_desc..."
if (-not (Test-Path $VENV_DIR)) {
    Write-Host "Creating virtual environment in: $VENV_DIR"
    python3 -m venv $VENV_DIR
} else {
    Write-Host "Virtual environment already exists in: $VENV_DIR"
}

# Step 3: Activate the virtual environment
$step++
$step_desc = "Activate the virtual environment"
Write-Host "Step $step: $step_desc..."
Write-Host "Activating virtual environment..."
# Use the virtual environment's Python directly
$venvPython = Join-Path -Path $VENV_DIR -ChildPath "Scripts\python.exe"

# Step 4: Upgrade pip to ensure you're using the latest version
Write-Host "Upgrading pip..."
& $venvPython -m pip install --upgrade pip

# Step 5: Perform the packages install
$step++
$step_desc = "Perform the packages install"
Write-Host "Step $step: $step_desc..."
& $venvPython -m pip install .

# Step 6: Set executable permissions for shell scripts (on non-Windows systems)
$step++
$step_desc = "Set executable permissions for shell scripts"
Write-Host "Step $step: $step_desc..."
if ($IsWindows -eq $false) {
    Write-Host "Setting executable permissions for shell scripts..."
    chmod +x (Join-Path -Path $BIN_DIR -ChildPath "conn_mgr.sh")
    chmod +x (Join-Path -Path $BIN_DIR -ChildPath "ora_tapi.sh")
} else {
    Write-Host "Skipping permission changes on Windows."
}

Write-Host "Setup completed successfully!"

# Return to the original directory
Pop-Location

