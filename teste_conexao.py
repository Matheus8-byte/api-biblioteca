import pyodbc

conexao = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=Biblioteca;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

cursor = conexao.cursor()
cursor.execute("SELECT name FROM sys.tables")

print("Tabelas encontradas no banco 'Biblioteca':")
for linha in cursor.fetchall():
    print("-", linha.name)

conexao.close()