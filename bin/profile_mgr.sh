#!/usr/bin/env bash
#------------------------------------------------------------------------------
# Author: Clive Bostock
#   Date: 4 April 2026
#   Name: profile_mgr.sh
#  Descr: Wrapper shell for calling OraTAPI/src/controller/profile_mgr.py
#------------------------------------------------------------------------------

realpath() {
  [[ $1 = /* ]] && echo "$1" || echo "$PWD/${1#./}"
}
ENTRY_POINT="$(basename $0 .sh).py"
SCRIPT_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
PROJECT_DIR=$(dirname "${SCRIPT_DIR}")
CONTROL_DIR="${PROJECT_DIR}/src/controller"

VENV_DIR="$PROJECT_DIR/venv"

if [[ "$(uname -s)" =~ ^MINGW64_NT ]]; then
  ACTIVATE_SCRIPT="$VENV_DIR/Scripts/activate"
else
  ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
fi

if [[ -f "$ACTIVATE_SCRIPT" ]]
then
  source "$ACTIVATE_SCRIPT"
fi

PYTHON_INTERPRETER=""
if command -v python >/dev/null 2>&1; then
  PYTHON_INTERPRETER="python"
elif command -v py >/dev/null 2>&1; then
  PYTHON_INTERPRETER="py"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_INTERPRETER="python3"
fi

if [[ -z "$PYTHON_INTERPRETER" ]]; then
  echo "Error: No compatible Python interpreter found (python3, python, or py)!"
  exit 1
fi

export PYTHONPATH=${PROJECT_DIR}:${PYTHONPATH}
"$PYTHON_INTERPRETER" "${CONTROL_DIR}/${ENTRY_POINT}" "$@"
