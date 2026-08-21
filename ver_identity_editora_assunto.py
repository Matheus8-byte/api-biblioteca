import pyodbc

conexao = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=Biblioteca;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

cursor = conexao.cursor()
cursor.execute("""
    SELECT OBJECT_NAME(OBJECT_ID) AS Tabela, name AS Coluna
    FROM SYS.IDENTITY_COLUMNS
    WHERE OBJECT_NAME(OBJECT_ID) IN ('Editora', 'Assunto')
""")

resultado = cursor.fetchall()
if resultado:
    print("Colunas com auto-incremento (IDENTITY) encontradas:")
    for linha in resultado:
        print(f"- Tabela: {linha.Tabela} | Coluna: {linha.Coluna}")
else:
    print("Nenhuma coluna IDENTITY encontrada em Editora ou Assunto.")

conexao.close()