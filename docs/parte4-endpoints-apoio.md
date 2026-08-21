# Documentação (Parte 4) — Endpoints de apoio (Editoras e Assuntos)

Continuação da **Parte 3 — Postman + CRUD completo**. Nesta etapa: resolução de um gap de design de API identificado durante os testes de cadastro/atualização de livros.

---

## Motivação

Durante os testes de `POST`/`PUT` de livros, foi levantada a seguinte questão: os campos `IdEditora` e `IdAssunto` são obrigatórios e são chaves estrangeiras — mas **como um terceiro consumindo a API saberia quais IDs são válidos**, sem ter acesso direto ao banco de dados?

Até então, a API só "sabia" trabalhar com livros. Os dados de apoio (editoras e assuntos existentes) ficavam visíveis apenas para quem tinha acesso direto ao SQL Server.

**Problema real de design de API:** uma API bem projetada deve ser "autossuficiente" — ou seja, todo dado necessário para usá-la corretamente deve estar acessível através dela mesma, sem exigir que o consumidor tenha acesso a sistemas internos (como o banco de dados).

---

## Solução: endpoints de apoio (lookup endpoints)

Adicionados dois endpoints somente leitura, que expõem as tabelas de apoio usadas como chave estrangeira em `Livro`:

```
GET /editoras   → lista todas as editoras (IdEditora + NomeEditora)
GET /assuntos   → lista todos os assuntos (IdAssunto + NomeAssunto)
```

Com isso, o fluxo correto de uso da API passa a ser: primeiro consultar `GET /editoras` e `GET /assuntos` para descobrir os IDs disponíveis, e só então montar o `POST`/`PUT` de livro com IDs válidos.

> Esse padrão é chamado informalmente de **endpoint de apoio / lookup endpoint** — comum em qualquer API que tenha relacionamentos por chave estrangeira.

---

## Código adicionado ao `main.py`

```python
@app.get("/editoras")
def listar_editoras():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT IdEditora, NomeEditora FROM Editora ORDER BY NomeEditora")
    colunas = [coluna[0] for coluna in cursor.description]
    resultado = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    conexao.close()
    return resultado


@app.get("/assuntos")
def listar_assuntos():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT IdAssunto, NomeAssunto FROM Assunto ORDER BY NomeAssunto")
    colunas = [coluna[0] for coluna in cursor.description]
    resultado = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    conexao.close()
    return resultado
```

**Observações sobre a implementação:**
- Segue o mesmo padrão já usado em `GET /livros` (conecta, executa `SELECT`, converte para lista de dicionários, fecha conexão, retorna)
- **Não registram log** — decisão consciente, já que são endpoints de leitura simples, sem impacto em dados (diferente do `POST`/`PUT`/`DELETE` de livros, que alteram o banco e por isso precisam de auditoria)
- `ORDER BY NomeEditora` / `ORDER BY NomeAssunto` — ordenação alfabética, facilitando a leitura por quem for consumir a lista

---

## Endpoints atuais da API (visão geral após esta etapa)

| Método | Endpoint | Função |
|---|---|---|
| GET | `/livros` | Lista todos os livros |
| POST | `/livros` | Cadastra um novo livro |
| PUT | `/livros/{id}` | Atualiza um livro existente |
| DELETE | `/livros/{id}` | Remove um livro |
| GET | `/logs` | Consulta o log de integração/auditoria |
| **GET** | **`/editoras`** | **Lista as editoras disponíveis (novo)** |
| **GET** | **`/assuntos`** | **Lista os assuntos disponíveis (novo)** |

---

## Testes realizados

**GET /editoras** e **GET /assuntos** testados no Postman — ambos retornaram a lista completa de registros das respectivas tabelas, confirmando o funcionamento correto.

> **Nota operacional:** ao tentar acessar `/docs`, a conexão foi recusada porque o servidor uvicorn não estava mais rodando (havia sido encerrado anteriormente). Resolvido reiniciando com `python -m uvicorn main:app --reload` a partir da pasta correta do projeto.

---

## Roadmap atualizado

- [x] Endpoints de apoio (`GET /editoras`, `GET /assuntos`)
- [ ] Delete em lote
- [ ] Log do DELETE guardar o registro deletado
- [ ] Criar collection no Postman para reaproveitar as requisições
- [ ] (Opcional) Explorar SOAP/XML como comparação ao REST/JSON
- [ ] (Opcional) Adicionar validações extras (ex: checar se ISBN já existe antes de inserir)
- [ ] (Opcional) Variáveis de ambiente (.env) para não deixar a connection string no código
- [ ] (Opcional) Paginação no GET /livros
- [ ] (Opcional) Autenticação simples (API Key)

---

## Conceitos aprendidos nesta etapa

- Conceito de **API autossuficiente**: todo dado necessário para consumir a API corretamente deve estar acessível através dela mesma, sem depender de acesso direto ao banco
- Padrão de **endpoint de apoio / lookup endpoint**, comum em qualquer API com relacionamentos de chave estrangeira
- Decisão consciente de quando registrar log (operações que alteram dados) versus quando não é necessário (consultas simples de apoio)
- Reforço da rotina de verificação: sempre checar se o servidor uvicorn está rodando antes de testar (conexão recusada é sintoma comum de servidor parado)
