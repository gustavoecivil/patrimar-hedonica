# 06 — Lessons Learned

Estrutura criada na Fase 0. Nenhum aprendizado foi inventado — este
arquivo será preenchido à medida que fases futuras (ver [[03-ROADMAP]])
gerarem experiência real. Cada entrada deve citar a fase/execução em que
o aprendizado surgiu.

## Formato de cada entrada

```
### <título curto>
**Fase/execução:** <ex.: Fase 2 — RAW/STAGING/CORE, 2026-XX-XX>
**O que aconteceu:**
**O que foi aprendido:**
**Como isso muda o trabalho futuro:**
```

## Entradas

_Nenhuma entrada registrada ainda além dos pontos observacionais abaixo,
que não são "lições" no sentido de terem sido aprendidas por tentativa e
erro, mas observações estruturais já visíveis nesta auditoria (Fase 0) e
que vale ter em mente nas próximas fases:_

- O projeto reusa a mesma lógica de gerador de dados e de OLS entre
  navegador e Node executando o JS de `index.html` dentro de uma sandbox
  `vm` (ver `scripts/*.mjs` e `tests/model-smoke.mjs`). É um padrão
  eficaz para não duplicar lógica, mas frágil: qualquer mudança na
  estrutura dos `<script>` de `index.html` (ex.: dividir em múltiplos
  arquivos) quebra esses scripts e o teste sem aviso explícito além da
  falha de execução.
- O schema SQL existe em dois arquivos (`database/schema.sql` e a
  migração Netlify) sem mecanismo de sincronização — risco de drift
  documentado em [[02-ARCHITECTURE]].
- Não existe `.gitignore` no projeto — risco documentado no relatório da
  Fase 0 e em [[01-CURRENT-STATE]].
