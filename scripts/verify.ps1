$ErrorActionPreference = 'Stop'

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$manifestPath = Join-Path $repositoryRoot 'examples\resilient-batch\Cargo.toml'
$sqlDirectory = (Resolve-Path (Join-Path $repositoryRoot 'sql')).Path
$containerName = "stockbot-case-study-pg-$PID"
$containerStarted = $false
$verificationError = $null
$cleanupError = $null

function Assert-NativeSuccess {
    param([string]$Step)

    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

try {
    python (Join-Path $PSScriptRoot 'privacy_guard.py') $repositoryRoot
    Assert-NativeSuccess 'privacy guard'

    python (Join-Path $PSScriptRoot 'check_markdown_links.py') $repositoryRoot
    Assert-NativeSuccess 'Markdown link check'

    cargo fmt --manifest-path $manifestPath --check
    Assert-NativeSuccess 'cargo fmt'

    cargo clippy --manifest-path $manifestPath --all-targets -- -D warnings
    Assert-NativeSuccess 'cargo clippy'

    cargo test --manifest-path $manifestPath
    Assert-NativeSuccess 'cargo test'

    docker run --detach --rm `
        --name $containerName `
        --env POSTGRES_HOST_AUTH_METHOD=trust `
        postgres:16-alpine | Out-Null
    Assert-NativeSuccess 'start PostgreSQL container'
    $containerStarted = $true

    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        docker exec $containerName pg_isready -U postgres | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    }

    if (-not $ready) {
        throw 'PostgreSQL did not become ready within 30 seconds'
    }

    docker cp "$sqlDirectory\." "${containerName}:/work"
    Assert-NativeSuccess 'copy synthetic SQL fixtures'

    docker exec $containerName `
        psql -U postgres -v ON_ERROR_STOP=1 -f /work/test-weekly-aggregation.sql
    Assert-NativeSuccess 'PostgreSQL regression test'

}
catch {
    $verificationError = $_
}

if ($containerStarted) {
    docker rm --force $containerName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $cleanupError = "remove PostgreSQL container failed with exit code $LASTEXITCODE"
    }
}

if ($null -ne $verificationError) {
    throw $verificationError
}

if ($null -ne $cleanupError) {
    throw $cleanupError
}

Write-Output 'All case-study checks passed, including container cleanup.'
