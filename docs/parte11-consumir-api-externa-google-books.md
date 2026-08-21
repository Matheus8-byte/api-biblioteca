# Documentação (Parte 11) — Consumindo uma API externa (Google Books)

Continuação da **Parte 10 — Variáveis de ambiente (.env)**. Conclusão da **Fase 3** do Plano de Estudos. Nesta etapa: a API deixou de ser só provedora (recebendo chamadas) e passou a atuar também como **cliente**, consumindo uma API pública de terceiros (Google Books) para importar livros automaticamente a partir de um ISBN.

---

## Motivação

Até aqui, todo dado inserido no banco vinha de um `POST`/`PUT` manual, com o usuário preenchendo todos os campos. O objetivo desta etapa foi fechar o ciclo de integração: fazer o **próprio Python chamar uma API externa**, tratar a resposta, e persistir os dados no banco — o mesmo tipo de fluxo usado em integrações reais de mercado (sistema A busca dado em sistema B e grava em si mesmo).

---

## Conceito-chave: por que ISBN, e não um "listar tudo"

Diferente do `GET /livros` (que lista tudo sem precisar saber nada de antemão), o novo endpoint de importação funciona por **busca dirigida**: é necessário informar o ISBN do livro desejado. O ISBN funciona como um identificador universal, presente em qualquer edição física ou loja online — diferente dos IDs internos do projeto (`IdLivro`, `IdEditora`), que só fazem sentido dentro do próprio banco `Biblioteca`. O ganho da integração não é "descobrir livros desconhecidos", e sim evitar digitar manualmente todos os campos de um livro que já se sabe qual é.

---

## Passo 1 — Instalar a biblioteca `requests`

```
pip install requests
```

Biblioteca padrão de mercado para o Python realizar chamadas HTTP **de saída** — usada aqui para consultar a Google Books API a partir de dentro do próprio endpoint.

---

## Passo 2 — Entendendo a resposta da Google Books API

Exemplo de chamada e resposta (campos relevantes):

```
GET https://www.googleapis.com/books/v1/volumes?q=isbn:9788535914849
```

```json
{
  "items": [
    {
      "volumeInfo": {
        "title": "1984",
        "publisher": "Companhia das Letras",
        "publishedDate": "2009",
        "pageCount": 416,
        "categories": ["Fiction"]
      }
    }
  ]
}
```

**Particularidades observadas na resposta, que moldaram o código:**
- `"items"` é sempre uma **lista**; se o ISBN não for encontrado, essa chave simplesmente não existe na resposta — é assim que se detecta "não encontrado"
- `publishedDate` pode vir incompleto (`"2009"`, `"2009-06"` ou `"2009-06-08"`), exigindo tratamento antes de gravar na coluna `DataPub` (que espera data completa)
- `publisher` e `categories` podem vir ausentes, dependendo de quão completo é o cadastro daquele livro na base da Google Books

---

## Passo 3 — Decisões de design tomadas antes de implementar

### `IdEditora` e `IdAssunto`: a API externa não os fornece

A Google Books devolve nome de editora e categoria como **texto solto**, sem relação com os IDs internos do banco `Biblioteca`.

**Decisão tomada:** buscar a editora/assunto pelo nome no banco; se já existir, reaproveitar o ID; se não existir, criar automaticamente uma nova linha (usando o próprio auto-incremento das tabelas).

**Confirmado antes de implementar:** `IdEditora` (tabela `Editora`) e `IdAssunto` (tabela `Assunto`) são colunas `IDENTITY`, verificado via script Python reaproveitando o padrão da Parte 1:

```sql
SELECT OBJECT_NAME(OBJECT_ID) AS Tabela, name AS Coluna
FROM SYS.IDENTITY_COLUMNS
WHERE OBJECT_NAME(OBJECT_ID) IN ('Editora', 'Assunto')
```

Resultado confirmado: ambas são `IDENTITY` — não é necessário gerar os IDs manualmente nem usar trigger; o próprio SQL Server cuida disso a cada `INSERT`, exatamente como já acontece com `IdLivro`.

> **Esclarecimento conceitual discutido durante a etapa:** cogitou-se usar uma trigger no banco para essa geração de ID. Não é necessário — os IDs já são gerados automaticamente pelo `IDENTITY` em qualquer INSERT, seja ele vindo do código Python ou de qualquer outra fonte. A lógica de "existe ou não existe" (decidir se busca ou cria) é uma decisão que precisa ser tomada *antes* do INSERT, com base em uma consulta — por isso foi implementada no próprio código Python, seguindo o mesmo padrão de "verificar antes de agir" já usado no DELETE (Parte 6).

### `PrecoLivro`: a API externa não fornece preço

A coluna é `NOT NULL` na tabela `Livro`, mas a Google Books não devolve nenhum dado de preço.

**Decisão tomada:** importar com `PrecoLivro = 0.00` por padrão, com opção de informar um valor real via query string (`?preco=49.90`) na própria chamada de importação; ajustes posteriores ficam a cargo de um `PUT` normal.

### Tamanho das colunas `NomeEditora` e `NomeAssunto`

Ao verificar a estrutura das tabelas (`INFORMATION_SCHEMA` / `sp_help`), identificou-se que `NomeEditora` era `VARCHAR(50)` e `NomeAssunto` era `VARCHAR(25)` — tamanhos que poderiam ser insuficientes para nomes/categorias mais longos vindos da Google Books (ex: `"Fiction / Science Fiction / General"`).

**Decisão tomada:** em vez de truncar o texto no Python (`[:50]`/`[:25]`), resolver na raiz, ampliando as colunas via `ALTER TABLE` — mesmo padrão já usado na Parte 5:

```sql
USE Biblioteca;
GO

ALTER TABLE Editora
ALTER COLUMN NomeEditora VARCHAR(100) NOT NULL;
GO

ALTER TABLE Assunto
ALTER COLUMN NomeAssunto VARCHAR(50) NOT NULL;
GO
```

---

## Código adicionado ao `main.py`

### Funções auxiliares

```python
def tratar_data_publicacao(data_str):
    if not data_str:
        return None
    partes = data_str.split("-")
    if len(partes) == 1:
        return f"{partes[0]}-01-01"
    elif len(partes) == 2:
        return f"{partes[0]}-{partes[1]}-01"
    else:
        return data_str

def buscar_ou_criar_editora(nome_editora, cursor, conexao):
    if not nome_editora:
        nome_editora = "Editora não informada"

    cursor.execute("SELECT IdEditora FROM Editora WHERE NomeEditora = ?", nome_editora)
    linha = cursor.fetchone()

    if linha:
        return linha.IdEditora

    cursor.execute("""
        INSERT INTO Editora (NomeEditora)
        OUTPUT INSERTED.IdEditora
        VALUES (?)
    """, nome_editora)
    novo_id = cursor.fetchone()[0]
    conexao.commit()
    return novo_id

def buscar_ou_criar_assunto(nome_assunto, cursor, conexao):
    if not nome_assunto:
        nome_assunto = "Assunto não informado"

    cursor.execute("SELECT IdAssunto FROM Assunto WHERE NomeAssunto = ?", nome_assunto)
    linha = cursor.fetchone()

    if linha:
        return linha.IdAssunto

    cursor.execute("""
        INSERT INTO Assunto (NomeAssunto)
        OUTPUT INSERTED.IdAssunto
        VALUES (?)
    """, nome_assunto)
    novo_id = cursor.fetchone()[0]
    conexao.commit()
    return novo_id
```

### Endpoint principal

```python
@app.post("/livros/importar/{isbn}", dependencies=[Depends(verificar_api_key)])
def importar_livro(isbn: str, preco: float = 0.00):
    resposta_google = requests.get(
        "https://www.googleapis.com/books/v1/volumes",
        params={"q": f"isbn:{isbn}", "key": GOOGLE_BOOKS_API_KEY}
    )
    dados_google = resposta_google.json()

    if "items" not in dados_google:
        registrar_log(f"/livros/importar/{isbn}", "POST", None, "ERRO", mensagem_erro="Livro não encontrado na Google Books API")
        raise HTTPException(status_code=404, detail="Livro não encontrado na Google Books API")

    volume_info = dados_google["items"][0]["volumeInfo"]

    nome_livro = volume_info.get("title", "Título não informado")
    editora_texto = volume_info.get("publisher")
    assunto_texto = volume_info.get("categories", [None])[0]
    data_pub = tratar_data_publicacao(volume_info.get("publishedDate"))
    numero_paginas = volume_info.get("pageCount", 0)

    payload_json = json.dumps(volume_info, default=str)

    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        id_editora = buscar_ou_criar_editora(editora_texto, cursor, conexao)
        id_assunto = buscar_ou_criar_assunto(assunto_texto, cursor, conexao)

        cursor.execute("""
            INSERT INTO Livro (NomeLivro, ISBN13, DataPub, PrecoLivro, NumeroPaginas, IdEditora, IdAssunto, Edicao)
            OUTPUT INSERTED.IdLivro
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, nome_livro, isbn, data_pub, preco, numero_paginas, id_editora, id_assunto, 1)

        novo_id = cursor.fetchone()[0]
        conexao.commit()

        registrar_log(f"/livros/importar/{isbn}", "POST", payload_json, "SUCESSO", id_gerado=novo_id)

        return {
            "mensagem": "Livro importado com sucesso da Google Books API!",
            "IdLivro": novo_id,
            "NomeLivro": nome_livro,
            "Editora": editora_texto,
            "Assunto": assunto_texto
        }

    except pyodbc.Error as e:
        conexao.rollback()
        registrar_log(f"/livros/importar/{isbn}", "POST", payload_json, "ERRO", mensagem_erro=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conexao.close()
```

**Pontos técnicos importantes:**
- **`preco: float = 0.00`** — parâmetro opcional de query string; permite informar o preço já na importação (`?preco=49.90`) ou aceitar o padrão
- **`requests.get(..., params={...})`** — o `requests` monta a query string automaticamente a partir do dicionário, sem concatenação manual de texto
- **`.get("publisher")` / `.get("categories", [None])[0]`** — uso de `.get()` em vez de acesso direto, para não quebrar o programa quando campos opcionais não vierem preenchidos na resposta da Google Books
- **`payload_json = json.dumps(volume_info, ...)`** — a resposta completa da Google Books é registrada no log de auditoria, mesmo padrão já usado em outros endpoints de escrita
- **Endpoint protegido** (`dependencies=[Depends(verificar_api_key)]`) — segue o mesmo critério definido na Parte 9 (grava dado no banco, portanto exige autenticação)
- **`Edicao` fixo em `1`** — a Google Books não fornece esse conceito no mesmo formato usado na tabela `Livro`; assumido como padrão

---

## Necessidade de uma API Key própria para a Google Books

### Erro encontrado: quota excedida (429)

No primeiro teste, a chamada sem nenhuma chave de identificação retornou:

```json
{
  "error": {
    "code": 429,
    "message": "Quota exceeded for quota metric 'Queries' and limit 'Queries per day'...",
    "status": "RESOURCE_EXHAUSTED"
  }
}
```

**Causa:** chamadas feitas sem uma API Key própria compartilham uma cota anônima global, usada simultaneamente por um número muito grande de aplicações no mundo todo — não se trata de uso excessivo individual, e sim de um "balde compartilhado" já saturado por terceiros.

**Solução:** criação de uma API Key própria no Google Cloud Console, seguindo os passos:
1. Criar um projeto no Google Cloud Console
2. Ativar a **Books API** na biblioteca de APIs do projeto
3. Gerar uma **API Key** em "APIs & Services → Credentials"
4. Restringir a chave para funcionar apenas com a Books API (boa prática de segurança)

Não foi necessário habilitar faturamento/cartão de crédito para esse uso.

### Guardando a chave

Seguindo o mesmo padrão já estabelecido na Parte 10, a chave foi adicionada ao `.env`:

```
GOOGLE_BOOKS_API_KEY=AIzaSy...
```

E lida no `main.py`:

```python
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY")
```

---

## Erro encontrado: edição de arquivo na pasta errada

Ao reabrir o terminal após uma pausa, os comandos `notepad .env` e `notepad main.py` foram executados **sem antes navegar para `C:\projetos\api-biblioteca`** — o terminal estava em `C:\Users\Matheus`. Isso fez com que o Notepad criasse/abrisse arquivos `.env` e `main.py` **diferentes**, soltos na pasta pessoal do usuário, sem relação com o projeto real.

**Sintoma que expôs o problema:** o `main.py` que apareceu era uma versão muito antiga do código (sem autenticação, sem `.env`, sem vários endpoints), o que não correspondia ao estado real e mais avançado do projeto.

**Correção:** navegação para a pasta correta (`cd C:\projetos\api-biblioteca`) antes de reabrir os arquivos, e aplicação manual dos ajustes pendentes (adicionar `GOOGLE_BOOKS_API_KEY` ao `.env` real, e os dois trechos correspondentes no `main.py` real).

> **Lição prática, reforçando um padrão já visto na Parte 1:** confirmar sempre a pasta atual do terminal (`cd`, ou observar o prompt) antes de editar arquivos — o mesmo tipo de erro (editar/criar arquivo na pasta errada, sem gerar nenhum aviso visível) já havia acontecido durante o setup inicial do projeto.

---

## Erro encontrado: `Invalid protocol: post http:` no Postman

Ao montar a requisição de teste no Postman, o verbo `POST` foi digitado tanto no dropdown de método quanto, por engano, dentro do próprio campo de URL (`POST {{base_url}}/livros/importar/...`). Isso fez o Postman tentar interpretar a palavra `POST` como parte do endereço, resultando em erro de protocolo inválido.

**Correção:** remover a palavra `POST` do campo de URL, deixando apenas o endereço (`{{base_url}}/livros/importar/...`) — o método já é definido separadamente, no dropdown à esquerda.

---

## Limitação observada: cobertura de ISBN da Google Books

Testes com ISBNs de edições brasileiras (ex: `9788525432629`, do livro "Sapiens") retornaram `404` mesmo após a chave própria estar configurada corretamente. Investigação direta na Google Books (`totalItems: 0`) confirmou que **o problema não era técnico** — esses ISBNs específicos simplesmente não estão cadastrados na base de dados da Google Books, que tem cobertura mais forte para edições em inglês/americanas do que para edições brasileiras.

**Conclusão:** essa é uma limitação da fonte de dados externa, não um defeito da integração construída. Vale ter em mente ao escolher ISBNs de teste no futuro.

---

## Teste final validado (fluxo completo)

**Requisição:** `POST {{base_url}}/livros/importar/9780132350884` (Clean Code, Robert C. Martin)

**Resposta:**
```json
{
    "mensagem": "Livro importado com sucesso da Google Books API!",
    "IdLivro": 130,
    "NomeLivro": "Clean Code",
    "Editora": "Pearson Education",
    "Assunto": "Computers"
}
```

**Confirmado no banco/API, em sequência:**
- `GET /livros` — `IdLivro: 130` presente, com `NomeLivro: "Clean Code"`
- `GET /editoras` — `"Pearson Education"` criada automaticamente
- `GET /assuntos` — `"Computers"` criado automaticamente
- `GET /logs` — entrada para `/livros/importar/9780132350884`, `Status: SUCESSO`, com o `PayloadRecebido` contendo o JSON completo devolvido pela Google Books

---

## Roadmap atualizado

- [x] Autenticação simples (API Key) — Fase 1
- [x] Variáveis de ambiente (.env) — Fase 2
- [x] Consumir uma API externa (Python como cliente) — Fase 3
- [ ] Paginação no GET /livros — Fase 4
- [ ] Validação de ISBN duplicado antes de inserir — Fase 4
- [ ] SQL em paralelo (conforme curso avança) — Fase 5
- [ ] SOAP Fault — Fase 6 (opcional)
- [ ] Git/GitHub — Radar

---

## Conceitos aprendidos nesta etapa

- Diferença entre uma API atuando como **provedora** (recebe chamadas) e como **cliente** (faz chamadas) — o mesmo projeto agora exerce os dois papéis
- Uso da biblioteca `requests` para chamadas HTTP de saída, incluindo montagem de query string via dicionário `params`
- Padrão **buscar-ou-criar** ("find or create"), aplicado a `IdEditora`/`IdAssunto`: verificar existência antes de decidir entre reaproveitar um ID existente ou inserir um novo registro
- Reforço de que colunas `IDENTITY` no SQL Server já resolvem a geração de IDs automaticamente — não é necessário criar triggers para esse propósito; a lógica de negócio (existe/não existe) fica no código da aplicação
- Tratamento defensivo de dados vindos de uma fonte externa (`.get()` com valor padrão) — uma API de terceiros não garante que todos os campos estarão sempre preenchidos
- Conceito de **cota (quota) de uso de uma API pública** e a diferença entre uso anônimo (compartilhado, facilmente esgotado) e uso autenticado com chave própria (cota individual)
- Passo a passo de criação de uma API Key no Google Cloud Console, restrita a uma API específica
- Reforço da importância de confirmar a pasta ativa do terminal antes de editar arquivos — o mesmo tipo de erro silencioso (editar arquivo errado, sem mensagem de aviso) já visto na Parte 1 se repetiu nesta etapa
- Diferenciação entre um erro seu (bug no código) e uma limitação de dados de uma fonte externa (cobertura incompleta de ISBNs) — importante para não gastar tempo depurando código que já está correto
