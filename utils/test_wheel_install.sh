#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./utils/test_wheel_install.sh [python-version] [wheel-path]

Examples:
  ./utils/test_wheel_install.sh
  ./utils/test_wheel_install.sh 3.11.11
  ./utils/test_wheel_install.sh 3.11.11 dist/oratapi-2.4.1-py3-none-any.whl

Behavior:
  - uses the current python3/python on PATH by default
  - uses pyenv if a Python version is supplied
  - creates a scratch virtualenv under /tmp
  - installs the selected wheel into that virtualenv
  - runs a small OraTAPI smoke test:
      * quick_config -t basic
      * ora_tapi --help
      * profile_mgr --show-active
      * conn_mgr --help
  - leaves the scratch environment in place for manual follow-on testing

Wheel selection:
  - if [wheel-path] is supplied, that file is used
  - otherwise the script looks for the newest *.whl in ./dist
EOF
}

realpath_compat() {
  if command -v readlink >/dev/null 2>&1; then
    readlink -f "$1"
  else
    cd "$(dirname "$1")" && pwd
  fi
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

if [ $# -gt 2 ]; then
  usage
  exit 1
fi

PYTHON_VERSION="${1:-}"
WHEEL_PATH="${2:-}"

if [ -n "${PYTHON_VERSION}" ]; then
  if ! command -v pyenv >/dev/null 2>&1; then
    echo "ERROR: pyenv is not available on PATH."
    exit 1
  fi

  if ! pyenv prefix "${PYTHON_VERSION}" >/dev/null 2>&1; then
    echo "ERROR: Python ${PYTHON_VERSION} is not installed in pyenv."
    echo "Install it with: pyenv install ${PYTHON_VERSION}"
    exit 1
  fi
fi

if [ -z "${PYTHON_VERSION}" ] && [ -z "${WHEEL_PATH}" ] && [ $# -eq 1 ] && [ -f "${1}" ]; then
  WHEEL_PATH="${1}"
  PYTHON_VERSION=""
fi

if [ -z "${WHEEL_PATH}" ]; then
  WHEEL_PATH=$(find ./dist -maxdepth 1 -type f -name '*.whl' -printf '%T@ %p\n' | sort -nr | head -1 | cut -d ' ' -f2-)
fi

if [ -z "${WHEEL_PATH}" ]; then
  echo "ERROR: No wheel found under ./dist."
  echo "Build one first with: poetry build --format wheel"
  exit 1
fi

if [ ! -f "${WHEEL_PATH}" ]; then
  echo "ERROR: Wheel not found: ${WHEEL_PATH}"
  exit 1
fi

WHEEL_PATH=$(realpath_compat "${WHEEL_PATH}")
STAMP=$(date +%Y%m%d-%H%M%S)
SCRATCH_ROOT="/tmp/oratapi-wheel-test-${PYTHON_VERSION}-${STAMP}"
VENV_DIR="${SCRATCH_ROOT}/venv"
HOME_DIR="${SCRATCH_ROOT}/home"

mkdir -p "${SCRATCH_ROOT}" "${HOME_DIR}"

if [ -n "${PYTHON_VERSION}" ]; then
  export PYENV_VERSION="${PYTHON_VERSION}"
  PYTHON_BIN="pyenv exec python"
  PYTHON_LABEL="pyenv Python: ${PYTHON_VERSION}"
else
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "ERROR: Neither python3 nor python is available on PATH."
    exit 1
  fi
  PYTHON_LABEL="$(${PYTHON_BIN} --version 2>&1)"
fi

echo "Using ${PYTHON_LABEL}"
echo "Creating scratch environment: ${VENV_DIR}"
${PYTHON_BIN} -m venv "${VENV_DIR}"

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing wheel: ${WHEEL_PATH}"
python -m pip install "${WHEEL_PATH}"

echo "Running smoke checks..."
HOME="${HOME_DIR}" quick_config -t basic >/dev/null
HOME="${HOME_DIR}" ora_tapi --help >/dev/null
HOME="${HOME_DIR}" profile_mgr --show-active >/dev/null
HOME="${HOME_DIR}" conn_mgr --help >/dev/null

echo
echo "Wheel smoke test passed."
echo "Scratch root : ${SCRATCH_ROOT}"
echo "Virtualenv   : ${VENV_DIR}"
echo "Runtime home : ${HOME_DIR}/OraTAPI"
echo
echo "Activate it with:"
echo "  source ${VENV_DIR}/bin/activate"
echo
echo "Installed package summary:"
python -m pip show oratapi || true
