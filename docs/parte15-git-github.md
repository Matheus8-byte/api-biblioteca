# Documentação (Parte 15) — Versionamento com Git e GitHub

Continuação da **Parte 14 — SOAP Fault**. Conclusão da **Fase 7** do Plano de Estudos. Nesta etapa: instalação e configuração do Git, criação do primeiro repositório local, e publicação do projeto completo (código + documentação) no GitHub.

---

## Motivação

Até aqui, o projeto existia apenas localmente, sem nenhum histórico de versões — qualquer alteração sobrescrevia o estado anterior, sem possibilidade de comparar, reverter, ou compartilhar o progresso. Git resolve isso: um sistema de controle de versões que registra "fotografias" (commits) do projeto ao longo do tempo, e o GitHub serve como um backup remoto e uma forma de compartilhar/expor o trabalho.

---

## Passo 1 — Instalação do Git

Download em **https://git-scm.com/download/win**, instalação com as opções padrão (incluindo a recomendada "Git from the command line and also from 3rd-party software", que já vem marcada por padrão).

**Confirmação:**
```
git --version
```
Resultado: `git version 2.55.0.windows.5`

> **Detalhe importante:** após a instalação, foi necessário fechar e reabrir o terminal para o novo comando `git` ser reconhecido — o PATH do sistema só é atualizado em sessões novas.

---

## Passo 2 — Configuração de identidade

Configuração única por máquina, usada para identificar o autor de cada commit (independente do login usado no GitHub):

```
git config --global user.name "matheus.silva"
git config --global user.email "matheustobias51@gmail.com"
```

---

## Passo 3 — Inicializar o repositório local

```
cd C:\projetos\api-biblioteca
git init
```

Cria uma pasta oculta `.git` dentro do projeto, onde todo o histórico de versões passa a ser armazenado.

---

## Passo 4 — Primeiro commit

```
git add .
git status
```

Confirmado no `git status` que o arquivo `.env` **não** apareceu na lista de arquivos rastreados — validação prática de que o `.gitignore`, configurado desde a Parte 10, está funcionando corretamente e protegendo os segredos do projeto desde o primeiro momento em que o Git entrou em cena.

```
git commit -m "Commit inicial: API Biblioteca com CRUD, auth, .env, importação Google Books, paginação e validação de ISBN"
```

Resultado: 9 arquivos, 566 linhas, commit `dc811c0`.

---

## Passo 5 — Criação e conexão do repositório remoto no GitHub

1. Repositório criado em `https://github.com/Matheus8-byte/api-biblioteca`, sem README/`.gitignore`/licença inicial (para evitar conflito com o histórico local já existente)
2. Conexão do repositório local ao remoto:

```
git remote add origin https://github.com/Matheus8-byte/api-biblioteca.git
```

3. Envio do commit inicial:

```
git push -u origin master
```

**Autenticação:** realizada via navegador (fluxo padrão do Git moderno para autenticação com o GitHub), sem necessidade de configuração manual de token nesta etapa.

`-u origin master` vincula a branch local `master` à branch remota, permitindo que comandos futuros de `push` sejam usados sem repetir esses parâmetros.

---

## Passo 6 — Publicando a documentação do projeto

Organização de todos os documentos das Partes 1 a 14 (mais o plano de estudos) dentro de uma pasta `docs/`, publicada junto do código.

### Ajustes realizados antes do commit

- **Arquivo faltante:** a Parte 13 (mapeamento do banco) havia passado despercebida no processo de download, adicionada em seguida
- **Arquivo duplicado:** encontrada uma cópia (`parte5-delete-em-lote - Copia.md`), removida
- **Versão desatualizada:** o `plano-de-estudos.md` baixado inicialmente estava desatualizado em relação às últimas marcações de progresso; refeito o download com a versão mais recente

### Commit e envio

```
git add .
git status
```

Conferido: 16 novos arquivos, todos dentro de `docs/`, nenhum arquivo indevido (`.env`, `__pycache__`) presente.

```
git commit -m "Adiciona documentação completa do projeto (Partes 1 a 14) e plano de estudos"
git push
```

Resultado: commit `0b571bc`, 16 arquivos, 3.476 linhas adicionadas, enviado com sucesso.

---

## Observação técnica: aviso de LF/CRLF

Durante o `git add`, apareceram avisos do tipo:
```
warning: in the working copy of 'docs/...md', LF will be replaced by CRLF the next time Git touches it
```

**Não é um erro.** É o Git avisando sobre a normalização automática de quebras de linha entre convenções diferentes: `LF` (padrão Unix/Linux/Mac) e `CRLF` (padrão Windows). O Git ajusta isso automaticamente para manter consistência no ambiente local, sem necessidade de nenhuma ação corretiva.

---

## O ciclo padrão de trabalho, a partir de agora

Para qualquer alteração futura no projeto:

```
git add .
git commit -m "Descrição objetiva do que mudou"
git push
```

(sem necessidade de repetir `-u origin master` nas próximas vezes, já configurado desde o primeiro `push`)

---

## Roadmap atualizado

- [x] Autenticação simples (API Key) — Fase 1
- [x] Variáveis de ambiente (.env) — Fase 2
- [x] Consumir uma API externa (Python como cliente) — Fase 3
- [x] Paginação e validação de ISBN duplicado — Fase 4
- [ ] SQL em paralelo (conforme curso avança) — Fase 5, contínua
- [x] SOAP Fault — Fase 6
- [x] Git/GitHub — Fase 7
- [ ] Site conectado ao banco (via API) — Fase 8

---

## Conceitos aprendidos nesta etapa

- Fluxo básico do Git: **working directory → staging (`git add`) → commit (`git commit`) → repositório remoto (`git push`)**
- Diferença entre configuração de identidade do Git (`user.name`/`user.email`, usada nos commits) e conta/login do GitHub — são independentes
- Papel do `.gitignore`, validado na prática: arquivos configurados desde a Parte 10 (`.env`) foram automaticamente excluídos do rastreamento, sem necessidade de nenhuma ação extra nesta etapa
- Conceito de repositório **remoto** (`origin`) versus **local**, e como conectá-los (`git remote add`)
- Uso de `git status` como ferramenta de conferência antes de cada commit — hábito que evita commitar arquivos indesejados
- Reconhecimento de mensagens informativas do Git (como o aviso de normalização LF/CRLF) que não indicam erro, apenas comportamento padrão de compatibilidade entre sistemas operacionais
- Reforço da importância de conferir que os arquivos baixados/organizados estão completos e atualizados antes de um commit — replicando o mesmo cuidado de verificação já praticado ao longo de todo o projeto com arquivos de código
