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

set -e

find_python() {
  if [ "${OS}" = "Windows_NT" ]; then
    PYTHON="python"
    SOURCE_DIR="Scripts"
    PIP="pip"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
    SOURCE_DIR="bin"
    PIP="pip3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
    SOURCE_DIR="bin"
    PIP="pip"
  else
    echo "Error: Neither python3 nor python is installed."
    exit 1
  fi
}

# Function to get the absolute path
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

pushd "${APP_HOME}"

find_python

# Verify Python installation
${PYTHON} --version 2> /dev/null
if [ $? -ne 0 ]; then
    echo "Error: Neither python3 nor python is installed."
    exit 1
fi
echo "Using Python interpreter: $PYTHON"

# Define variables
VENV_DIR="venv"  # Name of the virtual environment
BIN_DIR="bin"     # Directory containing shell scripts

# Step 1: Check if pip is installed
let step=${step}+1
step_desc="Check if pip is installed"
echo "Step ${step}: ${step_desc}..."
if ! command -v ${PIP} >/dev/null 2>&1; then
    echo "${PIP} not found. Installing pip..."
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
if [ -d "$VENV_DIR" ]; then
    echo "Recreating virtual environment in: $VENV_DIR"
    rm -fr $VENV_DIR
else
    echo "Creating virtual environment in: $VENV_DIR"
fi
$PYTHON -m venv "$VENV_DIR"

# Step 3: Activate the virtual environment
let step=${step}+1
step_desc="Activate the virtual environment"
echo "Step ${step}: ${step_desc}..."
VENV_PYTHON="${APP_HOME}/${VENV_DIR}/${SOURCE_DIR}/python"
if [ ! -x "$VENV_PYTHON" ]; then
    echo "Error: Python not found in the virtual environment. Exiting."
    exit 1
fi
echo "Activating virtual environment..."
if [ -f "${APP_HOME}/${VENV_DIR}/${SOURCE_DIR}/activate" ]
then
  source "${APP_HOME}/${VENV_DIR}/${SOURCE_DIR}/activate"
else
  echo $E "Error - could not locate: ${APP_HOME}/${VENV_DIR}/${SOURCE_DIR}/activate"
  echo $E "Deploying chute - bailing out!"
  exit 1
fi
# Step 4: Upgrade pip
let step=${step}+1
step_desc="Upgrade pip"
echo "Step ${step}: ${step_desc}..."
"$VENV_PYTHON" -m pip install --upgrade pip

# Step 5: Install deployment dependencies
let step=${step}+1
step_desc="Install deployment dependencies"
echo "Step ${step}: ${step_desc}..."
"$VENV_PYTHON" -m pip install -r requirements.txt
"$VENV_PYTHON" -m pip install --no-deps .

# Step 6: Set executable permissions for shell scripts
let step=${step}+1
step_desc="Set executable permissions for shell scripts"
echo "Step ${step}: ${step_desc}..."
echo "Setting executable permissions for shell scripts..."
chmod +x "$BIN_DIR"/*.sh

echo "Setup completed successfully!"

popd
