# Documentação (Parte 12) — Paginação e validação de ISBN duplicado

Continuação da **Parte 11 — Consumindo uma API externa (Google Books)**. Conclusão da **Fase 4** do Plano de Estudos. Nesta etapa: duas melhorias na API já existente — paginação no `GET /livros` e uma resposta mais clara para cadastro de ISBN duplicado.

---

## Parte A — Paginação no `GET /livros`

### Motivação

O endpoint `GET /livros` sempre retornou **todos** os registros de uma vez, numa lista só. Funciona com poucos dados, mas não escala: em uma tabela com muitos registros, isso gera respostas lentas e pesadas. Paginação é o padrão de mercado para resolver isso — o cliente pede uma "página" de resultados por vez, em vez da tabela inteira.

### Decisão de design: formato da resposta

Discutidas duas abordagens: devolver só a lista de livros (formato simples, igual ao que já existia) ou devolver a lista **junto com metadados** (total de registros, página atual, total de páginas).

**Decisão tomada:** incluir os metadados — padrão mais comum em APIs maduras, permite que quem consome a API saiba de antemão quantas páginas existem, sem precisar "adivinhar" tentando páginas sucessivas até encontrar uma vazia.

### Código implementado

```python
@app.get("/livros")
def listar_livros(page: int = 1, limit: int = 10):
    conexao = get_conexao()
    cursor = conexao.cursor()

    cursor.execute("SELECT COUNT(*) FROM Livro")
    total_livros = cursor.fetchone()[0]
    total_paginas = (total_livros + limit - 1) // limit if total_livros > 0 else 0

    pular = (page - 1) * limit
    cursor.execute("""
        SELECT IdLivro, NomeLivro, ISBN13, PrecoLivro
        FROM Livro
        ORDER BY IdLivro
        OFFSET ? ROWS
        FETCH NEXT ? ROWS ONLY
    """, pular, limit)

    colunas = [coluna[0] for coluna in cursor.description]
    livros = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
    conexao.close()

    return {
        "total_livros": total_livros,
        "pagina_atual": page,
        "total_paginas": total_paginas,
        "livros": livros
    }
```

**Pontos técnicos importantes:**
- **`page: int = 1, limit: int = 10`** — parâmetros de query string opcionais, com valores padrão; chamar `GET /livros` sem nenhum parâmetro continua funcionando (traz a primeira página, 10 itens), preservando compatibilidade com o comportamento anterior
- **`SELECT COUNT(*)`** — consulta separada, só para contar o total de registros, sem trazer os dados em si
- **`total_paginas = (total_livros + limit - 1) // limit`** — fórmula de "arredondamento para cima" usando divisão inteira; o `if total_livros > 0 else 0` evita divisão indevida quando a tabela está vazia
- **`pular = (page - 1) * limit`** — calcula quantos registros pular antes de começar a trazer a página pedida
- **`OFFSET ? ROWS FETCH NEXT ? ROWS ONLY`** — sintaxe de paginação do SQL Server. Requer obrigatoriamente uma cláusula `ORDER BY` (usado aqui `ORDER BY IdLivro`) — sem ordenação definida, "pular registros" não tem significado determinístico, e o SQL Server rejeita a sintaxe

### Testes realizados

| Chamada | Resultado |
|---|---|
| `GET /livros?page=2&limit=5` | Trouxe exatamente do 6º ao 10º livro (IdLivro 107 a 111), confirmando o cálculo de offset |
| `GET /livros?limit=100` | Com 21 livros cadastrados, trouxe todos numa página só (`total_paginas: 1`), confirmando o comportamento com limite maior que o total de registros |

Ambos os testes confirmaram os metadados (`total_livros`, `pagina_atual`, `total_paginas`) coerentes com os dados reais da tabela.

---

## Parte B — Validação de ISBN duplicado com mensagem clara

### Motivação

O banco já impede ISBN duplicado através de uma restrição `UNIQUE KEY` (existente desde as primeiras etapas do projeto). Porém, quando essa restrição era violada, a API devolvia o **erro bruto do SQL Server** — um texto técnico longo, com código de erro `23000`, nome da constraint interna, etc. Do ponto de vista de quem consome a API, essa mensagem é pouco amigável e expõe detalhes internos do banco desnecessariamente.

### Decisão de design

Verificar a existência do ISBN **antes** de tentar o `INSERT`, devolvendo um erro específico e claro caso já exista — mantendo, porém, a restrição `UNIQUE` do banco como camada de segurança final.

### Código implementado

```python
@app.post("/livros", dependencies=[Depends(verificar_api_key)])
def criar_livro(livro: LivroEntrada):
    payload_json = livro.model_dump_json()
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        cursor.execute("SELECT IdLivro FROM Livro WHERE ISBN13 = ?", livro.ISBN13)
        livro_existente = cursor.fetchone()

        if livro_existente:
            registrar_log("/livros", "POST", payload_json, "ERRO", mensagem_erro=f"ISBN já cadastrado (IdLivro: {livro_existente.IdLivro})")
            raise HTTPException(status_code=409, detail=f"ISBN já cadastrado para o livro de IdLivro {livro_existente.IdLivro}")

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
```

**Pontos técnicos importantes:**
- **`SELECT IdLivro FROM Livro WHERE ISBN13 = ?`** — verificação prévia, antes do `INSERT`
- **Status `409 Conflict`** — escolhido em vez do `400` genérico usado em outros erros do projeto; `409` é o código HTTP semanticamente correto para "o recurso que você está tentando criar já existe / conflita com um existente"
- **Mensagem incluindo o `IdLivro` conflitante** — mais útil para quem consome a API do que um "duplicado" genérico: já indica **qual** registro é o conflitante, permitindo consultá-lo ou atualizá-lo diretamente
- **A checagem via `try/except pyodbc.Error` (restrição `UNIQUE` do banco) foi mantida** — funciona como segunda camada de proteção, cobrindo o caso raro de duas requisições simultâneas passarem pela checagem prévia ao mesmo tempo (condição de corrida). A checagem antecipada melhora a experiência (mensagem clara, resposta mais rápida), mas não substitui a garantia definitiva do banco.

### Erro de investigação durante os testes

Um teste inicial retornou o erro bruto do SQL Server mesmo após o ajuste no código. Investigação revelou que as chamadas de teste feitas não correspondiam à rota correta:
- `POST /livros/{isbn}` (ISBN direto na URL) → não é uma rota existente, resultando em `405 Method Not Allowed`
- `POST /livros/importar/{isbn}` → rota de importação da Google Books (Parte 11), que não possui essa validação — é uma rota diferente do cadastro manual

**Causa raiz:** confusão entre as duas rotas de criação de livro (`POST /livros`, cadastro manual via Body; e `POST /livros/importar/{isbn}`, importação externa via ISBN na URL). Corrigido testando a rota correta, com o Body em JSON.

**Lição prática:** ao testar uma mudança específica em um endpoint, importante confirmar que a chamada realizada realmente aciona a rota alterada — em um projeto com várias rotas parecidas (ex: mais de um jeito de "criar livro"), é fácil testar sem querer a rota errada e concluir erroneamente que a mudança não funcionou.

### Testes realizados

**1 — Tentativa de cadastro com ISBN já existente** (`9788535914849`, já usado por `IdLivro: 106`):
```json
{"detail": "ISBN já cadastrado para o livro de IdLivro 106"}
```
Status `409`, mensagem clara e específica.

**2 — Cadastro de um livro novo e real, com ISBN inédito** ("Harry Potter e a Pedra Filosofal", ISBN `9788532511010`):
```json
{"mensagem": "Livro cadastrado com sucesso!", "IdLivro": 132}
```
Confirma que a validação não interfere em cadastros legítimos.

---

## Roadmap atualizado

- [x] Autenticação simples (API Key) — Fase 1
- [x] Variáveis de ambiente (.env) — Fase 2
- [x] Consumir uma API externa (Python como cliente) — Fase 3
- [x] Paginação no GET /livros — Fase 4
- [x] Validação de ISBN duplicado antes de inserir — Fase 4
- [ ] SQL em paralelo (conforme curso avança) — Fase 5
- [ ] SOAP Fault — Fase 6 (opcional)
- [ ] Git/GitHub — Radar
- [ ] Considerar aplicar checagem de duplicidade também no `PUT /livros/{id}` (se o ISBN for alterado para um já existente em outro registro) — melhoria futura identificada durante esta etapa, ainda não implementada

---

## Conceitos aprendidos nesta etapa

- Padrão de **paginação via `OFFSET`/`FETCH NEXT`** no SQL Server, e a obrigatoriedade de um `ORDER BY` para que a paginação tenha significado determinístico
- Cálculo de metadados de paginação (total de páginas via divisão inteira arredondada para cima) sem depender de bibliotecas externas
- Diferença entre validar **antecipadamente** (consulta prévia, mensagem amigável) e depender só da **restrição do banco** (mais tardia, porém definitiva) — as duas abordagens se complementam, uma não substitui a outra
- Uso correto do status HTTP **`409 Conflict`**, mais específico que `400`, para sinalizar tentativa de criar um recurso já existente
- Importância de mensagens de erro **específicas e acionáveis** (incluir o ID do registro conflitante) em vez de mensagens técnicas genéricas expondo detalhes internos do banco
- Reforço de um cuidado prático: ao testar uma alteração, confirmar que a rota/endpoint realmente exercitado é o que foi alterado — especialmente relevante em projetos com múltiplas rotas de propósito parecido
