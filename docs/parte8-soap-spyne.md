# Documentação (Parte 8) — Serviço SOAP com spyne (comparação REST vs SOAP)

Continuação da **Parte 7 — Collection e Environment no Postman**. Nesta etapa: criação de um serviço SOAP simples com a biblioteca `spyne`, geração de WSDL, testes via SoapUI, e comparação prática com a API REST já construída nas partes anteriores.

---

## Motivação

Até aqui, todo o projeto foi construído em torno de REST/JSON (FastAPI + Postman). O objetivo desta etapa foi sair do papel e experimentar, na prática, o outro grande paradigma de web services: **SOAP/XML**, usando o SoapUI como cliente de teste — para entender as diferenças reais entre os dois, não só na teoria.

---

## Problema encontrado antes de começar: incompatibilidade do spyne com Python 3.14.7

A biblioteca `spyne` (usada para criar serviços SOAP em Python) é pouco mantida e **não funciona nas versões recentes do Python**:

- No **Python 3.12+**, quebra porque depende do módulo `six` embutido, que foi removido da biblioteca padrão.
- No **Python 3.13+** (incluindo o 3.14.7 já instalado no projeto), quebra porque usa o módulo `cgi`, também removido da biblioteca padrão (PEP 594).

**Decisão tomada:** em vez de arriscar quebrar o ambiente Python principal (usado pela API REST), foi criado um **ambiente isolado**, usando uma segunda versão do Python (3.10.11) já disponível na máquina, dedicado exclusivamente a este experimento SOAP — sem qualquer alteração no Python 3.14.7 nem no projeto `api-biblioteca` já existente.

---

## Passo 1 — Estrutura do novo projeto

Nova pasta, separada do projeto REST:

```
C:\projetos\soap-livros\
```

Confirmação de que o Python 3.10 estava disponível na máquina, via Python Launcher:

```
py -0
```

**Resultado:**
```
Installed Pythons found by py Launcher for Windows
 -3.14-64 *
 -3.10-64
```

O `*` indica que o 3.14 continua sendo a versão padrão do comando `python` — o 3.10 só é usado quando chamado explicitamente.

---

## Passo 2 — Criar e ativar a venv

```
mkdir C:\projetos\soap-livros
cd C:\projetos\soap-livros
py -3.10 -m venv venv
venv\Scripts\activate
```

Confirmação de que a venv ativou corretamente (prompt passa a mostrar `(venv)` no início da linha):

```
(venv) C:\projetos\soap-livros>python --version
Python 3.10.11
```

> **Conceito de venv:** uma "caixinha isolada" dentro da pasta do projeto, com sua própria cópia do Python e das bibliotecas instaladas, sem interferir no Python principal da máquina nem em outros projetos. Precisa ser ativada a cada nova sessão de terminal (`venv\Scripts\activate`) — a ativação não é permanente.

---

## Passo 3 — Instalar as bibliotecas dentro da venv

```
pip install spyne lxml pyodbc
```

**Bibliotecas instaladas:**
- `spyne` — cria o serviço SOAP e gera o WSDL automaticamente
- `lxml` — processamento de XML, exigido pelo spyne
- `pyodbc` — mesmo driver usado na API REST, para o serviço SOAP consultar o **mesmo banco** `Biblioteca` (comparação justa entre os dois protocolos, usando os mesmos dados)

Instalação concluída sem erros (diferente do que aconteceria no Python 3.14.7).

---

## Passo 4 — Código do serviço SOAP (`soap_service.py`)

```python
from spyne import Application, rpc, ServiceBase, Integer, Unicode, Decimal, ComplexModel
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from wsgiref.simple_server import make_server
import pyodbc


def get_conexao():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=Biblioteca;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )


# Estrutura de dados que o SOAP vai devolver (equivalente ao "response model")
class LivroSoap(ComplexModel):
    IdLivro = Integer
    NomeLivro = Unicode
    ISBN13 = Unicode
    PrecoLivro = Decimal
    NumeroPaginas = Integer


class LivroService(ServiceBase):
    @rpc(Integer, _returns=LivroSoap)
    def consultar_livro(ctx, id_livro):
        conexao = get_conexao()
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT IdLivro, NomeLivro, ISBN13, PrecoLivro, NumeroPaginas FROM Livro WHERE IdLivro = ?",
            id_livro
        )
        linha = cursor.fetchone()
        conexao.close()

        if linha is None:
            return LivroSoap(IdLivro=0, NomeLivro="Não encontrado", ISBN13="", PrecoLivro=0, NumeroPaginas=0)

        return LivroSoap(
            IdLivro=linha.IdLivro,
            NomeLivro=linha.NomeLivro,
            ISBN13=linha.ISBN13,
            PrecoLivro=linha.PrecoLivro,
            NumeroPaginas=linha.NumeroPaginas
        )


application = Application(
    [LivroService],
    tns='biblioteca.soap.service',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

wsgi_app = WsgiApplication(application)

if __name__ == '__main__':
    servidor = make_server('127.0.0.1', 8001, wsgi_app)
    print("Serviço SOAP rodando em http://127.0.0.1:8001")
    print("WSDL disponível em http://127.0.0.1:8001/?wsdl")
    servidor.serve_forever()
```

**Pontos técnicos importantes:**
- **`ComplexModel`** — equivalente ao `BaseModel` do Pydantic (usado no FastAPI): define a "forma" dos dados trocados. Aqui, `LivroSoap` descreve os campos que o SOAP devolve.
- **`@rpc(Integer, _returns=LivroSoap)`** — decorador que transforma um método Python comum em uma **operação SOAP**, equivalente ao `@app.get(...)` do FastAPI, no "idioma" do spyne. `Integer` é o tipo do parâmetro de entrada (`id_livro`), `_returns=LivroSoap` é o tipo do retorno.
- **Porta `8001`**, diferente da porta `8000` usada pela API REST — de propósito, para permitir rodar os dois serviços ao mesmo tempo e comparar lado a lado.
- **Mesma connection string do `main.py`** — o SOAP lê o mesmo banco `Biblioteca`, possibilitando consultar o mesmo `IdLivro` nos dois protocolos.
- **`make_server` + `serve_forever()`** — servidor de desenvolvimento embutido no próprio Python (`wsgiref`), cumprindo o mesmo papel que o `uvicorn` cumpre para o FastAPI — sem precisar instalar nada a mais.

---

## Passo 5 — Rodar o serviço e acessar o WSDL

```
python soap_service.py
```

**Resultado:**
```
Serviço SOAP rodando em http://127.0.0.1:8001
WSDL disponível em http://127.0.0.1:8001/?wsdl
```

Terminal fica ocupado rodando o servidor (mesmo comportamento do `uvicorn` na API REST) — precisa permanecer aberto enquanto o serviço estiver em uso.

Acessando `http://127.0.0.1:8001/?wsdl` no navegador: retorna um documento XML extenso — o **WSDL**, contrato que descreve a operação `consultar_livro`, os tipos de dados envolvidos e o endereço do serviço. É esse documento que ferramentas como o SoapUI leem para montar automaticamente as requisições de teste, sem depender do código-fonte.

---

## Passo 6 — Importar no SoapUI

1. **File → New SOAP Project**
2. **Project Name:** `Biblioteca SOAP`
3. **Initial WSDL:** `http://127.0.0.1:8001/?wsdl`
4. Opção **"Create Requests"** marcada — o SoapUI monta automaticamente uma requisição de exemplo para `consultar_livro`

Estrutura gerada na árvore do projeto:
```
Biblioteca SOAP
 └─ LivroService
     └─ consultar_livro
         └─ Request 1
```

---

## Passo 7 — Testes realizados

### Teste 1 — Consulta de livro existente (`IdLivro: 101`)

**Requisição enviada:**
```xml
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:bib="biblioteca.soap.service">
   <soapenv:Header/>
   <soapenv:Body>
      <bib:consultar_livro>
         <bib:id_livro>101</bib:id_livro>
      </bib:consultar_livro>
   </soapenv:Body>
</soapenv:Envelope>
```

**Resposta recebida:**
```xml
<soap11env:Envelope xmlns:soap11env="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="biblioteca.soap.service">
   <soap11env:Body>
      <tns:consultar_livroResponse>
         <tns:consultar_livroResult>
            <tns:IdLivro>101</tns:IdLivro>
            <tns:NomeLivro>Vinte Mil Leguas Submarinas</tns:NomeLivro>
            <tns:ISBN13>9788582850022</tns:ISBN13>
            <tns:PrecoLivro>24.5000</tns:PrecoLivro>
            <tns:NumeroPaginas>448</tns:NumeroPaginas>
         </tns:consultar_livroResult>
      </tns:consultar_livroResponse>
   </soap11env:Body>
</soap11env:Envelope>
```

### Teste 2 — Consulta de livro inexistente (`IdLivro: 99999`)

**Resposta recebida (status HTTP 200, sem erro formal):**
```xml
<soap11env:Envelope xmlns:soap11env="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="biblioteca.soap.service">
   <soap11env:Body>
      <tns:consultar_livroResponse>
         <tns:consultar_livroResult>
            <tns:IdLivro>0</tns:IdLivro>
            <tns:NomeLivro>Não encontrado</tns:NomeLivro>
            <tns:ISBN13/>
            <tns:PrecoLivro>0</tns:PrecoLivro>
            <tns:NumeroPaginas>0</tns:NumeroPaginas>
         </tns:consultar_livroResult>
      </tns:consultar_livroResponse>
   </soap11env:Body>
</soap11env:Envelope>
```

---

## Erro encontrado durante os testes: requisição "sumindo" no SoapUI

Em um primeiro teste com `IdLivro: 101`, o SoapUI retornou `<missing raw response data>` e o terminal do serviço SOAP não registrou nenhuma chamada `POST` — apenas os `GET /?wsdl` anteriores. Isso indicava que a requisição **não chegou a sair do SoapUI**, falhando localmente antes do envio.

**Hipótese investigada:** namespace (`xmlns:bib=...`) mal declarado no XML da requisição, o que faria o SoapUI recusar o envio. Ao inspecionar o XML completo, o namespace estava, na verdade, declarado corretamente.

**Resolução:** o teste foi refeito (após reabertura do ambiente numa sessão posterior, com os servidores religados) e funcionou normalmente — sugerindo que o problema foi pontual/momentâneo do SoapUI (possivelmente cache da requisição), não um erro de configuração real. Registrado aqui como referência, caso o sintoma se repita no futuro.

**Checklist útil para esse tipo de sintoma** (resposta ausente + nenhum log no servidor):
1. Verificar se o servidor SOAP (`python soap_service.py`) ainda está rodando no terminal
2. Verificar o campo de **endpoint** na tela da requisição do SoapUI (deve apontar para `http://127.0.0.1:8001/`)
3. Conferir se o namespace usado nas tags do XML está declarado no `<soapenv:Envelope>`
4. Testar a mesma chamada via Postman (POST cru, com `Content-Type: text/xml`) para isolar se o problema é do SoapUI especificamente ou do serviço/rede

---

## Comparação lado a lado — REST (JSON) vs SOAP (XML)

Mesmo livro (`IdLivro: 101`), consultado nos dois protocolos:

**REST — `GET {{base_url}}/livros` (Postman):**
```json
{
  "IdLivro": 101,
  "NomeLivro": "Vinte Mil Leguas Submarinas",
  "ISBN13": "9788582850022",
  "PrecoLivro": 24.5
}
```

**SOAP — `consultar_livro` (SoapUI):**
```xml
<tns:consultar_livroResult>
   <tns:IdLivro>101</tns:IdLivro>
   <tns:NomeLivro>Vinte Mil Leguas Submarinas</tns:NomeLivro>
   <tns:ISBN13>9788582850022</tns:ISBN13>
   <tns:PrecoLivro>24.5000</tns:PrecoLivro>
   <tns:NumeroPaginas>448</tns:NumeroPaginas>
</tns:consultar_livroResult>
```

### Diferenças observadas na prática

| Aspecto | REST (JSON) | SOAP (XML) |
|---|---|---|
| **Formato do dado** | JSON — mais compacto, leve | XML — mais verboso, envelope (`Envelope`/`Body`) obrigatório em toda chamada |
| **Descoberta do serviço** | Não obrigatória (Swagger `/docs` é conveniência do FastAPI, não parte do padrão REST) | WSDL obrigatório — contrato formal e detalhado, permite gerar clientes automaticamente |
| **Como cada operação é acessada** | Verbo HTTP + URL (`GET /livros/101`) | Um único endpoint (`/`), a operação é definida dentro do corpo da mensagem (`consultar_livro`) |
| **Sinalização de erro/não encontrado** | Status HTTP dedicado (ex: `404`) | Neste serviço: resposta HTTP 200 "normal", com dado sinalizando o problema (`IdLivro: 0`) — **não** usamos SOAP Fault, o mecanismo de erro formal do próprio protocolo |
| **Legibilidade para humanos** | Mais direta | Mais verbosa, exige entender a estrutura do envelope |

### Ponto de atenção sobre o tratamento de "não encontrado" no SOAP

No REST (`main.py`), um recurso inexistente gera `raise HTTPException(status_code=404, ...)` — um erro HTTP reconhecível por qualquer cliente, sem precisar interpretar o corpo da resposta.

No serviço SOAP implementado aqui, essa mesma situação foi tratada retornando um objeto com valores "vazios" (`IdLivro=0`, `NomeLivro="Não encontrado"`), dentro de uma resposta de **sucesso** (HTTP 200). Isso funciona para este experimento, mas é uma limitação de design: qualquer cliente que consumir esse serviço precisa conhecer essa convenção específica (`IdLivro == 0` significa erro) para tratar o caso corretamente — diferente do REST, onde o status code já basta.

> **Nota para evolução futura (fora do escopo desta etapa):** o SOAP possui um mecanismo de erro formal chamado **SOAP Fault**, equivalente a uma exceção dentro do próprio protocolo. Não foi utilizado neste experimento — ficou registrado como possível melhoria futura, caso o projeto SOAP avance além da comparação inicial.

---

## Roadmap atualizado

- [x] Explorar SOAP/XML como comparação ao REST/JSON
- [ ] (Opcional) Adicionar validações extras (ex: checar se ISBN já existe antes de inserir)
- [ ] (Opcional) Variáveis de ambiente (.env) para não deixar a connection string no código
- [ ] (Opcional) Paginação no GET /livros
- [ ] (Opcional) Autenticação simples (API Key)
- [ ] (Opcional) Usar SOAP Fault para tratamento formal de erros no serviço SOAP

---

## Conceitos aprendidos nesta etapa

- Verificar compatibilidade de uma biblioteca com a versão do Python **antes** de instalar em um ambiente já em uso — bibliotecas antigas/pouco mantidas (como `spyne`) podem depender de módulos removidos em versões recentes da linguagem (`six`, `cgi`)
- Conceito e uso prático de **ambiente virtual (venv)**: isolar dependências de um projeto experimental sem afetar o Python principal nem outros projetos
- Uso do **Python Launcher for Windows** (`py -0`, `py -3.10`) para gerenciar múltiplas versões do Python instaladas na mesma máquina
- Estrutura básica de um serviço SOAP com `spyne`: `ComplexModel` (forma dos dados), `@rpc` (operação exposta), `Application` + `WsgiApplication` (equivalentes ao `app = FastAPI()` e ao `uvicorn`)
- O que é um **WSDL** e para que serve: contrato formal que descreve as operações de um serviço SOAP, permitindo que ferramentas como o SoapUI montem requisições automaticamente
- Diferenças práticas entre REST/JSON e SOAP/XML: formato de dados, forma de descoberta do serviço, e principalmente **como cada protocolo trata erros** — status HTTP dedicado (REST) vs. mecanismo próprio do protocolo, o SOAP Fault, que neste experimento não chegou a ser implementado
- Importância de ter múltiplos terminais abertos simultaneamente ao trabalhar com mais de um serviço rodando em paralelo (REST na porta 8000, SOAP na porta 8001), e de religar tudo (banco, REST, SOAP) após reiniciar a máquina
