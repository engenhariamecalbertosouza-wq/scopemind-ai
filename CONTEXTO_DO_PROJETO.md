# 📘 CONTEXTO DO PROJETO — ScopeMind AI

> **Para a IA que for continuar este projeto:** leia este arquivo inteiro antes de mexer em qualquer coisa.
> O dono se chama **Alberto**, **não é programador** e fala **português do Brasil** — explique sempre de forma
> simples e em PT-BR. Antes de editar `server.py` ou `web/app.js`, **sempre dê Read no trecho exato** (a
> formatação real às vezes difere do esperado e o Edit falha). Teste cada mudança antes de declarar pronto.

---

## 1. VISÃO GERAL
**ScopeMind AI** — "Central de Inteligência Esportiva": um app de **análise de futebol** com **múltiplos agentes de IA**.
Slogan: *"Análise esportiva avançada com múltiplos agentes de inteligência artificial."*

- Mostra os jogos (hoje/amanhã, ao vivo, encerrados), tabelas, e gera **análises profundas** de uma partida
  usando **10 agentes de IA "doutores"** que debatem e chegam a uma conclusão com **grau de confiança**.
- Regra de ouro (inegociável): **é análise PROBABILÍSTICA, nunca garantia de resultado.** Nunca prometer acerto.
- Roda **localmente** no PC do Alberto (Windows). Está **preparado para hospedar** (Render), mas **ainda não hospedado**.

---

## 2. TECNOLOGIAS
- **Backend:** Python 3.12 usando **somente a biblioteca padrão** (`http.server`, `urllib`, `json`, `hmac`,
  `hashlib`, `secrets`, `re`, `datetime`). **Sem dependências de runtime** (não precisa `pip install` para rodar).
  - (Exceção: o **Pillow** foi usado **uma vez, localmente**, só para gerar os ícones do PWA. Não é usado em runtime.)
- **Frontend:** HTML + CSS + JavaScript **puro** (sem framework). SPA simples servida pelo próprio servidor Python.
- **APIs externas:**
  - **Anthropic (Claude)** → cérebro dos agentes. `POST https://api.anthropic.com/v1/messages`
    (headers `x-api-key`, `anthropic-version: 2023-06-01`). Modelo padrão `claude-opus-4-8`.
  - **API-Football (api-sports.io)** → dados dos jogos. `https://v3.football.api-sports.io`
    (header `x-apisports-key`, parâmetro `timezone=America/Sao_Paulo`). **Plano gratuito** (ver limites na seção 8).
  - **flagcdn.com** → imagens das bandeiras (`https://flagcdn.com/w80/{iso}.png`).
- **Python instalado em:** `C:\Users\Alberto Souza\AppData\Local\Programs\Python\Python312\python.exe`
  (instalado via `winget`).

---

## 3. COMO RODAR (local)
1. Pasta do projeto: `C:\Users\Alberto Souza\Desktop\AnaliseFutebol`
2. Dois cliques em **`INICIAR.bat`** → sobe o servidor e abre o navegador em **http://localhost:8765**
3. Login do dono: **admin / admin** (no campo de e-mail, digitar `admin`). Clientes entram com e-mail.
4. **Não fechar a janela preta** enquanto usar (é o servidor).
- Porta: **8765**. Local faz bind em `127.0.0.1`; hospedado usa `0.0.0.0` + `PORT` do ambiente.
- Para reiniciar o servidor em testes: **matar o python antigo antes** (senão "porta em uso").

---

## 4. ESTRUTURA DE ARQUIVOS
```
AnaliseFutebol/
├─ server.py            # Servidor HTTP + rotas/API + autenticação/usuários + cota + placar + agendador 6h
├─ agentes.py           # Motor dos 10 agentes (chama Claude API); prompt; extrai CONFIANCA e PROGNOSTICO
├─ dados_futebol.py     # Cliente API-Football; normalização; tradução PT; filtros; tabela; ao vivo; cache
├─ relatorios.py        # Salvar/listar/obter/excluir análises; todos(); para_reanalisar(); chave_do_jogo()
├─ chat.py              # Motor do Chat ao vivo (mensagens em chat/mensagens.json; denúncias; Lock; filtros)
├─ comunidade.py        # Motor do Placar da Comunidade (palpites, XP, ranking, badges; modelo recompute)
├─ config.json          # Chaves de API, usuários, secret  ⚠️ TEM SEGREDOS — NÃO vai pro Git (.gitignore)
├─ web/
│  ├─ index.html        # Telas (login/cadastro + app com todos os módulos + modais)
│  ├─ styles.css        # Estilo (tema escuro, verde/azul)
│  ├─ app.js            # Toda a lógica do front (fetch, render, favoritos, alertas, etc.)
│  ├─ manifest.json     # PWA (app instalável)
│  ├─ sw.js             # Service worker (PWA, network-first, não cacheia /api/)
│  ├─ icon-192.png      # Ícone PWA (luneta/mira) — gerado com Pillow
│  └─ icon-512.png      # Ícone PWA
├─ imagens/
│  ├─ Logo.png          # Logo (lockup com nome + slogan) — usada na tela de login
│  └─ background.png    # Fundo do app (central de IA) — servida via rota /imagens/
├─ cache/               # (gerado) cache dos fixtures por data (atômico)
├─ relatorios/          # (gerado) 1 .json por análise salva
├─ chat/                # (gerado) mensagens.json do Chat ao vivo (no .gitignore)
├─ comunidade/          # (gerado) palpites.json + admin.json do Placar da Comunidade (no .gitignore)
├─ INICIAR.bat          # Atalho que sobe o servidor
├─ LEIA-ME.txt          # Manual do usuário (PT-BR)
├─ DEPLOY-ScopeMind.txt # Guia de hospedagem na Render
├─ requirements.txt     # vazio (stdlib) — só pra Render detectar Python
├─ runtime.txt          # python-3.12.10
├─ render.yaml          # Blueprint da Render (start: python server.py + env vars)
└─ .gitignore           # ignora config.json, cache/, relatorios/, __pycache__, _*.py, .serverpid
```

---

## 5. MÓDULOS (o que o usuário vê)
Menu principal: **📅 Agenda de jogos · 🔴 Ao Vivo · ✅ Encerrados · 🏆 Tabelas · 📈 Placar de Acertos · 📄 Relatórios salvos**

1. **📅 Agenda de jogos** — abas **Hoje** e **Amanhã** (com data). Mostra **só jogos a começar**
   (jogos AO VIVO somem daqui e vão pro módulo Ao Vivo; ENCERRADOS vão pro módulo Encerrados).
   **Atualiza sozinha a cada 1 minuto** (sem recarregar a página). Jogos agrupados em **pastas por
   campeonato** (accordion recolhível). Tem **busca**, **filtro por campeonato**, **Expandir/Recolher** e **⭐ Favoritos**.
   Cada jogo: `🛡️ Time A × Time B 🛡️` numa linha só + placar + horário/onde-assistir. Clicar abre os Detalhes.
2. **🔴 Ao Vivo** — só jogos em andamento, placar em tempo real, **auto-refresh a cada 2 min**.
3. **✅ Encerrados** — jogos já encerrados (ontem + hoje) com placar final, agrupados por campeonato.
4. **🏆 Tabelas** — classificação de um campeonato (dropdown). ⚠️ No **plano grátis**, só temporadas passadas
   (a temporada atual vem vazia — mostra aviso).
5. **📈 Placar de Acertos** — compara o **palpite** da IA (Casa/Empate/Fora) com o **resultado real** (ontem/hoje)
   → mostra **% de acerto**, acertos, erros, pendentes. É a credibilidade do sistema.
6. **📄 Relatórios salvos** — toda análise feita fica salva; reabrir é **grátis** (não usa IA). Dá pra excluir.
7. **⭐ Favoritos** — estrela em **campeonatos** (pasta) e **times** (cartão). Favoritos vão pro **topo** + borda
   amarela. Botão "⭐ Favoritos" filtra só os favoritos. Salvo no **localStorage** do navegador.
8. **🔔 Alertas** — botão na barra; com permissão de notificação, **avisa quando um jogo do favorito vai começar**
   (≤15 min). (Alerta de "escalação saiu" ainda NÃO implementado — ver pendências.)
9. **Análise com IA** (botão "🧠 Analisar com IA" nos Detalhes) — roda os 10 agentes e gera o relatório.
   **Detalhes do jogo são grátis**; só o botão Analisar **gasta crédito**.
10. **🧾 Cadastro de clientes** — na tela de login, "Criar conta grátis" (nome, CPF, e-mail, senha).
12. **🎮 Placar da Comunidade** — **JÁ EXISTE** (construído em 2026-06-04). Área **gratuita e recreativa**
    (NÃO é aposta, NÃO tem dinheiro/prêmio) de **palpites de placar** com **XP e ranking** estilo Duolingo.
    Backend `comunidade.py` (palpites em `comunidade/palpites.json`, admin em `comunidade/admin.json`, Lock + atômico).
    **Regras:** acertar o placar EXATO = **+10 XP**; errar = **−2 XP**; pendente/adiado/cancelado = 0; **XP nunca
    fica negativo**. **1 palpite por jogo**, editável **até o início** (depois trava); placar de **0 a 20**.
    **Modelo "recompute" (importante):** XP e ranking são **recalculados** a partir dos palpites resolvidos +
    ajustes manuais, somando em ordem cronológica com **piso 0 a cada passo** (estilo Duolingo). Por isso o
    processamento é **idempotente** — reprocessar nunca duplica XP. **Processamento automático:** quando um jogo
    encerra (status `short` FT/AET/PEN do `dados_futebol`), o sistema resolve os palpites (compara placar);
    PST/SUSP→adiado, CANC→cancelado (0 XP). Roda no acesso ao módulo (throttle 90s) e no agendador de 6h.
    **Ranking:** desempate por XP→acertos→taxa→nº palpites→mais antigo→nome. **Faixas/badges** (selo = sempre a
    melhor): Top3 👑 Hall da Glória, Top10 🏆 Lenda, Top50 🥈 Mestre, Top100 🛡️ Analista, Top1000 🔭 Observador,
    resto 🌱 Estreante. **Abas:** Palpitar (cards com inputs), Ranking (pódio Top 3 + tabela), Meu desempenho
    (stats + evolução de XP + histórico) e **Admin** (só admin: registrar resultado/adiar/cancelar, reprocessar,
    ajustar XP manual, bloquear usuário, exportar CSV). **Quem participa:** qualquer logado (cliente, VIP, admin).
11. **💬 Chat ao vivo** — **JÁ EXISTE** (construído em 2026-06-04). Menu novo "💬 Chat ao vivo". Em
    `chat.py` (motor de mensagens, igual padrão do `relatorios.py`: arquivo `chat/mensagens.json`, gravação
    atômica + `threading.Lock`). **Acesso só VIP:** admin sempre entra; cliente só entra se tiver flag
    `vip: true` (clientes nas 3 grátis ficam numa tela "🔒 só VIP"). **Quem libera VIP:** o **admin**, num
    **painel dentro do próprio Chat** (lista os clientes cadastrados → botões "Tornar VIP" e "Suspender").
    **DENUNCIE:** botão 🚩 em cada mensagem (menos nas suas). A mensagem some com **3 denúncias** de pessoas
    diferentes (`DENUNCIAS_P_OCULTAR`), e isso vira um **strike** pro autor; com **3 strikes**
    (`STRIKES_P_SUSPENDER`) a conta é **suspensa automaticamente** (lê, mas não envia). Admin pode
    suspender/reativar na mão (reativar zera os strikes) e "🗑️ Limpar chat". **Moderação leve de conteúdo:**
    bloqueia palavrões (lista em `PALAVROES`), links e telefones; tamanho máx. 500 chars; anti-flood de 2s.
    Front faz **polling a cada 4,5s** (`/api/chat?desde=<ultimo_id>`): recebe mensagens novas + lista
    `ocultos` (ids removidos, p/ apagar da tela). **Suspensão/strikes ficam no `config.json`** (campos `vip`,
    `suspenso`, `strikes` no usuário); as **mensagens** ficam em `chat/` (no `.gitignore`).
    ⚠️ Em produção (Render, disco efêmero) precisa de **banco/disco persistente** — ver seção 9.

### Os 10 agentes (em `agentes.py`, SYSTEM_PROMPT)
Monitoramento, Estatístico, Classificação/Motivação, Tático, Elenco, Histórico/Confrontos,
**Contexto Externo e Fator Humano** (inclui estado psicológico/vida pessoal dos jogadores — ex.: caso Vini Jr),
Risco/Incerteza (tem poder de veto na confiança), Probabilidade/Cenários, Consenso Final.
- O relatório tem **25 seções** (1–24 + "25. Estimativas de mercado": 1X2, Mais/Menos, placar exato,
  intervalo, escanteios, provável artilheiro) + grau de confiança.
- No fim, a IA escreve 2 marcadores que o sistema lê e **remove da exibição**:
  `CONFIANCA: Baixa|Moderada|Boa|Alta` e `PROGNOSTICO: Casa|Empate|Fora`.

---

## 6. REGRAS DE NEGÓCIO
- **Análise é probabilística, NUNCA garantia.** Nunca prometer acerto/"aposta segura".
- **Economia de IA (custa dinheiro por análise):**
  - Análise SÓ roda no botão "Analisar com IA". Agenda, detalhes, relatórios salvos e tabelas são grátis.
  - **Jogo encerrado ou de data passada NÃO pode ser analisado** (bloqueado no front e no servidor).
  - **Teto diário global** de análises: env `MAX_ANALISES_DIA` (padrão 30).
  - **REAPROVEITAMENTO (2026-06-04, importante p/ custo):** se um jogo **já tem análise salva**, o
    `/api/analisar` **devolve a salva sem chamar a IA** (`reaproveitado: True`, custo ZERO). A IA só roda **na
    1ª vez** (quando não existe nenhuma análise daquele jogo). Assim, se 10 clientes clicam no mesmo jogo, só o
    1º "paga". O **admin** pode forçar uma análise nova com o botão **Refazer** (manda `forcar: true`; só o admin
    é obedecido). Para o cliente **não perceber** que é reaproveitada, o front mostra um **cronômetro dramático
    de 30s** ("100 IAs pensando", fundo `background.png` animado, janela `#modal-preparando` **sem como fechar**)
    e só então revela o relatório (espera no mínimo 30s; se a IA real demorar mais, espera até terminar).
- **Clientes (cadastro):**
  - **Cliente comum (não-VIP):** tem **3 análises grátis** (env `LIMITE_ANALISES_GRATIS`, padrão 3). **Cada JOGO
    diferente** que ele abre gasta **1 das 3**; **reabrir o MESMO jogo é grátis** (o servidor guarda a lista
    `jogos_abertos` no usuário; `analises_usadas` = tamanho dessa lista). Mesmo reaproveitada (custo zero p/ você),
    abrir um jogo novo **conta 1 das 3** (decisão do dono — mantém o funil das 3 grátis → vira VIP).
  - **VIP:** análises **ILIMITADAS** (é o benefício de pagar). VIP é a flag `vip: true` no usuário; admin é VIP por
    natureza. (VIP também é a chave do **Chat** — ver módulo 11.)
  - Cliente é **restrito**: **não vê a engrenagem (⚙️)**, **não vê o módulo "Relatórios salvos"**, não vê a etiqueta
    "📄 analisado" nos jogos, nem o atalho "ver salvo" (tudo isso revelaria o reaproveitamento). Os botões
    **Refazer/Excluir** do relatório também são escondidos do cliente.
  - **CPF** precisa ser **válido** (checksum brasileiro) e **único**; **e-mail** também **único**. Sem contas duplicadas.
- **Ordem dos campeonatos** (função `prioridadeGrupo` em app.js):
  **Copa do Mundo** (-100) → **Amistosos de seleções** (-50) → **Brasil** (Série A/B/C/D, Copa do Brasil) →
  **Inglaterra · Espanha · França · Itália · Alemanha** → continentais → demais.
  **Favoritos do usuário sempre vão pro topo.**
- **Filtros (só campeonatos profissionais de destaque):**
  - `PADRAO_NAO_PRO` (nome do campeonato) e `PADRAO_TIME_NAO_PRO` (nome do time) removem: base/sub (U17/U20),
    juvenil, reservas, amador, futebol feminino, e 3ª divisão pra baixo / regionais.
  - **Brasil**: `_eh_profissional` só deixa **Série A/B/C/D + Copa do Brasil + Copa do Nordeste** (corta estaduais/copas regionais).
  - **"Amistosos da Copa do Mundo 2026"** (liga "Friendlies"): só seleções principais, **nada de SUB**.
- **Tudo em português:** nomes de seleções e países traduzidos (`TRADUCAO_PAIS`/`traduzir` no backend);
  a liga "Friendlies" é exibida como "Amistosos da Copa do Mundo 2026" (`nomeLiga()` no front).

---

## 7. DECISÕES TÉCNICAS (e o porquê)
- **Python stdlib pura:** pra rodar no PC do Alberto sem instalar dependências (menos chance de erro).
- **Chaves via variável de ambiente na hospedagem:** mantém os segredos fora do código/Git.
- **Bandeiras via flagcdn (imagem PNG):** o emoji de bandeira **não renderiza no Windows** (vira "BR"). O ISO do
  país é extraído da URL de bandeira da API (`isoDaBandeira`) ou do mapa `PAIS_ISO`; senão, 🌍.
- **País interno em inglês + `country_pt` para exibir:** a lógica (prioridade, flag, filtro do Brasil) usa o nome
  em inglês; o front só exibe `country_pt`. **NÃO traduzir o campo `country` interno** (quebraria a lógica).
- **`nomeLiga()` no front:** exibe "Amistosos da Copa do Mundo 2026" mas mantém "Friendlies" interno (a prioridade
  depende disso). **NÃO renomear `league` interno.**
- **Cache do dia = 60s:** pra refletir rápido quando um jogo fica ao vivo (a agenda atualiza a cada 1 min).
- **Gravação atômica** (`tmp` + `os.replace`) em `config.json` e no cache: evita corromper com 2 requisições juntas.
- **Retry de rede no front:** `api()` re-tenta **GET** 3x em erro de rede ("Failed to fetch"); **não** re-tenta
  POST (não repetir análise/cadastro). Servidor usa `ServidorScopeMind` (threads daemon, fila de 128, reuse address).

---

## 8. LIMITES DO PLANO GRÁTIS DA API-FOOTBALL (importante!)
- **Datas:** só libera **ontem, hoje e amanhã**. Semana/mês completos e resultados antigos = **plano pago**.
- **Tabelas/Classificação:** só **temporadas passadas** (a atual vem vazia no grátis).
- **Cota:** ~**100 requisições/dia**. Por isso o Ao Vivo atualiza a cada 2 min e a Agenda a cada 1 min (com cache).
- A chave da API-Football do Alberto está em `config.json` (campo `football_api_key`).

---

## 9. HOSPEDAGEM (status)
- **Esclarecido ao usuário:** **GitHub** só guarda o código; **Vercel NÃO serve** (é pra frontend/serverless, não
  roda servidor Python ligado 24h); usar **Render** para rodar. Decisão: **plano Starter (~US$7/mês), privado**.
- Já existem: `render.yaml`, `requirements.txt`, `runtime.txt`, `.gitignore`, `DEPLOY-ScopeMind.txt`.
- **PERSISTÊNCIA RESOLVIDA (2026-06-04):** a Render apaga os arquivos a cada deploy (disco efêmero). Em vez de
  reescrever tudo para um banco, usamos o **DISCO PERMANENTE da Render** (~US$0,25/GB/mês). Todos os módulos que
  gravam dados agora usam a variável **`DATA_DIR`** (`os.environ.get("DATA_DIR") or BASE_DIR`): local = a própria
  pasta; na hospedagem = `/var/data` (o disco). Cobre `config.json`, `cache/`, `relatorios/`, `chat/`, `comunidade/`.
  O `render.yaml` já declara o disco (`scopemind-dados`, 1 GB, `mountPath: /var/data`) e seta `DATA_DIR=/var/data`.
  **Deploy pelo Blueprint** (lê o render.yaml e monta disco + variáveis automaticamente).
- **Git:** repositório **inicializado** e com **1º commit** na branch `main` (config.json fica fora pelo `.gitignore`).
  Falta: criar o repo no GitHub, `git remote add origin <url>` + `git push -u origin main`, e criar o Blueprint na Render.
- **AINDA NÃO HOSPEDADO** (faltam os cliques do Alberto no GitHub/Render — guia em `DEPLOY-ScopeMind.txt`).

### Variáveis de ambiente (na hospedagem)
`DATA_DIR` (=/var/data, o disco), `ANTHROPIC_API_KEY`, `FOOTBALL_API_KEY`, `ADMIN_USER`, `ADMIN_PASSWORD`,
`APP_SECRET` (gerada pela Render), `MAX_ANALISES_DIA` (padrão 30), `LIMITE_ANALISES_GRATIS` (padrão 3),
`PORT` (a Render injeta), `PYTHON_VERSION`. **Secretas (você cola): `ANTHROPIC_API_KEY`, `FOOTBALL_API_KEY`, `ADMIN_PASSWORD`.**

---

## 10. PENDÊNCIAS / PRÓXIMOS PASSOS
1. ✅ **💬 CHAT AO VIVO — FEITO (2026-06-04).** Construído e testado (ver módulo 11 na seção 5). Conceito de VIP
   resolvido com a **flag `vip: true`** no usuário (admin sempre é VIP); admin libera VIP no painel dentro do
   Chat. DENUNCIE com 3 denúncias → some + strike; 3 strikes → suspensão automática. **Ainda falta p/ produção:**
   o disco da Render é efêmero, então mensagens (`chat/`) e cadastros (`config.json`) zeram a cada deploy —
   precisa de **banco/disco persistente** antes de ter chat real com clientes (item 3).
2. **🔔 Alerta de "escalação saiu"** (lineup) — exige consultar a API de escalações periodicamente (custo de cota).
3. **Hospedagem** + **banco de dados persistente** (pré-requisito p/ clientes reais e chat).
4. Ideias futuras: favoritar time e fixar no topo, mais mercados, etc.

---

## 11. CUIDADOS PARA NÃO QUEBRAR O SISTEMA
- ✅ **Sempre Read antes de Edit** em `app.js`/`server.py` (a formatação real difere às vezes; o Edit falha por isso).
- ✅ **Não traduzir o campo `country` interno** nem renomear `league` interno — quebra prioridade/flag/filtro Brasil.
  Use `country_pt` e `nomeLiga()` apenas para EXIBIR.
- ✅ **`config.json` tem segredos** (chaves + hash de senhas + secret). NÃO commitar (já está no `.gitignore`).
  ⚠️ A chave da Anthropic foi exposta no chat uma vez (o dono optou por **não** trocar) — ela vive no config.json.
- ✅ **Análise gasta dinheiro** (Opus). Manter: só no botão Analisar, bloqueio em encerrados, cota do cliente, teto diário.
- ✅ Ao mexer nos filtros, lembrar que existem DOIS níveis: nome do **campeonato** (`PADRAO_NAO_PRO`) e nome do **time**
  (`PADRAO_TIME_NAO_PRO`), mais a regra especial do **Brasil** em `_eh_profissional`.
- ✅ **Login:** admin com `admin/admin` (env `ADMIN_PASSWORD` sobrescreve na hospedagem); clientes por e-mail.
  Token = `hmac(secret, usuario)`; role default ausente = "admin" (compatibilidade do admin legado).

### Como testar (sem gastar com IA)
1. **Sem erros de código:** `python -c "import server, agentes, dados_futebol, relatorios; print('OK')"`
   (rodar na pasta do projeto, com o python do caminho acima).
2. **Subir servidor de teste:** `Start-Process python server.py` (matar pythons antigos antes).
3. **Testar endpoints** com PowerShell `Invoke-RestMethod` (login → pega token → chamar as rotas).
4. ⚠️ **Screenshot pelo navegador (Chrome MCP) costuma TRAVAR** nesta página (ela se atualiza sozinha a cada 1 min e
   a ferramenta não acha um "momento parado"). Validar por **dados** (endpoints) e por **console sem erros**.

### Endpoints da API (referência rápida)
- `GET /api/status` · `GET /api/jogos?periodo=hoje|amanha|ontem|semana|mes|aovivo`
- `GET /api/tabela?league=&season=` · `GET /api/placar` · `GET /api/relatorios` · `GET /api/relatorio?chave=`
- `POST /api/login` · `POST /api/cadastrar` · `POST /api/configurar` (só admin) · `POST /api/analisar` · `POST /api/excluir-relatorio`
- **Chat:** `GET /api/chat?desde=<id>` (poll: `eu`, `acesso`, `mensagens`, `ocultos`, `ultimo_id`) ·
  `GET /api/chat/usuarios` (admin) · `POST /api/chat/enviar` · `POST /api/chat/denunciar` ·
  `POST /api/chat/usuario` (admin: `{email, vip?, suspenso?}`) · `POST /api/chat/remover` (admin) · `POST /api/chat/limpar` (admin)
- **Comunidade:** `GET /api/comunidade/jogos` (jogos+meu palpite) · `GET /api/comunidade/ranking?faixa=geral|top1000|top100|top50|top10|top3` ·
  `GET /api/comunidade/eu` (stats/histórico/evolução) · `POST /api/comunidade/palpitar` `{jogo, ph, pa}` ·
  Admin: `GET /api/comunidade/admin/usuarios` · `GET /api/comunidade/admin/palpites?q=` · `GET /api/comunidade/admin/exportar?tipo=ranking|palpites` ·
  `POST /api/comunidade/admin/resultado` `{chave, home_score, away_score, marcar:''|postponed|cancelled}` ·
  `POST /api/comunidade/admin/reprocessar` `{chave?}` · `POST /api/comunidade/admin/ajustar-xp` `{usuario, amount, motivo}` · `POST /api/comunidade/admin/bloquear` `{usuario, bloquear}`
- **Obs.:** `dados_futebol._normalizar` agora também devolve o campo `short` (código FT/PST/CANC/NS da API) — usado pela Comunidade p/ detectar encerrado/adiado/cancelado.
- Estáticos: `/` (index), `/styles.css`, `/app.js`, `/manifest.json`, `/sw.js`, `/imagens/...`
- ⚠️ **Bug corrigido junto (2026-06-04):** o menu não tinha o toggle de `#secao-placar` no `app.js` (Placar de
  Acertos abria em branco). Foi adicionada a linha `$("#secao-placar").classList.toggle("hidden", secao !== "placar")`.

---

## 12. OBSERVAÇÕES SOBRE O DONO (Alberto)
- **Não programa.** Explicar tudo em **PT-BR simples**, com analogias quando ajudar.
- Está construindo isto de forma **iterativa** (pede features novas a cada conversa).
- Há **memória automática** do projeto em
  `~/.claude/projects/C--Users-Alberto-Souza-Desktop-Jogo/memory/sistema-analise-esportiva.md`
  (resumo persistente entre conversas — também vale a leitura).
- Existe um segundo projeto não relacionado: um jogo em Godot ("Eras da Civilização") na mesma pasta `Desktop\Jogo`.

---
*Documento gerado em 2026-06-04 para handoff entre sessões. Mantenha-o atualizado conforme o projeto evoluir.*
