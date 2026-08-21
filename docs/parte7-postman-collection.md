# Documentação (Parte 7) — Collection e Environment no Postman

Continuação da **Parte 6 — Log do DELETE guardando o registro deletado**. Nesta etapa: organização de todas as requisições testadas ao longo do projeto dentro de uma Collection do Postman, com uso de variáveis de ambiente.

---

## O que é uma Collection

Uma **pasta dentro do Postman** que guarda um conjunto de requisições salvas e organizadas, prontas para reutilizar sem precisar remontar do zero a cada vez. Também é o formato usado para **compartilhar** requisições com outras pessoas ou exportar como backup.

## O que é um Environment

Um conjunto de **variáveis reutilizáveis** dentro do Postman. Em vez de digitar a URL completa em cada requisição, usa-se uma variável (ex: `{{base_url}}`) que é substituída automaticamente pelo valor configurado. Isso facilita alternar entre ambientes diferentes (ex: local, homologação, produção) sem precisar editar cada requisição manualmente.

---

## Passo 1 — Criar a Collection

1. Menu lateral esquerdo → **Collections** → `+` (New Collection)
2. Nomeada como **`Biblioteca API`**

## Passo 2 — Criar o Environment

1. Menu lateral esquerdo → **Environments** → `+`
2. Nomeado como **`Local`**
3. Variável criada:
   - **Variable:** `base_url`
   - **Initial Value / Current Value:** `http://127.0.0.1:8000`

> **Erro comum encontrado:** ao digitar o valor da variável, o "h" inicial de `http://` acabou não sendo digitado, resultando em `ttp://127.0.0.1:8000`. Corrigido conferindo o valor completo dentro do campo (a coluna da tabela de variáveis pode cortar visualmente o texto, mascarando o erro de digitação).

## Passo 3 — Ativar o Environment

O Environment criado precisa ser **selecionado** no dropdown localizado no canto superior direito da tela de requisições do Postman (por padrão, aparece como "No Environment"). Sem essa seleção, a variável `{{base_url}}` não é substituída e a requisição falha.

---

## Passo 4 — Salvar as requisições na Collection

Processo repetido para cada requisição:
1. Montar a requisição (método + URL usando `{{base_url}}`, e Body quando necessário)
2. **Save** (ou `Ctrl+S`)
3. Definir o nome da requisição
4. Selecionar a Collection `Biblioteca API`
5. Salvar

### Lista completa de requisições salvas

| Nome | Método | URL | Tem Body? |
|---|---|---|---|
| Listar livros | GET | `{{base_url}}/livros` | Não |
| Cadastrar livro | POST | `{{base_url}}/livros` | Sim (raw/JSON) |
| Atualizar livro | PUT | `{{base_url}}/livros/1` | Sim (raw/JSON) |
| Remover livro | DELETE | `{{base_url}}/livros/1` | Não |
| Remover livros em lote | **POST** | `{{base_url}}/livros/delete-batch` | Sim (raw/JSON) |
| Listar editoras | GET | `{{base_url}}/editoras` | Não |
| Listar assuntos | GET | `{{base_url}}/assuntos` | Não |
| Consultar logs | GET | `{{base_url}}/logs` | Não |

### JSONs usados nos Bodies

**Cadastrar livro (POST):**
```json
{
  "NomeLivro": "1984",
  "ISBN13": "9788535914849",
  "DataPub": "1949-06-08",
  "PrecoLivro": 45.90,
  "NumeroPaginas": 328,
  "IdEditora": 3,
  "IdAssunto": 1,
  "Edicao": 1
}
```

**Atualizar livro (PUT):**
```json
{
  "NomeLivro": "1984",
  "ISBN13": "9788535914849",
  "DataPub": "1949-06-08",
  "PrecoLivro": 39.90,
  "NumeroPaginas": 328,
  "IdEditora": 3,
  "IdAssunto": 1,
  "Edicao": 2
}
```

**Remover livros em lote (POST):**
```json
{
  "ids": [1, 2, 3]
}
```

---

## Ponto de confusão esclarecido: DELETE individual não tem Body, DELETE em lote tem (e usa POST)

Durante o processo de salvar as requisições, surgiu a dúvida sobre se o `DELETE` deveria ter Body. Esclarecimento:

| Requisição | Método | Onde vai a informação | Tem Body? |
|---|---|---|---|
| Remover livro (individual) | DELETE | ID na própria URL (`/livros/1`) | ❌ Não |
| Remover livros em lote | **POST** | Lista de IDs no Body | ✅ Sim |

Reforça um conceito já visto na Parte 3: nem toda ação de "deletar" usa necessariamente o método HTTP `DELETE` — a escolha do endpoint de lote por `POST` foi uma decisão de design pragmática (ver Parte 5), já que `DELETE` com Body tem suporte inconsistente em diferentes ferramentas/clientes HTTP.

---

## Resultado final

Collection **Biblioteca API** criada com as 8 requisições organizadas, todas usando a variável `{{base_url}}` do Environment `Local` — pronta para reutilização, exportação ou compartilhamento futuro, sem depender de digitar URLs manualmente a cada teste.

---

## Roadmap atualizado

- [x] Criar collection no Postman para reaproveitar as requisições
- [ ] Explorar SOAP/XML como comparação ao REST/JSON *(próxima e última etapa planejada)*
- [ ] (Opcional) Adicionar validações extras (ex: checar se ISBN já existe antes de inserir)
- [ ] (Opcional) Variáveis de ambiente (.env) para não deixar a connection string no código
- [ ] (Opcional) Paginação no GET /livros
- [ ] (Opcional) Autenticação simples (API Key)

---

## Conceitos aprendidos nesta etapa

- Diferença entre **Collection** (conjunto de requisições salvas) e **Environment** (conjunto de variáveis reutilizáveis) no Postman
- Uso de variáveis (`{{variavel}}`) para evitar repetição e facilitar troca de ambiente (local → produção, por exemplo) sem editar cada requisição individualmente
- Necessidade de **ativar/selecionar** um Environment antes de suas variáveis funcionarem nas requisições — criá-lo não é suficiente
- Reforço prático de que o método HTTP de uma ação (ex: "deletar") não é fixo — depende de decisões de design da própria API, sendo importante ler a documentação (ou lembrar da própria implementação) em vez de assumir por convenção
