import pandas as pd

dados = [
    {"IdLivro": 101, "NomeLivro": "Vinte Mil Léguas Submarinas", "PrecoLivro": 24.50},
    {"IdLivro": 106, "NomeLivro": "1984", "PrecoLivro": 29.67},
    {"IdLivro": 130, "NomeLivro": "Clean Code", "PrecoLivro": 0.00},
]

df = pd.DataFrame(dados)

print(df)
print()
print("Tipo de 'df':", type(df))
print()
print("Preço médio:", df["PrecoLivro"].mean())