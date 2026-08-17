import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sklearn.metrics.pairwise import cosine_similarity
 
load_dotenv()
 
CONEXAO = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}
 
# O SQLAlchemy é necessário para o to_sql do pandas; o psycopg2 sozinho só lê
URL = (f"postgresql+psycopg2://{CONEXAO['user']}:{CONEXAO['password']}"
       f"@{CONEXAO['host']}:{CONEXAO['port']}/{CONEXAO['dbname']}")
engine = create_engine(URL)
 
PRODUTO = "Bússola de Bordo 702"
PRODUTO_REF = "Motor de Popa 1949"
JANELA = 3
FIM_TREINO = "2025-12-31"
INICIO_TESTE = "2026-01-01"
FIM_TESTE = "2026-03-31"
 
 
# Série mensal do produto da Questão 6
QUERY_SERIE = """
    SELECT
        DATE_TRUNC('month', o.created_at)::date as mes,
        SUM(oi.quantity) as quantidade
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p ON p.id = pv.product_id
    WHERE p.name = %s
    GROUP BY 1
    ORDER BY 1
"""
 
# Pares cliente-produto da Questão 7
QUERY_PARES = """
    SELECT DISTINCT
        o.customer_id,
        p.name as produto
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p ON p.id = pv.product_id
"""
 
conn = psycopg2.connect(**CONEXAO)
df_serie = pd.read_sql(QUERY_SERIE, conn, params=(PRODUTO,))
df_pares = pd.read_sql(QUERY_PARES, conn)
conn.close()
 
 
# Questão 6: refaz o baseline walk-forward e monta a série completa para o gráfico
df_serie['mes'] = pd.to_datetime(df_serie['mes'])
serie = df_serie.set_index('mes').asfreq('MS', fill_value=0)['quantidade']
 
treino = serie[serie.index <= FIM_TREINO]
teste = serie[INICIO_TESTE:FIM_TESTE]
 
historico = list(treino.values)
previsoes = []
for data in teste.index:
    previsoes.append(sum(historico[-JANELA:]) / JANELA)
    historico.append(teste[data])
 
# Uma linha por mês de toda a série, com a previsão preenchida apenas no período de teste
# Assim o gráfico do Power BI mostra o histórico e a projeção na mesma escala
previsao_por_mes = dict(zip(teste.index, previsoes))
 
fato_previsao = pd.DataFrame({
    'mes': serie.index,
    'produto': PRODUTO,
    'real': serie.values,
    'previsto': [round(previsao_por_mes.get(m), 2) if m in previsao_por_mes else None
                 for m in serie.index],
    'periodo': ['teste' if m in previsao_por_mes else 'treino' for m in serie.index]
})
fato_previsao['erro_absoluto'] = (fato_previsao['real'] - fato_previsao['previsto']).abs()
 
 
# Questão 7: refaz a matriz e o ranking de similaridade
matriz = pd.crosstab(df_pares['customer_id'], df_pares['produto'])
sim_df = pd.DataFrame(
    cosine_similarity(matriz.T),
    index=matriz.columns,
    columns=matriz.columns
)
 
similares = sim_df[PRODUTO_REF].sort_values(ascending=False).drop(PRODUTO_REF)
 
fato_recomendacao = (
    similares.head(20)
    .reset_index()
    .rename(columns={'produto': 'produto_similar', PRODUTO_REF: 'similaridade'})
)
fato_recomendacao['produto_referencia'] = PRODUTO_REF
fato_recomendacao['posicao'] = range(1, len(fato_recomendacao) + 1)
fato_recomendacao['similaridade'] = fato_recomendacao['similaridade'].round(4)
 
 
# Grava as duas tabelas no banco; replace deixa o script reexecutável
fato_previsao.to_sql('fato_previsao_demanda', engine, if_exists='replace', index=False)
fato_recomendacao.to_sql('fato_recomendacao', engine, if_exists='replace', index=False)
 
print(f"fato_previsao_demanda: {len(fato_previsao)} linhas")
print(f"fato_recomendacao: {len(fato_recomendacao)} linhas")
 