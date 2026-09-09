# Reference Allocation Engine — Relatório de Execução (sintético)

> REFERENCE_ALLOCATION_V1 e uma implementacao de referencia 100% sintetica. NAO representa a metodologia proprietaria da Patrimar/Rodolfo.

- Algoritmo: `REFERENCE_ALLOCATION_V1`
- Unidades: 40
- VGV alvo (sintético): 10000000.00
- VGV sistemático (soma dos preços calculados): 10000000.00
- Validação VGV_RECONCILIATION: INFO (diferença: 0.00)
- Soma das participações (deve ser 1, dentro da precisão Decimal): 1.000000000000000000000000000000000000000
- Hash lógico determinístico (RUN 1 — SYSTEM_ONLY): `9a955e218e71e806ab4906fbf06b0111d635649658732d4f4a6048261d3dcf8c`

## Override de demonstração (RUN 2 — WITH_OVERRIDE)

- Unidade: torre `TOWER-1`, código `0101`
- Preço anterior (sistemático): 125066.70
- Preço final após override: 175066.70
- Impacto no VGV: 50000.00
- VGV sistemático: 10000000.00
- VGV final (após override): 10050000.00
- Delta VGV após override: 50000.00

## Fonte

Gerado a partir de `fixtures/v2/reference_allocation_scenario.json` por `scripts/generate_v2_seed.py`. Não editar este relatório manualmente — regenerar.
