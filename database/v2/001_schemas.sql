-- Patrimar Pricing Intelligence — Schema canônico v2
-- Namespaces e extensões. Não altera o schema legado (database/schema.sql).
--
-- Ordem de execução completa: 001 -> 002 -> 003 -> 004 -> 005 -> 006 -> 007.
-- Ver database/v2/README.md para a razão de algumas foreign keys serem
-- adicionadas via ALTER TABLE em arquivos posteriores (dependência entre
-- schemas que se referenciam em mais de uma direção).

CREATE EXTENSION IF NOT EXISTS pgcrypto; -- gen_random_uuid() (nativo desde PG13, mantido por compatibilidade)

CREATE SCHEMA IF NOT EXISTS core;    -- cadastro estável: empreendimentos, torres, tipologias, unidades
CREATE SCHEMA IF NOT EXISTS pricing; -- Unit Price Allocation Engine (Motor B)
CREATE SCHEMA IF NOT EXISTS audit;   -- proveniência e linhagem de dados
CREATE SCHEMA IF NOT EXISTS market;  -- fundação mínima do Market Pricing Engine (Motor A)

COMMENT ON SCHEMA core IS
  'Cadastro físico estável de empreendimentos/torres/tipologias/unidades. Compartilhado pelos dois motores (D7).';
COMMENT ON SCHEMA pricing IS
  'Unit Price Allocation Engine (Motor B) — distribuição de VGV/preço-base entre unidades. Ver docs/09 e docs/10.';
COMMENT ON SCHEMA audit IS
  'Proveniência (data_sources) e linhagem (data_lineage) de dados. Nenhuma tabela aqui contém dado de negócio.';
COMMENT ON SCHEMA market IS
  'Fundação mínima e extensível do Market Pricing Engine (Motor A). Ver database/v2/README.md — deliberadamente '
  'não inclui comparáveis/transações/ofertas ainda: nenhuma fonte real dessas existe no projeto até a Fase 1D/2.';

-- raw e staging (camadas de ingestão bruta/normalizada de fontes externas,
-- incluindo eventuais planilhas) são um plano FUTURO, não implementado
-- nesta fase — ver docs/11-DATABASE-V2-DESIGN.md, seção "Camadas futuras".
-- Nenhuma tabela derivada de planilha privada é criada aqui ou em
-- qualquer outro arquivo deste diretório.
