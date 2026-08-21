# Documentação (Parte 2) — Log de Integração (Auditoria de chamadas da API)

Continuação da **Parte 1 — Setup inicial**, onde a API REST em Python (FastAPI) já estava rodando e conectada ao banco `Biblioteca` no SQL Server, com o cadastro de livros (`POST /livros`) funcionando via Postman.

## Motivação

Manter um registro de auditoria de tudo que é enviado para a API — histórico de chamadas, sucesso ou erro, payload recebido, e o ID gerado (quando aplicável). Isso é uma prática comum em sistemas reais, geralmente chamada de **log de auditoria** ou **log de integração**.

**O que a tabela guarda:**
- Data/hora da chamada
- Endpoint chamado (ex: `/livros`)
- Método HTTP (POST, GET, etc.)
- Payload recebido (o JSON, como texto)
- Status (sucesso ou erro)
- Mensagem de erro (se houver)
- ID gerado (se foi um cadastro bem-sucedido)

---

## Passo 1 — Criar a tabela `LogIntegracao`

Criada diretamente no banco (via SSMS/sqlcmd, decisão de rodar DDL direto no banco em vez de via Python):

```sql
USE Biblioteca;
GO

CREATE TABLE LogIntegracao (
    IdLog INT IDENTITY(1,1) PRIMARY KEY,
    DataHora DATETIME NOT NULL DEFAULT GETDATE(),
    Endpoint VARCHAR(100) NOT NULL,
    MetodoHttp VARCHAR(10) NOT NULL,
    PayloadRecebido NVARCHAR(MAX) NULL,
    Status VARCHAR(20) NOT NULL,
    MensagemErro NVARCHAR(500) NULL,
    IdGerado INT NULL
);
GO
```

---

## Passo 2 — Atualizar o `main.py` para gravar o log

Foi adicionada a função `registrar_log()`, chamada tanto no caminho de sucesso quanto no de erro dentro do `POST /livros`, além de um novo endpoint `GET /logs` para consultar o histórico pela própria API.

**Arquivo completo atualizado (`main.py`):**

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date
from typing import Optional
import pyodbc
import json

app = FastAPI()

def get_conexao():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=Biblioteca;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

def registrar_log(endpoint, metodo, payload, status, mensagem_erro=None, id_gerado=None):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("""
        INSERT INTO LogIntegracao (Endpoint, MetodoHttp, PayloadRecebido, Status, MensagemErro, IdGerado)
        VALUES (?, ?, ?, ?, ?, ?)
    """, endpoint, metodo, payload, status, mensagem_erro, id_gerado)
    conexao.commit()
    conexao.close()

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
    payload_json = livro.model_dump_json()
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

        registrar_log("/livros", "POST", payload_json, "SUCESSO", id_gerado=novo_id)

        return {"mensagem": "Livro cadastrado com sucesso!", "IdLivro": novo_id}

    except pyodbc.Error as e:
        conexao.rollback()
        registrar_log("/livros", "POST", payload_json, "ERRO", mensagem_erro=str(e))
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

@app.get("/logs")
def listar_logs():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM LogIntegracao ORDER BY DataHora DESC")
    colunas = [coluna[0] for coluna in cursor.description]
    resultado = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    conexao.close()
    return resultado
```

**Pontos-chave da implementação:**
- `payload_json = livro.model_dump_json()` — serializa o objeto Pydantic recebido de volta para uma string JSON, para guardar exatamente o que foi enviado
- Em caso de sucesso: `registrar_log("/livros", "POST", payload_json, "SUCESSO", id_gerado=novo_id)`
- Em caso de erro: `registrar_log("/livros", "POST", payload_json, "ERRO", mensagem_erro=str(e))`
- O log é gravado com uma **conexão separada** dentro de `registrar_log()`, então ele é salvo independentemente do sucesso ou falha da operação principal

> **Erro comum encontrado neste passo:** ao reiniciar o servidor após editar o `main.py`, o terminal (PowerShell) estava na pasta errada (`C:\Users\Matheus` em vez de `C:\projetos\api-biblioteca`), fazendo com que o `notepad main.py` criasse/editasse um arquivo diferente do projeto. O uvicorn subia normalmente, mas rodando a versão antiga do código (sem os endpoints novos). Foi identificado ao conferir a lista de endpoints em `/docs` — o `/logs` não aparecia. Corrigido navegando para a pasta certa com `cd` antes de editar e rodar o servidor novamente.

---

## Passo 3 — Testar cenário de sucesso

**Requisição POST → `http://127.0.0.1:8000/livros`:**

```json
{
  "NomeLivro": "Neuromancer",
  "ISBN13": "9788576570032",
  "DataPub": "1984-07-01",
  "PrecoLivro": 49.90,
  "NumeroPaginas": 320,
  "IdEditora": 3,
  "IdAssunto": 1,
  "Edicao": 1
}
```

**Resultado:** cadastrado com sucesso (`IdLivro: 120`).

**Conferência do log via GET → `http://127.0.0.1:8000/logs`:**

```json
[
    {
        "IdLog": 1,
        "DataHora": "2026-08-16T16:35:03.477000",
        "Endpoint": "/livros",
        "MetodoHttp": "POST",
        "PayloadRecebido": "{\"NomeLivro\":\"Neuromancer\",\"ISBN13\":\"9788576570032\",\"DataPub\":\"1984-07-01\",\"PrecoLivro\":49.9,\"NumeroPaginas\":320,\"IdEditora\":3,\"IdAssunto\":1,\"Edicao\":1}",
        "Status": "SUCESSO",
        "MensagemErro": null,
        "IdGerado": 120
    }
]
```

Log gravado corretamente, com o payload completo, status `SUCESSO` e o `IdGerado` batendo com o `IdLivro` retornado.

---

## Passo 4 — Testar cenário de erro (de propósito)

Para validar que o log também registra falhas, foi enviado um cadastro com `IdEditora: 999` (inexistente na tabela `Editora`), forçando uma violação de chave estrangeira:

**Requisição POST → `http://127.0.0.1:8000/livros`:**

```json
{
  "NomeLivro": "Livro Teste Erro",
  "ISBN13": "9999999999999",
  "DataPub": "2024-01-01",
  "PrecoLivro": 10.00,
  "NumeroPaginas": 100,
  "IdEditora": 999,
  "IdAssunto": 1,
  "Edicao": 1
}
```

**Resposta da API (status 400):**

```json
{
    "detail": "('23000', '[23000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]A instrução INSERT conflitou com a restrição do FOREIGN KEY \"fk_id_editora\". O conflito ocorreu no banco de dados \"Biblioteca\", tabela \"dbo.Editora\", column \\'IdEditora\\'. (547) (SQLExecDirectW); [23000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]A instrução foi finalizada. (3621)')"
}
```

**Registro correspondente na tabela `LogIntegracao`** (confirmado tanto via `GET /logs` quanto consultando o banco diretamente):

| IdLog | DataHora | Endpoint | MetodoHttp | Status | MensagemErro | IdGerado |
|---|---|---|---|---|---|---|
| 2 | 2026-08-16 16:35:50.587 | /livros | POST | ERRO | (mensagem de erro do SQL Server, violação da FK `fk_id_editora`) | NULL |

**Conclusão:** o log captura tanto chamadas bem-sucedidas quanto falhas, sem interromper o funcionamento da API — exatamente o comportamento esperado de um log de auditoria/integração. A API respondeu com o erro apropriado (400) ao cliente, e o banco manteve o histórico completo da tentativa.

---

## Próximos passos

- [x] Criar tabela de log de integração (`LogIntegracao`)
- [x] Gravar log em caso de sucesso
- [x] Gravar log em caso de erro
- [x] Endpoint `GET /logs` para consulta via API
- [ ] Criar collection no Postman para reaproveitar as requisições
- [ ] (Opcional) Explorar SOAP/XML como comparação ao REST/JSON
- [ ] (Opcional) Adicionar endpoints de UPDATE e DELETE
- [ ] (Opcional) Adicionar validações extras (ex: checar se ISBN já existe antes de inserir)
- [ ] (Opcional) Registrar log também no `GET /livros` (hoje só o POST é logado)
- [ ] (Opcional) Adicionar log genérico/reutilizável para outros endpoints futuros, sem repetir a lógica em cada rota

---

## Conceitos aprendidos nesta etapa

- Conceito de **log de integração/auditoria**: registrar toda chamada recebida por uma API (payload, sucesso/erro, timestamp) para rastreabilidade futura
- Uso de `try/except/finally` em Python para garantir que o log seja registrado tanto no caminho de sucesso quanto no de erro, sem impedir o `HTTPException` de ser lançado corretamente
- `model_dump_json()` do Pydantic para serializar o corpo recebido de volta em JSON antes de persistir
- Como um erro de integridade referencial (`FOREIGN KEY`) se propaga do SQL Server → pyodbc → FastAPI (`HTTPException`) → resposta HTTP 400 para o cliente
- A importância de sempre confirmar a pasta ativa do terminal antes de editar/rodar arquivos, já que rodar o comando certo na pasta errada não gera nenhum erro visível — só um comportamento silenciosamente incorreto
