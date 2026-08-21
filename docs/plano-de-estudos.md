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

## Fase 7 — Git/GitHub (versionar o projeto)

- [ ] Instalar/configurar Git, se ainda não estiver
- [ ] `git init` no projeto, primeiro commit
- [ ] Confirmar que `.gitignore` (já criado na Fase 2) está protegendo `.env` corretamente
- [ ] Criar repositório no GitHub, subir o projeto
- [ ] Conceitos básicos: commit, branch, push/pull — o necessário para versionar esse projeto com segurança

---

## Fase 8 — Site conectado ao banco (via API)

- [ ] Entender a arquitetura: site como mais um cliente da API (site → API → banco, nunca site → banco direto)
- [ ] Telas básicas: listar, cadastrar, editar, remover livros
- [ ] `fetch` em JavaScript para chamar os endpoints já existentes
- [ ] Discussão de segurança: como lidar com a API Key no frontend (diferente de guardar ela num `.env` de servidor)
- [ ] Começar simples (HTML + CSS + JavaScript puro), sem framework — objetivo é fechar o ciclo banco → API → tela, não aprofundar em frontend
- [ ] (Se fizer sentido depois) evoluir para um framework como React, como trilha à parte

---

## Radar (ideias mais pra frente, sem compromisso)

- [ ] Deploy simples (rodar a API além do `localhost`)
- [ ] Autenticação mais robusta (JWT), se o mercado-alvo pedir

---

## Como isso vai sendo registrado

Cada fase concluída vira uma nova "Parte" documentada (Parte 9, Parte 10...), no mesmo padrão dos documentos já existentes: motivação, código, erros encontrados, testes realizados e conceitos aprendidos.
