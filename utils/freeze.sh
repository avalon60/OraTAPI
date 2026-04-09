##############################################################################
# Author: Clive Bostock
#   Date: 1 Dec 2022 (A Merry Christmas to one and all! :o)
#   Name: freeze.bat
#  Descr: Generates requirements.txt from the Poetry lock file
##############################################################################
find_poetry() {
  if command -v poetry >/dev/null 2>&1; then
    echo "poetry"
  elif [ -x "${HOME}/.local/bin/poetry" ]; then
    echo "${HOME}/.local/bin/poetry"
  else
    echo ""
  fi
}

PROG_PATH=$(realpath "$0")
PROG_DIR=$(dirname "${PROG_PATH}")
APP_HOME=$(dirname "${PROG_DIR}")

pushd "${APP_HOME}" || { echo "Failed to switch to APP_HOME"; exit 1; }
POETRY=$(find_poetry)
if [ -z "${POETRY}" ]; then
  echo "Poetry is required to export requirements.txt."
  exit 1
fi
"${POETRY}" export --format requirements.txt --without-hashes --only main --output requirements.txt
