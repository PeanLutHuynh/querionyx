param(
    [Parameter(Position = 0)]
    [ValidateSet("setup", "research-setup", "api", "frontend", "up", "down", "ps", "logs", "test", "check", "assets", "evaluate", "clean", "clean-all", "help")]
    [string]$Action = "help"
)

$ErrorActionPreference = "Stop"

function Write-Usage {
    Write-Host "Querionyx command runner"
    Write-Host ""
    Write-Host "  .\run.ps1 setup           Install the lightweight API runtime"
    Write-Host "  .\run.ps1 research-setup  Install optional RAG/evaluation packages"
    Write-Host "  .\run.ps1 api             Start FastAPI on http://localhost:8000"
    Write-Host "  .\run.ps1 frontend        Start Next.js on http://localhost:3000"
    Write-Host "  .\run.ps1 up              Build and start backend + frontend with Docker"
    Write-Host "  .\run.ps1 test            Run focused Python regression tests"
    Write-Host "  .\run.ps1 check           Run compile, tests, readiness, and lock checks"
    Write-Host "  .\run.ps1 assets          Regenerate thesis-safe figures and tables"
    Write-Host "  .\run.ps1 evaluate        Run every frozen experiment and regenerate assets"
    Write-Host "  .\run.ps1 clean           Remove build and runtime caches"
    Write-Host "  .\run.ps1 clean-all       Also remove environments, models, and vector indexes"
}

function Get-BootstrapPython {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @("py", "-3.12")
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "Python 3.12 is required. Install it and retry."
    }
    return @($python.Source)
}

function Ensure-VenvPython {
    $pythonPath = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        $bootstrap = Get-BootstrapPython
        if ($bootstrap.Count -eq 2) {
            & $bootstrap[0] $bootstrap[1] -m venv .venv
        } else {
            & $bootstrap[0] -m venv .venv
        }
    }
    return $pythonPath
}

function Ensure-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker Desktop with Compose v2 is required."
    }
    docker compose version | Out-Null
}

function Invoke-PythonCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Python,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: $($Arguments -join ' ')"
    }
}

function Ensure-ResearchPython {
    $python = Ensure-VenvPython
    & $python -c "import chromadb, langchain_ollama, matplotlib, sentence_transformers" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Invoke-PythonCommand -Python $python -Arguments @("-m", "pip", "install", "--upgrade", "pip")
        Invoke-PythonCommand -Python $python -Arguments @("-m", "pip", "install", "-r", "requirements-research.txt")
    }
    return $python
}

Push-Location $PSScriptRoot
try {
    switch ($Action) {
        "setup" {
            $python = Ensure-VenvPython
            Invoke-PythonCommand -Python $python -Arguments @("-m", "pip", "install", "--upgrade", "pip")
            Invoke-PythonCommand -Python $python -Arguments @("-m", "pip", "install", "-r", "requirements.txt")
        }
        "research-setup" {
            $python = Ensure-VenvPython
            Invoke-PythonCommand -Python $python -Arguments @("-m", "pip", "install", "--upgrade", "pip")
            Invoke-PythonCommand -Python $python -Arguments @("-m", "pip", "install", "-r", "requirements-research.txt")
        }
        "api" {
            $python = Ensure-VenvPython
            Invoke-PythonCommand -Python $python -Arguments @("-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload")
        }
        "frontend" {
            Push-Location frontend
            try {
                if (-not (Test-Path -LiteralPath node_modules)) { npm ci }
                npm run dev
            } finally {
                Pop-Location
            }
        }
        "up" {
            Ensure-Docker
            if (-not (Test-Path -LiteralPath .env)) {
                throw "Create .env from .env.example before starting Docker."
            }
            docker compose up --build -d
            docker compose ps
        }
        "down" {
            Ensure-Docker
            docker compose down
        }
        "ps" {
            Ensure-Docker
            docker compose ps
        }
        "logs" {
            Ensure-Docker
            docker compose logs --tail=100
        }
        "test" {
            $python = Ensure-VenvPython
            Invoke-PythonCommand -Python $python -Arguments @("-m", "unittest", "tests.test_db_connect", "tests.test_fast_sql_planner", "tests.test_evaluation_lock", "tests.test_chunk_store", "tests.test_automatic_scoring", "tests.test_hybrid_merge", "tests.test_no_ollama_audit")
        }
        "check" {
            $python = Ensure-VenvPython
            Invoke-PythonCommand -Python $python -Arguments @("-m", "compileall", "-q", "backend", "services", "src", "scripts", "tests")
            Invoke-PythonCommand -Python $python -Arguments @("-m", "unittest", "tests.test_db_connect", "tests.test_fast_sql_planner", "tests.test_evaluation_lock", "tests.test_chunk_store", "tests.test_automatic_scoring", "tests.test_hybrid_merge", "tests.test_no_ollama_audit")
            Invoke-PythonCommand -Python $python -Arguments @("scripts/audit_no_ollama_readiness.py")
            Invoke-PythonCommand -Python $python -Arguments @("scripts/check_project_lock.py")
        }
        "assets" {
            $python = Ensure-ResearchPython
            Invoke-PythonCommand -Python $python -Arguments @("scripts/generate_thesis_assets.py")
        }
        "evaluate" {
            $python = Ensure-ResearchPython
            Invoke-PythonCommand -Python $python -Arguments @("-m", "src.evaluation.benchmark_runner", "--dataset", "benchmarks/datasets/eval_90_queries.json", "--config", "benchmarks/configs/full_v3.json", "--manifest", "benchmarks/manifests/default_manifest.json", "--references", "benchmarks/references/eval_90_sql_references.json", "--output-dir", "reports/experiment_runs/final_90_full_v3")
            Invoke-PythonCommand -Python $python -Arguments @("-m", "src.evaluation.router_stress_test", "--dataset", "benchmarks/datasets/eval_150_queries.json", "--execution-mode", "evaluation_real", "--output-dir", "reports/experiment_runs/final_router_curated_150")
            Invoke-PythonCommand -Python $python -Arguments @("-m", "src.evaluation.router_stress_test", "--dataset", "benchmarks/datasets/router_stress_100.json", "--execution-mode", "evaluation_real", "--output-dir", "reports/experiment_runs/final_router_stress")
            Invoke-PythonCommand -Python $python -Arguments @("-m", "src.evaluation.collect_baseline_outputs", "--execution-mode", "evaluation_real", "--output-dir", "reports/experiment_runs/final_baseline_20")
            Invoke-PythonCommand -Python $python -Arguments @("-m", "src.evaluation.collect_component_outputs", "--output-dir", "reports/experiment_runs/final_component_hybrid_30")
            Invoke-PythonCommand -Python $python -Arguments @("-m", "src.evaluation.benchmark_async_hybrid", "--execution-mode", "evaluation_real", "--output", "reports/experiment_runs/final_async_hybrid")
            Invoke-PythonCommand -Python $python -Arguments @("scripts/generate_thesis_assets.py")
            Invoke-PythonCommand -Python $python -Arguments @("scripts/check_project_lock.py")
        }
        "clean" { & (Join-Path $PSScriptRoot "scripts\clean_workspace.ps1") }
        "clean-all" { & (Join-Path $PSScriptRoot "scripts\clean_workspace.ps1") -Dependencies -ResearchCache }
        default { Write-Usage }
    }
}
finally {
    Pop-Location
}
