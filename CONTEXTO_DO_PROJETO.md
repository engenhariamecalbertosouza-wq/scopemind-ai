# 📘 CONTEXTO DO PROJETO — ScopeMind AI

> **Para a IA que for continuar este projeto:** leia este arquivo INTEIRO antes de mexer em qualquer coisa.
> O dono se chama **Alberto** (Luiz Alberto Siqueira de Souza), **não é programador** e fala **português do
> Brasil** — explique sempre de forma simples, em PT-BR, com analogias quando ajudar.
>
> **Regras de ouro para não quebrar:**
> 1. **Sempre dê Read no trecho exato antes de Edit** em `server.py`/`app.js` (a formatação real difere às vezes e o Edit falha).
> 2. **Sempre valide o `web/app.js` no navegador ANTES de publicar** — um erro de sintaxe derruba o front INTEIRO (já aconteceu; ver seção 13).
> 3. O **custo de IA importa muito** — análise só roda quando o usuário manda; nunca ligar auto-análise-em-lote sem trava.
> 4. **Economia de cota da API-Football** (plano grátis = ~100 consultas/dia).
> 5. **Publicar (`git push origin main`) exige autorização explícita do Alberto** a cada deploy.
> 6. **Eu (IA) NÃO insiro credenciais financeiras/tokens** — o Alberto cola os segredos (Anthropic, API-Football, Mercado Pago) na Render sozinho.

*Atualizado em **2026-06-07**, no fim da sessão "ScopeMind IA (Pt.3)". Próxima aba: "ScopeMind IA (Pt.4)".*
*Histórico: Pt.1/Pt.2 = construção do app local → no ar com domínio próprio. Pt.3 = confiança 70%+, Cérebro de Análise ao Vivo (tela inicial), correção de fuso horário, auditoria de segurança, **pagamentos automáticos (Mercado Pago)**, layout celular + menu gaveta, Placar de Acertos da IA (regra asiática + placar exato), bloqueio temporário do celular, fim do CPF + limite por IP, **Radar de Oportunidades** e **modelo de trial (3 dias de VIP grátis)**.*

---

## 1. VISÃO GERAL
**ScopeMind AI** — "Central de Inteligência Esportiva": app web de **análise de futebol** com **múltiplos agentes
de IA**. Slogan: *"Análise esportiva avançada com múltiplos agentes de inteligência artificial."*

- Mostra jogos (hoje/amanhã, ao vivo, encerrados), gera **análises profundas** de uma partida (agentes
  "doutores" que debatem e concluem com **grau de confiança**), tem **Radar de Oportunidades**, **chat VIP**,
  **comunidade de palpites (XP)**, **cadastro de clientes**, **VIP pago automático** e **painel admin**.
- **Regra de ouro (inegociável):** é análise **PROBABILÍSTICA, nunca garantia**. Nunca prometer acerto/"aposta segura".
- **Tela inicial pós-login = "Cérebro de Análise ao Vivo"** (animação cinematográfica de 100 agentes; botão "ENTRAR NO SISTEMA"). Ver seção 11.
- **NO AR EM PRODUÇÃO:** **https://scopemind-ai.com.br** (domínio próprio, HTTPS) e também
  **https://scopemind-ai.onrender.com** (endereço da Render, sempre funciona). Roda na **Render** (plano Starter +
  disco permanente). Também roda **localmente** no PC do Alberto (Windows) com duplo clique no `INICIAR.bat`.
- **Marketing/copy do produto:** fala em **"100 agentes de IA especialistas"** (decisão explícita do dono).
- **Monetização:** cadastro dá **3 dias de VIP grátis (trial)**; depois o cliente comum só vê o **Radar** (vitrine) e
  precisa assinar **VIP por R$49,90** (promo "1000 primeiros", de R$99,90) — pagamento automático via **Mercado Pago**.
- 📱 **CELULAR LIBERADO** (religado em 2026-06-07; flag `BLOQUEAR_CELULAR=false` no fim do `app.js` — pôr `true` desliga
  de novo). O layout é responsivo e tem menu gaveta. ⚠️ Lembrar: com celular liberado o consumo de IA/cota sobe.

---

## 2. TECNOLOGIAS
- **Backend:** Python 3.12 usando **só a biblioteca padrão** (`http.server`, `urllib`, `json`, `hmac`, `hashlib`,
  `secrets`, `re`, `csv`, `io`, `time`, `threading`, `datetime`, `unicodedata`, `mimetypes`). **Sem dependências de runtime** (sem `pip`).
  - (Exceção histórica: Pillow usado **uma vez, local**, só pra gerar ícones do PWA. Não é usado em runtime.)
- **Frontend:** HTML + CSS + JavaScript **puro** (sem framework, sem build). SPA simples servida pelo próprio servidor Python.
  - O **Cérebro** é Canvas/CSS puro (sem React/Tailwind, apesar do spec original).
- **APIs externas (todas via `urllib`):**
  - **Anthropic (Claude)** → cérebro dos agentes. `POST https://api.anthropic.com/v1/messages` (headers `x-api-key`,
    `anthropic-version: 2023-06-01`). Modelo padrão `claude-opus-4-8`; **em produção o dono trocou para
    `claude-sonnet-4-6`** (mais barato) pela engrenagem. Trocável também por Haiku.
  - **API-Football (api-sports.io)** → dados dos jogos. `https://v3.football.api-sports.io` (header
    `x-apisports-key`, parâmetro `timezone=America/Sao_Paulo`). **Plano grátis** (ver limites na seção 9).
  - **Mercado Pago** → pagamentos/VIP. `https://api.mercadopago.com` (header `Authorization: Bearer <MP_ACCESS_TOKEN>`).
    Usa **Checkout Pro** (`POST /checkout/preferences`) para Pix e Cartão. Ver seção 8.
  - **flagcdn.com** → bandeiras (`https://flagcdn.com/w80/{iso}.png`).
- **Python local:** `C:\Users\Alberto Souza\AppData\Local\Programs\Python\Python312\python.exe` (via winget).
- **Hospedagem:** **Render** (Web Service Starter ~US$7/mês + **disco permanente** /var/data ~US$0,25/GB/mês).
- **Código:** GitHub `engenhariamecalbertosouza-wq/scopemind-ai` (branch `main`). Deploy automático: `git push` → Render republica (~2 min; 502 breve é normal).

---

## 3. COMO RODAR / ATUALIZAR
### Local (PC do Alberto)
1. Pasta: `C:\Users\Alberto Souza\Desktop\AnaliseFutebol`
2. Duplo clique em **`INICIAR.bat`** → sobe o servidor e abre http://localhost:8765
3. Login admin local: **admin / admin** (no campo de e-mail digitar `admin`). Não fechar a janela preta.
4. Porta 8765. Para reiniciar em testes: **matar o python antigo antes** (senão "porta em uso").
5. Para ver só o Cérebro isolado: **`VER-CEREBRO.bat`** (abre `web/cerebro.html` no navegador).

### Atualizar o site no ar (PRECISA de "Sim" do Alberto)
- Editar local → `git push origin main` → a Render **republica sozinha** (~2 min; um **502 breve** durante o
  reinício é NORMAL, com disco não há zero-downtime). Pedir ao Alberto **Ctrl+Shift+R** (ou aba anônima) pra o
  navegador pegar a versão nova.
- ⚠️ O classificador do modo automático costuma **bloquear o push** — explicar ao Alberto e pedir confirmação ("Sim") antes de publicar.
- Commits terminam com: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

### Testar sem gastar IA (no PC)
- Compilar: `python -c "import server, agentes, dados_futebol, relatorios, chat, comunidade, radar, pagamentos; print('OK')"`
- Servidor de teste em outra porta: `PORT=8799 python server.py`
  ⚠️ **Faça backup do `config.json` antes** de testes que cadastram usuários, e **restaure depois**; remova as
  pastas de dados geradas no teste (`chat/`, `comunidade/`, `pagamentos/`) e os scripts `_*.py` temporários (estão no `.gitignore`).
- Testar endpoints com `urllib`/`curl` (login admin → token → chamar rotas). Login admin local = `admin/admin`.
- Console do Windows não imprime emoji (cp1252) — use `-X utf8` / `PYTHONIOENCODING=utf-8` ou evite emoji nos prints.

---

## 4. ESTRUTURA DE ARQUIVOS
```
AnaliseFutebol/
├─ server.py            # Servidor HTTP + rotas/API + auth/usuários + cota + placar + agendador + conta/VIP + pagamentos + radar
├─ agentes.py           # Motor dos agentes (Claude). Devolve JSON ESTRUTURADO p/ o painel visual + bloco "mercados" + fallback texto
├─ dados_futebol.py     # Cliente API-Football; normalização; tradução PT; filtros; cache; cota; fuso BR; "asiático"; destaque
├─ relatorios.py        # Salvar/listar/obter/excluir análises (inclui o campo "dados" estruturado)
├─ chat.py              # Motor do Chat ao vivo (mensagens em chat/mensagens.json; denúncias; Lock; filtros)
├─ comunidade.py        # Motor do Placar da Comunidade (palpites, XP, ranking, badges; modelo "recompute")
├─ radar.py             # (NOVO) Deriva mercados/oportunidades das análises salvas + valueScore + ranking + destaques (ZERO IA)
├─ pagamentos.py        # (NOVO) Mercado Pago (Checkout Pro): cria Pix/Cartão, consulta, webhook; pagamentos/pagamentos.json
├─ config.json          # Chaves de API, usuários, secret  ⚠️ TEM SEGREDOS — NÃO vai pro Git (.gitignore)
├─ web/
│  ├─ index.html        # Telas (login/cadastro + app + modais + menu gaveta + overlay do Cérebro + bloqueio celular + pagamento)
│  ├─ styles.css        # Estilo (tema escuro; cards; .pa-* painel; .rdr-* radar; .pag-* pagamento; drawer; responsivo)
│  ├─ app.js            # Toda a lógica do front (fetch, render, radar, favoritos, alertas, chat, comunidade, conta, painel, pagamento, drawer, cérebro)
│  ├─ cerebro.html      # (NOVO) "Cérebro de Análise ao Vivo" autossuficiente (Canvas). Carregado em iframe na tela inicial
│  ├─ manifest.json     # PWA (instalável)
│  ├─ sw.js             # Service worker (PWA; network-first; CACHE="scopemind-v5"; SHELL inclui /cerebro.html; limpa cache antigo)
│  ├─ icon-192.png / icon-512.png   # Ícones PWA
├─ imagens/
│  ├─ Logo.png          # Logo (usada na tela de login)
│  ├─ background.png    # Fundo do app (central de IA); também usado na tela do cronômetro
│  └─ Entrada.png       # (asset extra)
├─ cache/               # (gerado) cache dos fixtures por data (atômico) — em DATA_DIR (.gitignore)
├─ relatorios/          # (gerado) 1 .json por análise salva — em DATA_DIR (.gitignore)
├─ chat/                # (gerado) mensagens.json do Chat — em DATA_DIR (.gitignore)
├─ comunidade/          # (gerado) palpites.json + admin.json — em DATA_DIR (.gitignore)
├─ pagamentos/          # (gerado) pagamentos.json do Mercado Pago — em DATA_DIR (.gitignore)
├─ INICIAR.bat          # Sobe o servidor (local)
├─ VER-CEREBRO.bat      # Abre só o Cérebro (web/cerebro.html) no navegador
├─ LEIA-ME.txt          # Manual do usuário (PT-BR)
├─ DEPLOY-ScopeMind.txt # Guia de hospedagem na Render
├─ requirements.txt     # vazio (stdlib) — só pra Render detectar Python
├─ runtime.txt          # python-3.12.10
├─ render.yaml          # Blueprint da Render (web service Starter + DISCO /var/data + env vars)
└─ .gitignore           # ignora config.json, cache/, relatorios/, chat/, comunidade/, pagamentos/, __pycache__, *.pyc, _*.py
```

### `DATA_DIR` (persistência na hospedagem — IMPORTANTE)
Todos os módulos que gravam dados usam **`DATA_DIR = os.environ.get("DATA_DIR") or BASE_DIR`**:
- **Local:** `DATA_DIR` = a própria pasta do projeto (nada muda no PC).
- **Hospedagem:** `DATA_DIR=/var/data` (o **disco permanente** da Render) → `config.json`, `cache/`, `relatorios/`,
  `chat/`, `comunidade/`, `pagamentos/` ficam lá e **NÃO somem a cada deploy**. (Sem isso, o disco da Render é efêmero e
  zeraria cadastros/chat/palpites/pagamentos a cada atualização — era o bloqueio nº 1 da produção, já resolvido.)

---

## 5. MÓDULOS (o que o usuário vê)
**Navegação:** no **desktop** há um **menu gaveta (hambúrguer ☰) na lateral esquerda** (`#btn-menu` → `#menu` +
`#menu-overlay`), com o **nome do usuário e o status VIP/Teste** no topo (`#menu-usuario`). No **celular** aparece a tela
**🚫 de bloqueio** (`#bloqueio-celular`) — celular desativado por enquanto (economia). No topo: **"👋 Bem-vindo, <Nome>"**.

Itens do menu: **🎯 Radar de Oportunidades · 🔴 Ao Vivo · ✅ Encerrados · 📈 Placar de Acertos da IA ·
📄 Relatórios salvos (só admin) · 🎮 Placar da Comunidade · 💬 Chat ao vivo · 👤 Conta**. Botão flutuante **💬 Suporte** (WhatsApp).

1. **🎯 Radar de Oportunidades** (era "Agenda") — vitrine inteligente do dia: **Destaques do Dia** + **cards** por jogo
   agrupados em **seções** (🔥 Oportunidades fortes / 📊 Outras leituras / ⏳ Aguardando análise, com contadores) +
   **barra de filtros** (por mercado, por risco, "🔥 só fortes", "⭐ alta confiança" e "✕ limpar") + **detalhes por abas**
   (modal `#modal-radar`: Resultado / Gols / Escanteios / Marcadores / Placar exato, com barras por mercado e botão "ver
   análise completa" que respeita cota/VIP). Como reaproveita análises salvas (ZERO IA), jogos sem análise aparecem
   "Aguardando análise"; admin clica "Analisar" e o jogo vira card com oportunidades. **Auto-atualiza a cada 10 min.**
   **Só campeonatos de DESTAQUE** (ver seção 6). Linguagem SEMPRE de análise/probabilidade, NUNCA promessa. (Detalhe técnico na seção 10.)
2. **🔴 Ao Vivo** — jogos em andamento; auto-refresh 2 min (cache 90s).
3. **✅ Encerrados** — encerrados (ontem+hoje) com placar.
4. **📈 Placar de Acertos da IA** — compara o palpite da IA com o resultado real → % de acerto. Mostra o **nome do time**
   (não "Casa/Fora"): rótulos **"Palpite da IA"** e **"Resultado Real: (time vencedor)"**, com o Resultado Real **abaixo**
   do Palpite. Conta **acertos** e **placares exatos** (contador próprio + 🎉 "ACERTOU O PLACAR EXATO" festivo no card).
   **Regra dos jogos asiáticos:** em jogos asiáticos de baixa notoriedade os **erros** da IA **não são mostrados nem
   contados** (os **acertos** continuam contando) — `dados_futebol.eh_asiatico(...)`.
5. **📄 Relatórios salvos** — **escondido do cliente** (só admin). Reabrir é grátis.
6. **🎮 Placar da Comunidade** — área **gratuita e recreativa** de palpites com XP e ranking (estilo Duolingo). NÃO é
   aposta. Acertar placar EXATO = +10 XP; errar = −2; pendente/adiado/cancelado = 0; XP nunca negativo (piso 0 por
   evento). 1 palpite/jogo, editável até o início, placar 0–20. Faixas/badges: Top3 👑 Hall da Glória, Top10 🏆 Lenda,
   Top50 🥈 Mestre, Top100 🛡️ Analista, Top1000 🔭 Observador, resto 🌱 Estreante. Abas: Palpitar, Ranking, Meu
   desempenho, **Admin**. Processa XP quando o jogo encerra (`short` FT/AET/PEN), idempotente ("recompute").
7. **💬 Chat ao vivo** — **só VIP** (admin sempre entra; cliente não-VIP vê tela 🔒 + WhatsApp). Polling 4,5s. **DENUNCIE**
   🚩: 3 denúncias ocultam a msg + 1 strike; 3 strikes = suspensão automática. Moderação leve (palavrões/links/telefones;
   máx 500 chars; anti-flood 2s). Admin libera VIP/suspende/limpa num painel dentro do chat.
8. **👤 Conta** (todos) — cabeçalho com avatar; **status**: 🎁 **Teste VIP** (trial, com dias restantes) **/** ⭐ **VIP**
   (com barra de duração decrescente + data de vencimento; ≤5 dias = barra vermelha + renovar) **/** "Plano grátis"
   (pós-trial). **Aba Pagamentos e Assinatura VIP** (ver seção 8). **Trocar senha** (só cliente). **Suporte WhatsApp**.
9. **Análise com IA** — botão nos Detalhes do jogo. Roda os agentes e gera o **PAINEL VISUAL** (ver 5.1). **Detalhes do
   jogo são grátis**; só o botão Analisar gasta. Tela "100 IAs pensando" (cronômetro 20s) aparece p/ todos.
10. **🧾 Cadastro de clientes** — "Criar conta — 3 dias de VIP grátis 🎁" (nome, e-mail, senha). **SEM CPF** (removido).
    Limite de **2 contas por IP**.

### 5.1. O RELATÓRIO É UM PAINEL VISUAL
A IA (`agentes.py`) devolve um **JSON ESTRUTURADO** e o front (`renderPainelAnalise` em app.js) monta cards `.pa-*`:
barra de **confiança** colorida (nota 0–100), **barras de probabilidade** (casa/empate/fora), card **"Cenário mais
provável"**, cards de **placar** (principal + alternativos), **artilheiros reais** (nome/time/posição/% de gol/status), 
**leitura do jogo** (frases com ícones), **o que favorece cada lado**, **por que a confiança é X**, **indicadores
rápidos** e botão **"Ver análise completa"** (markdown). Relatórios antigos (só texto) ainda abrem (fallback). Há também
o bloco **`mercados`** (alimenta o Radar): `gols`[{linha,prob}], `ambas_marcam_sim`, `escanteios`{faixa,linha,prob},
`vence_sem_sofrer`{time,prob}, `placares`[{placar,prob}]. Campos: `confianca`(Média/Alta), `confianca_score`(**70–90**),
`confianca_motivos[]`, `prognostico`, `favorito`, `prob_casa/empate/fora`, `placar_principal`(+motivo), `placares_alt[]`,
`artilheiros[]`, `artilheiros_aviso`, `leitura[]`, `forcas_casa/forcas_fora`, `indicadores{}`, `mercados{}`, `detalhes`.

---

## 6. REGRAS DE NEGÓCIO
- **Análise é probabilística, NUNCA garantia.**
- **Modelo de acesso / monetização (mudou na Pt.3):**
  - O antigo "**3 análises grátis avulsas**" ACABOU. Agora o **cadastro dá 3 dias de VIP grátis (trial)**: `_cadastrar`
    seta `vip=True`, `vip_ate = agora + TRIAL_DIAS*86400` (env `TRIAL_DIAS`=3), `trial=True`.
  - Durante o trial = **acesso total** (Radar completo + análises ilimitadas + chat).
  - **Pós-trial:** vira **cliente comum** (`LIMITE_ANALISES_GRATIS=0`) → só enxerga o **Radar** (vitrine de resumos);
    detalhes/análise completa e chat são VIP → precisa **assinar**.
  - **Pagamento aprovado** limpa o trial e vira **VIP pago** (`_vip_dias` dias, padrão 30). `_ativar_vip_usuario(key)`
    seta `vip=True`, `vip_ate=agora+vip_dias*86400`, `trial=False`.
  - Conta/badge mostram "🎁 Teste VIP" + dias restantes durante o trial; "∞ UNLIMITED"/⭐ VIP quando pago.
  - `/api/conta` devolve `trial` (bool) e `vip_dias_total` (= `TRIAL_DIAS` no trial, `_vip_dias` no VIP pago).
- **VIP:** flag `vip:true` + validade `vip_ate`. `_vip_valido(u)` = admin sempre; vip True e não vencido; sem `vip_ate`
  = vitalício. **Expirado volta a cliente comum.** VIP é também a chave do **Chat** e da **análise completa**.
- **Economia de IA (custa dinheiro por análise):**
  - Análise só roda no botão Analisar. Radar, detalhes, relatórios salvos e a Conta são grátis.
  - **Jogo encerrado ou de data passada NÃO pode ser analisado** (bloqueado no front e no servidor).
  - **Teto diário global:** env `MAX_ANALISES_DIA` (padrão 30).
  - **REAPROVEITAMENTO (custo zero):** se o jogo **já tem análise salva**, `/api/analisar` devolve a salva **sem chamar
    a IA** (`reaproveitado:True`). A IA só roda na **1ª vez**. Admin força nova via "Refazer" (`forcar:true`, só admin).
    A tela de 20s disfarça o reaproveitamento para o cliente.
- **Confiança (decisão do dono, Pt.3):** o score é **clampado em 70–90** e o rótulo **NUNCA é "Baixa"** (em `agentes._saneia`:
  `sc=max(70,min(90,...))`, `confianca="Alta" if sc>=80 else "Média"`). Distribuição alvo: **70–75 comum, 76–80 raro,
  80–85 muito raro**. ("Risco de dar errado" no Cérebro é SEMPRE baixo.)
- **Cadastro de clientes:**
  - **SEM CPF** (removido na Pt.3). Limite de **2 contas por IP** (`_cadastrar` conta clientes com mesmo `ip`; ≥2 → 409).
  - E-mail **único**. Login/cadastro dão `.strip()` na senha.
  - Cliente é **restrito**: não vê ⚙️, "Relatórios salvos", etiqueta "analisado" de outros, nem Refazer/Excluir.
- **Campeonatos de DESTAQUE (filtro do Radar/ao vivo):** mostra só **a 1ª divisão** de cada país de destaque (whitelist
  `TOP_DIVISAO` por nome exato em `dados_futebol`) + **Brasil = Série A, B, C + Copa do Brasil** + as **internacionais**
  (Copa do Mundo, Champions, Europa/Conference, Libertadores, Sul-Americana, Nations League, Euro, Copa América,
  eliminatórias, amistosos de seleção, Mundial de Clubes). Países de destaque: Brasil, Inglaterra, Espanha, França,
  Alemanha, Itália, Portugal, Holanda, Argentina, Arábia Saudita, EUA/MLS, Bélgica, México, Colômbia, Chile, **Uruguai
  (1ª divisão incluída na Pt.3)**, Canadá, China. **Teto `MAX_JOGOS_DIA=100`** (aumentar NÃO gasta cota; só corta na
  exibição). Antes existe `_eh_profissional` (remove base/sub/juvenil/reservas/amador/feminino + 3ª divisão pra baixo/regionais).
- **Jogos "asiáticos" de baixa notoriedade:** `eh_asiatico(country, home, away, league)` usa `_norm_txt` (minúsculas, sem
  acento, hifens→espaço), o conjunto `PAISES_ASIA` (nomes EN+PT; **exclui** Austrália e asiáticos da UEFA) e a lista
  `_LIGAS_NOTORIAS`. Usado no Placar de Acertos da IA para **não exibir/contar erros** (acertos contam).
- **Tudo em português:** seleções/países traduzidos (`TRADUCAO_PAIS`/`traduzir`); `country` interno fica em inglês
  (**NÃO traduzir** — lógica/flag/prioridade dependem disso; use `country_pt` só pra exibir). "Friendlies" é EXIBIDA como
  "Amistosos da Copa do Mundo 2026" (`nomeLiga()`; **não renomear `league` interno**).
- **Fuso horário (corrigido na Pt.3):** `FUSO_BR = UTC-3`; `_hoje_brasil()` = `datetime.now(FUSO_BR).date()`. A Render é
  UTC; à noite no Brasil "virava amanhã" → a aba Hoje mostrava amanhã e bloqueava análise de hoje. Usado em
  `_fixtures_do_dia`/`_fixtures_live`/`_intervalo_datas`/`_demo` e no bloco de data passada do `_analisar`.
- **Termo no relatório:** "convocação histórica" → "convocações anteriores" (`agentes._corrigir_termos`, pós-IA).

---

## 7. SEGURANÇA (auditoria da Pt.3)
**Modelo de autorização (SÓLIDO):** token = `hmac(secret, usuario)` (compare com `hmac.compare_digest`); papel
(admin/cliente) e VIP vêm SEMPRE do `config.json` no servidor — o cliente NÃO vira VIP/admin mexendo no localStorage/
requisição. Toda rota sensível re-checa `_eh_admin`/`_vip_valido`. XSS escapado (`esc`), sem path traversal
(`relatorios._safe`), CSRF não se aplica (token em header, não cookie), `config.json` não é exposto pela web.

**Corrigido e publicado:**
- **`/api/relatorio` (FURO CRÍTICO achado em revisão adversarial):** antes não tinha auth → qualquer cliente lia QUALQUER
  análise completa de graça (o Radar expõe as `chave`s), furando o modelo de cota/VIP. Agora exige login e só libera p/
  **admin/VIP ou cliente que já abriu o jogo** (`chave in jogos_abertos`); senão **402**.
- **`/api/relatorios`** restrito a **admin** (403 senão).
- **`/api/excluir-relatorio`** exige admin.
- **Anti força-bruta no login:** `_LOGIN_FAILS`/`_LOGIN_LOCK` por IP (15 falhas/10min → bloqueia 5min; **429**); usa
  `X-Forwarded-For` na Render (`_login_ip()`).
- **`_corpo_json`** limitado a **256 KB** (anti-DoS de memória; fecha a conexão se passar).
- **Fuso horário** (ver seção 6).
- **Pagamentos:** VIP só é liberado quando a API do MP responde `approved` (nunca confia no clique); webhook re-consulta
  a API (anti-fraude); Access Token só no backend. `abrirDetalhesRadar`: cliente NUNCA cai em "ver salvo" grátis.

**RECOMENDAÇÕES PENDENTES (decisão do dono):**
1. **Trocar a senha do admin `Alberto2026`** (fraca) por uma forte 16+ aleatória na Render (env `ADMIN_PASSWORD`). Defesa nº 1.
2. **Migrar o hash de senha de SHA-256 (1 rodada) para PBKDF2** (`hashlib.pbkdf2_hmac`, stdlib), com retrocompat
   (detecta formato antigo no login e re-hasheia) pra não deslogar ninguém.
3. Chave da Anthropic exposta no chat uma vez; dono optou por não trocar (reconsiderar).

**Riscos menores aceitos:** token não expira; sem lock no read-modify-write do `config.json` (cadastro × VIP simultâneos
podem perder update — baixa probabilidade); cadastro sem rate limit além do limite por IP (custo de IA limitado por `MAX_ANALISES_DIA`).

---

## 8. PAGAMENTOS / VIP AUTOMÁTICO (Mercado Pago) — NO AR ✅
**O que faz:** cliente sem VIP vê a oferta → **Conta › Pagamentos e Assinatura VIP** → escolhe **Pix** ou **Cartão** →
é levado ao **Checkout Pro** do Mercado Pago → paga → **VIP liberado automaticamente**. Preço: **R$49,90** (env `VIP_PRECO`;
promo "1000 primeiros", de R$99,90).

**Arquitetura (`pagamentos.py`, stdlib + urllib):**
- `plano()` (preço, `preco_de`=99.90, `duracao_dias`, benefícios).
- `_criar_checkout(usuario_key,email,nome,foco)` → `POST /checkout/preferences`. Pix exclui credit/debit/ticket/atm;
  Cartão exclui ticket/bank_transfer/atm. Usa `init_point` (ou `sandbox_init_point`). `criar_pix`/`criar_cartao` embrulham.
- `processar_webhook_payment`, `sincronizar`, `status_do_usuario`, `listar_admin`. Lê **só** `MP_ACCESS_TOKEN` do env.
  Grava em `pagamentos/pagamentos.json` (no DATA_DIR, gitignored). Integra com o VIP do `config.json` (`vip` + `vip_ate`).
- **Importante:** o Pix NÃO usa mais `/v1/payments` direto (dava "Unauthorized use of live credentials"); **tudo via
  Checkout Pro**. Confirmação por **webhook** + `back_urls` (`?vip=ok|pendente|falhou`).

**Endpoints (`server.py`):** GET `/api/mp/info`, `/api/mp/admin/pagamentos` (admin), `/api/mp/webhook`; POST `/api/mp/pix`,
`/api/mp/cartao`, `/api/mp/verificar`, `/api/mp/webhook`, `/api/mp/admin/liberar` (admin libera manualmente).
Liberação de VIP SÓ quando o MP diz `approved`.

**Front (`app.js`):** `irParaPagamento`/`gerarPix`/`pagarCartao`/`verificarPagamento` (+ poll), `carregarPagAdmin`,
`mostrarOfertaVip`. Card `#pagamento-card` (classes `.pag-*`). Admin vê lista de pagamentos + "Liberar VIP manualmente".

**Status / produção:** **testado em produção** — pagamento real de **R$1** via Pix liberou o VIP sozinho.
`MP_ACCESS_TOKEN` = token de **PRODUÇÃO** (`APP_USR-4944022736029400-...`) na Render. `APP_URL=https://scopemind-ai.com.br`.
Sandbox foi abandonado (precisava de comprador de teste). ⚠️ Durante o teste o preço foi a R$1 — **voltar `VIP_PRECO` para
`49.90`** na Render. A conta do próprio Alberto ficou VIP por causa do teste de R$1. (Eu NÃO insiro o token — o Alberto cola na Render.)

---

## 9. LIMITES DO PLANO GRÁTIS DA API-FOOTBALL (importante!)
- O **100 é de CONSULTAS/dia, NÃO de jogos** (1 consulta traz todos os jogos do dia). Limitar nº de jogos não economiza cota.
- **O que economiza cota:** consultar menos vezes (agenda 10 min + cache 10 min) e o tratamento de cota (serve dados velhos quando estoura).
- **Datas:** só ontem/hoje/amanhã. Semana/mês e resultados antigos = plano pago.
- **Tabelas/Classificação:** só temporadas passadas no grátis (módulo Tabelas **removido**; `/api/tabela` e
  `dados_futebol.tabela` ficaram dormentes).
- **PREÇOS (jun/2026, confirmar):** Free=100/dia; **Pro=US$19/mês (~R$110)=7.500/dia**; Ultra US$39 (75k/dia, +odds);
  Mega US$99 (150k/dia, +stats de jogador). O Pro já resolve com folga (e libera as Tabelas + o auto-análise em lote).
- Chave no `config.json` (`football_api_key`) e na env `FOOTBALL_API_KEY` da Render.

### Cache com tratamento de COTA (não apagar jogos!)
Quando a cota estoura, a API responde com "plan"/"request limit". `_fixtures_do_dia` separa **cota** de **bloqueado**
(data fora do plano) e **NUNCA sobrescreve o cache** em erro/cota (mantém os últimos jogos). Cache só é confiável se
não-vazio (`if valido and cache_jogos:`). Apenas mensagens específicas de data ("access to this date"/"do not have access
to this date") contam como "bloqueado"; nunca cacheia vazio. (Bug da Pt.3: msg de cota apagava os jogos do dia — resolvido.)

---

## 10. RADAR DE OPORTUNIDADES (detalhe técnico)
Reforma da Agenda numa **vitrine de mercados** (1X2, Mais/Menos gols, marcador, placar exato, vence sem sofrer,
escanteios) — construída **por etapas, o dono aprovando cada uma**. Reaproveita análises salvas (**ZERO IA**).

- **Etapa 1 (no ar):** `agentes.py` passou a gerar o bloco `mercados` no JSON (mesma chamada de IA, sem custo extra);
  `_saneia` valida (0–100) e não quebra análises antigas.
- **Etapa 2 (no ar):** `radar.py` deriva oportunidades + `value_score` + ranking + destaques; endpoint **GET `/api/radar`**
  (login obrigatório; filtra "a começar"; monta `mapa = {chave: dados}` das análises e devolve também `jogos_raw` — o
  front faz **1 chamada só**, `JOGOS = d.jogos_raw`). Tela nova: Destaques do Dia + cards. Funções front:
  `carregarRadar/renderRadar/rdrCardDestaque/rdrCardJogo/abrirDetalhesRadar` (+ `RDR_BADGE`). CSS `.rdr-*`.
- **Etapas 3–6 (no ar, 2026-06-07):** o front guarda `RADAR_DATA` (filtra sem nova chamada) e `RDR_FILTROS`.
  **(3/4) Seções agrupadas** por `estado` (forte/fraca/aguardando) com contadores (`renderRadar` + helper `secao`).
  **(5) Filtros** (`#radar-filtros`: `rf-mercado`/`rf-risco`/`rf-forte`/`rf-alta`/`rf-limpar`) via `RDR_GRUPOS`
  (RESULTADO/GOLS/ESCANTEIOS/MARCADORES/PLACAR), `rdrFiltrar` + `rdrOpDestaque` (quando filtra por mercado, o card mostra
  a leitura daquele mercado). **(6) Detalhes por abas** (`#modal-radar`): `rdrRenderModal`/`rdrOpLinha` montam abas só dos
  grupos presentes (1X2 com 3 barras casa/empate/fora; gols com todas as linhas; marcadores com status; placar com aviso);
  o botão `#rdr-modal-completa` chama `abrirAnaliseCompleta` (admin→`verSalvo`; cliente→`rodarAnaliseCliente`, respeita
  cota/VIP). **Tudo reaproveita os dados já carregados — custo ZERO de IA.** Validado no preview (`new Function` + render real).
- **`value_score`:** `prob*0.45 + confianca*0.35 +` bônus de risco (Baixo +15 / Médio +7 / Alto −10) `− 15` se
  PLACAR_EXATO `− 10` se marcador sem status. **Destaque (`eh_forte`)** se prob≥55, conf≥55, value≥60 (marcador: prob≥22,
  conf≥50, value≥55; placar exato: prob≥15, conf≥55, value≥50). `melhor_oportunidade` exclui PLACAR_EXATO salvo se for a única.
  `montar(itens)` → `{destaques, ranking, jogos, total, analisados, fortes}`.
- **Como o dono vê:** no início a maioria fica "Aguardando análise"; admin clica "Analisar" em alguns jogos → viram cards
  + entram nos Destaques.
- **Etapas 3–6 ✅ feitas (2026-06-07).** Falta só a **etapa final: auto-análise EM LOTE** (caro: roda 1× no servidor/cron,
  com teto `MAX_ANALISES_DIA` + cache; **só LIGAR no plano Pro**) — é o "analisar todos os jogos sozinho" que o dono quer.

---

## 11. CÉREBRO DE ANÁLISE AO VIVO (tela inicial)
Tela cenográfica: **100 agentes de IA**, núcleo cerebral pulsante, rede neural, partículas e feed ao vivo. JavaScript puro
(Canvas/CSS), **sem React/Tailwind** (pra rodar sem build).

- **É a tela inicial pós-login:** aparece toda vez que `entrarNoApp()` roda (login, cadastro, auto-login). Botão **"ENTRAR
  NO SISTEMA"** (3 linhas: ENTRAR/NO/SISTEMA) fecha e mostra o app.
- **Integração (importante p/ não quebrar):** `web/cerebro.html` é **autossuficiente** e é carregado **ISOLADO** num
  `<iframe id="cerebro-frame">` dentro de `<div id="cerebro-overlay">` (z-index 9999) — assim o JS do cérebro **não tem
  como derrubar o `app.js`**. `mostrarCerebro()` seta `src=cerebro.html?t=<ts>` e mostra o overlay; o botão dentro do
  iframe faz `window.parent.postMessage("cerebro-entrar")` → listener no `app.js` chama `esconderCerebro()` (esconde +
  seta iframe `about:blank` pra parar a CPU). `sw.js` (v5) inclui `/cerebro.html`.
- **Conteúdo (decisões do dono):** núcleo é GLOBAL (recebe sinais de TODAS as próximas partidas; sem times/placar/Casa-
  Empate-Fora). Confiança 70–85 com peso. 10 grupos (10 IAs cada = 100) num painel à esquerda, cada bloco com "Ver mais"
  → modal com as 10 IAs (nomes em PT, em movimento). Bolinhas sobem ao hub; o hub carrega e solta UMA bola grande por
  linha que viaja bem devagar (`BIG_SPEED≈0.045`) e **dissolve** ao tocar a borda do núcleo (ripple + flash). Barra
  inferior: Partidas monitoradas · Confiança média · [ENTRAR NO SISTEMA] · Agentes ativos · Risco de dar errado. Feed >100 sinais/s.
- **Pendência conhecida:** reaparece a cada refresh/auto-login. Se ficar repetitivo, mostrar 1×/sessão (flag em `sessionStorage`).

---

## 12. PENDÊNCIAS / PRÓXIMOS PASSOS
1. **Confirmar na Render:** `LIMITE_ANALISES_GRATIS=0` e `TRIAL_DIAS=3` (o render.yaml já tem; verificar que sincronizou)
   e **voltar `VIP_PRECO` para `49.90`** (ficou R$1 no teste).
2. **Segurança (recomendado):** trocar a senha admin `Alberto2026`; migrar hash SHA-256 → PBKDF2 (ver seção 7).
3. **Radar — falta só a etapa final:** o **auto-análise em lote** (analisar todos os jogos sozinho) — caro, só no plano
   Pro, com teto + cache + lembrete de custo; rodar 1× no servidor, NÃO por cliente. (Etapas 3–6 já feitas e no ar.)
4. **Celular:** está **LIBERADO** (`BLOQUEAR_CELULAR=false` no fim do `app.js`). O dono pediu pra ligar em 2026-06-07 e
   disse que **desliga depois** (pôr `BLOQUEAR_CELULAR=true` re-bloqueia). Com celular ligado, o consumo de IA/cota sobe.
5. **Plano pago da API-Football (Pro ~R$110/mês)** quando houver clientes usando bastante (libera consultas/datas/Tabelas).
6. **Otimização opcional:** pausar auto-atualização quando a aba está em segundo plano (Page Visibility API).
7. **Comunidade:** ranking semanal/mensal, missões, sequência, perfil público, conquistas (estrutura já pensada).

---

## 13. CUIDADOS PARA NÃO QUEBRAR (LIÇÕES)
- ✅ **SEMPRE validar o `web/app.js` no navegador ANTES de publicar.** Um erro de sintaxe **derruba o front INTEIRO**
  (login e tudo param). Como validar sem node/deno: subir um preview Python servindo `web/`, abrir uma página `/check` que
  faz `new Function(fetch('/app.js'))` e checar `document.title` (`SINTAXE_OK` ou o erro). O **screenshot do preview trava**
  se `background.png` estiver com `background-attachment: fixed` — use a página `/check` (não carrega o index). A
  ferramenta de preview às vezes engasga: reiniciar resolve.
- ✅ **Sempre Read antes de Edit** em `app.js`/`server.py` (a formatação real difere).
- ✅ **Publicar exige "Sim" do Alberto** (o classificador do modo automático bloqueia o push).
- ✅ **Eu (IA) NÃO insiro credenciais financeiras/tokens** — o Alberto cola `MP_ACCESS_TOKEN`/chaves na Render. **NUNCA**
  exibir os valores dos segredos. (As credenciais de produção do MP apareceram em prints; o dono optou por mantê-las.)
- ✅ **Não traduzir `country` interno** nem renomear `league` interno (quebra prioridade/flag/filtro Brasil). Use
  `country_pt` e `nomeLiga()` só pra EXIBIR.
- ✅ **`config.json` tem segredos** (chaves + hash de senhas + secret). NÃO commitar (já no `.gitignore`).
- ✅ **Análise gasta dinheiro** (só no botão Analisar, bloqueio em encerrados, reaproveitamento, teto diário; NÃO ligar
  auto-análise-em-lote sem trava + plano Pro).
- ✅ **Cota da API:** NÃO apagar o cache bom quando a API falha (o tratamento de cota já cuida).
- ✅ **Render:** deploy tem 502 breve (normal). Disco persiste entre deploys. ⚠️ **NUNCA clicar em "Delete Web Service"**
  (botão vermelho) — apaga o site INTEIRO. ⚠️ Não mexer na zona DNS do outro domínio do dono (`mapmanutencao.com.br`, na Vercel).
- ✅ **Ao testar local:** backup do `config.json`, rode em `PORT=8799`, restaure o config e apague pastas de dados/scripts `_*.py` depois.

### Endpoints da API (referência rápida)
**GET:** `/api/status` · `/api/jogos?periodo=hoje|amanha|ontem|aovivo` · `/api/tabela` (dormente) · `/api/placar` ·
`/api/relatorios` (admin) · `/api/relatorio?chave=` (login; admin/VIP/dono-do-jogo, senão 402) · `/api/conta` ·
`/api/radar` (login) · `/api/mp/info` · `/api/mp/admin/pagamentos` (admin) · `/api/mp/webhook` · Chat: `/api/chat?desde=<id>` ·
`/api/chat/usuarios` (admin) · Comunidade: `/api/comunidade/{jogos,ranking?faixa=,eu,admin/usuarios,admin/palpites?q=,admin/exportar?tipo=}`
**POST:** `/api/login` · `/api/cadastrar` · `/api/configurar` (admin) · `/api/analisar` (`forcar` só admin) ·
`/api/excluir-relatorio` (admin) · `/api/trocar-senha` (cliente) · Chat: `/api/chat/{enviar,denunciar,usuario,remover,limpar}` ·
Comunidade: `/api/comunidade/{palpitar,admin/resultado,admin/reprocessar,admin/ajustar-xp,admin/bloquear}` ·
Pagamentos: `/api/mp/{pix,cartao,verificar,webhook,admin/liberar}`
**Estáticos:** `/` (index) · `/styles.css` · `/app.js` · `/cerebro.html` · `/manifest.json` · `/sw.js` · `/imagens/...`

---

## 14. HOSPEDAGEM (CONCLUÍDA ✅) + VARIÁVEIS DE AMBIENTE
- **No ar:** **https://scopemind-ai.com.br** (HTTPS) + **https://scopemind-ai.onrender.com**. www → raiz (301).
- **Render:** Web Service **Starter** (~US$7/mês) + **Disco permanente** `/var/data` (1 GB). GitHub
  `engenhariamecalbertosouza-wq/scopemind-ai`, branch `main`. Push → deploy automático.
- **Domínio (registro.br):** A da raiz → **216.24.57.1**; CNAME `www` → **scopemind-ai.onrender.com**.

### Variáveis de ambiente (render.yaml)
`PYTHON_VERSION=3.12.10` · `DATA_DIR=/var/data` · `ANTHROPIC_API_KEY` (secreta) · `FOOTBALL_API_KEY` (secreta) ·
`ADMIN_USER` (=**`admin@scopemind.com.br`**) · `ADMIN_PASSWORD` (secreta, =**`Alberto2026`**) · `APP_SECRET` (gerada pela
Render) · `MAX_ANALISES_DIA=30` · **`LIMITE_ANALISES_GRATIS=0`** (0 = sem análises avulsas; quem dá acesso é o trial) ·
**`TRIAL_DIAS=3`** (dias de VIP grátis pós-cadastro) · `VIP_DIAS` (30, opcional) · **`MP_ACCESS_TOKEN`** (secreta, Mercado
Pago) · **`APP_URL=https://scopemind-ai.com.br`** (webhook + retorno do cartão) · **`VIP_PRECO=49.90`** · `PORT` (injetada).
**Login admin em produção:** `admin@scopemind.com.br` / `Alberto2026`. **Suporte/WhatsApp do dono:** `5582920012133`.

---

## 15. OBSERVAÇÕES SOBRE O DONO (Alberto)
- **Não programa.** Explicar tudo em **PT-BR simples**, iterativo (pede features a cada conversa). **Custo importa muito.**
- Princípio do produto: análise **PROBABILÍSTICA, NUNCA garantia** — jamais "aposta garantida".
- **Memória automática** do projeto em `~/.claude/projects/C--Users-Alberto-Souza-Desktop-Jogo/memory/` (vários arquivos:
  `sistema-analise-esportiva`, `cerebro-analise-ao-vivo`, `scopemind-seguranca`, `scopemind-pagamentos`, `scopemind-radar`).
- Existe um 2º projeto **não relacionado**: um jogo em Godot ("Eras da Civilização"). O caminho da memória usa
  `Desktop-Jogo`, mas o app fica em `Desktop\AnaliseFutebol` (coisas diferentes).

---
*Documento de handoff entre sessões. Mantenha-o atualizado conforme o projeto evoluir.*
