#!/usr/bin/env bash
#------------------------------------------------------------------------------
# Author: Clive Bostock
#   Date: 16 December, 2024
#   Name: setup.sh
#  Descr: Script to set up the application environment, including creating a
#         virtual environment, installing dependencies, and configuring scripts.
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

PROG_PATH=$(realpath $0)
APP_HOME=$(dirname ${PROG_PATH})

# Exit on any error
set -e

pushd ${APP_HOME}

# Define variables
VENV_DIR="venv"  # Change this if you want a different name for the virtual env
BIN_DIR="bin"    # Directory containing shell scripts

# Step 1: Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists in: $VENV_DIR"
fi

# Step 2: Activate the virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Step 3: Upgrade pip to ensure you're using the latest version
echo "Upgrading pip..."
pip install --upgrade pip

# Step 4: Install dependencies from requirements.txt or manually install required packages
echo "Installing dependencies..."
pip install -r requirements.txt || echo "requirements.txt not found, installing from current directory"
pip install .

# Step 5: Set executable permissions for shell scripts
echo "Setting executable permissions for shell scripts..."
chmod +x "$BIN_DIR/conn_mgr.sh"
chmod +x "$BIN_DIR/ora_tapi.sh"

echo "Setup completed successfully!"

