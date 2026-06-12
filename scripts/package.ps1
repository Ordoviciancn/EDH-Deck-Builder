param(
    [string]$Name = "edh-deck-builder-agent"
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $root
try {
    $dirty = git status --short
    if ($dirty) {
        throw "Working tree is not clean. Commit or stash changes before packaging."
    }

    python -m unittest discover

    Get-ChildItem -Path . -Recurse -Directory -Filter "__pycache__" |
        Remove-Item -Recurse -Force

    New-Item -ItemType Directory -Force -Path "dist" | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $output = Join-Path "dist" "$Name-$stamp.zip"

    git archive --format=zip --output=$output HEAD
    Write-Host "Package created: $output"
}
finally {
    Pop-Location
}
