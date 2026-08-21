# Documentação (Parte 14) — SOAP Fault

Continuação da **Parte 8 — Serviço SOAP com spyne**. Conclusão da **Fase 6** do Plano de Estudos. Nesta etapa: substituição do tratamento "improvisado" de erro no serviço SOAP (resposta de sucesso com dados vazios) pelo mecanismo formal do protocolo — o **SOAP Fault**.

---

## Motivação

Na Parte 8, quando um `id_livro` não era encontrado, o serviço SOAP devolvia uma resposta de **sucesso** (HTTP 200), com valores "vazios" sinalizando o problema (`IdLivro: 0`, `NomeLivro: "Não encontrado"`). Funcionava, mas exigia que qualquer cliente consumidor conhecesse essa convenção específica para detectar o erro — diferente do REST, onde um status `404` já é reconhecido universalmente, sem necessidade de interpretar o conteúdo da resposta.

Essa limitação já havia sido identificada e registrada como melhoria futura na própria Parte 8.

---

## O que é um SOAP Fault

Equivalente, dentro do protocolo SOAP, a uma exceção formal — o mesmo papel que o `HTTPException` cumpre no lado REST do projeto. Em vez de uma estrutura de dados "fingindo sucesso", a resposta já vem estruturalmente marcada como erro (elemento `<Fault>` dentro do XML), reconhecível por qualquer cliente SOAP sem depender de convenções específicas do serviço.

---

## Implementação com spyne

A biblioteca `spyne` já fornece uma classe pronta, `Fault`. Levantar (`raise`) uma instância dela dentro de uma operação `@rpc` faz o spyne montar automaticamente a resposta no formato de erro SOAP padrão, em vez do formato de sucesso.

### Código alterado em `soap_service.py`

**Import:**
```python
from spyne import Application, rpc, ServiceBase, Integer, Unicode, Decimal, ComplexModel, Fault
```

**Dentro de `consultar_livro`:**

**Antes:**
```python
        if linha is None:
            return LivroSoap(IdLivro=0, NomeLivro="Não encontrado", ISBN13="", PrecoLivro=0, NumeroPaginas=0)
```

**Depois:**
```python
        if linha is None:
            raise Fault(
                faultcode="Client.LivroNaoEncontrado",
                faultstring=f"Livro com IdLivro {id_livro} não foi encontrado"
            )
```

**Pontos técnicos importantes:**
- **`raise Fault(...)` em vez de `return`** — o spyne intercepta a exceção e monta a resposta como erro SOAP formal
- **`faultcode`** — segue a convenção do protocolo, prefixado por `Client.` (erro causado pelo lado de quem chamou — ex: ID inexistente) ou `Server.` (erro do lado do serviço — ex: falha de conexão com o banco). Usado `Client.LivroNaoEncontrado` neste caso, já que o problema está no valor informado pela requisição
- **`faultstring`** — mensagem de erro legível, equivalente ao `detail` do `HTTPException` no FastAPI
- **Qualificação automática do namespace** — o spyne devolveu o `faultcode` já prefixado com o namespace do envelope (`soap11env:Client.LivroNaoEncontrado`), seguindo a exigência formal do SOAP 1.1 de que o código do fault seja qualificado — comportamento automático, sem necessidade de configuração extra

---

## Erros encontrados durante a etapa (organização de terminais e edição)

### Contexto: múltiplos terminais e uma pausa no meio do processo

Diferente das etapas anteriores, esta envolveu **3 terminais simultâneos** (API REST, terminal livre para edição/scripts, e o serviço SOAP), o que gerou confusão adicional após uma pausa com desligamento da máquina no meio da implementação.

### Erro 1 — Política de execução do PowerShell bloqueando a venv

Ao tentar reativar a venv do SOAP em uma nova sessão de terminal:
```
venv\Scripts\activate : O arquivo ... Activate.ps1 não pode ser carregado porque a execução de scripts foi desabilitada neste sistema.
```

**Causa:** política de segurança padrão do PowerShell, que bloqueia execução de scripts (`.ps1`) por padrão.

**Solução:**
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

`RemoteSigned` permite rodar scripts criados localmente (como o `activate.ps1` gerado pela própria venv) sem exigir assinatura digital, mas mantém a exigência de assinatura para scripts baixados da internet — ajuste equilibrado de segurança, aplicado apenas ao usuário atual (`-Scope CurrentUser`), sem alterar configuração de sistema.

### Erro 2 — Edição do `Fault` não foi salva antes da pausa

Após reorganizar os terminais e reiniciar o serviço SOAP, o teste continuou retornando a resposta antiga (sem `Fault`). Investigação via `Ctrl+F` no Notepad confirmou que o arquivo `soap_service.py` ainda estava na versão original da Parte 8 — a edição proposta antes da pausa na máquina nunca chegou a ser salva.

**Solução:** reaplicação manual do ajuste (import + bloco `raise Fault`) diretamente no arquivo.

### Erro 3 — Erro de indentação (`IndentationError`) após reaplicar o ajuste

Ao colar o trecho novamente, a linha `if linha is None:` ficou com um espaço a mais de indentação em relação às linhas vizinhas (`conexao.close()`, `cursor.execute(...)`), quebrando a estrutura de blocos do Python.

**Causa:** Python exige indentação **consistente** dentro de um mesmo bloco de código — diferença de até um único espaço já é suficiente para interromper a execução.

**Solução:** correção manual do espaçamento, alinhando a linha `if` exatamente com as linhas adjacentes do mesmo bloco.

> **Lição prática, reforçando um padrão já visto em etapas anteriores do projeto:** diferenças sutis, invisíveis à primeira vista (um espaço extra, uma letra faltando), continuam sendo a causa mais comum de erro ao editar código manualmente em um editor sem realce de sintaxe. Conferir o arquivo linha a linha antes de assumir que "está igual" ao esperado é um hábito que vale manter.

### Lembrete técnico: o serviço SOAP não recarrega sozinho

Diferente da API REST (que roda com `uvicorn --reload`, detectando mudanças automaticamente), o `soap_service.py` usa o servidor simples do `wsgiref` (`make_server`), que **não observa alterações no arquivo**. Após qualquer edição, é necessário parar o servidor manualmente (`Ctrl+C`) e executar `python soap_service.py` novamente — passo que precisou ser reforçado nesta etapa após a reaplicação do ajuste.

---

## Testes realizados

### Teste 1 — Livro inexistente (`IdLivro: 99999`), com SOAP Fault

**Resposta:**
```xml
<soap11env:Envelope xmlns:soap11env="http://schemas.xmlsoap.org/soap/envelope/">
   <soap11env:Body>
      <soap11env:Fault>
         <faultcode>soap11env:Client.LivroNaoEncontrado</faultcode>
         <faultstring>Livro com IdLivro 99999 não foi encontrado</faultstring>
         <faultactor/>
      </soap11env:Fault>
   </soap11env:Body>
</soap11env:Envelope>
```

Diferente da Parte 8, a resposta agora é estruturalmente reconhecida como erro pelo próprio XML (elemento `Fault`), sem necessidade de interpretar valores "vazios" nos dados.

### Teste 2 — Livro existente (`IdLivro: 101`), confirmando ausência de regressão

**Resposta:**
```xml
<tns:consultar_livroResult>
   <tns:IdLivro>101</tns:IdLivro>
   <tns:NomeLivro>Vinte Mil Leguas Submarinas</tns:NomeLivro>
   <tns:ISBN13>9788582850022</tns:ISBN13>
   <tns:PrecoLivro>24.5000</tns:PrecoLivro>
   <tns:NumeroPaginas>448</tns:NumeroPaginas>
</tns:consultar_livroResult>
```

Confirma que o caminho de sucesso permanece inalterado — a mudança afetou exclusivamente o tratamento do caso de erro.

---

## Comparação atualizada: tratamento de erro REST vs SOAP

| | REST (`HTTPException`, status 404) | SOAP — antes (Parte 8) | SOAP — agora (Parte 14) |
|---|---|---|---|
| Como sinaliza erro | Status HTTP dedicado | Resposta de sucesso com dados vazios | Elemento `Fault` formal no XML |
| Cliente precisa conhecer convenção própria? | Não — status code é padrão universal | Sim — precisa saber checar `IdLivro == 0` | Não — `Fault` é reconhecido pela estrutura, padrão do protocolo |
| Ferramentas de teste destacam o erro visualmente? | Sim (status code diferente de 2xx) | Não | Sim (SoapUI sinaliza Fault visualmente) |

Com essa mudança, o serviço SOAP do projeto passa a seguir a mesma filosofia de "erro autoexplicativo" já praticada no lado REST, eliminando a limitação identificada desde a Parte 8.

---

## Roadmap atualizado

- [x] Autenticação simples (API Key) — Fase 1
- [x] Variáveis de ambiente (.env) — Fase 2
- [x] Consumir uma API externa (Python como cliente) — Fase 3
- [x] Paginação e validação de ISBN duplicado — Fase 4
- [ ] SQL em paralelo (conforme curso avança) — Fase 5, contínua
- [x] SOAP Fault — Fase 6
- [ ] Git/GitHub — Fase 7
- [ ] Site conectado ao banco (via API) — Fase 8

---

## Conceitos aprendidos nesta etapa

- Conceito de **SOAP Fault** como mecanismo de erro formal do protocolo SOAP, equivalente funcional ao `HTTPException` do lado REST
- Uso da classe `Fault` do spyne, incluindo a convenção de prefixos `Client.`/`Server.` no `faultcode` para indicar a origem do erro
- Diferença de comportamento entre o servidor REST (`uvicorn --reload`, recarrega sozinho) e o servidor SOAP (`wsgiref.make_server`, exige reinício manual após qualquer alteração de código)
- Política de execução de scripts do PowerShell (`Set-ExecutionPolicy`) e o ajuste `RemoteSigned` como meio-termo seguro para permitir scripts locais (como os gerados por uma venv) sem abrir mão de proteção contra scripts externos não assinados
- Reforço da importância de **confirmar que uma edição foi realmente salva** antes de assumir que o comportamento observado reflete o código esperado — especialmente relevante após interrupções na sessão de trabalho (like desligamentos de máquina no meio de uma tarefa)
- Sensibilidade do Python a indentação: diferenças de um único espaço quebram a execução, e esse tipo de erro é fácil de introduzir ao reeditar manualmente um trecho de código
