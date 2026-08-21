# Documentação (Parte 9) — Autenticação via API Key

Continuação da **Parte 8 — Serviço SOAP com spyne**. Início da **Fase 1** do Plano de Estudos. Nesta etapa: implementação de autenticação simples via API Key nos endpoints que alteram dados, e configuração da chave no nível da Collection do Postman.

---

## Motivação

Até aqui, qualquer pessoa com acesso à URL da API conseguia cadastrar, atualizar ou remover livros, sem nenhuma verificação de identidade. Autenticação é um requisito básico de praticamente qualquer API usada em produção, e um assunto recorrente em vagas de integração — por isso entrou como primeira fase do roadmap de estudos.

---

## Conceitos: Autenticação vs Autorização

- **Autenticação** — responde "quem é você?": provar identidade. Neste projeto, a API Key cumpre esse papel.
- **Autorização** — responde "o que você pode fazer?": definida a identidade, decidir o nível de acesso (ex: uma chave só de leitura vs uma chave com permissão total).

**Escopo desta etapa:** apenas autenticação, com uma única chave que libera acesso completo às operações protegidas. Autorização por níveis de chave/permissão fica como possível evolução futura, fora do escopo atual.

---

## Decisão de design: quais endpoints proteger

**Discutido antes de implementar:** exigir a API Key em todos os endpoints (incluindo `GET`s) ou só nos que alteram dado?

**Decisão tomada:** proteger apenas os endpoints de **escrita** (`POST`, `PUT`, `DELETE`) — padrão comum em APIs de mercado (leitura livre, escrita protegida).

| Endpoint | Protegido? |
|---|---|
| `GET /livros` | Não |
| `GET /editoras` | Não |
| `GET /assuntos` | Não |
| `GET /logs` | Não |
| `POST /livros` | **Sim** |
| `PUT /livros/{id}` | **Sim** |
| `DELETE /livros/{id}` | **Sim** |
| `POST /livros/delete-batch` | **Sim** |

---

## Código adicionado ao `main.py`

```python
from fastapi import FastAPI, HTTPException, Header, Depends

API_KEY = "biblioteca-2026-secreta"  # temporário — vai pro .env na Fase 2

def verificar_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida ou ausente")
```

E, nos 4 endpoints de escrita, adição de `dependencies=[Depends(verificar_api_key)]` no decorador:

```python
@app.post("/livros", dependencies=[Depends(verificar_api_key)])
def criar_livro(livro: LivroEntrada):
    ...

@app.put("/livros/{id_livro}", dependencies=[Depends(verificar_api_key)])
def atualizar_livro(id_livro: int, livro: LivroEntrada):
    ...

@app.delete("/livros/{id_livro}", dependencies=[Depends(verificar_api_key)])
def deletar_livro(id_livro: int):
    ...

@app.post("/livros/delete-batch", dependencies=[Depends(verificar_api_key)])
def deletar_livros_em_lote(entrada: DeleteLoteEntrada):
    ...
```

**Pontos técnicos importantes:**
- **`Header(...)`** — informa ao FastAPI que se espera um header chamado `X-API-Key` (o parâmetro `x_api_key` é convertido automaticamente para o nome do header em kebab-case pela convenção do framework). As reticências (`...`) tornam o header **obrigatório**: se ausente, o FastAPI já rejeita a requisição com `422`, antes mesmo de a função `verificar_api_key` ser executada.
- **`Depends(verificar_api_key)`** — mecanismo de **injeção de dependência** do FastAPI: "pluga" uma verificação antes da rota executar, sem precisar repetir o código de checagem dentro de cada função. Se a função levantar uma exceção (`HTTPException`), a rota nunca chega a rodar.
- **`API_KEY` como constante fixa no código** — decisão temporária e consciente. Guardar segredos direto no código-fonte é uma prática ruim (fica exposto para quem tiver acesso ao repositório/arquivo), mas foi mantida assim de propósito nesta etapa para isolar o conceito de autenticação, sem misturar com o assunto de variáveis de ambiente — que é o objetivo da **Fase 2** do roadmap (`.env`).

---

## Erros encontrados durante a edição do arquivo (copy-paste)

Durante a edição manual do `main.py` no Notepad, ocorreram dois problemas comuns de digitação/copy-paste, identificados e corrigidos antes de rodar:

1. **Import incompleto** — a linha `from fastapi import ...` perdeu a letra inicial "f", virando `rom fastapi import ...`.
2. **Bloco duplicado** — as linhas `app = FastAPI()` e `def get_conexao():` apareceram repetidas, com a segunda ocorrência de `get_conexao()` cortada pela metade (sem corpo).

**Solução adotada:** em vez de seguir corrigindo trecho por trecho, o arquivo `main.py` foi **substituído por completo** (apagar tudo no Notepad e colar a versão final integral) — reduzindo o risco de sobras de edições anteriores se misturarem com o código novo.

> **Lição prática:** ao editar arquivos de código em um editor sem realce de sintaxe (como o Notepad puro), pequenas omissões de caracteres (como uma letra faltando no início de uma linha) são fáceis de não notar visualmente. Revisar o arquivo completo antes de rodar, ou substituir o conteúdo inteiro em vez de editar por cima, ajuda a evitar esse tipo de erro silencioso.

---

## Testes realizados

Testados os 4 endpoints protegidos e os 4 endpoints livres, confirmando o comportamento esperado em cada cenário:

### Cenário 1 — Requisição sem o header `X-API-Key`

**Resultado:** status `422`, com o FastAPI rejeitando automaticamente por campo obrigatório ausente:
```json
{
    "detail": [
        {
            "type": "missing",
            "loc": ["header", "x-api-key"],
            "msg": "Field required",
            "input": null
        }
    ]
}
```

### Cenário 2 — Requisição com header presente, mas chave errada

**Resultado:** status `401`:
```json
{"detail": "API Key inválida ou ausente"}
```

### Cenário 3 — Requisição com a chave correta

**Resultado:** requisição autenticada com sucesso, seguindo o fluxo normal do endpoint (ex: `POST /livros` retornando `{"mensagem": "Livro cadastrado com sucesso!", "IdLivro": 126}`).

Confirmado nos 4 endpoints protegidos (`POST /livros`, `PUT /livros/{id}`, `DELETE /livros/{id}`, `POST /livros/delete-batch`) e verificado que os 4 endpoints de leitura (`GET /livros`, `GET /editoras`, `GET /assuntos`, `GET /logs`) permanecem acessíveis sem qualquer header.

### Erro à parte, sem relação com autenticação: `405 Method Not Allowed`

Durante o teste do `PUT /livros/{id}`, a URL foi enviada sem o `IdLivro` no caminho (ex: `{{base_url}}/livros` em vez de `{{base_url}}/livros/126`). Como a rota no FastAPI é definida como `{id_livro}`, uma URL sem o parâmetro não corresponde a nenhuma rota registrada, gerando `405` — erro de roteamento, não de autenticação. Corrigido incluindo o ID na URL.

### Erro à parte, sem relação com autenticação: `400` por ISBN duplicado

Em dois momentos dos testes (`POST` e `PUT`), o Body enviado usava um `ISBN13` que já existia no banco, disparando a restrição `UNIQUE KEY` já existente na tabela `Livro` (implementada antes desta etapa). Esse erro **confirma indiretamente** que a autenticação funcionou: a requisição só chega a tocar no banco (e, portanto, só pode esbarrar nessa restrição) depois de passar pela verificação de `X-API-Key` — se a chave estivesse errada ou ausente, o erro teria sido `401`/`422`, não `400`.

---

## Configuração da API Key na Collection do Postman

Para evitar adicionar o header manualmente em cada requisição:

1. Collection **`Biblioteca API`** → aba **Authorization**
2. **Type:** `API Key`
3. **Key:** `X-API-Key`
4. **Value:** `biblioteca-2026-secreta`
5. **Add to:** `Header`

Nas 4 requisições protegidas (Cadastrar livro, Atualizar livro, Remover livro, Remover livros em lote), configurada a aba **Authorization** de cada uma como **"Inherit auth from parent"**, fazendo com que herdem automaticamente o header configurado no nível da Collection.

Testado com sucesso: `POST /livros` sem adicionar nenhum header manual na requisição, dependendo apenas da herança da Collection.

---

## Roadmap atualizado

- [x] Autenticação simples (API Key) — Fase 1 do Plano de Estudos
- [ ] Variáveis de ambiente (.env) — Fase 2
- [ ] Consumir uma API externa (Python como cliente) — Fase 3
- [ ] Paginação no GET /livros — Fase 4
- [ ] Validação de ISBN duplicado antes de inserir — Fase 4 *(nota: já existe uma proteção via restrição `UNIQUE` no banco, confirmada nos testes desta etapa; validar/tratar isso de forma mais amigável na própria API pode ser parte dessa fase)*
- [ ] SOAP Fault — Fase 6 (opcional)

---

## Conceitos aprendidos nesta etapa

- Diferença conceitual entre **autenticação** (provar identidade) e **autorização** (definir permissões) — e a decisão consciente de implementar só a primeira nesta etapa
- Uso de **`Header(...)`** no FastAPI para declarar um header HTTP obrigatório, com validação automática (`422`) caso ausente
- **Injeção de dependência** com `Depends()` — mecanismo do FastAPI para reaproveitar lógica de verificação entre múltiplas rotas, sem repetir código
- Decisão de design consciente sobre **quais endpoints proteger**: leitura livre, escrita protegida — padrão comum em APIs REST
- Diferenciar um erro de autenticação (`401`) de outros erros que também retornam status de "falha" (`400` por violação de integridade, `405` por rota incorreta) — nem todo erro após uma mudança está relacionado à mudança em si
- Configuração de autenticação no nível de **Collection** no Postman, com herança (`Inherit auth from parent`) nas requisições individuais — evita repetição manual e centraliza a configuração da chave
- Risco prático de editar arquivos de código em editores sem realce de sintaxe (Notepad puro): erros sutis de digitação (caractere faltando, blocos duplicados) são fáceis de passar despercebidos — substituir o arquivo por completo, em vez de editar por cima, reduz esse risco
