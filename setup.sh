#!/usr/bin/env bash
#------------------------------------------------------------------------------
# Author: Clive Bostock
#   Date: 16 December 2024
#   Name: setup.sh
#  Descr: Script to set up the application environment, including creating a
#         virtual environment, checking/installing pip, installing dependencies,
#         and configuring scripts. Determines Python interpreter based on the
#         system.
#------------------------------------------------------------------------------

realpath() {
  if command -v readlink >/dev/null 2>&1; then
    # Linux or systems where readlink is available
    readlink -f "$1"
  else
    # macOS or systems where readlink -f is not available
    cd "$(dirname "$1")" && pwd
  fi
}
step=0
PROG_PATH=$(realpath "$0")
APP_HOME=$(dirname "${PROG_PATH}")

# Exit on any error
set -e

pushd "${APP_HOME}"

# Determine Python interpreter
if [ "${OS}" = "Windows_NT" ]
then
    PYTHON="python"
    SOURCE_DIR="Scripts"
elif command -v python3 >/dev/null 2>&1
then
    PYTHON="python3"
    SOURCE_DIR="bin"
fi

${PYTHON} --version 2> /dev/null
if [ $? -ne 0 ]
then
    echo "Error: Neither python3 nor python is installed."
    exit 1
fi
echo "Using Python interpreter: $PYTHON"

# Define variables
VENV_DIR="venv"  # Change this if you want a different name for the virtual env
BIN_DIR="bin"    # Directory containing shell scripts

# Step 1: Check if pip is installed
let step=${step}+1
step_desc="Check if pip is installed"
echo "Step ${step}: ${step_desc}..."
if ! command -v pip >/dev/null 2>&1; then
    echo "pip not found. Installing pip..."
    curl -O https://bootstrap.pypa.io/get-pip.py
    $PYTHON get-pip.py
    rm get-pip.py
else
    echo "pip is already installed."
fi

# Step 2: Create virtual environment if it doesn't exist
let step=${step}+1
step_desc="Create virtual environment if it doesn't exist"
echo "Step ${step}: ${step_desc}..."
if [  -d "$VENV_DIR" ]
then
    rm -fr $VENV_DIR
    echo "Recreating virtual environment in: $VENV_DIR"
else
    echo "Creating virtual environment in: $VENV_DIR"
fi
$PYTHON -m venv "$VENV_DIR"

# Step 3: Activate the virtual environment
let step=${step}+1
step_desc="Activate the virtual environment"
echo "Step ${step}: ${step_desc}..."
echo "Activating virtual environment..."
source "${VENV_DIR}/${SOURCE_DIR}/activate"

# Step 4: Upgrade pip to ensure you're using the latest version
echo "Upgrading pip..."
venv/${SOURCE_DIR}/python -m pip install --upgrade pip


# Step 5: Perform the packages install
step_desc="Perform the packages install"
let step=${step}+1
echo "Step ${step}: ${step_desc}..."
$PYTHON -m pip install .

# Step 6: Set executable permissions for shell scripts
step_desc="Set executable permissions for shell script"
let step=${step}+1
echo "Step ${step}: ${step_desc}..."
echo "Setting executable permissions for shell scripts..."
chmod +x "$BIN_DIR/conn_mgr.sh"
chmod +x "$BIN_DIR/ora_tapi.sh"

echo "Setup completed successfully!"

popd

