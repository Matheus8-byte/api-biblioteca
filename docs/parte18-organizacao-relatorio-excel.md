# Documentação (Parte 18) — Organização de scripts e relatório via API

Continuação da **Parte 17 — pandas: a ponte entre Python e SQL**. Nesta etapa: organização dos scripts auxiliares do projeto, criação de um catálogo de referência rápida, diagnóstico dos dados de teste residuais, e um novo endpoint que gera um relatório Excel sob demanda, direto pela API.

---

## Parte A — Organização dos scripts

### Motivação

Com o crescimento do projeto, a pasta raiz acumulou 9 scripts auxiliares soltos (`ver_estrutura.py`, `mapear_banco.py`, `pandas_biblioteca.py`, entre outros), misturados com o `main.py` — o arquivo que efetivamente roda a aplicação. Isso dificultava identificar rapidamente o que era "aplicação" e o que era "ferramenta de apoio pontual".

### Ação tomada

Criada a pasta `scripts/`, e todos os scripts auxiliares movidos para dentro dela — exceto `main.py`, que permanece na raiz por ser o arquivo executado pelo `uvicorn`.

```
move ajustar_coluna.py scripts\
move teste_conexao.py scripts\
move ver_estrutura.py scripts\
move ver_identity.py scripts\
move ver_identity_editora_assunto.py scripts\
move mapear_banco.py scripts\
move pandas_biblioteca.py scripts\
move teste_pandas.py scripts\
move limpar_isbns.py scripts\
```

### Catálogo de referência rápida

Criado `docs/scripts-referencia.md` — um índice objetivo (script → o que faz → como rodar → onde foi documentado), sem a narrativa completa de cada Parte, para consulta rápida sem precisar reabrir toda a documentação. Diferente das Partes numeradas, este documento é **vivo**: cresce conforme novos scripts forem criados.

---

## Parte B — Diagnóstico dos dados de teste residuais

Usando pandas para filtrar registros com `ISBN13` fora do padrão de 13 dígitos:

```python
import pandas as pd
import pyodbc

conexao = pyodbc.connect(...)
df = pd.read_sql("SELECT * FROM Livro", conexao)
conexao.close()

problematicos = df[df["ISBN13"].str.strip().str.len() != 13]
print(problematicos[["IdLivro", "NomeLivro", "ISBN13"]])
```

**Pontos técnicos:**
- **`.str`** — acessor que permite aplicar operações de texto (`strip()`, `len()`, etc.) em uma coluna inteira do DataFrame de uma vez, sem escrever um loop manual
- **`df[condição]`** — sintaxe de filtro do pandas: uma expressão que resulta em `True`/`False` por linha; só as linhas `True` permanecem no resultado. Equivalente direto ao `WHERE` do SQL, aplicado em Python

**Resultado confirmado:** apenas `IdLivro 126` e `127`, com ISBNs incompletos (`97885`, `9788510`) — resíduos conhecidos dos testes de validação de duplicidade das Partes 9 a 11.

**Decisão consciente:** manter os registros como estão por enquanto. Não afetam o funcionamento da API; documentados aqui e no catálogo de scripts para referência futura, caso apareçam em alguma consulta ou relatório.

---

## Parte C — Endpoint `GET /relatorios/acervo`

### Motivação

Até então, gerar o relatório em Excel exigia rodar manualmente `python scripts\pandas_biblioteca.py`. Um endpoint dedicado permite que o relatório seja gerado **sob demanda**, direto pela API — útil tanto para uso próprio quanto como demonstração de um padrão comum em sistemas corporativos (APIs que devolvem arquivos, não apenas JSON).

### Conceito novo: devolver um arquivo em vez de JSON

Todas as rotas construídas até aqui devolvem `dict` (convertido automaticamente para JSON pelo FastAPI). Para devolver um arquivo binário, o FastAPI oferece a classe `StreamingResponse`.

### Conceito novo: gerar o arquivo em memória, sem tocar o disco

Em vez de salvar o Excel fisicamente no servidor e depois reabri-lo para enviar, o arquivo é gerado inteiramente em memória, usando `BytesIO` — um objeto que se comporta como um arquivo, mas existe apenas durante a execução da requisição.

### Código implementado

```python
import pandas as pd
from io import BytesIO
from fastapi.responses import StreamingResponse

@app.get("/relatorios/acervo")
def relatorio_acervo():
    conexao = get_conexao()

    df_livros = pd.read_sql("SELECT * FROM Livro", conexao)
    df_editoras = pd.read_sql("SELECT * FROM Editora", conexao)
    df_assuntos = pd.read_sql("SELECT * FROM Assunto", conexao)
    conexao.close()

    df_completo = df_livros.merge(df_editoras, on="IdEditora").merge(df_assuntos, on="IdAssunto")

    buffer = BytesIO()
    df_completo.to_excel(buffer, index=False, sheet_name="Acervo")
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=relatorio_acervo.xlsx"}
    )
```

**Pontos técnicos importantes:**
- **`buffer = BytesIO()`** — cria um "arquivo" que existe apenas na memória RAM
- **`df_completo.to_excel(buffer, ...)`** — mesma função já usada na Parte 17, mas recebendo um objeto de memória em vez de um nome de arquivo em disco
- **`buffer.seek(0)`** — após escrever, o cursor de leitura do buffer fica no final do conteúdo; `seek(0)` o reposiciona no início, essencial para que a resposta não saia vazia
- **`media_type`** — string MIME que identifica o conteúdo como um arquivo `.xlsx` real para o navegador/cliente
- **`Content-Disposition: attachment; filename=...`** — instrui o navegador a baixar o arquivo com esse nome, em vez de tentar exibi-lo como texto
- **Endpoint não protegido por API Key** — decisão consciente, seguindo o mesmo critério já usado para os demais `GET`s (somente leitura, sem alteração de dados)

### Erro de investigação: múltiplas versões do `main.py` abertas simultaneamente

Durante a implementação, o teste do endpoint retornou `404 Not Found` mesmo após a edição aparentemente correta. Investigação revelou uma situação de risco real:

1. Uma primeira tentativa de edição não havia sido salva de fato — confirmado via `findstr /C:"relatorios/acervo" main.py`, que retornou vazio
2. Ao reabrir o arquivo para tentar novamente, foi identificada uma **segunda janela do Notepad**, aberta anteriormente, contendo uma versão **muito mais antiga** do `main.py` (equivalente à Parte 2 do projeto — sem autenticação, CORS, paginação, importação, ou os endpoints de editoras/assuntos)

**Risco identificado:** salvar aquela janela antiga por engano teria sobrescrito o `main.py` real, revertendo todo o progresso das Partes 3 a 16.

**Como o risco foi evitado:** a prática de **confirmar sempre via terminal** (`findstr`, `dir` com tamanho de arquivo) — em vez de confiar apenas no que aparecia colado na conversa — permitiu identificar a divergência antes de qualquer ação destrutiva. O arquivo antigo foi fechado sem salvar, e a edição foi refeita diretamente no arquivo real, confirmado por caminho completo (`notepad C:\projetos\api-biblioteca\main.py`) e validado novamente via `findstr` antes de qualquer teste no navegador.

> **Lição reforçada:** ao trabalhar com múltiplas janelas de edição abertas ao longo de uma sessão longa, é fácil perder de vista qual delas reflete o estado real do arquivo em disco. Confirmar o conteúdo (tamanho do arquivo, busca por trecho específico) diretamente via terminal, antes de salvar ou testar, é uma proteção simples e eficaz contra esse tipo de erro silencioso — já visto de formas similares nas Partes 1 e 11.

### Teste realizado

Acesso direto via navegador:
```
http://127.0.0.1:8000/relatorios/acervo
```

**Resultado:** download automático do arquivo `relatorio_acervo.xlsx`, contendo o acervo completo com editora e assunto já combinados — confirmando o endpoint funcional de ponta a ponta.

---

## Roadmap atualizado

- [x] O que é um DataFrame, e por que ele é relevante para integração/dados — Parte 17
- [x] `pd.read_sql`, `groupby`, `merge`, `to_excel` — Parte 17
- [x] Endpoint `GET /relatorios/acervo`, devolvendo Excel gerado na hora — Parte 18
- [x] Organização dos scripts auxiliares em pasta própria, com catálogo de referência — Parte 18
- [ ] (Possível extensão) exercício de ETL simples: ler um CSV externo, limpar com pandas, inserir no banco
- [ ] (Radar) Tela de login para o painel administrativo (JWT)
- [ ] (Radar) Deploy simples, evolução do frontend

---

## Conceitos aprendidos nesta etapa

- Uso de `.str` para aplicar operações de texto em uma coluna inteira de um DataFrame, e de filtros por condição (`df[condição]`) como equivalente ao `WHERE` do SQL em Python
- `StreamingResponse` do FastAPI como forma de devolver arquivos binários (não apenas JSON) em uma rota
- `BytesIO` como técnica para gerar arquivos inteiramente em memória, sem necessidade de escrever e reler do disco
- Diferença entre um script rodado manualmente (`python scripts\arquivo.py`) e a mesma lógica exposta como endpoint de API — ambos usam o mesmo código-base de pandas, mudando apenas a forma de acionamento e entrega do resultado
- Reforço prático da importância de validar o conteúdo real de um arquivo via terminal (não apenas visualmente) antes de ações potencialmente destrutivas, especialmente em sessões longas com múltiplas janelas de edição abertas
- Organização de projeto: separar arquivos de aplicação (`main.py`) de ferramentas de apoio pontuais (`scripts/`), com um índice de referência rápida complementando a documentação narrativa completa
