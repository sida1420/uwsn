param([string]$Study = (Join-Path $PSScriptRoot 'runs/ready-expanded'))
$ErrorActionPreference = 'Stop'

function Read-ProgressJson([string]$Path) {
    try { Get-Content -LiteralPath $Path -Raw -ErrorAction Stop | ConvertFrom-Json }
    catch { return $null }
}

while ($true) {
    $state = Read-ProgressJson (Join-Path $Study 'state.json')
    $cfg = Read-ProgressJson (Join-Path $Study 'config.json')
    $owner = Read-ProgressJson (Join-Path $Study 'owner.json')
    $runtime = Read-ProgressJson (Join-Path $Study 'launch-runtime.json')
    $controller = $null
    if ($owner) {
        $candidate = Get-Process -Id $owner.pid -ErrorAction SilentlyContinue
        if ($candidate) {
            $created = ($candidate.StartTime.ToUniversalTime() - [datetime]'1970-01-01').TotalSeconds
            if ([math]::Abs($created - $owner.created) -lt 1) { $controller = $candidate }
        }
    }
    Clear-Host
    Write-Host 'D-ACO live progress' -ForegroundColor Cyan
    Write-Host "Study: $Study"
    Write-Host "Updated: $(Get-Date -Format 'HH:mm:ss') | refresh every 3 seconds"
    if ($state -and $cfg) {
        $complete = @($state.jobs.PSObject.Properties | Where-Object { $_.Name -ne 'reference' -and $_.Value.status -eq 'complete' }).Count
        $hours = $state.spent_wall / 3600
        Write-Host ("Completed configurations: {0}/{1} | Active time: {2:F2}/{3} hours" -f $complete,$cfg.max_trials,$hours,$cfg.max_wall_hours)
        $activity = if ($controller) { 'RUNNING' } else { 'STOPPED' }
        Write-Host "Controller: $activity | Last recorded reason: $($state.stop_reason)"
        if ($runtime) { Write-Host "Parallel runs: $($runtime.workers) | Session limit: none (overall budget still applies)" }
        Write-Host ''
        foreach ($property in $state.jobs.PSObject.Properties) {
            $job = $property.Value
            if ($job.status -notin @('running','paused','failed')) { continue }
            $jobPath = Join-Path $Study "trials/$($property.Name)"
            $current = Read-ProgressJson (Join-Path $jobPath 'current_seed.json')
            $progress = $null
            if ($current -and $null -ne $current.seed) {
                $progressPath = Join-Path $jobPath "$($current.seed)/progress.json"
                $progress = Read-ProgressJson $progressPath
            }
            $process = $null
            if ($job.pid) { $process = Get-Process -Id $job.pid -ErrorAction SilentlyContinue }
            $line = "Trial $($property.Name): $($job.status)"
            if ($current) { $line += " | seed $($current.seed)" }
            if ($progress) {
                $age = [math]::Max(0, ((Get-Date) - (Get-Item -LiteralPath $progressPath).LastWriteTime).TotalSeconds)
                $line += " | round $($progress.round)/$($cfg.horizon) | alive $($progress.alive) | checkpoint $([int]$age)s ago"
            } else { $line += ' | preparing / waiting for first checkpoint' }
            if ($process) { $line += (" | CPU {0:F0}s | RAM {1:F0} MB" -f $process.CPU,($process.WorkingSet64/1MB)) }
            Write-Host $line
            if ($job.last_error) { Write-Host "  Last error: $($job.last_error)" -ForegroundColor Yellow }
        }
        $best = Get-ChildItem -LiteralPath (Join-Path $Study 'trials') -Filter aggregate.json -Recurse -ErrorAction SilentlyContinue |
            ForEach-Object { Read-ProgressJson $_.FullName } | Where-Object { $_.feasible } |
            Sort-Object mean_service_capped -Descending | Select-Object -First 1
        if ($best) { Write-Host ("Best feasible so far: {0:F1} service rounds | {1:F4} J" -f $best.mean_service_capped,$best.energy_K_mean) }
    } else { Write-Host 'Waiting for study files...' }
    Write-Host ''
    Write-Host 'Rounds update at checkpoints (normally every 25 rounds). Increasing CPU time means the worker is computing.'
    Write-Host 'Q = return/close display (run continues). S = request a graceful stop.'
    for ($tick=0; $tick -lt 12; $tick++) {
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true).Key
            if ($key -eq 'Q') { return }
            if ($key -eq 'S') {
                New-Item -ItemType File -Path (Join-Path $Study 'STOP') -Force | Out-Null
            }
        }
        Start-Sleep -Milliseconds 250
    }
}
