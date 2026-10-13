param([string]$Study = (Join-Path $PSScriptRoot 'runs/service3500'))
while ($true) {
    try {
        $state = Get-Content -LiteralPath (Join-Path $Study 'state.json') -Raw | ConvertFrom-Json
        $cfg = Get-Content -LiteralPath (Join-Path $Study 'config.json') -Raw | ConvertFrom-Json
        Clear-Host
        Write-Host ("Optimizer: {0:F1}/{1:F1} active minutes | {2}" -f ($state.spent_wall/60),($cfg.budget_seconds/60),$state.stop_reason)
        foreach ($property in $state.jobs.PSObject.Properties) {
            $job = $property.Value
            Write-Host "Trial $($property.Name): $($job.status)"
            if ($job.status -eq 'running') {
                $trialPath = Join-Path $Study "trials/$($property.Name)"
                $seed = Get-Content -LiteralPath (Join-Path $trialPath 'current_seed.json') -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json
                if ($seed) {
                    $progress = Get-Content -LiteralPath (Join-Path $trialPath "$($seed.seed)/progress.json") -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json
                    if ($progress) { Write-Host "  seed $($seed.seed), round $($progress.round)/$($cfg.horizon), alive $($progress.alive)" }
                }
                $process = Get-Process -Id $job.pid -ErrorAction SilentlyContinue
                if ($process) { Write-Host ("  CPU {0:F0}s, RAM {1:F0} MB" -f $process.CPU,($process.WorkingSet64/1MB)) }
            }
        }
    } catch { Write-Host 'Waiting for campaign files...' }
    Write-Host 'Q: close display (run continues). S: stop and save.'
    for ($tick=0; $tick -lt 12; $tick++) {
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true).Key
            if ($key -eq 'Q') { return }
            if ($key -eq 'S') { New-Item -ItemType File -Path (Join-Path $Study 'STOP') -Force | Out-Null }
        }
        Start-Sleep -Milliseconds 250
    }
}
