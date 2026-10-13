param(
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$Study,
    [string[]]$PythonPrefix = @(),
    [ValidateRange(1,32)][int]$Workers = 2
)
$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$studyPath = (Resolve-Path -LiteralPath $Study).Path
if (-not (Test-Path -LiteralPath (Join-Path $studyPath 'config.json'))) { throw 'Initialize the study first.' }
$hasher = [System.Security.Cryptography.SHA256]::Create()
try { $launchId = [BitConverter]::ToString($hasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($studyPath.ToLowerInvariant()))).Replace('-','') }
finally { $hasher.Dispose() }
$launchMutex = [Threading.Mutex]::new($false, "Local\DACO-launch-$launchId")
$acquired = $false
try {
    try { $acquired = $launchMutex.WaitOne(0) }
    catch [Threading.AbandonedMutexException] { $acquired = $true }
    if (-not $acquired) {
        Write-Output 'A launch is already in progress. Opening progress only.'
        return
    }
    Push-Location $repoPath
    try {
        & $Python @PythonPrefix -B (Join-Path $PSScriptRoot 'windows/recover.py') --study $studyPath
        if ($LASTEXITCODE -eq 10) {
            Write-Output 'This study is already running. Opening progress only.'
            return
        }
        if ($LASTEXITCODE -ne 0) { throw 'Study recovery failed; no new controller was started.' }
    } finally { Pop-Location }
    $quotedStudy = '"' + $studyPath + '"'
    $runtimePath = '"' + (Join-Path $PSScriptRoot 'windows/runtime.py') + '"'
    $process = Start-Process -FilePath $Python -ArgumentList ($PythonPrefix + @('-B',$runtimePath,'--study',$quotedStudy,'--workers',$Workers.ToString())) -WorkingDirectory $repoPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $studyPath 'controller.out') -RedirectStandardError (Join-Path $studyPath 'controller.err') -PassThru
    $process.Id | Set-Content -LiteralPath (Join-Path $studyPath 'controller.pid')
    # Keep the launcher mutex until the controller has acquired its own lock.
    for ($attempt=0; $attempt -lt 100; $attempt++) {
        $process.Refresh()
        if ($process.HasExited) { throw "Controller exited. See $studyPath/controller.err" }
        try { $owner = Get-Content -LiteralPath (Join-Path $studyPath 'owner.json') -Raw | ConvertFrom-Json }
        catch { $owner = $null }
        if ($owner -and $owner.pid -eq $process.Id) { break }
        Start-Sleep -Milliseconds 100
    }
    Write-Output "Controller PID $($process.Id). Closing this window leaves it running. Logs: $studyPath"
} finally {
    if ($acquired) { $launchMutex.ReleaseMutex() }
    $launchMutex.Dispose()
}
