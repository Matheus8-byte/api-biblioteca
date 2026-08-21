# Documentação (Parte 6) — Log do DELETE guardando o registro deletado

Continuação da **Parte 5 — Delete em Lote**. Nesta etapa: resolução do gap identificado nas etapas anteriores — o log de auditoria não guardava os dados do livro no momento da exclusão, apenas o ID e o status da operação.

---

## Motivação (recapitulando o gap identificado)

Nos testes de `DELETE`, o campo `PayloadRecebido` da tabela `LogIntegracao` sempre vinha `NULL`, porque o método `DELETE` não recebe Body — não havia "o que registrar" no momento da chamada.

**Problema real de auditoria:** o log mostrava *que* um livro foi deletado (ou tentativa de deleção), mas não *quais eram os dados* daquele livro no momento da exclusão. Para um log de auditoria de verdade, essa informação é essencial — permite reconstruir o que foi removido, mesmo depois de o registro não existir mais na tabela principal.

---

## Solução implementada

Antes de executar o `DELETE` de fato, o código agora:
1. Busca o registro completo do livro (`SELECT * FROM Livro WHERE IdLivro = ?`)
2. Se encontrado, converte o resultado em um dicionário e depois em uma string JSON
3. Só então executa o `DELETE`
4. Grava esse JSON (o "retrato" do livro no momento da exclusão) no campo `PayloadRecebido` do log

Essa mudança foi aplicada em **dois lugares**: no `DELETE` individual e no loop do `DELETE` em lote.

---

## Código atualizado — DELETE individual

```python
@app.delete("/livros/{id_livro}")
def deletar_livro(id_livro: int):
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        # Busca o registro ANTES de deletar, para guardar no log
        cursor.execute("SELECT * FROM Livro WHERE IdLivro = ?", id_livro)
        linha = cursor.fetchone()

        if linha is None:
            registrar_log(f"/livros/{id_livro}", "DELETE", None, "ERRO", mensagem_erro="Livro não encontrado")
            raise HTTPException(status_code=404, detail="Livro não encontrado")

        colunas = [coluna[0] for coluna in cursor.description]
        registro_deletado = dict(zip(colunas, linha))
        registro_deletado_json = json.dumps(registro_deletado, default=str)

        cursor.execute("DELETE FROM Livro WHERE IdLivro = ?", id_livro)
        conexao.commit()

        registrar_log(f"/livros/{id_livro}", "DELETE", registro_deletado_json, "SUCESSO", id_gerado=id_livro)
        return {"mensagem": "Livro removido com sucesso!", "IdLivro": id_livro}

    except pyodbc.Error as e:
        conexao.rollback()
        registrar_log(f"/livros/{id_livro}", "DELETE", None, "ERRO", mensagem_erro=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conexao.close()
```

## Código atualizado — DELETE em lote (dentro do loop)

```python
@app.post("/livros/delete-batch")
def deletar_livros_em_lote(entrada: DeleteLoteEntrada):
    resultados = []
    for id_livro in entrada.ids:
        conexao = get_conexao()
        cursor = conexao.cursor()
        try:
            # Busca o registro ANTES de deletar, para guardar no log
            cursor.execute("SELECT * FROM Livro WHERE IdLivro = ?", id_livro)
            linha = cursor.fetchone()

            if linha is None:
                registrar_log(f"/livros/{id_livro}", "DELETE (lote)", None, "ERRO", mensagem_erro="Livro não encontrado")
                resultados.append({"IdLivro": id_livro, "status": "ERRO", "motivo": "Livro não encontrado"})
                continue

            colunas = [coluna[0] for coluna in cursor.description]
            registro_deletado = dict(zip(colunas, linha))
            registro_deletado_json = json.dumps(registro_deletado, default=str)

            cursor.execute("DELETE FROM Livro WHERE IdLivro = ?", id_livro)
            conexao.commit()

            registrar_log(f"/livros/{id_livro}", "DELETE (lote)", registro_deletado_json, "SUCESSO", id_gerado=id_livro)
            resultados.append({"IdLivro": id_livro, "status": "SUCESSO"})

        except pyodbc.Error as e:
            conexao.rollback()
            registrar_log(f"/livros/{id_livro}", "DELETE (lote)", None, "ERRO", mensagem_erro=str(e))
            resultados.append({"IdLivro": id_livro, "status": "ERRO", "motivo": str(e)})

        finally:
            conexao.close()

    total_sucesso = len([r for r in resultados if r["status"] == "SUCESSO"])
    total_erro = len([r for r in resultados if r["status"] == "ERRO"])

    return {
        "mensagem": f"Processado: {total_sucesso} removido(s), {total_erro} com erro.",
        "detalhes": resultados
    }
```

---

## Pontos técnicos importantes

- **`cursor.fetchone()`** — retorna a linha do livro (ou `None` se não existir) antes de deletar. Isso substitui a checagem antiga baseada em `cursor.rowcount == 0` (que só era possível saber *depois* do DELETE) — agora a checagem de existência acontece *antes*, através do próprio SELECT.
- **`dict(zip(colunas, linha))`** — mesmo padrão já usado em `listar_livros`, para converter a linha do banco em um dicionário Python.
- **`json.dumps(registro_deletado, default=str)`** — o parâmetro `default=str` é essencial aqui: o campo `DataPub` retorna como um objeto `date` do Python, que o `json.dumps` não sabe serializar nativamente. `default=str` resolve isso convertendo automaticamente qualquer tipo não suportado (como `date`) para texto.
- **`continue`** no loop do lote — ao não encontrar o livro, registra o log de erro, adiciona o resultado na lista, e pula direto para o próximo ID da lista, sem tentar executar o `DELETE`.

---

## Teste realizado

**Requisição:** `DELETE http://127.0.0.1:8000/livros/102`

**Log gravado, consultado via SQL:**

```sql
SELECT TOP 1 * FROM LogIntegracao ORDER BY DataHora DESC;
```

| IdLog | Endpoint | MetodoHttp | PayloadRecebido | Status | IdGerado |
|---|---|---|---|---|---|
| 13 | /livros/102 | DELETE | `{"IdLivro": 102, "NomeLivro": "O Investidor Inteligente", "ISBN13": "9788595080805", "DataPub": "2016-01-25", "PrecoLivro": "79.9000", "NumeroPaginas": 450, "IdEditora": 6, "IdAssunto": 7, "Edicao": null}` | SUCESSO | 102 |

**Resultado:** o log agora guarda o retrato completo do livro no momento da exclusão — gap resolvido.

---

## Observação técnica: tipo `money` vira string no JSON

No resultado do teste, o campo `PrecoLivro` apareceu como `"79.9000"` (string, com zeros à direita), em vez de `79.9` (número). Isso acontece porque:
- O tipo `money` do SQL Server é convertido pelo pyodbc para um tipo decimal do Python
- Como esse tipo também não é serializável nativamente pelo `json.dumps`, ele cai no mesmo tratamento do `default=str`, sendo convertido para texto — preservando a precisão decimal original do banco (`79.9000`)

**Não é um erro** — é uma particularidade esperada da conversão automática de tipos não nativos do JSON (como `date` e `Decimal`) para string, através do parâmetro `default=str`.

---

## Roadmap atualizado

- [x] Log do DELETE guardar o registro deletado (individual e em lote)
- [ ] Criar collection no Postman para reaproveitar as requisições
- [ ] (Opcional) Explorar SOAP/XML como comparação ao REST/JSON
- [ ] (Opcional) Adicionar validações extras (ex: checar se ISBN já existe antes de inserir)
- [ ] (Opcional) Variáveis de ambiente (.env) para não deixar a connection string no código
- [ ] (Opcional) Paginação no GET /livros
- [ ] (Opcional) Autenticação simples (API Key)

---

## Conceitos aprendidos nesta etapa

- Padrão de **"capturar o estado antes de modificar"** (capture-before-mutate): buscar e preservar o dado antes de uma operação destrutiva (DELETE), técnica comum em sistemas de auditoria reais
- Uso do parâmetro `default=str` no `json.dumps()` para lidar com tipos Python que não são nativamente serializáveis em JSON (como `date` e `Decimal`)
- Diferença entre checar existência de um registro **antes** (via `SELECT` + `fetchone()`) versus **depois** (via `cursor.rowcount`) de uma operação — a primeira abordagem permite capturar os dados antes da exclusão, a segunda não
- Reconhecer particularidades de conversão de tipos entre banco de dados (SQL Server `money`) → driver Python (`pyodbc`) → formato de intercâmbio (JSON), e diferenciar isso de um erro real de código
