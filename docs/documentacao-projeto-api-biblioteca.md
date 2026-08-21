# Documentação — API REST em Python conectada ao SQL Server (Banco Biblioteca)

Este documento registra o passo a passo seguido para conectar um banco SQL Server local a uma API REST feita em Python (FastAPI), testável via Postman. Serve como referência para revisão futura.

## Objetivo do projeto

Aprender a fazer chamadas HTTP (via Postman) para cadastrar dados em um banco SQL Server, usando uma API REST (JSON) como camada intermediária entre o Postman e o banco de dados.

**Conceito-chave:** nem o Postman nem o SOAP conversam diretamente com o banco de dados. Eles falam HTTP. É necessária uma API no meio, que recebe a requisição HTTP, executa o SQL no banco e devolve a resposta.

---

## Ambiente

- **Sistema operacional:** Windows
- **Banco de dados:** SQL Server Express (instância `SQLEXPRESS`)
- **Banco usado:** `Biblioteca`
- **Autenticação:** Windows Authentication (Trusted Connection)
- **Linguagem da API:** Python 3.14.7
- **Framework:** FastAPI + Uvicorn
- **Driver de conexão:** pyodbc + ODBC Driver 18 for SQL Server
- **Pasta do projeto:** `C:\projetos\api-biblioteca`

---

## Passo 1 — Descobrir a instância do SQL Server

O nome do servidor não estava óbvio. Foi localizado através dos serviços do Windows:

```
sc query state= all | findstr "SQL"
```

Resultado relevante:
```
NOME_DO_SERVIÇO: MSSQL$SQLEXPRESS
NOME_PARA_EXIBIÇÃO: SQL Server (SQLEXPRESS)
```

**Conclusão:** o nome de conexão da instância é:
```
localhost\SQLEXPRESS
```

---

## Passo 2 — Testar conexão via sqlcmd

Primeira tentativa (deu erro de certificado SSL):
```
sqlcmd -S localhost\SQLEXPRESS -E
```

Erro:
```
Sqlcmd: Erro: Microsoft ODBC Driver 18 for SQL Server : Provedor SSL: A cadeia de certificação foi emitida por uma autoridade que não é de confiança.
```

**Causa:** o ODBC Driver 18 exige criptografia com certificado confiável por padrão. O SQL Server local usa certificado autoassinado.

**Solução:** adicionar a flag `-C` (confiar no certificado do servidor):
```
sqlcmd -S localhost\SQLEXPRESS -E -C
```

Conectou com sucesso. Teste de listagem de bancos:
```sql
SELECT name FROM sys.databases;
GO
```

Resultado: `master`, `tempdb`, `model`, `msdb`, **`Biblioteca`**

> **Nota importante:** essa mesma questão do certificado se repete na conexão via Python — resolvida com o parâmetro `TrustServerCertificate=yes` na connection string.

---

## Passo 3 — Instalar o Python

- Baixado em [python.org/downloads](https://www.python.org/downloads/)
- Durante a instalação: aceitar a atualização de "long paths" (caminhos longos) e adicionar o diretório de comandos ao PATH
- Versão instalada: **Python 3.14.7**

Verificação:
```
python --version
pip --version
```

---

## Passo 4 — Instalar as bibliotecas Python

```
pip install fastapi uvicorn pyodbc
```

Pacotes principais instalados:
- `fastapi` — framework da API
- `uvicorn` — servidor ASGI que roda a API
- `pyodbc` — driver de conexão com o SQL Server

---

## Passo 5 — Criar a pasta do projeto

```
mkdir C:\projetos\api-biblioteca
cd C:\projetos\api-biblioteca
```

---

## Passo 6 — Testar a conexão Python → SQL Server

Arquivo: `teste_conexao.py`

```python
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
```

**Resultado:** conexão funcionou. Tabelas encontradas: `Surf`, `Autor`, `Editora`, `Assunto`, `Livro`, `LivroAutor`, `sysdiagrams`.

---

## Passo 7 — Levantar a estrutura da tabela `Livro`

Arquivo: `ver_estrutura.py`

```python
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
```

**Resultado — colunas da tabela `Livro`:**

| Coluna | Tipo | Permite nulo | Tamanho |
|---|---|---|---|
| IdLivro | smallint | NO | — |
| NomeLivro | varchar | NO | 70 |
| ISBN13 | char | NO | 13 |
| DataPub | date | YES | — |
| PrecoLivro | money | NO | — |
| NumeroPaginas | smallint | NO | — |
| IdEditora | smallint | NO | — (chave estrangeira → Editora) |
| IdAssunto | tinyint | NO | — (chave estrangeira → Assunto) |
| Edicao | tinyint | YES | — |

---

## Passo 8 — Verificar se `IdLivro` é auto-incremento (IDENTITY)

Arquivo: `ver_identity.py`

```python
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
```

**Resultado:** `IdLivro` é IDENTITY (auto-incremento). Por isso, **não** é enviado no JSON de cadastro — o próprio SQL Server gera o valor.

> **Nota técnica:** `sys.identity_columns` usa a coluna `name`, diferente das views `INFORMATION_SCHEMA` que usam `COLUMN_NAME`. Isso gerou um erro na primeira tentativa (`Nome de coluna 'COLUMN_NAME' inválido`), corrigido trocando para `name`.

---

## Passo 9 — Criar a API (main.py)

Arquivo: `main.py`

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date
from typing import Optional
import pyodbc

app = FastAPI()

def get_conexao():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=Biblioteca;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

# Modelo dos dados que a API espera receber (JSON)
class LivroEntrada(BaseModel):
    NomeLivro: str
    ISBN13: str
    DataPub: Optional[date] = None
    PrecoLivro: float
    NumeroPaginas: int
    IdEditora: int
    IdAssunto: int
    Edicao: Optional[int] = None

@app.post("/livros")
def criar_livro(livro: LivroEntrada):
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        cursor.execute("""
            INSERT INTO Livro (NomeLivro, ISBN13, DataPub, PrecoLivro, NumeroPaginas, IdEditora, IdAssunto, Edicao)
            OUTPUT INSERTED.IdLivro
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, livro.NomeLivro, livro.ISBN13, livro.DataPub, livro.PrecoLivro,
             livro.NumeroPaginas, livro.IdEditora, livro.IdAssunto, livro.Edicao)

        novo_id = cursor.fetchone()[0]
        conexao.commit()
        return {"mensagem": "Livro cadastrado com sucesso!", "IdLivro": novo_id}

    except pyodbc.Error as e:
        conexao.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conexao.close()

@app.get("/livros")
def listar_livros():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT IdLivro, NomeLivro, ISBN13, PrecoLivro FROM Livro")
    colunas = [coluna[0] for coluna in cursor.description]
    resultado = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    conexao.close()
    return resultado
```

**Endpoints criados:**
- `POST /livros` — cadastra um livro novo
- `GET /livros` — lista os livros existentes

---

## Passo 10 — Rodar o servidor

Comando `uvicorn main:app --reload` direto **não funcionou** (erro "não é reconhecido como comando"), porque o executável do uvicorn não estava no PATH.

**Solução:** rodar via módulo do Python:

```
python -m uvicorn main:app --reload
```

**Resultado:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Servidor no ar, disponível em `http://127.0.0.1:8000`.

Documentação automática (Swagger UI) disponível em:
```
http://127.0.0.1:8000/docs
```

---

## Passo 11 — Testar no Postman (em andamento)

Requisição de cadastro de livro:

- **Método:** POST
- **URL:** `http://127.0.0.1:8000/livros`
- **Body → raw → JSON:**

```json
{
  "NomeLivro": "O Senhor dos Anéis",
  "ISBN13": "9788533613379",
  "DataPub": "1954-07-29",
  "PrecoLivro": 89.90,
  "NumeroPaginas": 1200,
  "IdEditora": 1,
  "IdAssunto": 1,
  "Edicao": 1
}
```

> **Atenção:** como `IdEditora` e `IdAssunto` são chaves estrangeiras, os IDs usados precisam já existir nas tabelas `Editora` e `Assunto`, senão a inserção falha com erro de integridade referencial.

---

## Próximos passos (a continuar)

- [ ] Confirmar registros existentes em `Editora` e `Assunto` antes de cadastrar um livro
- [ ] Testar o `POST /livros` no Postman
- [ ] Testar o `GET /livros` no Postman
- [ ] Criar collection no Postman para reaproveitar as requisições
- [ ] (Opcional) Explorar SOAP/XML como comparação ao REST/JSON
- [ ] (Opcional) Adicionar endpoints de UPDATE e DELETE
- [ ] (Opcional) Adicionar validações extras (ex: checar se ISBN já existe antes de inserir)

---

## Conceitos aprendidos até aqui

- Diferença entre banco de dados, API e cliente HTTP (Postman/SOAP) — cada um fala um "idioma" diferente
- Como descobrir a instância de um SQL Server instalado localmente
- Erro comum de certificado SSL com ODBC Driver 18 e como resolver (`TrustServerCertificate=yes`)
- Como consultar metadados do banco (`INFORMATION_SCHEMA.COLUMNS`, `sys.identity_columns`) para entender uma tabela antes de programar contra ela
- Estrutura básica de uma API FastAPI: modelo de dados (Pydantic), rota POST com inserção no banco, rota GET com listagem
- Uso de `OUTPUT INSERTED.<coluna>` no SQL Server para recuperar o ID gerado automaticamente após um INSERT
- Como contornar problema de PATH rodando pacotes via `python -m <pacote>`
