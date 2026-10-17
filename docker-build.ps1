[CmdletBinding()]
param(
    [string]$Image = "sifar-excel-qa:latest"
)

$ErrorActionPreference = "Stop"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI is missing. Install Docker Desktop with Linux containers."
}
& docker info --format '{{.OSType}}/{{.Architecture}}'
if ($LASTEXITCODE -ne 0) {
    throw "Docker Engine is not ready. Start Docker Desktop in Linux container mode."
}
& docker build --platform linux/amd64 --tag $Image --file (Join-Path $PSScriptRoot "Dockerfile") $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw "Docker build failed (exit $LASTEXITCODE)." }
& docker image inspect $Image --format '{{.Os}}/{{.Architecture}} | entrypoint={{json .Config.Entrypoint}}'
if ($LASTEXITCODE -ne 0) { throw "Built image could not be inspected." }
