# Documentação (Parte 3) — Overview do Postman + CRUD completo (PUT/DELETE)

Continuação da **Parte 2 — Log de Integração**. Nesta etapa: entendimento de como o Postman funciona por dentro (pra não depender de comandos prontos), e finalização do CRUD com os endpoints de atualização e remoção de livros.

---

## Parte A — Overview do Postman

### O que é

Um **cliente HTTP com interface gráfica**. Monta requisições HTTP (a mesma coisa que o navegador faz ao acessar um site) e mostra a resposta de forma organizada — sem precisar programar nada.

### Anatomia de uma requisição

1. **Método HTTP** — a "intenção" da requisição:
   - `GET` → buscar dados
   - `POST` → criar algo novo
   - `PUT` → atualizar algo existente (id vai na URL)
   - `DELETE` → remover algo (id vai na URL)
   - `PATCH` → atualização parcial (menos usado no dia a dia)

2. **URL** — endereço do recurso (ex: `http://127.0.0.1:8000/livros/120`)

3. **Headers** — metadados sobre a requisição, não o conteúdo em si. O mais comum: `Content-Type: application/json` (o Postman adiciona automaticamente ao escolher "JSON" no Body)

4. **Body** — o conteúdo enviado, geralmente só em `POST`/`PUT`/`PATCH`

5. **Send** — dispara a requisição

6. **Resposta** — status code, corpo (JSON), tempo de resposta, headers de resposta

### Diferença entre POST/GET e PUT/DELETE (onde vai o ID)

| Ação | Método | URL | Body |
|---|---|---|---|
| Criar livro | POST | `/livros` | JSON com todos os dados |
| Listar livros | GET | `/livros` | (nenhum) |
| Atualizar livro | PUT | `/livros/120` ← ID na URL | JSON com os dados novos |
| Remover livro | DELETE | `/livros/100` ← ID na URL | (nenhum, normalmente) |

Quando a ação afeta **um recurso específico já existente** (atualizar ou remover), o ID desse recurso vai na própria URL — padrão REST. Isso é implementado no FastAPI com `{id_livro}` na rota, um "espaço reservado" que o framework captura automaticamente e entrega como argumento da função:

```python
@app.delete("/livros/{id_livro}")
def deletar_livro(id_livro: int):
```

### Tipos de Body: raw, x-www-form-urlencoded, form-data, binary

| Tipo | O que é | Quando usar |
|---|---|---|
| **raw** | Conteúdo puro (texto cru); com o formato JSON selecionado no dropdown | APIs REST modernas — **é o que usamos no projeto** |
| **x-www-form-urlencoded** | Pares `chave=valor` unidos por `&`, formato clássico de formulário HTML (`nome=Duna&preco=59.90`) | Formulários HTML simples, sem arquivos |
| **form-data** | Pares chave-valor que também suportam **upload de arquivo** (texto + binário misturados) | Formulários com upload de arquivo(s) junto com texto (ex: cadastro com foto de capa) |
| **binary** | Um único arquivo puro, sem campos nomeados | Upload de um único arquivo (ex: endpoint que só recebe uma imagem) |

No projeto atual (FastAPI + Pydantic), sempre usamos **raw + JSON**, pois é o formato esperado pelo modelo `LivroEntrada`.

### Outras funcionalidades do Postman (para explorar futuramente)

- **Collections** — pastas que guardam requisições salvas, para reaproveitar depois
- **Environments** — variáveis reutilizáveis (ex: `{{base_url}}`), úteis ao alternar entre ambiente local e produção
- **Params** — aba que monta parâmetros de URL visualmente (ex: `?page=1&limit=10`)
- **Tests/Scripts** — scripts JavaScript que rodam após a resposta, para validações automáticas (ex: checar se o status foi 200)
- **History** — histórico de tudo que já foi enviado, mesmo sem salvar em uma Collection

---

## Parte B — CRUD completo (PUT + DELETE)

### Motivação

A API já tinha `POST` (criar) e `GET` (listar). Faltavam `PUT` (atualizar) e `DELETE` (remover) para completar o CRUD (Create, Read, Update, Delete).

### Discussão prévia: e as chaves estrangeiras no DELETE?

Antes de implementar, foi levantada a dúvida: o que acontece ao tentar deletar um livro que tem vínculos em outra tabela (`LivroAutor`, relação N:N entre livros e autores)?

**Decisão de design tomada:** manter o comportamento padrão do banco — se o livro tiver vínculos, o `DELETE` **falha** com erro de integridade referencial, em vez de deletar em cascata. Essa é a opção mais segura e mais realista de sistemas em produção (evita deleção acidental de dados relacionados).

### Código adicionado ao `main.py`

```python
@app.put("/livros/{id_livro}")
def atualizar_livro(id_livro: int, livro: LivroEntrada):
    payload_json = livro.model_dump_json()
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        cursor.execute("""
            UPDATE Livro
            SET NomeLivro = ?, ISBN13 = ?, DataPub = ?, PrecoLivro = ?,
                NumeroPaginas = ?, IdEditora = ?, IdAssunto = ?, Edicao = ?
            WHERE IdLivro = ?
        """, livro.NomeLivro, livro.ISBN13, livro.DataPub, livro.PrecoLivro,
             livro.NumeroPaginas, livro.IdEditora, livro.IdAssunto, livro.Edicao, id_livro)

        if cursor.rowcount == 0:
            registrar_log(f"/livros/{id_livro}", "PUT", payload_json, "ERRO", mensagem_erro="Livro não encontrado")
            raise HTTPException(status_code=404, detail="Livro não encontrado")

        conexao.commit()
        registrar_log(f"/livros/{id_livro}", "PUT", payload_json, "SUCESSO", id_gerado=id_livro)
        return {"mensagem": "Livro atualizado com sucesso!", "IdLivro": id_livro}

    except pyodbc.Error as e:
        conexao.rollback()
        registrar_log(f"/livros/{id_livro}", "PUT", payload_json, "ERRO", mensagem_erro=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conexao.close()


@app.delete("/livros/{id_livro}")
def deletar_livro(id_livro: int):
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        cursor.execute("DELETE FROM Livro WHERE IdLivro = ?", id_livro)

        if cursor.rowcount == 0:
            registrar_log(f"/livros/{id_livro}", "DELETE", None, "ERRO", mensagem_erro="Livro não encontrado")
            raise HTTPException(status_code=404, detail="Livro não encontrado")

        conexao.commit()
        registrar_log(f"/livros/{id_livro}", "DELETE", None, "SUCESSO", id_gerado=id_livro)
        return {"mensagem": "Livro removido com sucesso!", "IdLivro": id_livro}

    except pyodbc.Error as e:
        conexao.rollback()
        registrar_log(f"/livros/{id_livro}", "DELETE", None, "ERRO", mensagem_erro=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conexao.close()
```

**Pontos técnicos importantes:**
- `{id_livro}` na rota — parâmetro de caminho (path parameter); o FastAPI captura o valor da URL automaticamente
- `cursor.rowcount` — indica quantas linhas foram afetadas. Se `0`, o `IdLivro` não existe → retorna **404 (Not Found)**
- Ambos os endpoints também gravam log (sucesso ou erro), mantendo a auditoria completa

---

## Testes realizados

### Teste 1 — PUT (sucesso)

Atualização do livro "Neuromancer" (`IdLivro: 120`):

```json
{
  "NomeLivro": "Neuromancer",
  "ISBN13": "9788576570032",
  "DataPub": "1984-07-01",
  "PrecoLivro": 39.90,
  "NumeroPaginas": 320,
  "IdEditora": 3,
  "IdAssunto": 1,
  "Edicao": 2
}
```

**Mudanças:** `PrecoLivro` de 49.90 → 39.90, `Edicao` de 1 → 2.

**Resultado:** sucesso, confirmado tanto na resposta da API quanto consultando `SELECT * FROM Livro WHERE IdLivro = 120` diretamente no banco.

> **Erro encontrado durante o teste:** a requisição retornou `{"detail": "Method Not Allowed"}`. Causa: o método no Postman ainda estava configurado como **POST** (herdado de uma requisição duplicada/anterior), enquanto a URL já apontava para `/livros/120`. Corrigido trocando o método para **PUT** no dropdown do Postman.

### Teste 2 — DELETE (sucesso, livro sem vínculo)

Antes de deletar, foi necessário identificar um livro sem vínculo na tabela `LivroAutor` (relação N:N com autores), pois um livro vinculado bloquearia a exclusão:

```sql
SELECT L.IdLivro, L.NomeLivro
FROM Livro L
LEFT JOIN LivroAutor LA ON L.IdLivro = LA.IdLivro
WHERE LA.IdLivro IS NULL;
```

Resultado: `IdLivro: 100` ("A Arte da Eletrônica").

**Requisição:** `DELETE http://127.0.0.1:8000/livros/100`

**Resultado:**
```json
{
    "mensagem": "Livro removido com sucesso!",
    "IdLivro": 100
}
```

> **Nota de segurança confirmada durante o teste:** o `DELETE FROM Livro WHERE IdLivro = ?` só afeta a linha do ID informado na URL — nunca a tabela inteira. Diferente de um `DELETE FROM Livro` sem `WHERE`, que apagaria todos os registros (nunca usado no projeto).

### Teste 3 — DELETE (erro, livro com vínculo em LivroAutor)

**Gap identificado:** a tabela `LivroAutor` ainda não tinha nenhum registro populado, impossibilitando testar o cenário de erro por FK. Foi inserido manualmente um vínculo de teste:

```
IdLivro: 101, IdAutor: 1
```

**Requisição:** `DELETE http://127.0.0.1:8000/livros/101`

**Resultado (status 400):**
```json
{
    "detail": "('23000', '[23000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]A instrução DELETE conflitou com a restrição do REFERENCE \"fk_id_livros\". O conflito ocorreu no banco de dados \"Biblioteca\", tabela \"dbo.LivroAutor\", column \\'IdLivro\\'. (547) (SQLExecDirectW); [23000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]A instrução foi finalizada. (3621)')"
}
```

**Log correspondente confirmado no banco:**

| IdLog | Endpoint | MetodoHttp | PayloadRecebido | Status | IdGerado |
|---|---|---|---|---|---|
| 6 | /livros/101 | DELETE | NULL | ERRO | NULL |

**Conclusão:** a proteção de integridade referencial funcionou como esperado — o SQL Server bloqueou o DELETE, a API capturou o erro corretamente (retornando 400 em vez de quebrar), e o log registrou a tentativa com falha.

---

## Gap identificado: log do DELETE não guarda os dados do registro deletado

Durante a revisão do log do Teste 3, foi notado que `PayloadRecebido` vem sempre `NULL` nas chamadas de `DELETE` — porque o método não recebe Body, então não há payload para registrar.

**Problema:** isso significa que o log mostra *que* um livro foi deletado (ou tentativa de deleção), mas não mostra **quais eram os dados daquele livro** — o que é essencial para um log de auditoria de verdade (ex: investigar depois "o que exatamente foi apagado").

**Melhoria proposta (adicionada ao roadmap):** antes de executar o `DELETE`, buscar os dados completos do registro (`SELECT * FROM Livro WHERE IdLivro = ?`) e gravar esse "retrato" do livro no campo `PayloadRecebido` do log — preservando a informação mesmo após a exclusão.

---

## Roadmap atualizado

- [x] CRUD completo (PUT + DELETE)
- [x] Testes de sucesso e erro no PUT e DELETE
- [ ] **Endpoints de apoio** (`GET /editoras`, `GET /assuntos`) — para que terceiros consumindo a API consigam descobrir os IDs válidos de `IdEditora`/`IdAssunto` sem acessar o banco diretamente
- [ ] **Delete em lote** — permitir deletar múltiplos registros de uma vez (opções avaliadas: query string com IDs separados por vírgula, endpoint dedicado `POST /livros/delete-batch` com lista de IDs no body, ou delete por filtro)
- [ ] **Log do DELETE guardar o registro deletado** — buscar os dados do livro antes de deletar e salvar no `PayloadRecebido` do log
- [ ] Criar collection no Postman para reaproveitar as requisições
- [ ] (Opcional) Explorar SOAP/XML como comparação ao REST/JSON
- [ ] (Opcional) Adicionar validações extras (ex: checar se ISBN já existe antes de inserir)
- [ ] (Opcional) Variáveis de ambiente (.env) para não deixar a connection string no código
- [ ] (Opcional) Paginação no GET /livros
- [ ] (Opcional) Autenticação simples (API Key)

---

## Conceitos aprendidos nesta etapa

- Anatomia de uma requisição HTTP no Postman: método, URL, headers, body, resposta
- Diferença entre os métodos HTTP e onde cada um coloca a informação relevante (URL vs Body)
- Diferença prática entre os 4 tipos de Body no Postman: `raw`, `x-www-form-urlencoded`, `form-data`, `binary` — e quando cada um é usado no mercado
- Path parameters no FastAPI (`{id_livro}`) — como a URL vira argumento de função
- `cursor.rowcount` como forma de saber se um UPDATE/DELETE realmente afetou alguma linha (útil para diferenciar "não existe" de "erro real")
- Decisão de design consciente sobre **não** deletar em cascata — proteção de integridade referencial como comportamento padrão mais seguro
- Importância de simular cenários de erro de propósito (livro com vínculo em FK) para validar que o sistema de log e tratamento de erros está realmente robusto, não só o caminho feliz
- Identificação de um gap real de auditoria (log de DELETE sem o retrato do dado apagado) — um exercício de pensar em log não só como "registro de chamada", mas como ferramenta de investigação futura
