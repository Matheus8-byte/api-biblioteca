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
    ALTER TABLE LogIntegracao
    ALTER COLUMN MetodoHttp VARCHAR(20) NOT NULL
""")
conexao.commit()

print("Coluna 'MetodoHttp' ajustada para VARCHAR(20) com sucesso!")

conexao.close()