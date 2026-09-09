<#
.SYNOPSIS
  Cria (ou recria) um banco PostgreSQL de TESTE isolado para o schema v2,
  mais uma role dedicada. Genérico — sem senha fixa no script, sem dado
  privado. Falha rápido em qualquer erro.

.DESCRIPTION
  Requer que o servidor PostgreSQL já esteja rodando (não instala nada).
  Usa o superusuário postgres (via variáveis de ambiente padrão do libpq
  ou .pgpass já configurado no ambiente) só para criar a role/banco de
  teste; a senha da nova role é gerada aleatoriamente nesta execução e
  gravada apenas no arquivo local indicado por -EnvFile (que deve
  permanecer fora do Git — ver .gitignore, padrão .env.*).

  RECUSA operar se -DatabaseName não contiver "_test", para nunca ser
  usado por engano contra um banco que não seja de teste.

.PARAMETER DatabaseName
  Nome do banco de teste a criar. Deve conter "_test".

.PARAMETER RoleName
  Nome da role dona do banco de teste.

.PARAMETER PsqlBin
  Caminho do executável psql. Se omitido, tenta localizar no PATH.

.PARAMETER EnvFile
  Arquivo local (fora do Git) onde as variáveis PGHOST/PGPORT/PGDATABASE/
  PGUSER/PGPASSWORD da nova role serão gravadas.
#>
param(
    [string]$DatabaseName = "patrimar_pricing_v2_test",
    [string]$RoleName = "patrimar_v2_test_owner",
    [string]$PgHost = "localhost",
    [int]$PgPort = 5432,
    [string]$PsqlBin = "",
    [string]$EnvFile = ".env.pricing_v2_test"
)

$ErrorActionPreference = "Stop"

if ($DatabaseName -notmatch "_test") {
    Write-Error "Recusado: DatabaseName '$DatabaseName' nao contem '_test'. Este script so opera em bancos de teste."
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

function Invoke-Psql {
    param([string]$Database, [string]$Sql)
    & $PsqlBin -h $PgHost -p $PgPort -U postgres -d $Database -v "ON_ERROR_STOP=1" -c $Sql
    if ($LASTEXITCODE -ne 0) {
        throw "psql falhou (exit $LASTEXITCODE) executando: $Sql"
    }
}

# gera senha aleatoria local, nunca reutilizada do usuario
Add-Type -AssemblyName System.Web -ErrorAction SilentlyContinue
$bytes = New-Object byte[] 24
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$testPassword = [Convert]::ToBase64String($bytes) -replace '[+/=]', ''

$tmpSql = [System.IO.Path]::GetTempFileName()
try {
    @"
DO `$do`$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$RoleName') THEN
    CREATE ROLE $RoleName LOGIN PASSWORD '$testPassword';
  ELSE
    ALTER ROLE $RoleName PASSWORD '$testPassword';
  END IF;
END
`$do`$;
"@ | Set-Content -Path $tmpSql -Encoding utf8

    & $PsqlBin -h $PgHost -p $PgPort -U postgres -d postgres -v "ON_ERROR_STOP=1" -f $tmpSql
    if ($LASTEXITCODE -ne 0) { throw "falha ao criar/atualizar role $RoleName" }
}
finally {
    Remove-Item -Path $tmpSql -Force -ErrorAction SilentlyContinue
}

Invoke-Psql -Database "postgres" -Sql "DROP DATABASE IF EXISTS $DatabaseName;"
Invoke-Psql -Database "postgres" -Sql "CREATE DATABASE $DatabaseName OWNER $RoleName;"

@"
# Credenciais LOCAIS de teste — NUNCA versionado (ver .gitignore .env.*)
PGHOST=$PgHost
PGPORT=$PgPort
PGDATABASE=$DatabaseName
PGUSER=$RoleName
PGPASSWORD=$testPassword
"@ | Set-Content -Path $EnvFile -Encoding utf8

Write-Host "OK: banco '$DatabaseName' e role '$RoleName' criados. Credenciais em '$EnvFile' (nao versionado)."
