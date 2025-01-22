#!/usr/bin/env bash
#------------------------------------------------------------------------------
# Author: Clive Bostock
#   Date: 5 August 2024
#   Name: update_ora_tapi.sh
#  Descr: Wrapper shell for calling OraTAPI/src/controller/update_ora_tapi.py
#  
# This utility updates the sample, config files, templates and executables from a
# downloaded OraTAPI distribution file.
#
#    For help, use:
#
#      <OraTAPI-Home>/bin/update_ora_tapi.sh -h
#
#------------------------------------------------------------------------------

# Use a workaround for realpath if it's not available (possibly not on Mac)
realpath() {
  [[ $1 = /* ]] && echo "$1" || echo "$PWD/${1#./}"
}
ENTRY_POINT="update_ora_tapi.py"
SCRIPT_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
PROJECT_DIR=$(dirname "${SCRIPT_DIR}")
BIN_DIR="${PROJECT_DIR}/bin"
CONTROL_DIR="${PROJECT_DIR}/src/controller"
VIEW_DIR="${PROJECT_DIR}/src/view"
LIB_DIR="${PROJECT_DIR}/src/lib"
MODEL_DIR="${PROJECT_DIR}/src/model"
E="-e"

E="-e"

# Virtual environment activation (adjust based on your setup)
VENV_DIR="$PROJECT_DIR/venv"  # Assuming venv directory is in the parent folder

if [[ "$(uname -s)" =~ ^MINGW64_NT ]]; then  # Check for windows systems
  ACTIVATE_SCRIPT="$VENV_DIR/Scripts/activate"  # Windows path
else
  ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"  # Linux/Mac path
fi

if [ ! -f "$ACTIVATE_SCRIPT" ]
then
  echo "WARNING: Unable locate a venv directory or activate script; no virtual environment activated."
fi
# Source virtual environment if it exists
if [[ -f "$ACTIVATE_SCRIPT" ]]
then
  source "$ACTIVATE_SCRIPT"
fi

# Detect operating system (Linux, Mac, or Windows)
OS="$(uname -s)"

# Choose Python interpreter based on user's PATH
PYTHON_INTERPRETER=""
if command -v python >/dev/null 2>&1; then
  PYTHON_INTERPRETER="python"
elif command -v py >/dev/null 2>&1; then
  PYTHON_INTERPRETER="py"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_INTERPRETER="python3"
fi

# Error handling if no interpreter found
if [[ -z "$PYTHON_INTERPRETER" ]]; then
  echo "Error: No compatible Python interpreter found (python3, python, or py)!"
  exit 1
fi

export PYTHONPATH=${PROJECT_DIR}:${PYTHONPATH}
# Execute the Python program
"$PYTHON_INTERPRETER" "${CONTROL_DIR}/${ENTRY_POINT}" "$@"
