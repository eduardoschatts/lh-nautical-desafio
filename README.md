# Desafio Lighthouse — LH Nautical

Projeto de dados para uma empresa fictícia de varejo náutico, indo do arquivo bruto até o dashboard.

O começo são 24 CSVs que vieram de um ERP que não deixa conectar direto no banco. A partir deles eu montei o schema, carreguei tudo num PostgreSQL, respondi as perguntas de negócio em SQL e Python, e fechei com um painel em Power BI.

---

## Estrutura

```
.
├── data/lh_nautical_csv/     os 24 CSVs de origem
├── scripts/                  scripts Python
├── sql/                      queries e schema
├── dashboard/                arquivo .pbix e o PDF das páginas
├── .env.example              modelo de configuração do banco
└── respostas.md              respostas discursivas do desafio
```

---

## Ambiente

PostgreSQL 16 no Docker:

```bash
docker run --name lh-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=sua_senha \
  -e POSTGRES_DB=lh_nautical \
  -p 5433:5432 -d postgres:16
```

Usei a porta 5433 porque já tinha um PostgreSQL nativo ocupando a 5432 aqui na máquina.

As credenciais ficam num `.env` na raiz, que não vai pro Git. O `.env.example` mostra o formato:

```
DB_HOST=localhost
DB_PORT=5433
DB_NAME=lh_nautical
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
```

Bibliotecas usadas: `psycopg2-binary`, `pandas`, `scikit-learn`, `sqlalchemy`, `python-dotenv`.

Ferramentas: VSCode pros scripts, DBeaver pra explorar o banco e testar as queries antes de fechar cada uma, e Power BI pro dashboard.

---

## Como rodar

Na ordem, a partir da raiz do projeto:

```bash
# 1. Gera o schema a partir dos CSVs
python3 scripts/questao2_schema.py

# 2. Cria as 24 tabelas no banco
docker exec -i lh-postgres psql -U postgres -d lh_nautical < sql/schema.sql

# 3. Carrega os dados
python3 scripts/questao3_carga.py

# 4. Cria as views do modelo dimensional
docker exec -i lh-postgres psql -U postgres -d lh_nautical < sql/dashboard_views.sql

# 5. Grava no banco os resultados dos modelos em Python
python3 scripts/exportar_resultados.py
```

Os scripts das questões 6 e 7 rodam sozinhos e imprimem o resultado no terminal.

---

## O que foi feito

### Schema e carga

O script do schema lê todos os CSVs usando só bibliotecas padrão do Python e descobre o tipo de cada coluna passando por todos os valores dela, escolhendo o tipo que comporta 100% dos registros.

Antes de decidir por isso eu testei amostragem de 1.000 a 50.000 linhas. Amostras de até 5.000 erravam duas colunas de `stock_movements`, porque os primeiros valores preenchidos delas só aparecem lá na linha 5.900. Como são só 24 arquivos e a leitura completa leva uns 10 segundos, não valia trocar precisão por performance.

Também coloquei algumas regras pra não corromper dado: número com zero à esquerda vira TEXT (senão um código de barras `0812...` perde o zero), e número com mais de 10 dígitos também, porque CPF, CNPJ e a chave da NF-e estouram o INTEGER.

A carga usa `COPY ... FROM STDIN`, que é a carga em massa nativa do PostgreSQL e muito mais rápida que INSERT linha a linha pras 433 mil linhas do conjunto. Campo vazio entra como NULL, então a camada bruta fica fiel ao que veio.

### Análises em SQL

**EDA da orders** — 48.998 pedidos entre 2020 e 2026, ticket médio de R$ 28.704,99. A distribuição tem cauda à direita mas sem outliers de verdade: a média fica só 11% acima da mediana.

**Clientes fiéis** — ticket médio cruzado com diversidade de categorias, percorrendo a cadeia `orders → order_items → product_variants → products → categories`.

**Dimensão de calendário** — aquele caso em que os dias sem venda somem do cálculo e inflam a média. Contando os 78 dias zerados do período, a quinta-feira sai do quarto lugar e vira o pior dia da semana, justamente por concentrar 20 desses dias.

### Modelos em Python

**Previsão de demanda** — baseline de média móvel de três meses em walk-forward, com MAE de 19,44 unidades no primeiro trimestre de 2026. Errou pra menos em 28%, o que mostra bem a limitação dele: não enxerga sazonalidade.

**Recomendação** — filtragem colaborativa item-item com similaridade de cosseno numa matriz binária de 2.000 clientes por 496 produtos.

### Dashboard

Quatro páginas no Power BI conectadas direto no PostgreSQL, em cima de um modelo estrela com uma fato e quatro dimensões:

- **Visão geral** — receita, margem, evolução mensal, canais e a comparação de vendas por dia da semana
- **Produtos** — margem por produto e categoria, mais os cadastros fora do padrão
- **Clientes** — lucro acumulado, dispersão de frequência por ticket médio e categorias mais consumidas
- **Previsão** — real contra previsto e o ranking de recomendação

---

## O que encontrei pelo caminho

**Nenhum produto dá prejuízo.** O enunciado sugeria um ranking de prejuízo por produto, mas quando fui verificar não existe: zero itens vendidos abaixo do custo em 147.320 registros. A margem é de 42,6% e bem parecida entre as categorias, variando só 3,7 pontos percentuais. Troquei o visual por um ranking de margem.

**Sete produtos ativos estão com nome de cadastro inválido** — `asdf` (que aparece duplicado), `TBD`, `Genérico`, `NAO INFORMADO`, `Cliente Genérico` e `João da Silva`. Juntos somam R$ 9,5 milhões de margem, e um deles é o terceiro produto mais lucrativo da empresa. Ele também lidera o ranking de recomendação, mas por alcance de cadastro e não por relação real de compra.

**Dois produtos diferentes têm o mesmo nome "Bússola de Bordo 702"**, cada um numa categoria. Como o enunciado identifica o produto pelo nome, a análise soma os dois, mas deixei a inconsistência registrada.

**O filtro de diversidade quase não filtra.** 1.971 dos 2.000 clientes compraram de 13 ou mais categorias. Com só 14 categorias na base e sete anos de histórico, quase todo cliente recorrente passa no critério, então quem decide o ranking mesmo é o ticket médio.

**Frequência e ticket médio não têm relação.** Cliente que comprou 12 vezes e cliente que comprou 38 vezes gastam parecido por pedido, o que sugere que pra crescer receita por cliente o caminho é frequência e não valor por transação.

---

## Sobre os dados

A base tem registros com data até 31/12/2026, depois da data atual, o que é cara de dado simulado. Isso não atrapalha as análises, já que o próprio desafio define o período de 2020 a 2026, mas o recorte de tempo precisa sair das datas que estão na base e não do calendário real.

Uns 15% dos pedidos estão como `cancelled` ou `draft`. O enunciado não fala nada sobre filtrar status, então segui a definição literal e considerei todas as transações. O impacto dessa escolha está documentado nos SQLs: na análise de clientes fiéis, só dois clientes continuam no top 10 em todos os cenários que testei.
