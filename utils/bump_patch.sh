#!/usr/bin/env bash
##############################################################################
# Author: Clive Bostock
#   Date: 16 Dec 2024 (A Merry Christmas to one and all! :o)
#   Name: package.sh
#  Descr: Creates an installable package of the project.
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
echo "App home: ${APP_HOME}"
bump2version patch
