# Catálogo de Scripts — Referência Rápida

Consulta rápida dos scripts auxiliares em `scripts/`, sem precisar reabrir a documentação narrativa completa (Partes 1 a 17). Cada linha diz o que o script faz e como rodar.

> Todos os scripts assumem que você está na pasta raiz do projeto (`C:\projetos\api-biblioteca`) ao rodar o comando `python scripts\nome_do_script.py`.

---

## Diagnóstico e exploração do banco

| Script | O que faz | Como rodar | Onde foi documentado |
|---|---|---|---|
| `teste_conexao.py` | Testa a conexão com o SQL Server e lista as tabelas existentes no banco `Biblioteca` | `python scripts\teste_conexao.py` | Parte 1 |
| `ver_estrutura.py` | Mostra colunas, tipos de dado e nulabilidade da tabela `Livro` | `python scripts\ver_estrutura.py` | Parte 1 |
| `ver_identity.py` | Verifica quais colunas da tabela `Livro` são `IDENTITY` (auto-incremento) | `python scripts\ver_identity.py` | Parte 1 |
| `ver_identity_editora_assunto.py` | Mesma verificação de `IDENTITY`, mas para as tabelas `Editora` e `Assunto` | `python scripts\ver_identity_editora_assunto.py` | Parte 11 |
| `mapear_banco.py` | Extrai a estrutura completa do banco: tabelas, colunas, chaves primárias, chaves estrangeiras (relacionamentos), colunas `IDENTITY` e restrições `UNIQUE` | `python scripts\mapear_banco.py` | Parte 13 |

## Ajustes de estrutura (DDL via Python)

| Script | O que faz | Como rodar | Onde foi documentado |
|---|---|---|---|
| `ajustar_coluna.py` | Amplia a coluna `MetodoHttp` da tabela `LogIntegracao` de `VARCHAR(10)` para `VARCHAR(20)` (corrige truncamento do valor `"DELETE (lote)"`) | `python scripts\ajustar_coluna.py` | Parte 5 |

> **Nota:** este script já foi executado e seu efeito é permanente no banco — rodar de novo não causa problema (a coluna já está no tamanho correto), mas também não é necessário.

## Análise de dados (pandas)

| Script | O que faz | Como rodar | Onde foi documentado |
|---|---|---|---|
| `teste_pandas.py` | Primeiro contato com DataFrame, usando dados inventados (sem banco) — bom para relembrar a sintaxe básica | `python scripts\teste_pandas.py` | Parte 17 |
| `pandas_biblioteca.py` | Lê `Livro`, `Editora` e `Assunto` do banco, junta as tabelas (`merge`), calcula preço médio por editora e quantidade de livros por assunto, e exporta tudo para `relatorio_acervo.xlsx` | `python scripts\pandas_biblioteca.py` | Parte 17 |
| `limpar_isbns.py` | Identifica livros com `ISBN13` fora do padrão de 13 dígitos (diagnóstico, não corrige automaticamente) | `python scripts\limpar_isbns.py` | Parte 17 |

---

## Situação conhecida: dados de teste residuais

Os livros `IdLivro 126` e `127` têm `ISBN13` incompleto (sobras de testes de validação de duplicidade, Partes 9–11). Identificado via `limpar_isbns.py`. **Decisão consciente:** manter como estão por enquanto — não afeta o funcionamento da API, apenas dados de teste conhecidos, documentados aqui para referência caso apareçam em alguma consulta ou relatório futuro.

---

## Scripts que passaram a viver dentro do `main.py`

Alguns scripts antigos foram **substituídos** por funcionalidade equivalente direto na API, e não precisam mais ser rodados manualmente:

| Script antigo (não existe mais como arquivo avulso) | Substituído por |
|---|---|
| Qualquer inserção manual de editora/assunto via script | `POST /editoras` e `POST /assuntos` (Parte 16) |

---

## Como manter este catálogo atualizado

Sempre que um novo script for criado em `scripts/`, adicionar uma linha na tabela correspondente (ou criar uma nova seção, se for um tipo de script diferente dos já existentes), com uma frase objetiva do que ele faz — sem repetir a explicação detalhada, que já vive na documentação narrativa (`docs/parteN-*.md`).
