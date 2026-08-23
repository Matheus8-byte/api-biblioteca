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
df_editoras = pd.read_sql("SELECT * FROM Editora", conexao)
df_assuntos = pd.read_sql("SELECT * FROM Assunto", conexao)

conexao.close()

df_completo = df.merge(df_editoras, on="IdEditora").merge(df_assuntos, on="IdAssunto")

print("=== Preço médio por editora (com nome) ===")
print(df_completo.groupby("NomeEditora")["PrecoLivro"].mean())

print()
print("=== Quantidade de livros por assunto ===")
print(df_completo.groupby("NomeAssunto").size())

df_completo.to_excel("relatorio_acervo.xlsx", index=False, sheet_name="Acervo")
print()
print("Relatório salvo em relatorio_acervo.xlsx")