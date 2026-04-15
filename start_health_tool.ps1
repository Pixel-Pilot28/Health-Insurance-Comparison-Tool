<#!
.SYNOPSIS
    Launches the Health Plan Tool backend (FastAPI) and frontend (React).

.DESCRIPTION
    Opens dedicated PowerShell windows for the backend and frontend so both stay running.
    The script automatically activates the Python virtual environment if it exists.

.PARAMETER NoBackend
    Skip launching the backend server.

.PARAMETER NoFrontend
    Skip launching the frontend development server.

.PARAMETER Production
    Launch servers in production mode (no auto-reload, multiple workers, serve built frontend).

.PARAMETER SkipFrontendBuild
    When used with -Production, skip running npm install/build and reuse the existing build output.

.PARAMETER BackendWorkers
    Number of uvicorn worker processes to use in production mode (default: 4).

.EXAMPLE
    .\start_health_tool.ps1
    # Starts both backend and frontend servers.

.EXAMPLE
    .\start_health_tool.ps1 -NoFrontend
    # Starts only the backend server.
#>
param(
    [switch]$NoBackend,
    [switch]$NoFrontend,
    [switch]$Production,
    [switch]$SkipFrontendBuild,
    [int]$BackendWorkers = 4
)

function Start-Backend {
    param(
        [string]$BackendDir,
        [string]$VenvActivate,
        [switch]$Production,
        [int]$Workers = 4
    )

    $commandParts = @()
    $commandParts += "Set-Location `"$BackendDir`""

    if (Test-Path $VenvActivate) {
        $commandParts += "& `"$VenvActivate`""
    } else {
        Write-Warning "Virtual environment not found at $VenvActivate. Using system Python."
    }

    if ($Production) {
        $commandParts += "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers $Workers"
    } else {
        $commandParts += "python -m uvicorn main:app --reload --port 8000"
    }
    $backendCommand = $commandParts -join '; '

    Start-Process PowerShell -ArgumentList "-NoExit", "-Command", $backendCommand
    if ($Production) {
        Write-Host "Backend production server launching at http://localhost:8000" -ForegroundColor Green
    } else {
        Write-Host "Backend server launching at http://localhost:8000" -ForegroundColor Green
    }
}

function Start-Frontend {
    param(
        [string]$FrontendDir,
        [switch]$Production,
        [switch]$SkipBuild
    )

    if ($Production) {
        $commandParts = @()
        $commandParts += "Set-Location `"$FrontendDir`""

        if (-not $SkipBuild) {
            $commandParts += "npm install"
            $commandParts += "npm run build"
        } else {
            Write-Host "Skipping frontend build; using existing build output" -ForegroundColor Yellow
        }

        $commandParts += "npx serve@latest -s build -l 3000"
        $frontendCommand = $commandParts -join '; '
        $statusMessage = "Frontend production server launching at http://localhost:3000"
    } else {
        $frontendCommand = "Set-Location `"$FrontendDir`"; npm start"
        $statusMessage = "Frontend launching at http://localhost:3000"
    }

    Start-Process PowerShell -ArgumentList "-NoExit", "-Command", $frontendCommand
    Write-Host $statusMessage -ForegroundColor Cyan
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir 'backend'
$frontendDir = Join-Path $scriptDir 'frontend'
$venvActivate = Join-Path $scriptDir 'venv\Scripts\Activate.ps1'

if (-not $NoBackend) {
    if (-not (Test-Path $backendDir)) {
        Write-Error "Backend directory not found at $backendDir"
    } else {
        Start-Backend -BackendDir $backendDir -VenvActivate $venvActivate -Production:$Production -Workers $BackendWorkers
    }
}

if (-not $NoFrontend) {
    if (-not (Test-Path $frontendDir)) {
        Write-Error "Frontend directory not found at $frontendDir"
    } else {
        Start-Frontend -FrontendDir $frontendDir -Production:$Production -SkipBuild:$SkipFrontendBuild
    }
}

if ($NoBackend -and $NoFrontend) {
    Write-Warning "Both backend and frontend were skipped. No processes started."
}
