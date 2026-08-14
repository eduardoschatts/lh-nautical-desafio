import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()  # Carrega as variáveis de ambiente do arquivo .env (Nesse caso a conexão com o banco de dados)
PASTA_CSV = "./data/lh_nautical_csv"

CONEXAO = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

arquivos = sorted(f for f in os.listdir(PASTA_CSV) if f.endswith(".csv"))

conn= psycopg2.connect(**CONEXAO)
cursor = conn.cursor()

for arquivo in arquivos:
    tabela = os.path.splitext(arquivo)[0]        # Nome do arquivo sem o final .csv
    caminho = os.path.join(PASTA_CSV, arquivo)  # Caminho completo até o arquivo

    with open(caminho, "r", encoding="utf-8") as f:
        cursor.copy_expert(
            f"COPY {tabela} FROM STDIN WITH (FORMAT csv, HEADER true)",
            f
        )
    print(f"ok: {tabela}")

conn.commit()
cursor.close()
conn.close()