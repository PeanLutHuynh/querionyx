param(
    [Parameter(Position = 0)]
    [ValidateSet("up", "down", "restart", "ps", "logs", "test", "api", "help")]
    [string]$Action = "help"
)

$ErrorActionPreference = "Stop"

function Write-Usage {
    Write-Host "Querionyx Command Runner"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\\run.ps1 up        # Start the local full-stack Docker demo"
    Write-Host "  .\\run.ps1 down      # Stop the local Docker demo"
    Write-Host "  .\\run.ps1 restart   # Restart the local Docker demo"
    Write-Host "  .\\run.ps1 ps        # Show service status"
    Write-Host "  .\\run.ps1 logs      # Show recent docker logs"
    Write-Host "  .\\run.ps1 test      # Run the focused backend tests"
    Write-Host "  .\\run.ps1 api       # Run the FastAPI backend locally"
    Write-Host "  .\\run.ps1 help      # Show this help"
}

function Ensure-DockerCli {
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCmd) {
        throw "docker not found. Install Docker Desktop and try again."
    }

    docker compose version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose v2 is required. Update Docker Desktop and try again."
    }
}

function Ensure-VenvPython {
    $pythonPath = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
    if (-not (Test-Path $pythonPath)) {
        $pythonPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    }
    if (-not (Test-Path $pythonPath)) {
        throw "Python venv not found. Expected venv\\Scripts\\python.exe or .venv\\Scripts\\python.exe"
    }
    return $pythonPath
}

Push-Location $PSScriptRoot
try {
    $composeFile = Join-Path $PSScriptRoot "deployment\docker\docker-compose.full-stack.yml"
    switch ($Action) {
        "up" {
            Ensure-DockerCli
            docker compose -f $composeFile up -d
            docker compose -f $composeFile ps
        }
        "down" {
            Ensure-DockerCli
            docker compose -f $composeFile down
        }
        "restart" {
            Ensure-DockerCli
            docker compose -f $composeFile down
            docker compose -f $composeFile up -d
            docker compose -f $composeFile ps
        }
        "ps" {
            Ensure-DockerCli
            docker compose -f $composeFile ps
        }
        "logs" {
            Ensure-DockerCli
            docker compose -f $composeFile logs --tail=80
        }
        "test" {
            $pythonExe = Ensure-VenvPython
            & $pythonExe -m unittest tests.test_db_connect tests.test_fast_sql_planner
        }
        "api" {
            $pythonExe = Ensure-VenvPython
            & $pythonExe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
        }
        default {
            Write-Usage
        }
    }
}
finally {
    Pop-Location
}
