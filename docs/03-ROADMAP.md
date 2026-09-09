# 03 — Roadmap

## Fase atual

**FASE 1C — Engenharia reversa da lógica de precificação.**
Executada em 2026-09-09 (ver [[05-WORKLOG]]). Reconstruído, com
evidência de fórmula (nunca por suposição), o fluxo de cálculo de
preço presente nas duas planilhas recebidas: entradas, parâmetros,
buscas/lookups, ajustes, agregações, e o(s) ponto(s) de override
humano sobre o preço final. Criada a ferramenta genérica
`scripts/analyze_pricing_logic.py` (reaproveitando
`scripts/audit_xlsx.py`, ainda sem dependência externa) com teste de
fumaça sintético. Toda a interpretação com conteúdo real (fórmulas,
parâmetros, valores, nomes de aba/campo) ficou exclusivamente em
`data/restricted/audit/` — ver [[09-PRICING-LOGIC-REVERSE-ENGINEERING]]
para a metodologia pública, sem conteúdo privado. Não foi desenhado
banco definitivo, migrado dado nenhum, nem alterado frontend/modelo/
API/Netlify.

**FASE 1B — Auditoria estrutural das planilhas do Rodolfo.**
Executada em 2026-09-09 (ver [[05-WORKLOG]]). Criada a ferramenta
genérica `scripts/audit_xlsx.py` (biblioteca padrão do Python, sem
dependência externa nova) e seu teste de fumaça com dados sintéticos
(`scripts/test_audit_xlsx.py`). Os dois workbooks recebidos na Fase
1A.1 foram auditados estruturalmente (abas, campos, fórmulas,
dependências entre abas, conteúdo oculto, qualidade de dados,
comparação entre os dois workbooks). Todos os resultados (incluindo
qualquer nome real de aba/campo) ficam exclusivamente em
`data/restricted/audit/` — ver [[08-SPREADSHEET-AUDIT-METHOD]] para a
metodologia pública, sem conteúdo privado. Nenhuma interpretação de
regra de negócio, conversão de formato, ou importação para banco foi
feita nesta fase.

**FASE 0.5 — Congelamento do legado e fundação segura.**
Executada em 2026-09-09 (ver [[05-WORKLOG]]). Criou tag local do legado
(`legacy-hedonica-pre-rebuild-20260909` → `7dd1d24`), a branch
`rebuild/pricing-intelligence` (ponto de partida da nova plataforma),
`.gitignore` (incluindo a zona restrita `data/restricted/` — ver
[[04-DECISIONS]] D6) e versionou a documentação da Fase 0. Nenhum
modelo, banco, frontend, função Netlify ou dado foi alterado.

**FASE 0 — Auditoria, inventário e documentação do legado.**
Iniciada e concluída em 2026-09-09 (ver [[05-WORKLOG]]). Nenhuma
implementação nova foi feita nesta fase; apenas leitura, execução segura
de teste local, e criação da documentação canônica em `docs/`.

## Fases futuras (registradas como plano, NÃO implementadas)

As fases abaixo são **hipótese/plano**, não compromisso de cronograma, e
não foram iniciadas. Ordem sugerida, sujeita a revisão:

1. **Auditoria das planilhas do Rodolfo** — levantar quais planilhas
   existem, o que contêm, qualidade e cobertura dos dados, e o que pode
   ser migrado para o repositório/banco. Qualquer planilha original
   trazida para o ambiente de trabalho deve ser salva em
   `data/restricted/` (zona restrita, ignorada pelo Git — ver
   [[04-DECISIONS]] D6), nunca na raiz de `data/` nem em nenhum outro
   caminho versionado. **Status:** recepção (Fase 1A/1A.1), auditoria
   estrutural (Fase 1B) e engenharia reversa da lógica de precificação
   (Fase 1C) concluídas. Falta a Fase 1D (gap analysis e modelo
   canônico preliminar, ainda não iniciada) e a validação das
   perguntas pendentes registradas privadamente para quem forneceu a
   planilha original.
2. **Dicionário de dados** — formalizar e expandir
   [[07-DATA-DICTIONARY]] cobrindo também os dados a importar das
   planilhas.
3. **RAW / STAGING / CORE** — camadas de dados para ingestão bruta,
   tratamento e modelo de domínio limpo, substituindo o CSV sintético
   único atual.
4. **PostgreSQL/PostGIS** — evoluir o schema atual (`database/schema.sql`)
   para suportar dados geoespaciais reais (hoje `developments` já tem
   `latitude`/`longitude` como `NUMERIC`, mas não há extensão PostGIS
   nem índices espaciais).
5. **Parâmetros** — parametrização de premissas de negócio (ex.: tabelas
   de referência, faixas de mercado) fora do código.
6. **Dados públicos** — incorporar fontes públicas adicionais (IPEAD,
   Secovi, ABRAINC/Fipe, etc., já citadas em `MODEL.md` como calibração,
   não como dados diretos).
7. **Comparáveis** — módulo de seleção/análise de comparáveis de
   mercado.
8. **Modelo hedônico (evolução)** — avaliar efeitos fixos de
   empreendimento, tempo, seleção de estoque e política de desconto,
   conforme já apontado como limitação em `MODEL.md`.
9. **Modelos concorrentes** — comparar o modelo hedônico OLS com
   abordagens alternativas (ex. árvores, regularização).
10. **Motor de preços** — camada de decisão de preço além da previsão
    pontual do modelo (regras de negócio, faixas, aprovações).
11. **Simulador** — evoluir a "Calculadora" atual (client-side, sessão
    única) para um simulador robusto e auditável.
12. **Painel** — evoluir as abas atuais de `index.html` para um painel
    de acompanhamento completo.
13. **Agentes** — agentes de IA operando sobre a base de dados e modelos
    (ex.: automatizar reprecificação, alertas, relatórios).
14. **Lessons learned** — consolidar aprendizados continuamente em
    [[06-LESSONS-LEARNED]] à medida que as fases avançam.

## Regras para avançar de fase

Nenhuma fase futura deve ser iniciada sem que [[04-DECISIONS]] e este
roadmap sejam atualizados primeiro, e sem que o estado local esteja
limpo (`git status`) antes de começar. Qualquer agente que comece uma
nova fase deve atualizar [[05-WORKLOG]] e [[99-HANDOFF]] ao final da
sessão de trabalho.
