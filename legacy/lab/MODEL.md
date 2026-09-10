# Modelo hedônico Patrimar

## Escopo

O modelo considera somente apartamentos novos no mercado primário: lançamento, construção, acabamento ou estoque pronto, sempre na primeira venda. Revendas e imóveis usados devem ser excluídos na visão `v_hedonic_model`.

## Especificação

A variável dependente é `ln(preco_m2)`. A especificação científica inclui:

- andar centrado no 10º pavimento e termo quadrático;
- logaritmo da área privativa;
- vagas e suítes;
- vista, orientação e posição;
- interações entre andar e vista;
- área de varanda e cobertura;
- índice de qualidade do produto (média de padrão e lazer);
- qualidade de localização;
- meses desde o lançamento e fase comercial.

Variáveis sem variação na amostra são removidas automaticamente. A estimação usa OLS com erros-padrão robustos HC3. A validação separa deterministicamente 80% das observações para treino e 20% para teste e informa RMSE, MAE e MAPE fora da amostra. Também são exibidos Jarque–Bera e o maior VIF.

## Base híbrida

`data/hedonic_seed_hybrid.csv` contém 626 unidades em 12 empreendimentos fictícios. Nenhuma linha representa uma venda individual real. A calibração usa apenas faixas e distribuições publicadas para imóveis novos de Belo Horizonte, com dispersão, interações, efeitos não observados por empreendimento e casos atípicos.

Fontes de calibração e metodologia:

- Fundação IPEAD/UFMG, Pesquisa do Mercado Imobiliário: Construção e Comercialização: https://www.ipead.face.ufmg.br/mercadoimobiliario/arquivos/Pesquisa%20Constru%C3%A7%C3%A3o%2012-2018_completo%20residencial.pdf
- CMI/Secovi-MG, DataSecovi: https://www.secovimg.com.br/noticia-detalhes.php?noticia=415
- ABRAINC/Fipe, mercado imobiliário primário: https://www.fipe.org.br/pt-br/indices/abrainc/
- Paixão (2023), preços hedônicos de apartamentos em Belo Horizonte: https://doi.org/10.54694/stat.2022.46
- Eurostat/OECD, fundamentos para métodos hedônicos e ajuste de qualidade: https://ec.europa.eu/eurostat/documents/3859598/7152852/KS-GQ-14-005-EN-N.pdf

## PostgreSQL e API

O esquema normalizado está em `database/schema.sql`. A visão `v_hedonic_model` é o contrato da aplicação. A função Netlify `GET /api/hedonic-data` consulta a visão por conexão TLS usando `DATABASE_URL`, que deve existir somente nas variáveis protegidas do ambiente.

O frontend aceita um array JSON ou `{ "data": [...] }`. Credenciais do PostgreSQL nunca devem ser colocadas no HTML.

## Limitações

- Coeficientes da base híbrida servem para teste funcional, não para decisão comercial.
- A causalidade dos atributos só poderá ser avaliada com observações reais e processo de coleta conhecido.
- Quando o banco Patrimar estiver disponível, devem ser avaliados efeitos fixos de empreendimento, tempo, seleção de estoque e política de descontos.
- O intervalo preditivo atual é aproximado e baseado na variância residual do modelo log-linear.
