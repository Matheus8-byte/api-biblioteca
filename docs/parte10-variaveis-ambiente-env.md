# Documentação (Parte 10) — Variáveis de ambiente (.env)

Continuação da **Parte 9 — Autenticação via API Key**. Conclusão da **Fase 2** do Plano de Estudos. Nesta etapa: remoção de segredos e configurações fixas do código-fonte, movendo-os para um arquivo `.env`, e criação do hábito de proteção desses arquivos (`.gitignore`, `.env.example`) mesmo antes de o projeto usar Git.

---

## Motivação

Duas informações estavam fixas ("hardcoded") no `main.py`:

1. A `API_KEY`, criada na Parte 9 — um segredo de autenticação, exposto diretamente no código.
2. Os parâmetros da connection string do banco (driver, servidor, nome do banco) — não são "segredos" no sentido estrito (a conexão usa Windows Authentication, sem senha), mas fixá-los no código é uma prática ruim: qualquer mudança de ambiente (outro servidor, outro banco) exigiria editar o código-fonte diretamente.

**Prática de mercado adotada:** mover esses valores para um arquivo `.env`, separado do código, nunca compartilhado nem versionado — o código passa a apenas *ler* essas variáveis em tempo de execução.

---

## Passo 1 — Instalar `python-dotenv`

```
pip install python-dotenv
```

Biblioteca responsável por ler um arquivo `.env` e carregar seu conteúdo como variáveis de ambiente do processo Python em execução.

---

## Passo 2 — Criar o arquivo `.env`

```
API_KEY=biblioteca-2026-secreta
DB_DRIVER={ODBC Driver 18 for SQL Server}
DB_SERVER=localhost\SQLEXPRESS
DB_DATABASE=Biblioteca
```

**Observações sobre o formato:**
- Cada linha segue o padrão `NOME_DA_VARIAVEL=valor`, sem aspas, sem espaço ao redor do `=`
- A connection string foi quebrada em **4 variáveis separadas** (`DB_DRIVER`, `DB_SERVER`, `DB_DATABASE`) em vez de uma string única — facilita ler e alterar um valor específico isoladamente no futuro
- Usuário/senha não foram incluídos porque o projeto usa **Windows Authentication** (`Trusted_Connection=yes`), que não requer credenciais explícitas. Caso o projeto migre para autenticação SQL (usuário + senha) no futuro, bastaria adicionar `DB_USER` e `DB_PASSWORD` a este arquivo

---

## Passo 3 — Ajustar o `main.py` para ler do `.env`

**Antes:**
```python
API_KEY = "biblioteca-2026-secreta"  # temporário — vai pro .env na Fase 2

app = FastAPI()

def get_conexao():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS;"
        "DATABASE=Biblioteca;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
```

**Depois:**
```python
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
DB_DRIVER = os.getenv("DB_DRIVER")
DB_SERVER = os.getenv("DB_SERVER")
DB_DATABASE = os.getenv("DB_DATABASE")

app = FastAPI()

def get_conexao():
    return pyodbc.connect(
        f"DRIVER={DB_DRIVER};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_DATABASE};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
```

**Pontos técnicos importantes:**
- **`load_dotenv()`** — precisa ser chamada **antes** de qualquer `os.getenv(...)`; localiza o arquivo `.env` na pasta atual e injeta seu conteúdo como variáveis de ambiente do processo
- **`os.getenv("NOME")`** — biblioteca padrão do Python (não precisa instalar nada), usada para ler uma variável de ambiente já carregada. Retorna `None` (em vez de erro) se a variável não existir — importante ter em mente ao testar
- **f-strings na connection string** (`f"DRIVER={DB_DRIVER};"`) — interpolação de variável dentro de uma string, substituindo os valores antes fixos
- Nenhuma outra parte do `main.py` precisou mudar (rotas, `registrar_log`, modelos Pydantic) — a alteração ficou isolada no topo do arquivo

---

## Passo 4 — Proteger o `.env` com `.gitignore`

Mesmo sem o projeto usar Git ainda, foi criado o hábito preventivamente:

```
.env
__pycache__/
*.pyc
```

**Motivo:** garante que, quando o projeto for versionado no futuro (item já presente no roadmap, seção "Radar"), o `.env` — contendo dados de configuração — nunca seja commitado ou compartilhado acidentalmente.

---

## Passo 5 — Criar `.env.example`

Arquivo de referência, sem valores reais, para indicar quais variáveis o projeto espera:

```
API_KEY=sua-chave-aqui
DB_DRIVER={ODBC Driver 18 for SQL Server}
DB_SERVER=localhost\SQLEXPRESS
DB_DATABASE=Biblioteca
```

Diferente do `.env`, este arquivo **pode** ser compartilhado/versionado normalmente — não expõe nenhum segredo, apenas a estrutura esperada de configuração.

---

## Testes realizados

Reaproveitando os mesmos cenários já validados na Parte 9, agora para confirmar que os valores estão sendo lidos corretamente do `.env` (e não mais fixos no código):

1. **`GET /livros`** — retornou a lista normalmente, confirmando que a conexão com o banco (via `DB_DRIVER`, `DB_SERVER`, `DB_DATABASE` lidos do `.env`) segue funcionando
2. **`POST /livros` sem header `X-API-Key`** — `422`, comportamento inalterado
3. **`POST /livros` com a chave correta** (`biblioteca-2026-secreta`, herdada da Collection do Postman) — requisição autenticada com sucesso e processada até o banco; resultado observado foi um erro `400` de ISBN duplicado (reaproveitando um ISBN já cadastrado nos testes anteriores) — o que **confirma indiretamente** que a `API_KEY` lida do `.env` bateu corretamente com a enviada, já que a requisição passou da camada de autenticação e chegou à camada de banco

---

## Estrutura final da pasta do projeto (arquivos relacionados a esta etapa)

```
C:\projetos\api-biblioteca\
 ├─ main.py
 ├─ .env              ← valores reais, nunca compartilhado
 ├─ .env.example       ← template, pode ser compartilhado
 ├─ .gitignore         ← impede o .env de ser versionado no futuro
 └─ ...
```

---

## Roadmap atualizado

- [x] Autenticação simples (API Key) — Fase 1
- [x] Variáveis de ambiente (.env) — Fase 2
- [ ] Consumir uma API externa (Python como cliente) — Fase 3
- [ ] Paginação no GET /livros — Fase 4
- [ ] Validação de ISBN duplicado antes de inserir — Fase 4
- [ ] SQL em paralelo (conforme curso avança) — Fase 5
- [ ] SOAP Fault — Fase 6 (opcional)
- [ ] Git/GitHub — Radar

---

## Conceitos aprendidos nesta etapa

- Motivo de **não deixar segredos e configurações de ambiente fixos no código-fonte** — dificulta trocar de ambiente e expõe informações sensíveis a quem tiver acesso ao código
- Uso da biblioteca `python-dotenv` para carregar variáveis de um arquivo `.env` em tempo de execução, via `load_dotenv()` e `os.getenv()`
- Diferença entre `.env` (valores reais, nunca compartilhado) e `.env.example` (template público, sem segredos) — padrão comum em projetos profissionais para documentar quais variáveis são necessárias sem expor as reais
- Função do `.gitignore` e a importância de configurá-lo **preventivamente**, mesmo antes de o projeto estar sob controle de versão — evita o risco de esquecer esse passo justamente no momento em que o Git for adotado
- Reforço de um padrão já visto nas etapas anteriores: um erro em uma camada posterior do sistema (ex: `400` por ISBN duplicado no banco) pode servir como **confirmação indireta** de que uma camada anterior (autenticação, leitura de configuração) funcionou corretamente
