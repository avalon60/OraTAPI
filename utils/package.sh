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
    if poetry --version >/dev/null 2>&1; then
      echo "poetry"
      return
    fi
  fi

  if [ -x "${HOME}/.local/bin/poetry" ]; then
    if "${HOME}/.local/bin/poetry" --version >/dev/null 2>&1; then
      echo "${HOME}/.local/bin/poetry"
      return
    fi
  fi

  if command -v pyenv >/dev/null 2>&1; then
    local pyenv_root
    pyenv_root=$(pyenv root)
    local poetry_path
    poetry_path=$(find "${pyenv_root}/versions" -mindepth 3 -maxdepth 3 -type f -path '*/bin/poetry' 2>/dev/null | sort -V | tail -1)
    if [ -n "${poetry_path}" ] && [ -x "${poetry_path}" ]; then
      echo "${poetry_path}"
      return
    fi
  fi

  echo ""
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

require_archive_member() {
  local archive_path="$1"
  local member_path="$2"
  local archive_type="$3"

  if [ "${archive_type}" = "sdist" ]; then
    tar -tf "${archive_path}" | grep -Fx "${member_path}" >/dev/null
  else
    unzip -Z -1 "${archive_path}" | grep -Fx "${member_path}" >/dev/null
  fi
}

assert_archive_contains_text() {
  local archive_path="$1"
  local member_path="$2"
  local archive_type="$3"
  local expected_text="$4"

  if [ "${archive_type}" = "sdist" ]; then
    tar -xOf "${archive_path}" "${member_path}" | grep -F "${expected_text}" >/dev/null
  else
    unzip -p "${archive_path}" "${member_path}" | grep -F "${expected_text}" >/dev/null
  fi
}

verify_release_samples() {
  local sdist_file="$1"
  local wheel_file="$2"
  local sdist_root="oratapi-${VERSION_TAG}"
  local sdist_members=(
    "${sdist_root}/resources/config/OraTAPI.ini.sample"
    "${sdist_root}/src/oratapi/ora_tapi_package_data/resources/config/OraTAPI.ini.sample"
  )
  local wheel_member="oratapi/ora_tapi_package_data/resources/config/OraTAPI.ini.sample"
  local sentinel_lines=(
    "enable_ut_code_generation = false"
    "default_table_owner = hr"
    "colour_console = true"
  )

  for member in "${sdist_members[@]}"; do
    require_archive_member "${sdist_file}" "${member}" "sdist" || {
      echo "ERROR: Missing expected sample config in sdist: ${member}"
      exit 1
    }
    for sentinel in "${sentinel_lines[@]}"; do
      assert_archive_contains_text "${sdist_file}" "${member}" "sdist" "${sentinel}" || {
        echo "ERROR: Incomplete sample config in sdist: ${member} is missing '${sentinel}'."
        exit 1
      }
    done
  done

  require_archive_member "${wheel_file}" "${wheel_member}" "wheel" || {
    echo "ERROR: Missing expected sample config in wheel: ${wheel_member}"
    exit 1
  }
  for sentinel in "${sentinel_lines[@]}"; do
    assert_archive_contains_text "${wheel_file}" "${wheel_member}" "wheel" "${sentinel}" || {
      echo "ERROR: Incomplete sample config in wheel: ${wheel_member} is missing '${sentinel}'."
      exit 1
    }
  done
}

pushd "${APP_HOME}" >/dev/null

if [ "${SHOW_VERSION:-N}" = "Y" ]; then
  pyproject_version
  popd >/dev/null
  exit 0
fi

if [ -z "${VERSION_TAG:-}" ]; then
  display_usage
fi

POETRY=$(find_poetry)
if [ -z "${POETRY}" ]; then
  echo "ERROR: Poetry is required to package this project."
  exit 1
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

echo "Verifying packaged sample configuration..."
verify_release_samples "${SDIST_FILE}" "${WHEEL_FILE}"

echo
echo "Built artefacts:"
echo "  Wheel : ${WHEEL_FILE}"
echo "  Sdist : ${SDIST_FILE}"

popd >/dev/null
