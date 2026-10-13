param([string]$Study)
if (-not $Study) {
    $selectionPath = Join-Path $PSScriptRoot 'active-study.json'
    if (Test-Path -LiteralPath $selectionPath) {
        $Study = Join-Path $PSScriptRoot ((Get-Content -LiteralPath $selectionPath -Raw | ConvertFrom-Json).study)
    } else { $Study = Join-Path $PSScriptRoot 'runs/service3500' }
}
while ($true) {
    $controllerRunning = $false
    try {
        $state = Get-Content -LiteralPath (Join-Path $Study 'state.json') -Raw | ConvertFrom-Json
        $cfg = Get-Content -LiteralPath (Join-Path $Study 'config.json') -Raw | ConvertFrom-Json
        $controllerRunning = $false
        $ownerPath = Join-Path $Study 'owner.json'
        if (Test-Path -LiteralPath $ownerPath) {
            $owner = Get-Content -LiteralPath $ownerPath -Raw | ConvertFrom-Json
            $controller = Get-Process -Id $owner.pid -ErrorAction SilentlyContinue
            if ($controller) {
                $created = ($controller.StartTime.ToUniversalTime() - [datetime]'1970-01-01').TotalSeconds
                $controllerRunning = [math]::Abs($created - $owner.created) -lt 1
            }
        }
        Clear-Host
        Write-Host ("Optimizer: {0:F1}/{1:F1} active minutes | {2}" -f ($state.spent_wall/60),($cfg.budget_seconds/60),$state.stop_reason)
        $referencePath = Join-Path $Study 'reference.json'
        if (Test-Path -LiteralPath $referencePath) {
            $reference = Get-Content -LiteralPath $referencePath -Raw | ConvertFrom-Json
            Write-Host "Energy window: $($reference.energy_window) rounds | limit $($cfg.energy_window) | +2% of matched SimpleACO"
        } else { Write-Host 'Energy window: waiting for the reference cohort' }
        if (-not $controllerRunning) { Write-Host 'Controller stopped. No optimization is running.' -ForegroundColor Yellow }
        if ($state.error) { Write-Host $state.error -ForegroundColor Red }
        elseif ($state.stop_reason -eq 'controller_error') {
            $errorPath = Join-Path $Study 'controller.err'
            if (Test-Path -LiteralPath $errorPath) { Get-Content -LiteralPath $errorPath -Tail 1 | Write-Host -ForegroundColor Red }
        }
        foreach ($property in $state.jobs.PSObject.Properties) {
            $job = $property.Value
            $displayStatus = if ($job.status -eq 'running' -and -not $controllerRunning) { 'stopped (stale running status)' } else { $job.status }
            Write-Host "Trial $($property.Name): $displayStatus"
            if ($job.status -eq 'running' -and $controllerRunning) {
                $trialPath = Join-Path $Study "trials/$($property.Name)"
                $seed = Get-Content -LiteralPath (Join-Path $trialPath 'current_seed.json') -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json
                if ($seed) {
                    $progress = Get-Content -LiteralPath (Join-Path $trialPath "$($seed.seed)/progress.json") -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json
                    if ($progress) { Write-Host "  seed $($seed.seed), round $($progress.round)/$($cfg.horizon), alive $($progress.alive)" }
                }
                $process = if ($job.pid) { Get-Process -Id $job.pid -ErrorAction SilentlyContinue } else { $null }
                if ($process) { Write-Host ("  CPU {0:F0}s, RAM {1:F0} MB" -f $process.CPU,($process.WorkingSet64/1MB)) }
            }
        }
    } catch { Write-Host "Unable to read progress: $($_.Exception.Message)" -ForegroundColor Yellow }
    if ($controllerRunning) { Write-Host 'Q: close display (run continues). S: stop and save.' }
    else { Write-Host 'Q: close display. Controller is stopped.' }
    for ($tick=0; $tick -lt 12; $tick++) {
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true).Key
            if ($key -eq 'Q') { return }
            if ($key -eq 'S') { New-Item -ItemType File -Path (Join-Path $Study 'STOP') -Force | Out-Null }
        }
        Start-Sleep -Milliseconds 250
    }
}
