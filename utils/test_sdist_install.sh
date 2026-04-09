#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./utils/test_sdist_install.sh [python-version] [sdist-path]

Examples:
  ./utils/test_sdist_install.sh
  ./utils/test_sdist_install.sh 3.11.11
  ./utils/test_sdist_install.sh 3.11.11 dist/oratapi-2.4.1.tar.gz

Behavior:
  - uses the current python3/python on PATH by default
  - uses pyenv if a Python version is supplied
  - creates a scratch virtualenv under /tmp
  - extracts the selected source distribution into /tmp
  - installs dependencies from requirements.txt
  - installs the package with pip install --no-deps .
  - runs a small legacy-flow smoke test:
      * bin/quick_config.sh -t basic
      * bin/ora_tapi.sh --help
      * bin/profile_mgr.sh --show-active
      * bin/conn_mgr.sh --help
  - leaves the scratch environment in place for manual follow-on testing

Sdist selection:
  - if [sdist-path] is supplied, that file is used
  - otherwise the script looks for the newest *.tar.gz in ./dist
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
SDIST_PATH="${2:-}"

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

if [ -z "${PYTHON_VERSION}" ] && [ -z "${SDIST_PATH}" ] && [ $# -eq 1 ] && [ -f "${1}" ]; then
  SDIST_PATH="${1}"
  PYTHON_VERSION=""
fi

if [ -z "${SDIST_PATH}" ]; then
  SDIST_PATH=$(find ./dist -maxdepth 1 -type f -name '*.tar.gz' -printf '%T@ %p\n' | sort -nr | head -1 | cut -d ' ' -f2-)
fi

if [ -z "${SDIST_PATH}" ]; then
  echo "ERROR: No source distribution found under ./dist."
  echo "Build one first with: ./utils/package.sh"
  exit 1
fi

if [ ! -f "${SDIST_PATH}" ]; then
  echo "ERROR: Source distribution not found: ${SDIST_PATH}"
  exit 1
fi

SDIST_PATH=$(realpath_compat "${SDIST_PATH}")
STAMP=$(date +%Y%m%d-%H%M%S)
SCRATCH_ROOT="/tmp/oratapi-sdist-test-${PYTHON_VERSION}-${STAMP}"
UNPACK_DIR="${SCRATCH_ROOT}/unpacked"
VENV_DIR="${SCRATCH_ROOT}/venv"
HOME_DIR="${SCRATCH_ROOT}/home"

mkdir -p "${SCRATCH_ROOT}" "${UNPACK_DIR}" "${HOME_DIR}"

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
echo "Extracting source distribution: ${SDIST_PATH}"
tar -xzf "${SDIST_PATH}" -C "${UNPACK_DIR}"

APP_DIR=$(find "${UNPACK_DIR}" -mindepth 1 -maxdepth 1 -type d | head -1)
if [ -z "${APP_DIR}" ]; then
  echo "ERROR: Failed to locate unpacked application directory."
  exit 1
fi

echo "Creating scratch environment: ${VENV_DIR}"
${PYTHON_BIN} -m venv "${VENV_DIR}"

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo "Upgrading pip..."
python -m pip install --upgrade pip

echo "Installing legacy deployment dependencies..."
python -m pip install -r "${APP_DIR}/requirements.txt"

echo "Installing package from extracted source..."
python -m pip install --no-deps "${APP_DIR}"

echo "Running legacy smoke checks..."
HOME="${HOME_DIR}" "${APP_DIR}/bin/quick_config.sh" -t basic >/dev/null
HOME="${HOME_DIR}" "${APP_DIR}/bin/ora_tapi.sh" --help >/dev/null
HOME="${HOME_DIR}" "${APP_DIR}/bin/profile_mgr.sh" --show-active >/dev/null
HOME="${HOME_DIR}" "${APP_DIR}/bin/conn_mgr.sh" --help >/dev/null

echo
echo "Legacy source-distribution smoke test passed."
echo "Scratch root : ${SCRATCH_ROOT}"
echo "Virtualenv   : ${VENV_DIR}"
echo "App dir      : ${APP_DIR}"
echo "Runtime home : ${HOME_DIR}/OraTAPI"
echo
echo "Activate it with:"
echo "  source ${VENV_DIR}/bin/activate"
