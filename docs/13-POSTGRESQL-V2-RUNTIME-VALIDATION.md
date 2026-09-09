# 13 — Validação em Execução Real (PostgreSQL v2)

Este documento registra a execução **real** do schema v2
(`database/v2/`, Fase 2) e do seed sintético (Fase 2B) contra um
PostgreSQL de verdade, isolado e local — não mais apenas validação
estrutural por parser Python. Não contém senha, connection string ou
qualquer informação privada.

## Ambiente utilizado

- **PostgreSQL 18.4**, `postgres.exe`/`psql.exe` etc., instalado via
  `winget` (pacote `PostgreSQL.PostgreSQL.18`) — instalação **já
  existente** no ambiente antes desta fase (não foi necessário
  instalar nada novo).
- Servidor local, serviço Windows já em execução. Este documento não
  reproduz o caminho de instalação nem qualquer detalhe específico da
  máquina além do necessário para reprodutibilidade conceitual.
- **Banco de teste isolado:** `patrimar_pricing_v2_test`, de
  propriedade de uma role dedicada (`patrimar_v2_test_owner`) criada
  nesta fase com senha gerada aleatoriamente. Credenciais gravadas
  apenas em um arquivo local `.env.pricing_v2_test`, coberto por
  `.gitignore` (padrão `.env.*`), nunca commitado.
- Nenhum outro banco do servidor pré-existente foi lido, alterado ou
  usado como referência — a role de teste só tem privilégio sobre o
  banco de teste que ela mesma possui.

## Segurança

- O servidor PostgreSQL pré-existente tem `listen_addresses = '*'`
  (configuração herdada, **não alterada por esta fase**), mas
  `pg_hba.conf` restringe autenticação por senha a `127.0.0.1/32` e
  `::1/128` — ou seja, na prática, só aceita conexões via loopback,
  independentemente do bind de rede. Esta fase não modificou
  `postgresql.conf` nem `pg_hba.conf`.
- Nenhuma porta foi aberta intencionalmente para fora da máquina por
  esta fase.
- Nenhuma senha foi versionada — verificado por busca textual em todo
  o repositório antes do commit.
- Nenhum arquivo `.env` está rastreado pelo Git.
- Nenhum dado de `data/restricted/` foi lido, usado ou referenciado
  nesta fase.

## Aplicação do DDL

Os 7 arquivos de `database/v2/` foram aplicados, em ordem, com
`psql -v ON_ERROR_STOP=1` (modo fail-fast) contra o banco de teste:
`001_schemas.sql` → `002_core.sql` → `003_pricing.sql` →
`004_audit.sql` → `005_market_foundation.sql` → `006_indexes.sql` →
`007_views.sql`. **Executou sem nenhum erro na primeira tentativa.**

Inventário confirmado de forma independente via `information_schema`/
`pg_catalog` (não apenas pelo parser Python da Fase 2):

| Objeto | Esperado (Fase 2) | Real (PostgreSQL) |
|---|---|---|
| Schemas | 4 | 4 |
| Tabelas (`core`/`pricing`/`audit`/`market`) | 4/12/2/3 = 21 | 4/12/2/3 = 21 |
| Views | 1 | 1 |
| Foreign keys | 34 | 34 |
| Constraints `UNIQUE` | — | 13 |
| Constraints `CHECK` | — | 36 |
| Índices totais (implícitos + explícitos) | — | 59 |

## Aplicação do seed sintético

`database/v2/seeds/001_demo_allocation.sql` aplicado em uma única
transação (`--single-transaction`). **391 `INSERT`s, sem erro.**
Contagens reais por tabela conferem exatamente com o esperado (Fase
2B): 1 empreendimento, 2 torres, 4 tipologias, 40 unidades, 1 cenário,
2 runs, 80 resultados por unidade, 240 ajustes, 1 override.

## Dois defeitos reais encontrados só ao executar de verdade

A validação estrutural (Fase 2/2B) não podia detectar nenhum dos dois
— ambos exigiam um PostgreSQL real:

1. **Empate de `completed_at` entre as duas runs.** O seed usava
   `now()` para os timestamps das duas runs dentro da mesma
   transação — resultando no **mesmo** instante para ambas. A view
   `pricing.v_unit_price_current` (`DISTINCT ON` + `ORDER BY
   completed_at DESC`) não tinha critério de desempate, e resolveu
   para a run errada (sem override) nesta execução. **Corrigido**: o
   seed agora usa timestamps literais e determinísticos, com a run de
   override completando depois da run de sistema; a view ganhou um
   desempate defensivo adicional (`r.id DESC`) para nunca mais
   depender de sorte em caso de empate futuro.
2. **Perda de precisão em `participation_share`.** A coluna
   `NUMERIC(9,6)` arredonda para 6 casas decimais um valor que, em
   memória (Python `Decimal`), tem dezenas de casas — o hash lógico
   calculado a partir do banco não reproduzia o hash calculado
   puramente em Python. O dinheiro (`system_calculated_price`) nunca
   foi afetado — só o hash de verificação, que usava mais precisão do
   que o esquema jamais persiste. **Corrigido**: a função de hash do
   motor de referência agora usa exatamente a mesma precisão da
   coluna (6 casas), porque o hash deve refletir o que é persistido,
   não a precisão interna arbitrária do cálculo em memória.

Ambos os defeitos foram corrigidos no código público/sintético desta
fase (`database/v2/007_views.sql`, `scripts/generate_v2_seed.py`,
`scripts/reference_allocation_engine.py`) — nenhum dado privado
envolvido em nenhum dos dois.

## Validações executadas com sucesso

- **VGV fecha exatamente** via SQL puro: `SUM(system_calculated_price)
  = target_value` para os dois runs (R$ 10.000.000,00 = R$
  10.000.000,00, diferença 0,00).
- **Override**: `SYSTEM_VGV` = R$ 10.000.000,00, impacto do override =
  +R$ 50.000,00, `FINAL_VGV` = R$ 10.050.000,00 — calculado
  diretamente por SQL, não hardcoded.
- **View `pricing.v_unit_price_current`**: 40 linhas, resolve para a
  run mais recente do cenário ativo, reflete o override em
  exatamente 1 unidade, preserva o preço sistemático das demais.
- **Rastreabilidade completa** de uma unidade sintética escolhida
  deterministicamente (torre `TOWER-1`, código `0101`): reconstruído
  via SQL o caminho completo empreendimento → torre → unidade → run →
  cenário → parameter set → calibration sets → ajustes (com
  referência ao parâmetro/calibração exata usada em cada etapa) →
  resultado do sistema → override → validação da run — respondendo
  "por que esta unidade recebeu este preço?" apenas com dado sintético
  já persistido.
- **7 tentativas de inserção inválida, todas rejeitadas** pelo
  PostgreSQL real (cada uma em `BEGIN`/tentativa/`ROLLBACK`, sem
  deixar dado inválido no banco): FK inexistente, preço negativo
  (`CHECK`), status inválido (`CHECK`), `business_key` duplicada
  (`UNIQUE`), override referenciando resultado inexistente (FK
  composta), entrada de calibração duplicada (`UNIQUE`), segundo
  cenário `ACTIVE` para o mesmo empreendimento (índice único parcial).
- **Histórico preservado**: os dois runs coexistem; o preço
  sistemático da unidade com override é **idêntico** nos dois runs
  (nunca sobrescrito); a tabela de overrides tem exatamente 1 linha
  (nunca um `UPDATE`); `parameter_set`/`calibration_sets` permanecem
  referenciáveis por ambos os runs; a view mostra só o estado atual
  (40 linhas) sem apagar o histórico completo (80 linhas em
  `unit_price_results`).

## Determinismo ponta a ponta

`scripts/verify_postgres_v2.py` conecta ao banco real, reconstrói a
mesma estrutura de dados do motor de referência a partir dos dados
persistidos, recalcula o hash lógico com a mesma função
(`reference_allocation_engine.logical_hash`), e compara com
`fixtures/v2/reference_allocation_expected.json`. Resultado, após as
correções acima:

```
hash_from_db = f065d10503bd9ca6480fc920baf3e5519ef4ef55036e95766574b80dfb49082f
hash_expected = f065d10503bd9ca6480fc920baf3e5519ef4ef55036e95766574b80dfb49082f
```

**Idênticos.**

## Teste de recriação (idempotência do ambiente, não do seed)

Ciclo completo executado **duas vezes**: `DROP DATABASE` → `CREATE
DATABASE` → aplicar os 7 arquivos de DDL → aplicar o seed → validar.
Nas duas vezes, DDL e seed aplicaram sem erro, e a segunda vez
reproduziu exatamente os mesmos resultados lógicos (mesmo hash) da
primeira. O seed em si **não** foi projetado para ser re-executado
duas vezes no mesmo banco sem recriar (geraria violação de chave
única, comportamento esperado e documentado — não é o cenário
testado aqui).

## Scripts criados

- `scripts/verify_postgres_v2.py` — conecta via `psql` (subprocesso,
  saída `--csv`), sem depender de `psycopg2` (não disponível no
  ambiente); credenciais só por variável de ambiente, nunca no código.
- `scripts/db_v2_create_test.ps1` / `db_v2_apply.ps1` /
  `db_v2_verify.ps1` / `db_v2_drop_test.ps1` — wrappers PowerShell
  genéricos. Os três que podem alterar dados **recusam operar** se o
  nome do banco não contiver `_test` (testado explicitamente: uma
  tentativa contra um nome sem `_test` foi rejeitada com erro,
  antes de qualquer tentativa de conexão destrutiva).

## Estado final desta fase

O banco `patrimar_pricing_v2_test` **permanece ativo** localmente
(não foi removido) para a próxima fase — ver [[99-HANDOFF]]. O script
de remoção existe (`db_v2_drop_test.ps1`) mas não foi executado como
parte do encerramento desta fase.

## Limitações

- Esta validação usa um servidor PostgreSQL de desenvolvimento
  pré-existente na máquina, não um ambiente efêmero/containerizado —
  Docker não foi instalado nem usado (fora do escopo autorizado desta
  fase).
- O seed sintético não foi desenhado para ser idempotente dentro do
  mesmo banco (reaplica-lo sem recriar o banco antes gera violação de
  chave única, por design).
- Nenhum dado real da Patrimar foi usado nem seria apropriado usar
  nesta fase — ver [[04-DECISIONS]] D8.
