#!/usr/bin/env bash
##############################################################################
# Author: Clive Bostock
#   Date: 16 Dec 2024 (A Merry Christmas to one and all! :o)
#   Name: tree.sh
#  Descr: Get a tree map of the project
##############################################################################
# Use a workaround for realpath if it's not available (possibly not on Mac)
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
PROG_DIR=$(dirname ${PROG_PATH})
APP_HOME=$(dirname ${PROG_DIR})
pushd ${APP_HOME}
tree -I "dist|logs|venv|staging|*egg-info*|.idea|.git|build|*.pyc|*pycache*|*utils*"
