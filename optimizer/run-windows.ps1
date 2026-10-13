$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$studyPath = Join-Path $PSScriptRoot 'runs/ready-expanded'

# Prefer the Python runtime already used to prepare this study. Fall back to
# a normal Python installation if the project is moved to another machine.
$bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (Test-Path -LiteralPath $bundledPython) {
    $python = $bundledPython
    $pythonPrefix = @()
} else {
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $python = $pythonCommand.Source
        $pythonPrefix = @()
    } else {
        $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
        if (-not $pyCommand) {
            Write-Host 'Python was not found. Install Python 3.10 or newer, then reopen this launcher.' -ForegroundColor Red
            Read-Host 'Press Enter to close'
            exit 1
        }
        $python = $pyCommand.Source
        $pythonPrefix = @('-3')
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $studyPath 'config.json'))) {
    Write-Host "The prepared study was not found: $studyPath" -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}

function Invoke-Optimizer([string[]]$Arguments) {
    Push-Location $repoPath
    try {
        & $python @pythonPrefix -B -m optimizer @Arguments
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Optimizer exited with code $LASTEXITCODE." -ForegroundColor Red
        } elseif ($Arguments[0] -eq 'report') {
            & $python @pythonPrefix -B (Join-Path $PSScriptRoot 'windows/report_top.py') --study $studyPath
            if ($LASTEXITCODE -ne 0) { Write-Host 'Top-five report generation failed.' -ForegroundColor Red }
        }
    } finally {
        Pop-Location
    }
    Read-Host 'Press Enter to return to the menu'
}

$done = $false
while (-not $done) {
    Clear-Host
    Write-Host 'D-ACO optimizer' -ForegroundColor Cyan
    Write-Host "Study: $studyPath"
    Write-Host "Python: $python"
    Write-Host ''
    Write-Host '1. Run or resume the study'
    Write-Host '2. Show live progress'
    Write-Host '3. Request a graceful stop'
    Write-Host '4. Generate the report'
    Write-Host '5. Exit'
    $choice = Read-Host 'Choose 1-5'
    switch ($choice) {
        '1' {
            $defaultWorkers = (Get-Content -LiteralPath (Join-Path $studyPath 'config.json') -Raw | ConvertFrom-Json).max_workers
            $runtimeFile = Join-Path $studyPath 'launch-runtime.json'
            if (Test-Path -LiteralPath $runtimeFile) {
                $defaultWorkers = (Get-Content -LiteralPath $runtimeFile -Raw | ConvertFrom-Json).workers
            }
            do {
                $workerText = Read-Host "Parallel runs (1-32; Enter uses $defaultWorkers)"
                $workers = 0
                if ([string]::IsNullOrWhiteSpace($workerText)) { $workers = $defaultWorkers }
                elseif (-not [int]::TryParse($workerText, [ref]$workers)) { $workers = 0 }
                if ($workers -lt 1 -or $workers -gt 32) { Write-Host 'Enter a whole number from 1 to 32.' }
            } while ($workers -lt 1 -or $workers -gt 32)
            Write-Host 'No session time limit. The remaining overall time budget still applies.'
            & (Join-Path $PSScriptRoot 'launch.ps1') -Python $python -PythonPrefix $pythonPrefix -Study $studyPath -Workers $workers
            & (Join-Path $PSScriptRoot 'progress-windows.ps1') -Study $studyPath
        }
        '2' { & (Join-Path $PSScriptRoot 'progress-windows.ps1') -Study $studyPath }
        '3' { Invoke-Optimizer @('stop', '--study', $studyPath) }
        '4' { Invoke-Optimizer @('report', '--study', $studyPath) }
        '5' { $done = $true }
        default { Write-Host 'Enter 1, 2, 3, 4 or 5.'; Start-Sleep -Seconds 1 }
    }
}
