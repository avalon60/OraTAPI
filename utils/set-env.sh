START_DIR=`pwd`
PROJECT_DIR=$(echo ${START_DIR} | sed "s/OraTAPI.*/OraTAPI/")
echo "Project directory: ${PROJECT_DIR}"
pushd ${PROJECT_DIR}
source venv/bin/activate

CTL=$(cd "${PROJECT_DIR}/controller" || exit; pwd)
VIEW=$(cd "${PROJECT_DIR}/view" || exit; pwd)
MDL=$(cd "${PROJECT_DIR}/model" || exit; pwd)
export PYTHONPATH=${PROJECT_DIR}:${LIBS}:${CTL}:${VIEW}:${MDL}${PYTHONPATH}
popd
