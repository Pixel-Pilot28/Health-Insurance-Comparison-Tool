<#
.SYNOPSIS
    Stops the Health Plan Tool backend and frontend processes.

.DESCRIPTION
    Searches for running PowerShell windows or processes launched by the startup script
    (uvicorn backend server and npm frontend dev server) and terminates them.

.PARAMETER Force
    Forcefully terminate matching processes without confirmation.

.PARAMETER DryRun
    Show which processes would be stopped without terminating them.

.EXAMPLE
    .\stop_health_tool.ps1
    # Prompts before stopping each matching process.

.EXAMPLE
    .\stop_health_tool.ps1 -Force
    # Immediately stops all matching processes.

.EXAMPLE
    .\stop_health_tool.ps1 -DryRun
    # Displays the processes that would be stopped.
#>
param(
    [switch]$Force,
    [switch]$DryRun
)

function Get-TargetProcesses {
    $patterns = @(
        'uvicorn main:app',
        'python -m uvicorn',
        'npm start',
        'react-scripts start',
        'npx serve',
        'serve@latest -s build'
    )

    $processes = Get-CimInstance Win32_Process |
        Where-Object {
            $cmd = $_.CommandLine
            if (-not $cmd) { return $false }
            foreach ($pattern in $patterns) {
                if ($cmd -like "*$pattern*") { return $true }
            }
            return $false
        }

    return $processes
}

$targets = Get-TargetProcesses

if (-not $targets) {
    Write-Host "No backend/frontend processes found." -ForegroundColor Yellow
    return
}

foreach ($proc in $targets) {
    $info = "[{0}] {1}" -f $proc.ProcessId, $proc.CommandLine

    if ($DryRun) {
        Write-Host "Would stop: $info"
        continue
    }

    if ($Force) {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped: $info" -ForegroundColor Red
    } else {
        $answer = Read-Host "Stop $info ? (Y/N)"
        if ($answer -match '^[Yy]') {
            Stop-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
            Write-Host "Stopped: $info" -ForegroundColor Red
        } else {
            Write-Host "Skipped: $info" -ForegroundColor Gray
        }
    }
}
