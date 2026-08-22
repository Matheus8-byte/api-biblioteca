# Documentação (Parte 16) — Site conectado ao banco: vitrine e painel administrativo

Continuação da **Parte 15 — Git e GitHub**. Conclusão da **Fase 8** do Plano de Estudos, e do plano original traçado no início desta etapa de aprendizado. Nesta etapa: construção de um frontend em HTML/CSS/JavaScript puro, consumindo a API REST já existente — fechando o ciclo **banco de dados → API → tela no navegador**.

---

## Motivação

Até aqui, a API só havia sido consumida por ferramentas de teste (Postman, SoapUI) e por ela mesma (a chamada à Google Books). Faltava a peça que fecha a arquitetura completa: um cliente real, rodando no navegador, que qualquer pessoa (não só quem sabe usar Postman) consegue usar.

**Decisão de escopo, definida antes de começar:** dividir o site em duas páginas com propósitos distintos, aproveitando a divisão que já existia na própria API desde a Fase 1 (leitura livre, escrita protegida):
- **Vitrine** (`vitrine.html`) — pública, somente leitura, sem necessidade de API Key
- **Painel administrativo** (`admin.html`) — protegido por API Key, para cadastrar e remover livros

---

## Conceito técnico: CORS

Diferente de Postman e SoapUI, um **navegador** aplica uma política de segurança chamada CORS (Cross-Origin Resource Sharing): por padrão, uma página web só pode chamar APIs na mesma origem dela. Como o site roda como arquivo local e a API roda em `127.0.0.1:8000`, a chamada seria bloqueada sem autorização explícita da API.

**Solução — `CORSMiddleware` no FastAPI:**

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_origins=["*"]` libera qualquer origem — aceitável para este projeto de estudo local, mas seria restringido a domínios específicos em um cenário de produção real.

---

## Conceito técnico: limitação da API Key exposta no navegador

Discutido antes de construir o painel: qualquer valor usado em JavaScript no navegador pode ser visto por quem inspecionar a página (`F12`). Diferente do `.env` do servidor (oculto), a API Key digitada no painel fica **visível** a quem tiver acesso ao navegador.

**Decisão consciente:** aceitável para este projeto local de estudo. A chave é mantida apenas em memória (variável JavaScript, nunca salva em `localStorage` ou em disco) — soma ao fechar a aba. Em um cenário de produção real, a solução usual envolveria um sistema de login/sessão intermediário, que mantém a chave real oculta do cliente.

---

## Parte 1 — A Vitrine

### Identidade visual

Após iteração de design (primeira versão com estética de "fichário de biblioteca", depois redirecionada para um tema escolhido pelo usuário: quiosque de praia vintage, ao entardecer, com luz baixa e âmbar — inspirado em cultura surf), a vitrine final apresenta cada livro como uma **prancha de surf retrô**, recortada via CSS `clip-path`.

**Elementos de identidade:**
- Paleta escura e quente (tons de madeira, âmbar, vermelho desbotado), remetendo a um entardecer de praia
- Tipografia: `Alfa Slab One` (títulos, estilo placa pintada à mão), `Special Elite` (dados técnicos, estilo máquina de escrever desgastada), `Inter` (texto corrido)
- Um "sol" retrô com listras horizontais no cabeçalho, e grão de filme sutil sobreposto a toda a página (via SVG `feTurbulence`), reforçando a sensação vintage

### Técnica: cards em formato de prancha

Implementado via `<clipPath>` do SVG com `clipPathUnits="objectBoundingBox"`, o que permite que uma forma desenhada em coordenadas normalizadas (0 a 1) se adapte automaticamente ao tamanho de qualquer elemento que a referencie via `clip-path: url(#id)`:

```html
<svg width="0" height="0" style="position:absolute">
  <defs>
    <clipPath id="board-long" clipPathUnits="objectBoundingBox">
      <path d="M0.5,0.01 C0.66,0.01 ... Z" />
    </clipPath>
    <clipPath id="board-fish" clipPathUnits="objectBoundingBox">
      <path d="M0.5,0.03 C0.70,0.03 ... Z" />
    </clipPath>
  </defs>
</svg>
```

Dois formatos alternam entre os cards: **longboard** (maioria, mais alongada) e **fish** (uma a cada cinco, mais curta, com rabo bipontudo/"andorinha").

**Detalhes autênticos adicionados, a partir de referência visual fornecida pelo usuário:**
- **Rail** — uma segunda camada por trás de cada card (mesma forma, levemente maior via `padding`), na cor de madeira escura, criando a borda visível ao redor do "deck", como o aro observado em pranchas reais
- **Grão de madeira** — a maioria dos cards usa `repeating-linear-gradient` em tons de madeira para simular veios; uma a cada quatro variantes é uma prancha "pintada", com uma tarja de cor sólida próxima ao rabo (efeito conseguido via `linear-gradient` com paradas de cor abruptas, sem elementos HTML extras)
- **Stringer** — linha central fina, simulando a régua de madeira que atravessa uma prancha de verdade
- **Tampão de leash** — pequeno círculo próximo ao rabo
- **Quilha (fin)** — pequeno triângulo "espiando" por baixo do contorno do rabo, via pseudo-elemento posicionado fora da área recortada

**Ponte técnica importante:** sombra tradicional (`box-shadow`) segue o formato retangular da caixa do elemento, não o contorno recortado pelo `clip-path` — resultaria em uma sombra quadrada atrás de uma prancha. Resolvido usando `filter: drop-shadow(...)`, que acompanha o alfa real do que é renderizado (a silhueta recortada), produzindo um brilho/sombra fiel ao formato da prancha.

### Funcionalidade (JavaScript)

```javascript
async function carregarLivros(pagina) {
  const resposta = await fetch(`${API_BASE}/livros?page=${pagina}&limit=${LIMIT}`);
  const dados = await resposta.json();
  // ... renderiza os cards, usando dados.total_paginas para exibir/ocultar
  // o botão "Carregar mais volumes"
}
```

Reaproveita diretamente a **paginação com metadados** construída na Fase 4 (Parte 12) — o botão "Carregar mais volumes" usa `total_paginas` para saber quando não há mais nada a buscar, sem precisar de lógica adicional no backend.

---

## Parte 2 — O Painel Administrativo

### Escopo definido

Decisão consciente do usuário: **sem funcionalidade de edição** no painel — alterações em registros existentes ficam a cargo de acesso técnico direto (API/banco), não do usuário final da interface. O painel cobre apenas:
- Cadastro de livro (manual ou via importação por ISBN)
- Remoção de livro

### Novos endpoints necessários: `POST /editoras` e `POST /assuntos`

Gap identificado durante a construção do painel: não existia forma de criar uma editora ou assunto isoladamente — a única criação automática acontecia de forma "escondida" dentro do fluxo de importação da Google Books (Parte 11). Para dar suporte à melhoria de UX de dropdowns com criação inline, dois endpoints novos foram adicionados, seguindo o mesmo padrão de validação já usado em `POST /livros`:

```python
class EditoraEntrada(BaseModel):
    NomeEditora: str

class AssuntoEntrada(BaseModel):
    NomeAssunto: str

@app.post("/editoras", dependencies=[Depends(verificar_api_key)])
def criar_editora(editora: EditoraEntrada):
    # verifica duplicidade (409 se já existir), senão insere e retorna o novo ID
    ...

@app.post("/assuntos", dependencies=[Depends(verificar_api_key)])
def criar_assunto(assunto: AssuntoEntrada):
    # mesma lógica, para Assunto
    ...
```

Ambos protegidos por API Key (alteram dado), com checagem de nome duplicado retornando `409 Conflict` — reaproveitando exatamente o padrão de validação de ISBN construído na Parte 12.

### Melhoria de UX: dropdowns em vez de IDs numéricos

**Problema identificado pelo usuário durante o teste:** os campos `IdEditora`/`IdAssunto` do cadastro manual exigiam que a pessoa soubesse de cor o número interno do banco — uma péssima experiência, e um convite a erros (ID inexistente só descoberto após tentar cadastrar).

**Solução implementada:** os campos viraram `<select>` (dropdown), populados dinamicamente a partir de `GET /editoras` e `GET /assuntos` assim que a página carrega. A pessoa escolhe pelo **nome**; o JavaScript envia o **ID** correspondente para a API, sem que o usuário precise conhecê-lo.

```javascript
async function carregarSelect(endpoint, selectEl, campoId, campoNome, placeholder) {
  const resposta = await fetch(`${API_BASE}/${endpoint}`);
  const dados = await resposta.json();
  selectEl.innerHTML = `<option value="">${placeholder}</option>`;
  dados.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item[campoId];
    opt.textContent = item[campoNome];
    selectEl.appendChild(opt);
  });
}
```

**Extensão adicional, também sugerida pelo usuário:** um botão "+" ao lado de cada dropdown, que revela um campo de texto para criar uma editora/assunto nova sem sair do formulário — chamando os endpoints `POST /editoras`/`POST /assuntos` recém-criados, e selecionando automaticamente a opção nova no dropdown após a criação.

### Funcionalidade completa do painel

- **Campo de API Key** — mantido em uma variável JavaScript (nunca persistido), com indicador visual (preenchida/vazia)
- **Duas abas de cadastro** — manual (todos os campos) e importar por ISBN (reaproveitando `POST /livros/importar/{isbn}`, da Parte 11)
- **Lista do acervo com remoção** — reaproveita `GET /livros` e `DELETE /livros/{id}`, com confirmação via `confirm()` antes de excluir
- Após qualquer cadastro/importação, a lista e os dropdowns de editora/assunto são recarregados automaticamente, refletindo o estado mais atual do banco

---

## Erros e situações encontradas durante a etapa

### Instabilidade momentânea da Google Books API

Durante os testes do painel, uma chamada de importação retornou `503 Service temporarily unavailable`. Pesquisa de confirmação revelou que a Google Books tem apresentado, mais recentemente, um comportamento de limitação de taxa mais agressivo do que o documentado oficialmente — um problema do lado do serviço externo, não do código do projeto. Resolvido apenas aguardando e tentando novamente.

### Movimentação de arquivos via terminal (PowerShell)

Ao mover o arquivo `vitrine.html` da pasta de downloads para a pasta do projeto, o nome real do arquivo baixado (`vitrine (2).html`, com espaço, por já existirem versões anteriores) não coincidia com a tentativa inicial (`vitrine(2).html`, sem espaço). Resolvido confirmando o nome exato via `dir C:\Users\Matheus\Downloads\vitrine*` antes de mover, e usando aspas no comando (`move "caminho com espaço" destino`) — sem as aspas, o PowerShell interpretaria o espaço como fim do primeiro argumento.

---

## Estrutura final da pasta do projeto (frontend)

```
C:\projetos\api-biblioteca\
 ├─ main.py
 ├─ .env / .env.example / .gitignore
 ├─ docs\              ← documentação (Partes 1 a 15)
 └─ frontend\
     ├─ vitrine.html    ← página pública
     └─ admin.html      ← painel protegido por API Key
```

---

## Roadmap atualizado

- [x] Autenticação simples (API Key) — Fase 1
- [x] Variáveis de ambiente (.env) — Fase 2
- [x] Consumir uma API externa (Python como cliente) — Fase 3
- [x] Paginação e validação de ISBN duplicado — Fase 4
- [ ] SQL em paralelo (conforme curso avança) — Fase 5, contínua
- [x] SOAP Fault — Fase 6
- [x] Git/GitHub — Fase 7
- [x] Site conectado ao banco (vitrine + painel administrativo) — Fase 8

Com a Fase 8 concluída, todas as fases planejadas originalmente no roadmap foram cumpridas (à exceção da Fase 5, que segue em andamento contínuo em paralelo aos estudos de SQL). Itens futuros ficam em aberto, a critério de continuidade do projeto: deploy da API além do `localhost`, autenticação mais robusta (JWT), e evolução do frontend com um framework, caso haja interesse em aprofundar nessa frente.

---

## Conceitos aprendidos nesta etapa

- **CORS** — por que existe, e como o `CORSMiddleware` do FastAPI autoriza chamadas de origens externas (o navegador, nesse caso)
- Limitação de segurança de expor segredos (API Key) em código que roda no navegador, e por que isso é uma decisão consciente aceitável em projetos locais de estudo, mas não em produção real
- **`clip-path` com `clipPathUnits="objectBoundingBox"`** — técnica de SVG que permite recortar elementos HTML em formas customizadas (normalizadas de 0 a 1) que escalam automaticamente com o tamanho do elemento
- Diferença entre `box-shadow` (segue a caixa retangular) e `filter: drop-shadow` (segue o alfa real do elemento renderizado) — relevante para qualquer elemento com formato não-retangular
- Reaproveitamento de decisões de design já tomadas na API (paginação com metadados, validação de duplicidade) diretamente no consumo pelo frontend, sem necessidade de lógica duplicada
- Identificação de um **gap de API durante o desenvolvimento do frontend**: a necessidade real de um cliente revelou a ausência de endpoints (`POST /editoras`, `POST /assuntos`) que não tinham sido necessários até então — reforço de que a evolução de uma API muitas vezes é guiada pelas necessidades reais dos consumidores, não apenas planejada de antemão
- Prática de **UX aplicada a formulários técnicos**: substituir campos que exigem conhecimento interno do sistema (IDs numéricos) por seleção guiada (dropdowns com nomes), reduzindo erro do usuário e a necessidade de descoberta manual de dados
- Reforço do cuidado com nomes de arquivo contendo espaços em comandos de terminal (uso de aspas), e da prática de confirmar nomes exatos via `dir` com caractere curinga (`*`) antes de operações de arquivo
