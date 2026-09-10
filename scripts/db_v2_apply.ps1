<#
.SYNOPSIS
  Aplica o DDL v2 (database/v2/*.sql) e, opcionalmente, o seed sintético,
  contra um banco cujo nome contenha "_test". Fail-fast: para no primeiro
  erro e não tenta mascará-lo.

.PARAMETER EnvFile
  Arquivo local com PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD (gerado
  por scripts/db_v2_create_test.ps1). Nunca versionado.

.PARAMETER WithSeed
  Se presente, também aplica database/v2/seeds/001_demo_allocation.sql
  (dados 100% sintéticos) em uma única transação.
#>
param(
    [string]$EnvFile = ".env.pricing_v2_test",
    [switch]$WithSeed,
    [string]$PsqlBin = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) {
    Write-Error "Arquivo de ambiente '$EnvFile' nao encontrado. Rode scripts/db_v2_create_test.ps1 primeiro."
    exit 1
}

Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $parts = $_ -split '=', 2
    if ($parts.Length -eq 2) {
        [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

if ($env:PGDATABASE -notmatch "_test") {
    Write-Error "Recusado: PGDATABASE '$($env:PGDATABASE)' nao contem '_test'."
    exit 1
}

if (-not $PsqlBin) {
    $found = Get-Command psql -ErrorAction SilentlyContinue
    if ($found) { $PsqlBin = $found.Source }
}
if (-not $PsqlBin -or -not (Test-Path $PsqlBin)) {
    Write-Error "psql nao encontrado. Passe -PsqlBin com o caminho completo do executavel."
    exit 1
}

$ddlFiles = @(
    "database/v2/001_schemas.sql",
    "database/v2/002_core.sql",
    "database/v2/003_pricing.sql",
    "database/v2/004_audit.sql",
    "database/v2/005_market_foundation.sql",
    "database/v2/006_indexes.sql",
    "database/v2/007_views.sql",
    "database/v2/008_ingestion.sql",
    "database/v2/009_promotion.sql"
)

foreach ($f in $ddlFiles) {
    Write-Host "Aplicando $f ..."
    & $PsqlBin -v "ON_ERROR_STOP=1" -f $f
    if ($LASTEXITCODE -ne 0) {
        Write-Error "FALHOU ao aplicar $f (exit $LASTEXITCODE) — parando, nada foi mascarado."
        exit 1
    }
}
Write-Host "OK: DDL v2 aplicado sem erro em '$($env:PGDATABASE)'."

if ($WithSeed) {
    $seedFile = "database/v2/seeds/001_demo_allocation.sql"
    Write-Host "Aplicando seed sintetico $seedFile ..."
    & $PsqlBin -v "ON_ERROR_STOP=1" --single-transaction -f $seedFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "FALHOU ao aplicar o seed (exit $LASTEXITCODE) — transacao revertida pelo proprio PostgreSQL."
        exit 1
    }
    Write-Host "OK: seed sintetico aplicado em '$($env:PGDATABASE)'."
}
