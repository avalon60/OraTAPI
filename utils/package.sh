#!/usr/bin/env bash
##############################################################################
# Author: Clive Bostock
#   Date: 9 Apr 2026
#   Name: package.sh
#  Descr: Builds OraTAPI release artefacts from the Poetry configuration.
##############################################################################
set -euo pipefail

realpath_fallback() {
  if command -v realpath >/dev/null 2>&1; then
    realpath "$1"
  elif command -v readlink >/dev/null 2>&1; then
    readlink -f "$1"
  else
    cd "$(dirname "$1")" && pwd
  fi
}

find_poetry() {
  if command -v poetry >/dev/null 2>&1; then
    echo "poetry"
  elif [ -x "${HOME}/.local/bin/poetry" ]; then
    echo "${HOME}/.local/bin/poetry"
  else
    echo ""
  fi
}

display_usage() {
  cat <<'EOF'
Usage:
  ./utils/package.sh -v <version_tag>
  ./utils/package.sh -V

Examples:
  ./utils/package.sh -v 2.4.1
  ./utils/package.sh -V

Use -V to print the version from pyproject.toml.
Use -v as a safety check before packaging.
EOF
  exit 1
}

PROG_PATH=$(realpath_fallback "$0")
PROG_DIR=$(dirname "${PROG_PATH}")
APP_HOME=$(dirname "${PROG_DIR}")
PYPROJECT_FILE="${APP_HOME}/pyproject.toml"
PACKAGE_INIT_FILE="${APP_HOME}/src/oratapi/__init__.py"
REQUIREMENTS_FILE="${APP_HOME}/requirements.txt"
DIST_DIR="${APP_HOME}/dist"

while getopts "v:V" options; do
  case "${options}" in
    v) VERSION_TAG="${OPTARG}" ;;
    V) SHOW_VERSION=Y ;;
    *) display_usage ;;
  esac
done

pyproject_version() {
  grep '^version = ' "${PYPROJECT_FILE}" | head -1 | cut -f2 -d "=" | tr -d ' "'
}

package_version() {
  grep '^__version__ = ' "${PACKAGE_INIT_FILE}" | head -1 | cut -f2 -d "=" | tr -d ' "'
}

POETRY=$(find_poetry)
if [ -z "${POETRY}" ]; then
  echo "ERROR: Poetry is required to package this project."
  exit 1
fi

pushd "${APP_HOME}" >/dev/null

if [ "${SHOW_VERSION:-N}" = "Y" ]; then
  pyproject_version
  popd >/dev/null
  exit 0
fi

if [ -z "${VERSION_TAG:-}" ]; then
  display_usage
fi

PYPROJECT_VERSION=$(pyproject_version)
PACKAGE_VERSION=$(package_version)

if [ "${VERSION_TAG}" != "${PYPROJECT_VERSION}" ]; then
  echo "ERROR: Version tag ${VERSION_TAG} does not match ${PYPROJECT_FILE} (${PYPROJECT_VERSION})."
  exit 1
fi

if [ "${VERSION_TAG}" != "${PACKAGE_VERSION}" ]; then
  echo "ERROR: Version tag ${VERSION_TAG} does not match ${PACKAGE_INIT_FILE} (${PACKAGE_VERSION})."
  exit 1
fi

echo "App home: ${APP_HOME}"
echo "Release version: ${VERSION_TAG}"

echo "Checking Poetry metadata..."
"${POETRY}" check

echo "Exporting requirements.txt..."
"${POETRY}" export --format requirements.txt --without-hashes --only main --output "${REQUIREMENTS_FILE}"

echo "Building sdist and wheel..."
"${POETRY}" build

WHEEL_FILE=$(find "${DIST_DIR}" -maxdepth 1 -type f -name "oratapi-${VERSION_TAG}-*.whl" | head -1)
SDIST_FILE=$(find "${DIST_DIR}" -maxdepth 1 -type f -name "oratapi-${VERSION_TAG}.tar.gz" | head -1)

if [ -z "${WHEEL_FILE}" ] || [ -z "${SDIST_FILE}" ]; then
  echo "ERROR: Expected build artefacts were not produced in ${DIST_DIR}."
  exit 1
fi

echo
echo "Built artefacts:"
echo "  Wheel : ${WHEEL_FILE}"
echo "  Sdist : ${SDIST_FILE}"

popd >/dev/null
