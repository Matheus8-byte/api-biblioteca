import pyodbc
from dotenv import load_dotenv
import os

load_dotenv()

conexao = pyodbc.connect(
    f"DRIVER={os.getenv('DB_DRIVER')};"
    f"SERVER={os.getenv('DB_SERVER')};"
    f"DATABASE={os.getenv('DB_DATABASE')};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)
cursor = conexao.cursor()

print("=" * 70)
print("TABELAS E COLUNAS")
print("=" * 70)
cursor.execute("""
    SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
           IS_NULLABLE, COLUMN_DEFAULT
    FROM INFORMATION_SCHEMA.COLUMNS
    ORDER BY TABLE_NAME, ORDINAL_POSITION
""")
for linha in cursor.fetchall():
    tamanho = f"({linha.CHARACTER_MAXIMUM_LENGTH})" if linha.CHARACTER_MAXIMUM_LENGTH else ""
    print(f"{linha.TABLE_NAME}.{linha.COLUMN_NAME} | {linha.DATA_TYPE}{tamanho} | "
          f"Nulo: {linha.IS_NULLABLE} | Default: {linha.COLUMN_DEFAULT}")

print()
print("=" * 70)
print("CHAVES PRIMÁRIAS")
print("=" * 70)
cursor.execute("""
    SELECT KU.TABLE_NAME, KU.COLUMN_NAME
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS TC
    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE KU
        ON TC.CONSTRAINT_NAME = KU.CONSTRAINT_NAME
    WHERE TC.CONSTRAINT_TYPE = 'PRIMARY KEY'
    ORDER BY KU.TABLE_NAME
""")
for linha in cursor.fetchall():
    print(f"{linha.TABLE_NAME}.{linha.COLUMN_NAME}")

print()
print("=" * 70)
print("CHAVES ESTRANGEIRAS (RELACIONAMENTOS)")
print("=" * 70)
cursor.execute("""
    SELECT
        FK.TABLE_NAME AS TabelaOrigem,
        CU.COLUMN_NAME AS ColunaOrigem,
        PK.TABLE_NAME AS TabelaDestino,
        PT.COLUMN_NAME AS ColunaDestino,
        C.CONSTRAINT_NAME AS NomeConstraint
    FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS C
    JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS FK
        ON C.CONSTRAINT_NAME = FK.CONSTRAINT_NAME
    JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS PK
        ON C.UNIQUE_CONSTRAINT_NAME = PK.CONSTRAINT_NAME
    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE CU
        ON C.CONSTRAINT_NAME = CU.CONSTRAINT_NAME
    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE PT
        ON C.UNIQUE_CONSTRAINT_NAME = PT.CONSTRAINT_NAME
    ORDER BY FK.TABLE_NAME
""")
for linha in cursor.fetchall():
    print(f"{linha.TabelaOrigem}.{linha.ColunaOrigem} -> {linha.TabelaDestino}.{linha.ColunaDestino} "
          f"(constraint: {linha.NomeConstraint})")

print()
print("=" * 70)
print("COLUNAS IDENTITY (AUTO-INCREMENTO)")
print("=" * 70)
cursor.execute("""
    SELECT OBJECT_NAME(OBJECT_ID) AS Tabela, name AS Coluna
    FROM SYS.IDENTITY_COLUMNS
""")
for linha in cursor.fetchall():
    print(f"{linha.Tabela}.{linha.Coluna}")

print()
print("=" * 70)
print("RESTRIÇÕES UNIQUE")
print("=" * 70)
cursor.execute("""
    SELECT KU.TABLE_NAME, KU.COLUMN_NAME, TC.CONSTRAINT_NAME
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS TC
    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE KU
        ON TC.CONSTRAINT_NAME = KU.CONSTRAINT_NAME
    WHERE TC.CONSTRAINT_TYPE = 'UNIQUE'
    ORDER BY KU.TABLE_NAME
""")
for linha in cursor.fetchall():
    print(f"{linha.TABLE_NAME}.{linha.COLUMN_NAME} (constraint: {linha.CONSTRAINT_NAME})")

conexao.close()