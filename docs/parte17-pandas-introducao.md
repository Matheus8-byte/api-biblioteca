# Documentação (Parte 17) — pandas: a ponte entre Python e SQL

Continuação da **Parte 16 — Site conectado ao banco**. Início da **Fase 9** do Plano de Estudos. Nesta etapa: primeiro contato com a biblioteca `pandas`, conectando-a diretamente ao banco `Biblioteca` para realizar agregações e gerar um relatório em Excel.

---

## Motivação e reflexão de escopo

Após a conclusão da Fase 8 (site), foi feita uma pausa consciente para reavaliar o próximo passo. A ideia natural seguinte seria aprofundar em frontend (tela de login, JWT) — mas essa direção foi conscientemente **adiada**, em favor de reforçar os três pilares definidos desde o início do processo de aprendizado: **integração, SQL e Python**.

`pandas` foi identificado como uma ponte direta entre esses três pilares: é uma biblioteca Python, criada especificamente para processar dados tabulares (o mesmo formato que já vem do SQL), e amplamente usada no mercado em tarefas de integração, relatórios e ETL — mais alinhada ao foco declarado do projeto do que aprofundar em frontend.

A tela de login/JWT não foi descartada — foi movida para o "Radar" do plano de estudos, para retomar quando fizer sentido.

---

## Conceito: o que é um DataFrame

Um `DataFrame` é a estrutura central do pandas: uma tabela em memória, com linhas e colunas nomeadas, equivalente ao resultado de uma consulta SQL ou a uma planilha — mas manipulável via código, com um conjunto amplo de operações prontas (agregação, filtro, junção, exportação) que, sem pandas, precisariam ser escritas manualmente em Python.

**Comparação com o que o projeto já fazia:**

| Tarefa | Sem pandas (já usado no `main.py`) | Com pandas |
|---|---|---|
| Buscar registros do banco | `cursor.execute(...)` + `dict(zip(colunas, linha))` | `pd.read_sql(query, conexao)` |
| Calcular média de uma coluna | Loop manual (`sum(...) / len(...)`) | `df["Coluna"].mean()` |
| Agrupar por categoria | `GROUP BY` no SQL | `df.groupby("Coluna")` |
| Combinar duas tabelas | `JOIN` no SQL | `df.merge(outro_df, on="ColunaChave")` |
| Exportar para Excel | Não existia no projeto | `df.to_excel("arquivo.xlsx")` |

---

## Passo 1 — Instalação

```
pip install pandas openpyxl
```

- **`pandas`** — a biblioteca em si
- **`openpyxl`** — motor usado internamente pelo pandas para ler/escrever arquivos `.xlsx`; sem ele, `.to_excel()` não funciona

Instalação trouxe também `numpy` (biblioteca de cálculo numérico, dependência interna do pandas), `python-dateutil` e `tzdata` (manipulação de datas), sem necessidade de instalação manual separada.

---

## Passo 2 — Primeiro contato, sem banco (dados inventados)

```python
import pandas as pd

dados = [
    {"IdLivro": 101, "NomeLivro": "Vinte Mil Léguas Submarinas", "PrecoLivro": 24.50},
    {"IdLivro": 106, "NomeLivro": "1984", "PrecoLivro": 29.67},
    {"IdLivro": 130, "NomeLivro": "Clean Code", "PrecoLivro": 0.00},
]

df = pd.DataFrame(dados)
print(df)
print("Preço médio:", df["PrecoLivro"].mean())
```

**Pontos técnicos discutidos:**
- **`pd.DataFrame(dados)`** — função construtora que transforma uma lista de dicionários em um DataFrame; os nomes das colunas vêm automaticamente das chaves dos dicionários
- **Índice automático** — toda linha recebe um número de índice (`0, 1, 2...`), gerado pelo pandas por padrão, distinto de qualquer coluna real dos dados (como `IdLivro`)
- **`df["PrecoLivro"]`** — seleciona uma única coluna, devolvendo uma `Series` (estrutura de uma única coluna, com métodos de cálculo próprios)
- **`.mean()`** — método aplicado sobre a `Series`, calculando a média sem necessidade de loop manual
- Padrão recorrente identificado: **`objeto["coluna"].metodo()`** — primeiro seleciona uma parte do dado, depois aplica uma operação sobre ela

---

## Passo 3 — Conectando ao banco `Biblioteca`

```python
import pandas as pd
import pyodbc

conexao = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=Biblioteca;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

df = pd.read_sql("SELECT * FROM Livro", conexao)
conexao.close()

print(df)
print("Colunas:", list(df.columns))
print("Quantidade de livros:", len(df))
print("Preço médio do acervo:", df["PrecoLivro"].mean())
```

**Resultado:** os 23 livros reais do acervo, trazidos em uma única linha de código (`pd.read_sql`), reaproveitando a mesma connection string `pyodbc` já usada em todo o projeto.

### `UserWarning` esperado

```
UserWarning: pandas only supports SQLAlchemy connectable (engine/connection) or database string URI or sqlite3 DBAPI2 connection. Other DBAPI2 objects are not tested. Please consider using SQLAlchemy.
```

O pandas foi projetado priorizando o uso com **SQLAlchemy** (uma camada de abstração de banco mais robusta), mas continua funcionando corretamente com uma conexão `pyodbc` "crua", como comprovado pelo resultado correto obtido. Aviso sem impacto funcional — adoção de SQLAlchemy fica como possível decisão de arquitetura futura, fora do escopo desta etapa.

### Observações sobre os dados reais

- **Valores `NaN`** na coluna `Edicao` — representação do pandas para valores nulos (`NULL` do SQL Server) em colunas numéricas; "Not a Number"
- **ISBNs incompletos visíveis** (`IdLivro 126` e `127`, ex: `"97885"`, `"9788510"`) — resíduos de testes de duplicidade de ISBN realizados nas Partes 9 a 11, agora visíveis de forma destacada pela tabela do pandas; candidatos a limpeza futura

---

## Passo 4 — Agregações com `groupby`

```python
print(df.groupby("IdEditora")["PrecoLivro"].mean())
```

**`groupby("IdEditora")`** — divide o DataFrame em subgrupos, um por valor distinto de `IdEditora`, equivalente direto ao `GROUP BY` do SQL. O resultado de uma agregação sobre um `groupby` é uma `Series`, cujo índice passa a ser a própria coluna agrupada (não mais `0, 1, 2...`).

**Limitação identificada:** o resultado mostra apenas o `IdEditora` numérico, não o nome — porque o DataFrame de `Livro` só contém a chave estrangeira, não o nome da editora (mesmo modelo de dados normalizado documentado no diagrama ER da Parte 13).

---

## Passo 5 — Combinando tabelas com `merge`

```python
df_editoras = pd.read_sql("SELECT * FROM Editora", conexao)
df_assuntos = pd.read_sql("SELECT * FROM Assunto", conexao)
conexao.close()

df_completo = df.merge(df_editoras, on="IdEditora").merge(df_assuntos, on="IdAssunto")

print(df_completo.groupby("NomeEditora")["PrecoLivro"].mean())
print(df_completo.groupby("NomeAssunto").size())
```

**Pontos técnicos:**
- **`.merge(outro_df, on="ColunaChave")`** — equivalente ao `JOIN` do SQL, combinando as colunas de dois DataFrames a partir de uma coluna em comum
- **Encadeamento de `.merge()`** — cada `.merge()` devolve um novo DataFrame, permitindo encadear uma segunda junção imediatamente (`df.merge(A, ...).merge(B, ...)`), padrão comum em pandas
- **`.size()`** em vez de `.mean()` — conta a quantidade de linhas por grupo, em vez de calcular um valor agregado sobre uma coluna específica

**Resultado — preço médio por editora, agora legível:**
```
Aleph                    44.47
Companhia das Letras     36.18
Francisco Alves          59.41
McGraw-Hill             212.58
Microsoft Press         432.00
Pearson Education         0.00
Penguin Books            51.70
Record                   51.99
Wiley                    45.90
```

**Resultado — quantidade de livros por assunto:**
```
Aventura               3
Computers               1
Eletronica               1
Ficcao Cientifica       11
Informatica               1
Romance                 6
```

**Importante:** todos os valores calculados via `groupby`/`merge` do pandas coincidiram exatamente com os valores obtidos previamente pelo `groupby` direto no `IdEditora` (sem nome) — confirmando que o `merge` apenas enriquece a legibilidade do resultado, sem alterar os cálculos em si.

---

## Passo 6 — Exportando para Excel

```python
df_completo.to_excel("relatorio_acervo.xlsx", index=False, sheet_name="Acervo")
```

**Pontos técnicos:**
- **`.to_excel(...)`** — gera um arquivo `.xlsx` real a partir do DataFrame, usando `openpyxl` como motor
- **`index=False`** — evita que a coluna de índice numérico automático (irrelevante para quem consome o relatório) seja incluída como coluna no arquivo final
- **`sheet_name="Acervo"`** — nomeia a aba do Excel, em vez do nome padrão genérico

Resultado: `relatorio_acervo.xlsx`, contendo o acervo completo com as colunas de `Livro` combinadas às de `Editora` e `Assunto`, aberto e validado com sucesso.

---

## Script final consolidado

```python
import pandas as pd
import pyodbc

conexao = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=Biblioteca;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

df = pd.read_sql("SELECT * FROM Livro", conexao)
df_editoras = pd.read_sql("SELECT * FROM Editora", conexao)
df_assuntos = pd.read_sql("SELECT * FROM Assunto", conexao)

conexao.close()

df_completo = df.merge(df_editoras, on="IdEditora").merge(df_assuntos, on="IdAssunto")

print("=== Preço médio por editora (com nome) ===")
print(df_completo.groupby("NomeEditora")["PrecoLivro"].mean())

print()
print("=== Quantidade de livros por assunto ===")
print(df_completo.groupby("NomeAssunto").size())

df_completo.to_excel("relatorio_acervo.xlsx", index=False, sheet_name="Acervo")
print()
print("Relatório salvo em relatorio_acervo.xlsx")
```

---

## Roadmap atualizado

- [x] O que é um DataFrame, e por que ele é relevante para o mercado de integração/dados
- [x] `pd.read_sql(...)` — puxar dados do banco direto para um DataFrame
- [x] Exercícios práticos com a base `Biblioteca`: preço médio por editora, quantidade de livros por assunto
- [x] Gerar relatório em Excel a partir do banco (`.to_excel()`)
- [ ] (Possível extensão) endpoint novo `GET /relatorios/...`, devolvendo um Excel gerado na hora, direto pela API
- [ ] (Possível extensão) exercício de ETL simples: ler um CSV externo, limpar com pandas, inserir no banco
- [ ] (Radar) Tela de login para o painel administrativo (JWT) — retomar quando fizer sentido
- [ ] (Radar) Deploy simples, evolução do frontend

---

## Conceitos aprendidos nesta etapa

- Papel do `DataFrame` como estrutura central do pandas, e sua relação direta com o formato de dados tabular que já existia no projeto (resultado de consultas SQL)
- Diferença entre um `DataFrame` (tabela completa) e uma `Series` (uma única coluna, obtida ao selecionar `df["Coluna"]`)
- Uso de `pd.read_sql()` como substituto direto do padrão manual `cursor.fetchall()` + `dict(zip(...))` já usado em todo o `main.py`
- `groupby()` como equivalente do `GROUP BY` do SQL, aplicável inteiramente em Python, sem depender de uma nova consulta ao banco
- `merge()` como equivalente do `JOIN` do SQL, incluindo o padrão de encadear múltiplos merges em sequência
- Diferença entre agregações que resumem valores (`.mean()`) e agregações que contam ocorrências (`.size()`)
- Geração de relatórios reais em Excel a partir de dados de um banco relacional — fluxo de trabalho comum em tarefas de integração e análise de dados no mercado
- Reforço de um padrão de leitura de dados: identificar resíduos ou inconsistências (como os ISBNs incompletos) ao visualizar os dados de forma agregada — um DataFrame frequentemente expõe problemas de qualidade de dado que passam despercebidos em consultas linha a linha
