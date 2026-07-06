param(
    [string]$JsonOutput = ".claude/tmp/env_status.json"
)

$ErrorActionPreference = "Stop"

function Test-PythonExecutable {
    param([string]$Path)

    if (-not $Path -or -not (Test-Path $Path)) {
        return $false
    }

    $item = Get-Item $Path
    if ($item.Length -eq 0) {
        return $false
    }

    & $Path --version *> $null
    return $LASTEXITCODE -eq 0
}

function Find-PythonExecutable {
    $candidates = @()

    if ($env:PAPER2WECHAT_PYTHON) {
        $candidates += $env:PAPER2WECHAT_PYTHON
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $candidates += $pythonCommand.Source
    }

    $localPrograms = Join-Path $env:LOCALAPPDATA "Programs\Python"
    if (Test-Path $localPrograms) {
        $candidates += Get-ChildItem $localPrograms -Recurse -Filter python.exe -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            ForEach-Object { $_.FullName }
    }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (Test-PythonExecutable $candidate) {
            return $candidate
        }
    }

    return $null
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$python = Find-PythonExecutable
if (-not $python) {
    Write-Error "No executable Python found. Install Python 3.8+ or set PAPER2WECHAT_PYTHON to python.exe."
    exit 1
}

Set-Location $root
& $python ".claude/scripts/check_env.py" --json-output $JsonOutput
exit $LASTEXITCODE
