##############################################################################
# Author: Clive Bostock
#   Date: 1 Dec 2022 (A Merry Christmas to one and all! :o)
#   Name: freeze.bat
#  Descr: Generates a Pyython requirements.txt file
##############################################################################
PROG_PATH=$(realpath "$0")
PROG_DIR=$(dirname "${PROG_PATH}")
APP_HOME=$(dirname "${PROG_DIR}")

pushd "${APP_HOME}" || { echo "Failed to switch to APP_HOME"; exit 1; }

# Source utils.env - this includes the source_venv function.
source utils/utils.env
source_venv
pip freeze | grep -v "apt-clone" > requirements.txt

# if [ -f pyproject.toml ]
# then
#  utils/sync_requirements.sh
#fi
