# Import das bibliotecas CSV para leitura correta dos arquivos
# e OS para interação com o sistema operacional e montar caminhos de arquivos
import csv
import os
from datetime import datetime

PASTA_CSV = "./data/lh_nautical_csv"
ARQUIVO_SAIDA = "./sql/schema.sql"


# Função que recebe um valor e devolve o tipo de dado correspondente
def classificar_valor(valor):
    valor = valor.strip()

    if valor == "":
        return None  # Célula vazia não informa o tipo da coluna, vira NULL na carga

    if valor.upper() in ("TRUE", "FALSE"):
        return "BOOLEAN"

    # Valores compostos apenas por dígitos
    if valor.isdigit():
        # Zero à esquerda indica código, vira TEXT para não perder o zero (Ex: código de barras)
        if len(valor) > 1 and valor[0] == "0":
            return "TEXT"
        # Acima de 10 dígitos supera o limite do INTEGER (Ex: NFs, com mais de 10 dígitos, não cabem em INTEGER)
        if len(valor) > 10:
            return "TEXT"
        return "INTEGER"

    # Valores com casas decimais
    try:
        float(valor)
        return "NUMERIC"
    except ValueError:
        pass

    # Valores no formato Ano-Mês-Dia
    try:
        datetime.strptime(valor, "%Y-%m-%d")
        return "DATE"
    except ValueError:
        pass

    # Valores no formato Ano-Mês-Dia com Hora, Minuto e Segundo
    try:
        datetime.strptime(valor, "%Y-%m-%d %H:%M:%S")
        return "TIMESTAMP"
    except ValueError:
        pass

    # Se não for nenhum dos anteriores, considera como TEXT
    return "TEXT"


# Função que recebe todos os tipos encontrados em uma coluna e decide qual optar
def resolver_tipo_coluna(tipos):
    tipos = {t for t in tipos if t is not None}  # Descarta os None: ausência de valor não informa o tipo

    if not tipos:
        return "TEXT"  # Coluna sem nenhum valor preenchido; TEXT aceita qualquer dado futuro

    if tipos == {"INTEGER"}:
        return "INTEGER"

    # Coluna que mistura inteiros e decimais, NUMERIC comporta os dois
    if tipos <= {"INTEGER", "NUMERIC"}:
        return "NUMERIC"

    if tipos == {"DATE"}:
        return "DATE"

    # TIMESTAMP comporta datas com e sem hora, DATE descartaria a hora
    if tipos <= {"DATE", "TIMESTAMP"}:
        return "TIMESTAMP"

    if tipos == {"BOOLEAN"}:
        return "BOOLEAN"

    # Qualquer mistura incompatível (Ex: número com texto) cai em TEXT
    return "TEXT"


# Função que lê todas as linhas do CSV, devolvendo as colunas e seus tipos, optei por ler todas as linhas para ter uma maior precisão nos tipos
def inferir_tipos(caminho):
    # newline='' é exigido pelo módulo csv, evita linhas fantasma em arquivos com \r\n
    with open(caminho, newline='', encoding='utf-8') as f:
        leitor = csv.reader(f)
        colunas = [c.strip() for c in next(leitor)]  # Removendo espaços em branco dos nomes

        # Um conjunto por coluna, acumulando os tipos encontrados
        tipos_por_coluna = {c: set() for c in colunas}

        for linha in leitor:
            for j, coluna in enumerate(colunas):
                valor = linha[j] if j < len(linha) else ""  # Protege contra linhas com menos campos que o cabeçalho
                tipos_por_coluna[coluna].add(classificar_valor(valor))

    return colunas, {c: resolver_tipo_coluna(t) for c, t in tipos_por_coluna.items()}


# Função que monta a instrução CREATE TABLE de uma tabela
def gerar_create_table(tabela, colunas, tipos):
    # Aspas duplas protegem nomes de coluna que possam colidir com palavras reservadas do SQL
    definicoes = ",\n".join(f'    "{c}" {tipos[c]}' for c in colunas)
    # DROP TABLE IF EXISTS permite reexecutar o schema sem gerar erro
    return (
        f"DROP TABLE IF EXISTS {tabela} CASCADE;\n"
        f"CREATE TABLE {tabela} (\n{definicoes}\n);\n"
    )


# Listando todos os arquivos CSV da pasta e ordenando eles
arquivos = sorted(f for f in os.listdir(PASTA_CSV) if f.endswith('.csv'))

os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)

blocos = [
    "-- schema.sql a partir dos CSVs da LH Nautical, Desafio Lighthouse",
    f"-- Tabelas: {len(arquivos)}",
    "",
]

# Percorrendo um arquivo por vez
for arquivo in arquivos:
    tabela = os.path.splitext(arquivo)[0]        # Nome do arquivo sem o final .csv
    caminho = os.path.join(PASTA_CSV, arquivo)   # Caminho completo até o arquivo
    colunas, tipos = inferir_tipos(caminho)
    blocos.append(gerar_create_table(tabela, colunas, tipos))
    print(f"ok: {tabela} ({len(colunas)} colunas)")

# Gravando todas as instruções em um único arquivo .sql
with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
    f.write("\n".join(blocos))

print(f"\nSchema gerado em: {ARQUIVO_SAIDA}")

# Testando a função classificar_valor com alguns exemplos

#print(classificar_valor("1136"))                  # INTEGER
#print(classificar_valor("0812356442423"))         # TEXT  (zero à esquerda)
#print(classificar_valor("9211151388880545876555803054291602072324265"))  # TEXT (gigante)
#print(classificar_valor("323.34"))                # NUMERIC
#print(classificar_valor("paid"))                  # TEXT
#print(classificar_valor("TRUE"))                  # BOOLEAN
#print(classificar_valor(""))                      # None