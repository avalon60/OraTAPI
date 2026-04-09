##############################################################################
# Author: Clive Bostock
#   Date: 27 Jan 2024
#   Name: freeze.ps1
#  Descr: Generates requirements.txt from the Poetry lock file
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

    throw "Poetry is required to export requirements.txt."
}

# Resolve the script's path and directories
$PROG_PATH = (Get-Item -Path $MyInvocation.MyCommand.Definition).FullName
$PROG_DIR = Split-Path -Path $PROG_PATH -Parent
$APP_HOME = Split-Path -Path $PROG_DIR -Parent

# Change to APP_HOME directory
Set-Location -Path $APP_HOME

$poetry = Get-PoetryCommand
& $poetry export --format requirements.txt --without-hashes --only main --output requirements.txt

# Notify the user
Write-Host "requirements.txt has been generated successfully." -ForegroundColor Green
