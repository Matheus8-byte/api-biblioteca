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
    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'Livro'
""")

print("Estrutura da tabela 'Livro':")
for linha in cursor.fetchall():
    print(f"- {linha.COLUMN_NAME} | tipo: {linha.DATA_TYPE} | permite nulo: {linha.IS_NULLABLE} | tamanho: {linha.CHARACTER_MAXIMUM_LENGTH}")

conexao.close()