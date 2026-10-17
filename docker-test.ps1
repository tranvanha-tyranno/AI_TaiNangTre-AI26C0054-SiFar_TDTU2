[CmdletBinding()]
param([string]$Image = "sifar-excel-qa:latest")

$ErrorActionPreference = "Stop"
$checks = Join-Path $PSScriptRoot "tests"
$smokeRoot = Join-Path $PSScriptRoot ("outputs/docker-smoke/" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $smokeRoot -Force | Out-Null
$inputPath = Join-Path $smokeRoot "input"
$outputPath = Join-Path $smokeRoot "output"
New-Item -ItemType Directory -Path $inputPath, $outputPath -Force | Out-Null
$prepareArgs = @(
    "run", "--rm", "--platform", "linux/amd64", "--network", "none", "--entrypoint", "python",
    "--mount", "type=bind,source=$checks,target=/checks,readonly",
    "--mount", "type=bind,source=$inputPath,target=/fixture",
    $Image, "-c", "import sys; sys.path.insert(0, '/checks'); from test_submission_contract import prepare_input; prepare_input('/fixture')"
)
& docker @prepareArgs
if ($LASTEXITCODE -ne 0) { throw "Failed to prepare the container test fixture." }
$testArgs = @(
    "run", "--rm", "--platform", "linux/amd64", "--network", "none", "--cpus", "6", "--memory", "4g",
    "--entrypoint", "python",
    "--mount", "type=bind,source=$checks,target=/checks,readonly",
    "--mount", "type=bind,source=$inputPath,target=/input,readonly",
    "--mount", "type=bind,source=$outputPath,target=/output",
    "--env", "SUBMISSION_SMOKE_INPUT=/input", "--env", "SUBMISSION_SMOKE_OUTPUT=/output",
    $Image, "-m", "unittest", "discover", "-s", "/checks", "-p", "test_submission_contract.py", "-v"
)
& docker @testArgs
if ($LASTEXITCODE -ne 0) { throw "Container contract test failed." }
Write-Output "Container contract passed. CSV only: $outputPath"
