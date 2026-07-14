param(
    [switch]$Dependencies,
    [switch]$ResearchCache
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Remove-WorkspacePath {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    if (-not $resolved.StartsWith($root + [IO.Path]::DirectorySeparatorChar)) {
        throw "Refusing to remove path outside workspace: $resolved"
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
    Write-Host "Removed $($resolved.Substring($root.Length + 1))"
}

$targets = @(
    (Join-Path $root "frontend\.next"),
    (Join-Path $root "frontend\.vercel"),
    (Join-Path $root ".pytest_cache"),
    (Join-Path $root "metrics"),
    (Join-Path $root "profiling")
)

Get-ChildItem -LiteralPath $root -Directory -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "__pycache__" } |
    ForEach-Object { $targets += $_.FullName }

if ($Dependencies) {
    $targets += Join-Path $root ".venv"
    $targets += Join-Path $root "venv"
    $targets += Join-Path $root "frontend\node_modules"
}

if ($ResearchCache) {
    $targets += Join-Path $root "data\models"
    $targets += Join-Path $root "data\chroma_db"
}

$targets | Select-Object -Unique | ForEach-Object { Remove-WorkspacePath -Path $_ }
