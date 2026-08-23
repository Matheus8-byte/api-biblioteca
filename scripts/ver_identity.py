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
    SELECT name
    FROM SYS.IDENTITY_COLUMNS
    WHERE OBJECT_NAME(OBJECT_ID) = 'Livro'
""")

resultado = cursor.fetchall()
if resultado:
    print("Coluna(s) com auto-incremento (IDENTITY):")
    for linha in resultado:
        print("-", linha.name)
else:
    print("Nenhuma coluna com IDENTITY nessa tabela — IdLivro precisa ser informado manualmente.")

conexao.close()