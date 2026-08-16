import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

CONEXAO = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

# Variáveis que vamos usar
PRODUTO_REF = "Motor de Popa 1949"
TOP = 5

# Pares distintos de cliente e produto, percorrendo a cadeia até chegar no nome do produto
# O DISTINCT já garante a regra de presença/ausência, comprou dez vezes ou uma, vira uma linha só (binarizar)
QUERY = """
    SELECT DISTINCT
        o.customer_id,
        p.name as produto
    FROM orders o
    JOIN order_items oi
        ON oi.order_id = o.id
    JOIN product_variants pv
        ON pv.id = oi.product_variant_id
    JOIN products p
        ON p.id = pv.product_id
"""

conn = psycopg2.connect(**CONEXAO)
df = pd.read_sql(QUERY, conn)
conn.close()

# Matriz de interação: linhas = clientes, colunas = produtos, célula = 1 se comprou
# Como o DISTINCT já limitou a uma linha por par, as células saem 0 ou 1 sem tratamento extra
matriz = pd.crosstab(df['customer_id'], df['produto'])

print(f"Pares cliente-produto: {len(df)}")
print(f"Matriz: {matriz.shape[0]} clientes x {matriz.shape[1]} produtos")
print(f"Valores distintos na matriz: {sorted(pd.unique(matriz.values.ravel()))}")

# Transpomos a matriz porque queremos comparar produtos, não clientes
# Assim cada produto vira um vetor que descreve quem o comprou
similaridade = cosine_similarity(matriz.T)

sim_df = pd.DataFrame(
    similaridade,
    index=matriz.columns,
    columns=matriz.columns
)

# Pega a coluna do produto de referência e ordena do mais similar para o menos
similares = sim_df[PRODUTO_REF].sort_values(ascending=False)

# Remove o próprio produto, que teria similaridade 1 consigo mesmo
similares = similares.drop(PRODUTO_REF)

print(f"\nProdutos mais similares a '{PRODUTO_REF}':\n")
for posicao, (produto, score) in enumerate(similares.head(TOP).items(), start=1):
    print(f"  {posicao}. {produto}  (similaridade: {score:.4f})")

# O primeiro colocado do ranking acima é o 'asdf', que não tem cara de nome de produto
# Para ver se era caso isolado, busquei todos os nomes que fogem do padrão da base, onde os produtos "legítimos" terminam com número
QUERY_NOMES = """
    SELECT
        p.id,
        p.name as produto,
        c.name as categoria,
        COUNT(DISTINCT o.customer_id) as clientes
    FROM products p
    JOIN categories c
        ON c.id = p.category_id
    LEFT JOIN product_variants pv
        ON pv.product_id = p.id
    LEFT JOIN order_items oi
        ON oi.product_variant_id = pv.id
    LEFT JOIN orders o
        ON o.id = oi.order_id
    WHERE p.name !~ '[0-9]$'
    GROUP BY p.id, p.name, c.name
    ORDER BY clientes DESC
"""

conn = psycopg2.connect(**CONEXAO)
suspeitos = pd.read_sql(QUERY_NOMES, conn)
conn.close()

print(f"\nProdutos com nome fora do padrão:\n")
print(suspeitos.to_string(index=False))

# Confirmado que são cadastros de teste (hipótese), e o 'asdf' ainda aparece duplicado
# Ele lidera por alcance de cadastro e não por relação real de compra, então refiz o ranking sem eles
ranking_limpo = similares.drop(suspeitos['produto'].unique().tolist(), errors='ignore')

print(f"\nRanking desconsiderando os cadastros inválidos:\n")
for posicao, (produto, score) in enumerate(ranking_limpo.head(TOP).items(), start=1):
    print(f"  {posicao}. {produto}  (similaridade: {score:.4f})")