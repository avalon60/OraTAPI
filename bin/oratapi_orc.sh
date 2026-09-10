#!/usr/bin/env bash
# Author: cbostock / DGGIU
# Created: 10-Sep-2026
# Run profile orchestration from a source checkout with its selected Python.

set -e
task_project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
task_python="${ORATAPI_PYTHON:-}"
if [[ -z "$task_python" ]]; then
    for task_candidate in "$task_project_dir/.venv/bin/python" "$task_project_dir/venv/bin/python"; do
        if [[ -x "$task_candidate" ]]; then
            task_python="$task_candidate"
            break
        fi
    done
fi
if [[ -z "$task_python" ]]; then
    task_python="$(command -v python3 || command -v python)"
fi
export PYTHONPATH="$task_project_dir/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$task_python" -m oratapi.controller.oratapi_orc "$@"
