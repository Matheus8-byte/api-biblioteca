# Plano de Estudos — Projeto API Biblioteca

Mapa dos próximos passos do projeto, organizado em fases. Não é uma ordem rígida — é mutável, conforme os assuntos forem sendo abordados e novos interesses/necessidades surgirem.

**Contexto:** já concluído até aqui — setup inicial (SQL Server + Python + FastAPI), CRUD completo de livros, log de auditoria, delete em lote, endpoints de apoio, Collection no Postman, e um serviço SOAP experimental com spyne (documentado nas Partes 1 a 8).

**Foco de aprendizado:** integração de sistemas (API REST + SOAP), SQL, e Python — as três frentes que mais interessam no momento, com aplicação direta no mercado de trabalho.

---

## Fase 1 — Autenticação ✅ concluída (Parte 9)

- [x] O que é autenticação vs autorização (diferença conceitual)
- [x] API Key simples via header (`X-API-Key`) — implementação no FastAPI
- [x] Onde guardar a chave com segurança (sem hardcoded no código) — resolvido de vez na Fase 2
- [x] Testar no Postman: com a chave certa, sem chave, com chave errada
- [ ] Diferença entre isso e autenticação "de verdade" (OAuth2, JWT) — ainda só pincelado, não aprofundado

---

## Fase 2 — Variáveis de ambiente (.env) ✅ concluída (Parte 10)

- [x] Por que a connection string e a API Key não devem ficar no código
- [x] Biblioteca `python-dotenv`
- [x] Arquivo `.env` + `.gitignore` (adiantado o hábito, mesmo sem Git ainda)
- [x] Refatorar `main.py` para ler tudo de variáveis de ambiente

---

## Fase 3 — Consumir uma API externa (Python como cliente) ✅ concluída (Parte 11)

- [x] Biblioteca `requests`
- [x] Chamar uma API pública (Google Books) a partir de um endpoint próprio
- [x] Tratar resposta inesperada (livro não encontrado, campos ausentes) e quota de uso (API Key própria)
- [x] Mapear um JSON de terceiro para os dados do banco, incluindo padrão "buscar ou criar" para editora/assunto
- [x] Endpoint novo: `POST /livros/importar/{isbn}`
- [ ] Tratar timeout e erro de rede explicitamente (ainda não implementado — próxima melhoria natural para esse endpoint)

---

## Fase 4 — Melhorias na API já existente ✅ concluída (Parte 12)

- [x] Paginação no `GET /livros` (`?page=1&limit=10`, com metadados: total, página atual, total de páginas)
- [x] Validação extra (checar ISBN duplicado antes de inserir, com erro 409 e mensagem clara)
- [ ] Talvez: filtros no `GET /livros` (por editora, por assunto) — ainda não abordado
- [ ] Aplicar checagem de ISBN duplicado também no `PUT /livros/{id}` — identificado como melhoria futura durante a Parte 12, ainda não implementado

---

## Fase 5 — SQL em paralelo (conforme o curso avança)

- [ ] Trazer os conceitos novos do curso para dentro do banco `Biblioteca`
- [ ] Candidatos prováveis: JOINs mais elaborados, subqueries, `GROUP BY`/agregações, índices, views
- [ ] Sem fase fixa — vai encaixando conforme o curso liberar os assuntos

---

## Fase 6 — SOAP mais a fundo ✅ concluída (Parte 14)

- [x] SOAP Fault (erro formal do protocolo, pendente da Parte 8)
- [ ] Talvez uma segunda operação no serviço SOAP (ex: `listar_livros`), para comparar mais casos com o REST — ainda não abordado, fica como possível extra futuro

---

## Fase 7 — Git/GitHub (versionar o projeto) ✅ concluída (Parte 15)

- [x] Instalar/configurar Git
- [x] `git init` no projeto, primeiro commit
- [x] Confirmar que `.gitignore` (já criado na Fase 2) está protegendo `.env` corretamente
- [x] Criar repositório no GitHub, subir o projeto (https://github.com/Matheus8-byte/api-biblioteca)
- [x] Conceitos básicos: commit, push — praticados; branch/pull ainda não foram necessários, ficam para quando surgir a necessidade (ex: ao mexer no site, Fase 8)
- [x] Documentação do projeto (Partes 1-14 + plano de estudos) publicada em `docs/` no repositório

---

## Fase 8 — Site conectado ao banco (via API) ✅ concluída (Parte 16)

- [x] Entender a arquitetura: site como mais um cliente da API (site → API → banco, nunca site → banco direto)
- [x] Vitrine pública (leitura livre): listagem de livros com paginação, identidade visual própria (cards em formato de prancha de surf vintage)
- [x] `fetch` em JavaScript para chamar os endpoints já existentes
- [x] CORS habilitado na API (`CORSMiddleware`), necessário para o navegador poder chamar a API
- [x] Painel administrativo (protegido por API Key): cadastro manual, importação por ISBN, remoção
- [x] Dropdowns de editora/assunto (com criação inline) — gerou 2 endpoints novos: `POST /editoras`, `POST /assuntos`
- [x] Discussão de segurança: API Key no frontend (mantida só em memória, limitação aceita conscientemente para projeto local)
- [ ] (Futuro, opcional) Evoluir para um framework como React, se houver interesse em aprofundar frontend

---

## Todas as fases planejadas foram concluídas 🎉

Restam em aberto apenas: a Fase 5 (SQL), que segue contínua em paralelo aos estudos externos, e os itens do radar abaixo, sem compromisso de prazo.

---

## Radar (ideias mais pra frente, sem compromisso)

- [ ] Deploy simples (rodar a API além do `localhost`)
- [ ] Autenticação mais robusta (JWT), se o mercado-alvo pedir

---

## Como isso vai sendo registrado

Cada fase concluída vira uma nova "Parte" documentada (Parte 9, Parte 10...), no mesmo padrão dos documentos já existentes: motivação, código, erros encontrados, testes realizados e conceitos aprendidos.
