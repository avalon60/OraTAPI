##############################################################################
# Author: Clive Bostock
#   Date: 16 Dec 2024 (A Merry Christmas to one and all! :o)
#   Name: build.ps1
#  Descr: Performs a build and install of the project as packages in edit mode).
##############################################################################

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-PoetryCommand {
    if (Get-Command poetry -ErrorAction SilentlyContinue) {
        return "poetry"
    }

    $localPoetry = Join-Path $HOME ".local/bin/poetry"
    if (Test-Path $localPoetry) {
        return $localPoetry
    }

    throw "Poetry is required for development setup."
}

# Function to emulate 'realpath' behavior
function Get-RealPath {
    param (
        [string]$Path
    )
    # Resolve the full path
    if (Test-Path $Path) {
        return (Resolve-Path $Path).Path
    } else {
        throw "Path not found: $Path"
    }
}

# Get script path and directories
$ScriptPath = Get-RealPath $MyInvocation.MyCommand.Path
$ScriptDir = Split-Path -Parent $ScriptPath
$AppHome = Split-Path -Parent $ScriptDir

# Navigate to the application home directory
Push-Location $AppHome
Write-Output "App home: $AppHome"

$poetry = Get-PoetryCommand
& $poetry config virtualenvs.in-project true --local
& $poetry install --sync
