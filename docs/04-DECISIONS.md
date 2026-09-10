# 04 — Decisions

Registro de decisões estruturais do projeto. Cada entrada deve ter data,
decisão e motivo. Decisões aqui têm precedência sobre preferências
individuais de qualquer agente ou sessão de chat.

---

### D1 — O repositório é a fonte permanente da verdade
**Data:** 2026-09-09
**Decisão:** Todo conhecimento relevante sobre o projeto (estado,
arquitetura, progresso, problemas, comandos, próximos passos) deve estar
documentado dentro do repositório (`docs/`, `CLAUDE.md`, `AGENTS.md`,
código e comentários onde apropriado) — não apenas na conversa com um
assistente de IA.
**Motivo:** o projeto precisa sobreviver à troca de ferramenta, de
assistente e de pessoa.

### D2 — Agentes e modelos de IA são substituíveis
**Data:** 2026-09-09
**Decisão:** O projeto deve poder continuar com Claude Code, Codex,
Gemini, NVIDIA, modelos locais, ou qualquer outro agente, sem depender do
histórico de conversa de nenhum deles especificamente.
**Motivo:** evitar lock-in em uma ferramenta específica e garantir
continuidade do trabalho independentemente de qual assistente está
disponível em um dado momento.

### D3 — Nenhum conhecimento importante pode existir somente no chat
**Decisão:** Se uma decisão, um resultado de teste, um risco encontrado
ou um próximo passo importa para o futuro do projeto, ele precisa ser
escrito em `docs/`, não apenas mencionado em uma resposta de chat.
**Motivo:** consequência direta de D1 — uma decisão que só existe no chat
está, na prática, perdida assim que a sessão termina.

### D4 — Dados restritos da Patrimar não devem ser publicados
**Data:** 2026-09-09
**Decisão:** Dados reais de vendas, preços, clientes ou qualquer
informação comercial restrita da Patrimar não devem ser commitados neste
repositório (que tem remote público em
`https://github.com/gustavoecivil/patrimar-hedonica.git`), nem em texto
plano, nem em exemplos, nem em fixtures de teste.
**Motivo:** o repositório é público (ou tratado como potencialmente
público); dados sintéticos/híbridos (como o CSV atual) são aceitáveis
para testes, dados reais não são.
**Como aplicar:** ao importar dados reais em fases futuras (ver
[[03-ROADMAP]]), avaliar se o repositório precisa se tornar privado ou se
os dados reais devem viver fora do Git (ex.: apenas no banco de
produção), antes de fazer qualquer commit com dados reais.

### D5 — Fase 0 é somente auditoria, sem alteração de comportamento
**Data:** 2026-09-09
**Decisão:** Esta execução (Fase 0) não alterou código de produção,
banco, deploy, nem fez commit/push/branch. Apenas leu o repositório,
executou o teste local seguro existente, e criou documentação nova em
`docs/`, `CLAUDE.md` e `AGENTS.md`.
**Motivo:** instrução explícita do responsável pelo projeto para separar
auditoria de execução.

### D6 — Zona restrita `data/restricted/` para dados privados da Patrimar
**Data:** 2026-09-09
**Decisão:** Toda planilha original de Rodolfo/Patrimar, todo dado real
de vendas/preços/clientes, e todo dado derivado que possa revelar essas
informações privadas devem ficar exclusivamente em `data/restricted/`
na cópia local do repositório. Essa pasta é listada em `.gitignore` e
**nenhum arquivo dentro dela pode ser commitado** neste repositório, que
tem remote público (`github.com/gustavoecivil/patrimar-hedonica`).
Nenhum dado real da Patrimar entra no Git público sem classificação
explícita do dado e autorização explícita do responsável pelo projeto
para aquele commit específico. Dados públicos, sintéticos ou
anonimizados (como `data/hedonic_seed_hybrid.csv`) continuam versionados
normalmente e devem ser claramente identificados como tal (ver
`origem`/proveniência em `MODEL.md` e no dicionário de dados).
**Motivo:** reforço operacional de D4 — o repositório passou a ter
`.gitignore` (Fase 0.5) e precisa de um local convencionado e protegido
para dados restritos antes que qualquer planilha real seja trazida ao
ambiente de trabalho, evitando que caia no Git por descuido.
**Como aplicar:** antes de importar qualquer planilha ou dado real
(ver Fase 1 do [[03-ROADMAP]]), salvar o arquivo dentro de
`data/restricted/` (nunca na raiz de `data/`), e verificar com
`git status`/`git check-ignore` que ele não ficou rastreado antes de
qualquer `git add`.

### D7 — Market Pricing Engine e Unit Price Allocation Engine são domínios separados e integráveis
**Data:** 2026-09-09
**Decisão:** A plataforma futura separa conceitualmente dois motores:
o **Market Pricing Engine** (Motor A — estima quanto um produto/
empreendimento/tipologia/unidade deveria valer frente ao mercado, a
partir de comparáveis, transações, indicadores e modelos estatísticos)
e o **Unit Price Allocation Engine** (Motor B — distribui um VGV/
preço-base já definido entre as unidades de um empreendimento,
respeitando área, área ponderada, pavimento, posição, parâmetros de
calibração e overrides humanos). O único ponto de integração formal
entre os dois é o VGV/preço-base recomendado, que o Motor A produz e
o Motor B consome.
**Motivo:** a engenharia reversa da lógica de precificação existente
(Fase 1C, ver [[09-PRICING-LOGIC-REVERSE-ENGINEERING]]) mostrou, com
evidência de fórmula, que a metodologia hoje em uso resolve apenas o
problema de alocação interna (Motor B) — não estima valor de mercado.
Separar os dois motores evita acoplar prematuramente uma lógica já
evidenciada (alocação) a uma lógica que ainda não existe como
mecanismo formal (precificação de mercado), e permite que cada um
evolua e seja validado de forma independente.
**Como aplicar:** todo desenho de schema, regra de negócio, ou
funcionalidade de precificação a partir da Fase 1D deve declarar a
qual motor pertence (ou se é o ponto de integração entre eles) — ver
[[10-PRICING-DOMAIN-MODEL]] para os princípios de modelagem
resultantes (classificação de dados, granularidade, histórico,
versionamento, overrides, validação de invariantes).

### D8 — REFERENCE_ALLOCATION_V1 é motor técnico sintético de referência, não metodologia oficial Patrimar
**Data:** 2026-09-09
**Decisão:** O algoritmo `REFERENCE_ALLOCATION_V1`
(`scripts/reference_allocation_engine.py`), criado na Fase 2B para
provar o schema PostgreSQL v2, e todo o cenário de demonstração que o
acompanha (`fixtures/v2/reference_allocation_scenario.json`,
`database/v2/seeds/001_demo_allocation.sql`) são **inteiramente
sintéticos e públicos**. Eles servem exclusivamente para provar que o
schema v2 (D7, Fase 2) é capaz de representar um ciclo completo de
distribuição de VGV entre unidades — parâmetros, calibrações, VGV-alvo,
unidades, cenário e empreendimento são fictícios. **Nenhum valor,
fórmula, parâmetro ou nome deste algoritmo ou deste cenário deve ser
tratado como, ou confundido com, a metodologia real de precificação da
Patrimar/Rodolfo** (reconstruída privadamente na Fase 1C — ver
[[09-PRICING-LOGIC-REVERSE-ENGINEERING]]).
**Motivo:** era necessário provar a arquitetura de dados (schema v2)
de ponta a ponta sem expor, reproduzir ou aproximar a fórmula
proprietária real, que é dado privado (D4/D6) e cuja reconstrução
ainda tem perguntas pendentes sem resposta de Rodolfo (ver
`data/restricted/audit/questions-for-rodolfo.md`). Um algoritmo
alternativo, público e claramente identificado como não-oficial,
permite testar o schema sem esse risco.
**Como aplicar:** qualquer uso futuro de `REFERENCE_ALLOCATION_V1` (ou
de qualquer variante dele) para decisão real de precificação está
proibido sem revisão explícita. Antes de qualquer motor real de
precificação entrar em produção, ele deve ser validado contra a
lógica reconstruída na Fase 1C (privadamente) e as perguntas
pendentes de Rodolfo devem estar respondidas — ver
[[12-REFERENCE-ALLOCATION-ENGINE]] para o algoritmo, os dados
sintéticos e as limitações desta referência.

### D9 — Testes de banco real usam um servidor PostgreSQL local pré-existente, isolado por banco/role dedicados, sem alterar sua configuração global
**Data:** 2026-09-09
**Decisão:** A Fase 2C executou o schema v2 e o seed sintético contra
um PostgreSQL 18 já instalado e em uso no ambiente local (não
instalado nesta fase). O isolamento é feito por um banco de dados
dedicado (`patrimar_pricing_v2_test`) e uma role própria com senha
gerada aleatoriamente nesta sessão, nunca reaproveitada de nenhuma
credencial real do usuário. **Nenhuma configuração global do servidor
(`postgresql.conf`, `pg_hba.conf`, `listen_addresses`) foi alterada**
— o servidor pré-existente já restringe autenticação a conexões via
loopback (`127.0.0.1`/`::1`) por `pg_hba.conf`, independentemente do
endereço de bind, e essa configuração herdada não foi tocada.
**Motivo:** o servidor local pode ter outros bancos/projetos do
usuário — alterar configuração global para uma necessidade estreita
de teste seria escopo maior que o necessário e arriscaria efeitos
colaterais fora do controle desta tarefa. Isolar por banco/role
dedicados atinge o mesmo objetivo (ambiente de teste seguro e
descartável) sem esse risco.
**Como aplicar:** qualquer script que crie, aplique DDL, verifique ou
remova esse banco de teste deve recusar operar se o nome não contiver
explicitamente `_test` (ver `scripts/db_v2_*.ps1`). Credenciais desses
testes vivem apenas em arquivos locais cobertos por `.gitignore`
(`.env.*`), nunca commitadas. O banco de teste criado nesta fase
permanece ativo entre sessões até uma decisão explícita de removê-lo
— ver [[99-HANDOFF]].

### D10 — Ingestão de dado privado real vive num banco PostgreSQL separado, nunca junto do banco sintético de teste

**Data:** 2026-09-09
**Decisão:** A Fase 3A criou um banco PostgreSQL adicional,
`patrimar_pricing_v2_private_dev`, exclusivamente para receber a
ingestão `raw`/`staging` das duas planilhas reais de Rodolfo. Esse
banco é **totalmente separado** de `patrimar_pricing_v2_test` (D9,
Fase 2C) — nenhum dado real jamais entra no banco de teste sintético,
e nenhum dado sintético de teste precisa ser removido ou misturado
para acomodar dado real. A senha desse banco foi gerada localmente
nesta sessão, nunca reutilizada de nenhuma credencial existente, e
nunca impressa em nenhum relatório ou log — vive apenas em
`.env.pricing_v2_private_dev` (local, `.gitignore`, nunca commitado).
O DDL genérico (`database/v2/008_ingestion.sql`) que cria os schemas
`raw`/`staging` é idêntico nos dois bancos; o que os diferencia são as
**linhas**, nunca o schema.
**Motivo:** misturar dado real e dado sintético no mesmo banco
tornaria qualquer verificação futura contra o banco de teste (ex.:
`verify_postgres_v2.py`) ambígua sobre se um resultado depende de
dado real ou sintético, e aumentaria o risco de dado privado vazar
para um artefato pensado como sintético/público (dump, backup,
captura de tela). Separar fisicamente os bancos elimina essa
ambiguidade por construção.
**Como aplicar:** nenhum script deste projeto deve aplicar dado real
contra um banco cujo nome não sinalize explicitamente essa natureza
(`_private_dev` ou equivalente revisado explicitamente); nenhum dump,
export ou backup desse banco pode ser salvo fora de
`data/restricted/` ou de um caminho fora do repositório. Antes de
qualquer promoção futura de `staging` para `core`/`pricing` (Fase 3B),
confirmar novamente qual banco está sendo usado como origem.

### D11 — Resultado importado de uma fonte externa nunca pode ser confundido com resultado calculado pelo sistema

**Data:** 2026-09-09
**Decisão:** Qualquer valor de preço, VGV ou execução que já existia
numa fonte externa (ex.: planilha real) e seja apenas armazenado no
schema v2 para referência/análise deve ser explicitamente marcado
como tal — `pricing.runs.run_type='IMPORTED_REFERENCE_RUN'` e
`pricing.unit_price_results.result_origin='IMPORTED_REFERENCE'`
(`database/v2/009_promotion.sql`, Fase 3B) — nunca com os valores
`SYSTEM_RUN`/`SYSTEM_CALCULATED`, reservados exclusivamente a uma
execução real do motor de alocação (`REFERENCE_ALLOCATION_V1` ou um
motor real futuro).
**Motivo:** a Fase 3B promoveu, do banco privado, resultados de preço
que já existiam nas duas planilhas reais — sem essa distinção
explícita no próprio dado persistido, seria possível, numa consulta
futura descuidada, apresentar um número que veio de uma planilha como
se fosse um cálculo produzido pelo Patrimar Pricing Intelligence. Isso
violaria a separação exigida entre "dado importado" e "resultado
calculado pelo novo sistema".
**Como aplicar:** nenhuma consulta, relatório, ou funcionalidade
futura que exiba `pricing.unit_price_results` pode omitir ou ignorar
`result_origin`. Nenhum motor real de precificação (Fase 3C ou
posterior) deve gravar resultados com `result_origin` diferente de
`SYSTEM_CALCULATED`. Ver [[15-STAGING-TO-CANONICAL-PROMOTION]].

### D12 — A lógica de precificação real é configuração privada; o código público é infraestrutura genérica

**Data:** 2026-09-10
**Decisão:** A partir da Fase 3C, todo motor que opera sobre a
metodologia real reconstruída (Fase 1C) é dividido em duas partes
com regras de versionamento diferentes: (1) um **engine genérico e
público** (`scripts/pricing_reproduction_engine.py`), que só conhece
um catálogo pequeno de operações abstratas (soma, soma ponderada,
busca por chave derivada, combinação linear, etc.) e não contém
nenhuma fórmula, constante ou nome real; (2) um **ruleset privado**
(`data/restricted/pricing_rules/`, nunca versionado), que declara
quais operações se aplicam a quais campos, com quais parâmetros
estruturais evidenciados nas Fases 1B/1C. Tabelas de calibração e
parâmetros numéricos reais nunca ficam no ruleset — são lidos ao vivo
do banco privado.
**Motivo:** a Fase 3C precisa executar de fato a lógica real para
comparar contra os preços já importados (Fase 3B), mas a lógica em si
continua sendo propriedade da Patrimar/Rodolfo (mesmo fundamento de
D4/D6/D8) — reproduzir a metodologia não significa publicá-la.
Separar "como calcular genericamente" (público, testável com dados
fictícios) de "o que calcular de verdade" (privado) permite que o
código do motor seja auditável e versionado sem nunca expor a
fórmula proprietária.
**Como aplicar:** qualquer novo motor que opere sobre a metodologia
real (Fase 3D em diante) deve seguir o mesmo padrão — catálogo de
operações genéricas em código público, parâmetros/tabelas/constantes
reais exclusivamente em `data/restricted/`. Nenhum commit público
pode conter uma fórmula, constante ou nome de campo real da fonte,
mesmo dentro de um comentário ou docstring.

### D13 — Fechamento de ambiguidade exige evidência classificada e prova estrutural antes de comparar contra o preço de referência

**Data:** 2026-09-10
**Decisão:** Toda ambiguidade que bloqueie a reprodução de preço só
pode ser resolvida com evidência classificada como `DIRECT`,
`STRUCTURAL` ou `INFERRED_STRONG` — nunca `INFERRED_WEAK` ou
suposição. Além disso, qualquer hipótese precisa ser comprovada
**usando somente a estrutura da própria fonte** (fórmula real,
identidade aritmética, valor já calculado e armazenado pela própria
fonte) **antes** de seu efeito ser medido contra o preço de
referência já conhecido. Uma hipótese encontrada olhando o preço
final para ajustar um valor é descartada como
`CONTAMINATED_HYPOTHESIS`, mesmo que reduza o erro observado.
**Motivo:** a Fase 3D encontrou e corrigiu, com esse método, um
defeito real de software (não uma ambiguidade de negócio) e
reconstruiu uma tabela de calibração inteira a partir de evidência de
fórmula — sem esse rigor, seria tentador "ajustar até bater", o que
produziria uma reprodução aparentemente perfeita mas sem
sustentação real, exatamente o resultado que este projeto rejeita
desde a Fase 3C (D8, D11: nunca confundir dado importado/ajustado com
resultado genuinamente calculado).
**Como aplicar:** qualquer fase futura que tente fechar uma
ambiguidade de cálculo (Fase 3D em diante) deve documentar, para cada
achado: a classificação da evidência, a prova estrutural que a
sustenta (antes de qualquer comparação com o preço final), e o
efeito medido depois. Reprodução matemática bem-sucedida
(`MATHEMATICAL_REPRODUCTION_CONFIRMED`) nunca deve ser apresentada
como equivalente a entender o motivo de negócio de uma regra
(`BUSINESS_SEMANTICS_CONFIRMED`) — as duas são registradas
separadamente, e a segunda pode continuar pendente mesmo quando a
primeira já foi alcançada.
