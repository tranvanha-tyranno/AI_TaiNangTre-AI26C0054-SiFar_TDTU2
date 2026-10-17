# Argument-wiring checks; the actual Linux container is tested by docker-test.ps1.
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
foreach ($name in @('docker-build.ps1', 'docker-run.ps1', 'docker-test.ps1')) {
    $tokens = $null
    $parseErrors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile(
        (Join-Path $projectRoot $name), [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors.Count) { throw "PowerShell syntax error in ${name}: $parseErrors" }
}
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ("docker-args-" + [Guid]::NewGuid().ToString('N'))
$dataset = Join-Path $testRoot 'data with spaces'
$resultDir = Join-Path $testRoot 'result with spaces'
New-Item -ItemType Directory -Path (Join-Path $dataset 'xlsx_files') -Force | Out-Null
Set-Content -LiteralPath (Join-Path $dataset 'queries.json') -Value '[]' -Encoding UTF8
$envFile = Join-Path $testRoot 'local.env'
Set-Content -LiteralPath $envFile -Value 'OPENROUTER_API_KEY="synthetic-key"' -Encoding UTF8
$global:submissionTestDockerArgs = $null
function global:docker {
    $global:LASTEXITCODE = 0
    if ($args[0] -eq 'info') { Write-Output 'linux/x86_64'; return }
    $global:submissionTestDockerArgs = @($args)
    New-Item -ItemType Directory -Path $resultDir -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $resultDir 'submission.csv') -Value "id,answer`n1,ok" -Encoding UTF8
}
try {
    & (Join-Path $projectRoot 'docker-run.ps1') -DatasetDir $dataset -OutputDir $resultDir -OpenRouterKey '' -EnvFile $envFile -Concurrency 2
    $received = $global:submissionTestDockerArgs
    if ($received[0] -ne 'run') { throw 'Expected docker run.' }
    foreach ($pair in @(@('--xlsx-dir','/input/xlsx_files'), @('--queries','/input/queries.json'),
                        @('--output','/output/submission.csv'), @('--openrouter-key','synthetic-key'),
                        @('--openrouter-model','qwen/qwen3.7-flash'), @('--openrouter-base-url','https://openrouter.ai/api/v1'),
                        @('--concurrency','2'))) {
        $index = [array]::IndexOf($received, $pair[0])
        if ($index -lt 0 -or $received[$index + 1] -ne $pair[1]) { throw "Wrong argument: $($pair[0])" }
    }
    if (-not ($received -contains "type=bind,source=$dataset,target=/input,readonly")) {
        throw 'Input bind mount is not readonly or a path with spaces was split.'
    }
    if (-not ($received -contains "type=bind,source=$resultDir,target=/output")) { throw 'Wrong output mount.' }
    Write-Output 'PowerShell syntax, .env key loading and six argument wiring passed.'
} finally {
    Remove-Item Function:\docker -ErrorAction SilentlyContinue
    Remove-Variable submissionTestDockerArgs -Scope Global -ErrorAction SilentlyContinue
    # Keep tiny fixtures in the temp directory for inspection on failure.
}

# Windows PowerShell -File evaluates parameter defaults differently from
# invoking & script.ps1. Defaults must resolve after entering the script body.
$savedApiKey = $env:OPENROUTER_API_KEY
try {
    $env:OPENROUTER_API_KEY = ''
    $missingEnvFile = Join-Path $testRoot 'not-created.env'
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $failureText = (& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $projectRoot 'docker-run.ps1') -EnvFile $missingEnvFile 2>&1 | Out-String)
    $failureCode = $LASTEXITCODE
    $ErrorActionPreference = $oldPreference
    if ($failureCode -eq 0 -or $failureText -notmatch 'Set.*OPENROUTER_API_KEY' -or $failureText -match 'empty string') {
        throw 'The one-command -File invocation did not resolve script-relative defaults correctly.'
    }
    Write-Output 'Windows PowerShell -File defaults passed.'
} finally {
    $env:OPENROUTER_API_KEY = $savedApiKey
}
