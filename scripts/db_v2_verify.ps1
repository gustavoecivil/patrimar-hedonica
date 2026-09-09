<#
.SYNOPSIS
  Executa scripts/verify_postgres_v2.py contra o banco de teste indicado
  por -EnvFile, comparando com fixtures/v2/reference_allocation_expected.json.

.PARAMETER EnvFile
  Arquivo local com PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD. Nunca
  versionado. Recusa operar se PGDATABASE nao contiver "_test".
#>
param(
    [string]$EnvFile = ".env.pricing_v2_test",
    [string]$Expected = "fixtures/v2/reference_allocation_expected.json",
    [string]$PythonBin = "python",
    [string]$PsqlBin = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) {
    Write-Error "Arquivo de ambiente '$EnvFile' nao encontrado."
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
if ($PsqlBin) {
    $env:PSQL_BIN = $PsqlBin
}

& $PythonBin scripts/verify_postgres_v2.py --expected $Expected
exit $LASTEXITCODE
