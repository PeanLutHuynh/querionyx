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
    Write-Host "  .\\run.ps1 up        # Start Docker services"
    Write-Host "  .\\run.ps1 down      # Stop Docker services"
    Write-Host "  .\\run.ps1 restart   # Restart Docker services"
    Write-Host "  .\\run.ps1 ps        # Show service status"
    Write-Host "  .\\run.ps1 logs      # Show recent docker logs"
    Write-Host "  .\\run.ps1 test      # Run test_connection.py"
    Write-Host "  .\\run.ps1 api       # Run FastAPI app if available"
    Write-Host "  .\\run.ps1 help      # Show this help"
}

function Ensure-DockerCli {
    $dockerComposeCmd = Get-Command docker-compose -ErrorAction SilentlyContinue
    if (-not $dockerComposeCmd) {
        $dockerPath = "C:\Program Files\Docker\Docker\resources\bin"
        if (Test-Path $dockerPath) {
            $env:Path += ";$dockerPath"
        }
    }

    $dockerComposeCmd = Get-Command docker-compose -ErrorAction SilentlyContinue
    if (-not $dockerComposeCmd) {
        throw "docker-compose not found. Install Docker Desktop and try again."
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
    switch ($Action) {
        "up" {
            Ensure-DockerCli
            docker-compose up -d
            docker-compose ps
        }
        "down" {
            Ensure-DockerCli
            docker-compose down
        }
        "restart" {
            Ensure-DockerCli
            docker-compose down
            docker-compose up -d
            docker-compose ps
        }
        "ps" {
            Ensure-DockerCli
            docker-compose ps
        }
        "logs" {
            Ensure-DockerCli
            docker-compose logs --tail=80
        }
        "test" {
            $pythonExe = Ensure-VenvPython
            & $pythonExe "test_connection.py"
        }
        "api" {
            $pythonExe = Ensure-VenvPython
            $apiEntry = Join-Path $PSScriptRoot "src\api\main.py"
            if (-not (Test-Path $apiEntry)) {
                Write-Host "src/api/main.py not found yet. API entrypoint chưa được tạo."
                exit 0
            }
            & $pythonExe -m uvicorn src.api.main:app --host 0.0.0.0 --port 8080 --reload
        }
        default {
            Write-Usage
        }
    }
}
finally {
    Pop-Location
}
