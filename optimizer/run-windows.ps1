$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$studyPath = Join-Path $PSScriptRoot 'runs/service3500'
$selectionPath = Join-Path $PSScriptRoot 'active-study.json'
if (Test-Path -LiteralPath $selectionPath) {
    $selection = Get-Content -LiteralPath $selectionPath -Raw | ConvertFrom-Json
    $studyPath = Join-Path $PSScriptRoot $selection.study
}
$python = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Bundled Python is missing; use the manual README commands.' }
while ($true) {
    Clear-Host
    Write-Host 'D-ACO optimizer: 3500 rounds; 90-minute admission cutoff'
    Write-Host 'At cutoff, active trials finish all seeds. Total time may exceed 90 minutes.'
    Write-Host "Study: $(Split-Path -Leaf $studyPath)"
    Write-Host '1. Start/resume (launches the campaign)'
    Write-Host '2. Live progress'
    Write-Host '3. Stop and save'
    Write-Host '4. Report'
    Write-Host '5. Exit'
    Write-Host '6. Prepare a new campaign for the current map (does not start it)'
    $choice = Read-Host 'Choose 1-6'
    if ($choice -eq '5') { return }
    if ($choice -eq '6') {
        $ownerPath = Join-Path $studyPath 'owner.json'
        if (Test-Path -LiteralPath $ownerPath) {
            $owner = Get-Content -LiteralPath $ownerPath -Raw | ConvertFrom-Json
            if (Get-Process -Id $owner.pid -ErrorAction SilentlyContinue) {
                Write-Host 'Stop/save the selected campaign and wait for it to stop before creating another.' -ForegroundColor Yellow
                Read-Host 'Press Enter to return'; continue
            }
        }
        $relativeStudy = 'runs/map-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
        $newStudy = Join-Path $PSScriptRoot $relativeStudy
        Push-Location $repoPath
        try {
            & $python -B -m optimizer init --config (Join-Path $PSScriptRoot 'config.example.yaml') --study $newStudy --legacy (Join-Path $PSScriptRoot 'runs/ready-expanded')
            if ($LASTEXITCODE -ne 0) { throw 'Map preparation failed; current campaign remains selected.' }
            @{ study = $relativeStudy } | ConvertTo-Json | Set-Content -LiteralPath $selectionPath
            $studyPath = $newStudy
            Write-Host 'Prepared with a frozen copy of the current map. Choose 1 to start.'
        } catch { Write-Host $_.Exception.Message -ForegroundColor Red }
        finally { Pop-Location }
        Read-Host 'Press Enter to return'; continue
    }
    if ($choice -eq '1') {
        $savedState = Get-Content -LiteralPath (Join-Path $studyPath 'state.json') -Raw | ConvertFrom-Json
        if ($savedState.stop_reason -eq 'reference_not_comparable') {
            Write-Host 'This campaign stopped because SimpleACO could not support its declared energy window.' -ForegroundColor Red
            Write-Host $savedState.error
            Write-Host 'Choose 6 to prepare the current map with the automatic reference window.'
            Read-Host 'Press Enter to return'
            continue
        }
        Write-Host 'To change worker count: press S to stop/save, wait until stopped, then resume.' -ForegroundColor Yellow
        Write-Host 'Fewer workers leave extra trials paused; they resume as slots become available and are not deleted.'
        $ownerFile = Join-Path $studyPath 'owner.json'
        $running = $false
        if (Test-Path -LiteralPath $ownerFile) {
            $owner = Get-Content -LiteralPath $ownerFile -Raw | ConvertFrom-Json
            $candidate = Get-Process -Id $owner.pid -ErrorAction SilentlyContinue
            if ($candidate) {
                $created = ($candidate.StartTime.ToUniversalTime() - [datetime]'1970-01-01').TotalSeconds
                $running = [math]::Abs($created - $owner.created) -lt 1
            }
        }
        if (-not $running) {
            $workers = 0
            do {
                $inputText = Read-Host 'Parallel runs (1-4; Enter uses 2)'
                if ([string]::IsNullOrWhiteSpace($inputText)) { $workers = 2 }
                else { [int]::TryParse($inputText,[ref]$workers) | Out-Null }
            } while ($workers -lt 1 -or $workers -gt 4)
            $quotedStudy = '"' + $studyPath + '"'
            $process = Start-Process -FilePath $python -ArgumentList @('-B','-m','optimizer','run','--study',$quotedStudy,'--workers',$workers) -WorkingDirectory $repoPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $studyPath 'controller.out') -RedirectStandardError (Join-Path $studyPath 'controller.err') -PassThru
            Write-Host "Campaign supervisor PID $($process.Id). Closing the display leaves it running."
        } else {
            Write-Host 'Campaign is already running. Worker count is unchanged; opening progress only.'
        }
    }
    if ($choice -in @('1','2')) {
        & (Join-Path $PSScriptRoot 'progress-windows.ps1') -Study $studyPath
    } elseif ($choice -in @('3','4')) {
        $command = if ($choice -eq '3') { 'stop' } else { 'report' }
        Push-Location $repoPath
        try { & $python -B -m optimizer $command --study $studyPath }
        finally { Pop-Location }
        Read-Host 'Press Enter to return'
    }
}
