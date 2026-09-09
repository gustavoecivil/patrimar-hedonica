<#
.SYNOPSIS
  Remove (DROP) o banco de teste isolado do schema v2. Existe para uso
  manual futuro — NÃO é executado automaticamente por nenhuma outra
  etapa/fase deste projeto (ver docs/13). Recusa operar em qualquer
  banco cujo nome não contenha "_test".

.PARAMETER DatabaseName
  Nome do banco a remover. Deve conter "_test".
#>
param(
    [string]$DatabaseName = "patrimar_pricing_v2_test",
    [string]$PgHost = "localhost",
    [int]$PgPort = 5432,
    [string]$PsqlBin = ""
)

$ErrorActionPreference = "Stop"

if ($DatabaseName -notmatch "_test") {
    Write-Error "Recusado: DatabaseName '$DatabaseName' nao contem '_test'. Este script nunca remove um banco fora do padrao de teste."
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

$env:PGCONNECT_TIMEOUT = "5"
& $PsqlBin -h $PgHost -p $PgPort -U postgres -d postgres -v "ON_ERROR_STOP=1" -c "DROP DATABASE IF EXISTS $DatabaseName;"
if ($LASTEXITCODE -ne 0) {
    Write-Error "FALHOU ao remover '$DatabaseName' (exit $LASTEXITCODE)."
    exit 1
}
Write-Host "OK: banco de teste '$DatabaseName' removido."
