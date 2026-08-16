import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

CONEXAO = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

# Variáveis que vamos usar no "experimento"
PRODUTO = "Bússola de Bordo 702"
JANELA = 3
FIM_TREINO = "2025-12-31"
INICIO_TESTE = "2026-01-01"
FIM_TESTE = "2026-03-31"

# Dataset unificado: junta as 4 tabelas e agrega a quantidade vendida por mês
# DATE_TRUNC para ter série mensal das vendas e filtro com %s pois vamos passar separadamente com a var PRODUTO
# Esse filtro será por nome porque existem dois product_id distintos cadastrados como "Bússola de Bordo 702"
QUERY = """
    SELECT
        DATE_TRUNC('month', o.created_at)::date as mes,
        SUM(oi.quantity) as quantidade
    FROM orders o
    JOIN order_items oi
        ON oi.order_id = o.id
    JOIN product_variants pv
        ON pv.id = oi.product_variant_id
    JOIN products p
        ON p.id = pv.product_id
    WHERE p.name = %s
    GROUP BY 1
    ORDER BY 1
"""

# Parametrização: o valor do produto viaja separado da SQL, para não termos problemas com acento
conn = psycopg2.connect(**CONEXAO)
df = pd.read_sql(QUERY, conn, params=(PRODUTO,))
conn.close()

# Completa os meses sem venda com zero, para não quebrar a sequência da série
# Se um mês sumisse, a janela dos 3 meses pegaria um mês mais antigo e distorceria a média
df['mes'] = pd.to_datetime(df['mes'])
serie = df.set_index('mes').asfreq('MS', fill_value=0)['quantidade']

# Separamos para que o modelo nunca tenha visto os meses que queremos prever
treino = serie[serie.index <= FIM_TREINO]
teste = serie[INICIO_TESTE:FIM_TESTE]

# Walk-forward: cada mês é previsto pela média dos 3 meses anteriores.
# O valor real só entra no histórico depois da previsão ser feita, evitando data leakage.
historico = list(treino.values)
previsoes = []

for data in teste.index:
    previsoes.append(sum(historico[-JANELA:]) / JANELA)
    historico.append(teste[data])


resultado = pd.DataFrame({
    'mes': teste.index.strftime('%Y-%m'),
    'real': teste.values,
    'previsto': [round(p, 2) for p in previsoes]
})

# O valor absoluto impede que erros para cima e para baixo se cancelem na média
resultado['erro_absoluto'] = (resultado['real'] - resultado['previsto']).abs()

mae = resultado['erro_absoluto'].mean()

print(f"Produto: {PRODUTO}")
print(f"Treino: {len(treino)} meses ({treino.index[0].date()} a {treino.index[-1].date()})")
print(f"Teste:  {len(teste)} meses\n")
print(resultado.to_string(index=False))
print(f"\nMAE: {mae:.2f}")
print(f"Soma das previsões do Q1/2026: {round(sum(previsoes))}")
