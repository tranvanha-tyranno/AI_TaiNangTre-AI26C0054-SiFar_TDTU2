[CmdletBinding()]
param(
    [string]$DatasetDir,
    [string]$OutputDir,
    [string]$Image = "sifar-excel-qa:latest",
    [string]$OpenRouterKey = $env:OPENROUTER_API_KEY,
    [string]$EnvFile,
    [ValidateRange(1, 6)]
    [int]$Concurrency = 1,
    [string]$Model = "qwen/qwen3.7-flash",
    [string]$BaseUrl = "https://openrouter.ai/api/v1"
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($DatasetDir)) { $DatasetDir = Join-Path $PSScriptRoot "input" }
if ([string]::IsNullOrWhiteSpace($OutputDir)) { $OutputDir = Join-Path $PSScriptRoot "output" }
if ([string]::IsNullOrWhiteSpace($EnvFile)) { $EnvFile = Join-Path $PSScriptRoot ".env" }
if ([string]::IsNullOrWhiteSpace($OpenRouterKey) -and (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    foreach ($line in [IO.File]::ReadAllLines((Resolve-Path -LiteralPath $EnvFile).Path)) {
        if ($line -match '^\s*(?:export\s+)?OPENROUTER_API_KEY\s*=\s*(.*)$') {
            $rawValue = $Matches[1].Trim()
            if ($rawValue -match '^"([^\"]*)"' -or $rawValue -match "^'([^']*)'") {
                $OpenRouterKey = $Matches[1]
            } else {
                $OpenRouterKey = ($rawValue -split '\s+#', 2)[0].Trim()
            }
            break
        }
    }
}
if ([string]::IsNullOrWhiteSpace($OpenRouterKey)) {
    throw 'Set $env:OPENROUTER_API_KEY or OPENROUTER_API_KEY in the local .env file.'
}
$datasetPath = (Resolve-Path -LiteralPath $DatasetDir).Path
if (-not (Test-Path -LiteralPath (Join-Path $datasetPath "xlsx_files") -PathType Container)) {
    throw "DatasetDir must contain xlsx_files/."
}
if (-not (Test-Path -LiteralPath (Join-Path $datasetPath "queries.json") -PathType Leaf)) {
    throw "DatasetDir must contain queries.json."
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$outputPath = (Resolve-Path -LiteralPath $OutputDir).Path
$inputPrefix = $datasetPath.TrimEnd([char[]]'\/') + [IO.Path]::DirectorySeparatorChar
if ($outputPath.Equals($datasetPath, [StringComparison]::OrdinalIgnoreCase) -or
    $outputPath.StartsWith($inputPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputDir must be outside DatasetDir to preserve input data."
}
if ($datasetPath.Contains(',') -or $outputPath.Contains(',')) {
    throw "Docker --mount paths must not contain commas."
}
& docker info --format '{{.OSType}}/{{.Architecture}}'
if ($LASTEXITCODE -ne 0) { throw "Docker Engine is not ready. Start Docker Desktop." }
$runArgs = @(
    "run", "--rm", "--platform", "linux/amd64", "--cpus", "6", "--memory", "4g",
    "--mount", "type=bind,source=$datasetPath,target=/input,readonly",
    "--mount", "type=bind,source=$outputPath,target=/output",
    $Image,
    "--xlsx-dir", "/input/xlsx_files",
    "--queries", "/input/queries.json",
    "--output", "/output/submission.csv",
    "--openrouter-key", $OpenRouterKey,
    "--openrouter-model", $Model,
    "--openrouter-base-url", $BaseUrl,
    "--concurrency", "$Concurrency"
)
& docker @runArgs
if ($LASTEXITCODE -ne 0) { throw "Container failed (exit $LASTEXITCODE)." }
$csvPath = Join-Path $outputPath "submission.csv"
if (-not (Test-Path -LiteralPath $csvPath -PathType Leaf)) {
    throw "Container exited without creating submission.csv."
}
Write-Output "Result: $csvPath"
