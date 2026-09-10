# Author: cbostock / DGGIU
# Created: 10-Sep-2026
# Run profile orchestration from a source checkout and propagate its exit code.

$ErrorActionPreference = 'Stop'
$taskProjectDir = Split-Path -Parent $PSScriptRoot
$taskPython = $env:ORATAPI_PYTHON
if (-not $taskPython) {
    foreach ($taskCandidate in @(
        (Join-Path $taskProjectDir '.venv/Scripts/python.exe'),
        (Join-Path $taskProjectDir 'venv/Scripts/python.exe'),
        (Join-Path $taskProjectDir '.venv/bin/python'),
        (Join-Path $taskProjectDir 'venv/bin/python')
    )) {
        if (Test-Path $taskCandidate) {
            $taskPython = $taskCandidate
            break
        }
    }
}
if (-not $taskPython) {
    $taskCommand = Get-Command python3, python -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $taskCommand) {
        Write-Error 'No Python interpreter found. Set ORATAPI_PYTHON to the project interpreter.'
        exit 1
    }
    $taskPython = $taskCommand.Source
}
$taskPreviousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = (Join-Path $taskProjectDir 'src')
    if ($taskPreviousPythonPath) {
        $env:PYTHONPATH += [IO.Path]::PathSeparator + $taskPreviousPythonPath
    }
    & $taskPython -m oratapi.controller.oratapi_orc @args
    $taskExitCode = $LASTEXITCODE
} finally {
    $env:PYTHONPATH = $taskPreviousPythonPath
}
exit $taskExitCode
