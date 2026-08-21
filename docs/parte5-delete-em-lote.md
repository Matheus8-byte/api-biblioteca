# Documentação (Parte 5) — Delete em Lote

Continuação da **Parte 4 — Endpoints de apoio**. Nesta etapa: implementação da remoção de múltiplos livros em uma única requisição, item do roadmap identificado durante os testes de `DELETE` individual.

---

## Motivação

O endpoint `DELETE /livros/{id}` só remove um registro por vez. Ao ser questionado sobre como remover, por exemplo, 10 registros de uma vez, foram discutidas 3 abordagens possíveis:

1. Múltiplos IDs via query string (`DELETE /livros?ids=100,101,102`)
2. **Endpoint dedicado com lista de IDs no body (`POST /livros/delete-batch`)** ← escolhida
3. Delete por filtro (`DELETE /livros?IdEditora=999`)

**Decisão:** endpoint dedicado via `POST`, mesmo fugindo um pouco do REST "purista" (usar POST para deletar), porque o método `DELETE` tradicionalmente não é usado com Body em várias implementações client-side — usar POST para essa ação específica é uma prática comum e pragmática no mercado.

**Comportamento definido:**
- Tenta deletar cada ID da lista, um por um, com commits **individuais**
- Se um item falhar (ex: por FK), os demais continuam sendo processados normalmente — não aborta o lote inteiro
- Cada tentativa é registrada individualmente no log de integração
- A resposta final resume quantos tiveram sucesso, quantos falharam, e o detalhe/motivo de cada item

---

## Código adicionado ao `main.py`

```python
class DeleteLoteEntrada(BaseModel):
    ids: list[int]

@app.post("/livros/delete-batch")
def deletar_livros_em_lote(entrada: DeleteLoteEntrada):
    resultados = []

    for id_livro in entrada.ids:
        conexao = get_conexao()
        cursor = conexao.cursor()
        try:
            cursor.execute("DELETE FROM Livro WHERE IdLivro = ?", id_livro)

            if cursor.rowcount == 0:
                registrar_log(f"/livros/{id_livro}", "DELETE (lote)", None, "ERRO", mensagem_erro="Livro não encontrado")
                resultados.append({"IdLivro": id_livro, "status": "ERRO", "motivo": "Livro não encontrado"})
            else:
                conexao.commit()
                registrar_log(f"/livros/{id_livro}", "DELETE (lote)", None, "SUCESSO", id_gerado=id_livro)
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

**Pontos técnicos importantes:**
- `DeleteLoteEntrada` — novo modelo Pydantic com um único campo `ids: list[int]`, validando que o Body deve conter uma lista de números inteiros
- **Uma conexão por item do loop** — cada `IdLivro` abre e fecha sua própria conexão/transação, garantindo que a falha de um item não afeta o processamento (nem o commit) dos demais
- `resultados` — lista acumulando o status individual de cada tentativa, retornada por completo na resposta final
- Cada chamada de log usa o texto `"DELETE (lote)"` no campo `MetodoHttp`, diferenciando das chamadas de `DELETE` individual no histórico de auditoria

---

## Erro encontrado durante a implementação: coluna do log truncada

Ao testar pela primeira vez, a API retornou **Internal Server Error** (erro 500). O traceback no terminal do uvicorn revelou a causa real:

```
pyodbc.ProgrammingError: ('42000', "[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Os dados de sequência ou binários estão truncados na tabela 'Biblioteca.dbo.LogIntegracao', coluna 'MetodoHttp'. Valor truncado: 'DELETE (lo'. (2628) ...")
```

**Causa:** a coluna `MetodoHttp` da tabela `LogIntegracao` (criada na Parte 2) foi definida como `VARCHAR(10)`, suficiente para `"POST"`, `"GET"`, `"PUT"`, `"DELETE"` — mas o novo valor `"DELETE (lote)"` tem 14 caracteres, ultrapassando o limite. O SQL Server rejeitou a inserção, o que interrompeu a execução do endpoint no meio do loop.

**Solução:** ajuste da estrutura da tabela via script Python (mais rápido que aguardar o SSMS carregar):

```python
import pyodbc

conexao = pyodbc.connect(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=Biblioteca;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

cursor = conexao.cursor()
cursor.execute("""
    ALTER TABLE LogIntegracao
    ALTER COLUMN MetodoHttp VARCHAR(20) NOT NULL
""")
conexao.commit()

print("Coluna 'MetodoHttp' ajustada para VARCHAR(20) com sucesso!")

conexao.close()
```

Coluna ampliada de `VARCHAR(10)` para `VARCHAR(20)`, resolvendo o problema.

> **Nota interessante confirmada na prática:** mesmo com o erro 500 geral interrompendo a resposta da API, o item que já havia sido processado **antes** do erro (o `DELETE` do `IdLivro: 120`) já tinha sido commitado individualmente no banco. Isso evidenciou, na prática, por que processar cada item do lote com sua própria transação/commit é importante: uma falha no meio do processo não desfaz o que já foi concluído.

---

## Teste final

**Requisição:** `POST http://127.0.0.1:8000/livros/delete-batch`

```json
{
  "ids": [120, 119, 101, 99999]
}
```

Cenários cobertos propositalmente:
- `120` (Neuromancer) — sem vínculo em `LivroAutor`
- `119` (Duna) — sem vínculo em `LivroAutor`
- `101` — **com** vínculo em `LivroAutor` (deve falhar por FK)
- `99999` — ID inexistente (deve falhar por "não encontrado")

**Resultado:**

```json
{
    "mensagem": "Processado: 1 removido(s), 3 com erro.",
    "detalhes": [
        { "IdLivro": 120, "status": "ERRO", "motivo": "Livro não encontrado" },
        { "IdLivro": 119, "status": "SUCESSO" },
        { "IdLivro": 101, "status": "ERRO", "motivo": "(erro de FK do SQL Server)" },
        { "IdLivro": 99999, "status": "ERRO", "motivo": "Livro não encontrado" }
    ]
}
```

**Interpretação do resultado:** o `120` apareceu como "não encontrado" porque já havia sido deletado na tentativa anterior (a que resultou em erro 500 antes do ajuste da coluna) — o commit individual daquele item já tinha sido persistido no banco, mesmo com a resposta geral daquela chamada tendo falhado.

**Conclusão:** os 4 cenários possíveis (sucesso, não encontrado, bloqueio por FK, e efeito de execução parcial anterior) foram cobertos, validando o comportamento de processamento independente por item.

---

## Backup preventivo antes do teste

Antes de rodar o delete em lote de teste, foi preparado um script de reversão para recriar os livros que seriam removidos (Neuromancer e Duna), útil caso fosse necessário desfazer:

```sql
-- Recriar "Neuromancer"
INSERT INTO Livro (NomeLivro, ISBN13, DataPub, PrecoLivro, NumeroPaginas, IdEditora, IdAssunto, Edicao)
VALUES ('Neuromancer', '9788576570032', '1984-07-01', 39.90, 320, 3, 1, 2);

-- Recriar "Duna"
INSERT INTO Livro (NomeLivro, ISBN13, DataPub, PrecoLivro, NumeroPaginas, IdEditora, IdAssunto, Edicao)
VALUES ('Duna', '9788576570025', '1965-08-01', 59.90, 688, 3, 1, 1);
```

> **Atenção:** como `IdLivro` é `IDENTITY` (auto-incremento), esse INSERT gera **novos IDs**, diferentes de `120` e `119` — não recria os registros com os mesmos IDs originais.

---

## Roadmap atualizado

- [x] Delete em lote (`POST /livros/delete-batch`)
- [ ] Log do DELETE guardar o registro deletado
- [ ] Criar collection no Postman para reaproveitar as requisições
- [ ] (Opcional) Explorar SOAP/XML como comparação ao REST/JSON
- [ ] (Opcional) Adicionar validações extras (ex: checar se ISBN já existe antes de inserir)
- [ ] (Opcional) Variáveis de ambiente (.env) para não deixar a connection string no código
- [ ] (Opcional) Paginação no GET /livros
- [ ] (Opcional) Autenticação simples (API Key)

---

## Conceitos aprendidos nesta etapa

- Trade-off de design de API: usar `POST` para uma ação de exclusão em lote, quebrando a "pureza" REST em favor de compatibilidade prática com clientes HTTP (Body em DELETE é tratado de forma inconsistente por várias ferramentas/bibliotecas)
- Processamento de lote com **transações independentes por item**: cada operação tem seu próprio commit/rollback, permitindo sucesso parcial em vez de tudo-ou-nada
- Como ler um **traceback** do Python no terminal para identificar a causa real de um erro 500 (Internal Server Error), que por si só é uma mensagem genérica
- Limitação prática de colunas `VARCHAR(N)` no SQL Server: um valor mais longo que o definido gera erro de truncamento em vez de aceitar o dado cortado
- Como alterar a estrutura de uma tabela existente via `ALTER TABLE ... ALTER COLUMN`, inclusive rodando via Python quando o acesso direto ao SSMS está lento
- Confirmação prática de que falhas parciais no meio de um processo não desfazem automaticamente o que já foi commitado antes do erro — reforçando a importância de processar item por item quando se quer resiliência parcial
