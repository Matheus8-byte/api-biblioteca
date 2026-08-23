import pandas as pd
import pyodbc

conexao = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=Biblioteca;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

df = pd.read_sql("SELECT * FROM Livro", conexao)
conexao.close()

# ISBN13 válido tem exatamente 13 dígitos numéricos
problematicos = df[df["ISBN13"].str.strip().str.len() != 13]

print("Livros com ISBN suspeito:")
print(problematicos[["IdLivro", "NomeLivro", "ISBN13"]])