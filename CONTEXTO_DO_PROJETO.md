# 📘 CONTEXTO DO PROJETO — ScopeMind AI

> **Para a IA que for continuar este projeto:** leia este arquivo inteiro antes de mexer em qualquer coisa.
> O dono se chama **Alberto** (Luiz Alberto Siqueira de Souza), **não é programador** e fala **português do
> Brasil** — explique sempre de forma simples, em PT-BR, com analogias quando ajudar.
> **Regras de ouro para não quebrar:** (1) **sempre dê Read no trecho exato antes de Edit** em `server.py`/
> `app.js` (a formatação real difere às vezes e o Edit falha); (2) **sempre valide o `web/app.js` no navegador
> ANTES de publicar** (um erro de sintaxe derruba o front INTEIRO — já aconteceu; ver seção 11); (3) o **custo
> de IA importa muito** — análise só roda quando manda; (4) **economia de cota da API-Football** (plano grátis).

*Atualizado em 2026-06-05, no fim de uma longa sessão que levou o projeto do "app local" até "no ar com domínio próprio".*

---

## 1. VISÃO GERAL
**ScopeMind AI** — "Central de Inteligência Esportiva": app web de **análise de futebol** com **múltiplos agentes
de IA**. Slogan: *"Análise esportiva avançada com múltiplos agentes de inteligência artificial."*

- Mostra jogos (hoje/amanhã, ao vivo, encerrados), gera **análises profundas** de uma partida (10 agentes
  "doutores" que debatem e concluem com **grau de confiança**), tem **chat**, **comunidade de palpites (XP)**,
  **cadastro de clientes**, **VIP** e **painel admin**.
- **Regra de ouro (inegociável):** é análise **PROBABILÍSTICA, nunca garantia**. Nunca prometer acerto/"aposta segura".
- **NO AR EM PRODUÇÃO:** **https://scopemind-ai.com.br** (domínio próprio, HTTPS) e também
  **https://scopemind-ai.onrender.com** (endereço da Render, sempre funciona). Roda na **Render** (plano Starter +
  disco permanente). Também roda **localmente** no PC do Alberto (Windows) com duplo clique no `INICIAR.bat`.
- **Marketing/copy do produto:** fala em **"100 agentes de IA especialistas"** (decisão explícita do dono).

---

## 2. TECNOLOGIAS
- **Backend:** Python 3.12 usando **só a biblioteca padrão** (`http.server`, `urllib`, `json`, `hmac`, `hashlib`,
  `secrets`, `re`, `csv`, `io`, `threading`, `datetime`, `unicodedata`). **Sem dependências de runtime** (sem `pip`).
  - (Exceção histórica: Pillow usado **uma vez, local**, só pra gerar ícones do PWA. Não é usado em runtime.)
- **Frontend:** HTML + CSS + JavaScript **puro** (sem framework). SPA simples servida pelo próprio servidor Python.
- **APIs externas:**
  - **Anthropic (Claude)** → cérebro dos agentes. `POST https://api.anthropic.com/v1/messages` (headers `x-api-key`,
    `anthropic-version: 2023-06-01`). Modelo padrão `claude-opus-4-8`; **em produção o dono trocou para
    `claude-sonnet-4-6`** (mais barato) pela engrenagem. Trocável também por Haiku.
  - **API-Football (api-sports.io)** → dados dos jogos. `https://v3.football.api-sports.io` (header
    `x-apisports-key`, parâmetro `timezone=America/Sao_Paulo`). **Plano grátis** (ver limites na seção 8).
  - **flagcdn.com** → bandeiras (`https://flagcdn.com/w80/{iso}.png`).
- **Python local:** `C:\Users\Alberto Souza\AppData\Local\Programs\Python\Python312\python.exe` (via winget).
- **Hospedagem:** **Render** (Web Service Starter ~US$7/mês + **disco permanente** /var/data ~US$0,25/GB/mês).
- **Código:** GitHub `engenhariamecalbertosouza-wq/scopemind-ai` (branch `main`). Deploy automático: `git push` → Render republica.

---

## 3. COMO RODAR / ATUALIZAR
### Local (PC do Alberto)
1. Pasta: `C:\Users\Alberto Souza\Desktop\AnaliseFutebol`
2. Duplo clique em **`INICIAR.bat`** → sobe o servidor e abre http://localhost:8765
3. Login admin local: **admin / admin** (no campo de e-mail digitar `admin`). Não fechar a janela preta.
4. Porta 8765. Para reiniciar em testes: **matar o python antigo antes** (senão "porta em uso").

### Atualizar o site no ar
- Editar local → `git push origin main` → a Render **republica sozinha** (~2 min; um **502 breve** durante o
  reinício é NORMAL, com disco não há zero-downtime). Pedir ao Alberto **Ctrl+Shift+R** (ou aba anônima) pra o
  navegador pegar a versão nova.

### Testar sem gastar IA (no PC)
- Compilar: `python -c "import server, agentes, dados_futebol, relatorios, chat, comunidade; print('OK')"`
- Servidor de teste em outra porta (não atrapalha a 8765 e não polui o config real): `PORT=8799 python server.py`
  ⚠️ **Faça backup do `config.json` antes** de testes que cadastram usuários, e **restaure depois**; remova as
  pastas de dados geradas no teste (`chat/`, `comunidade/`) e os scripts `_*.py` temporários (estão no `.gitignore`).
- Testar endpoints com `urllib`/`curl` (login admin → token → chamar rotas). Login admin local = `admin/admin`.

---

## 4. ESTRUTURA DE ARQUIVOS
```
AnaliseFutebol/
├─ server.py            # Servidor HTTP + rotas/API + auth/usuários + cota + placar + agendador 6h + conta/VIP
├─ agentes.py           # Motor dos agentes (Claude). Devolve JSON ESTRUTURADO p/ o painel visual + fallback texto
├─ dados_futebol.py     # Cliente API-Football; normalização; tradução PT; filtros; cache; tratamento de cota
├─ relatorios.py        # Salvar/listar/obter/excluir análises (inclui o campo "dados" estruturado)
├─ chat.py              # Motor do Chat ao vivo (mensagens em chat/mensagens.json; denúncias; Lock; filtros)
├─ comunidade.py        # Motor do Placar da Comunidade (palpites, XP, ranking, badges; modelo "recompute")
├─ config.json          # Chaves de API, usuários, secret  ⚠️ TEM SEGREDOS — NÃO vai pro Git (.gitignore)
├─ web/
│  ├─ index.html        # Telas (login/cadastro + app com todos os módulos + modais)
│  ├─ styles.css        # Estilo (tema escuro; verde/azul/ciano/dourado; cards; .pa-* do painel de análise)
│  ├─ app.js            # Toda a lógica do front (fetch, render, favoritos, alertas, chat, comunidade, conta, painel)
│  ├─ manifest.json     # PWA (instalável)
│  ├─ sw.js             # Service worker (PWA; network-first; CACHE="scopemind-v3"; limpa cache antigo no activate)
│  ├─ icon-192.png / icon-512.png   # Ícones PWA
├─ imagens/
│  ├─ Logo.png          # Logo (usada na tela de login)
│  ├─ background.png     # Fundo do app (central de IA); também usado na tela do cronômetro
│  └─ Entrada.png        # (asset extra)
├─ cache/               # (gerado) cache dos fixtures por data (atômico) — em DATA_DIR (.gitignore)
├─ relatorios/          # (gerado) 1 .json por análise salva — em DATA_DIR (.gitignore)
├─ chat/                # (gerado) mensagens.json do Chat — em DATA_DIR (.gitignore)
├─ comunidade/          # (gerado) palpites.json + admin.json — em DATA_DIR (.gitignore)
├─ INICIAR.bat          # Sobe o servidor (local)
├─ LEIA-ME.txt          # Manual do usuário (PT-BR)
├─ DEPLOY-ScopeMind.txt # Guia de hospedagem na Render
├─ requirements.txt     # vazio (stdlib) — só pra Render detectar Python
├─ runtime.txt          # python-3.12.10
├─ render.yaml          # Blueprint da Render (web service Starter + DISCO /var/data + env vars)
└─ .gitignore           # ignora config.json, cache/, relatorios/, chat/, comunidade/, __pycache__, *.pyc, _*.py
```

### `DATA_DIR` (persistência na hospedagem — IMPORTANTE)
Todos os módulos que gravam dados usam **`DATA_DIR = os.environ.get("DATA_DIR") or BASE_DIR`**:
- **Local:** `DATA_DIR` = a própria pasta do projeto (nada muda no PC).
- **Hospedagem:** `DATA_DIR=/var/data` (o **disco permanente** da Render) → `config.json`, `cache/`, `relatorios/`,
  `chat/`, `comunidade/` ficam lá e **NÃO somem a cada deploy**. (Sem isso, o disco da Render é efêmero e zeraria
  cadastros/chat/palpites a cada atualização — esse era o bloqueio nº 1 da produção, já resolvido.)

---

## 5. MÓDULOS (o que o usuário vê)
Menu: **📅 Agenda · 🔴 Ao Vivo · ✅ Encerrados · 📈 Placar de Acertos · 📄 Relatórios salvos (só admin) ·
🎮 Placar da Comunidade · 💬 Chat ao vivo · 👤 Conta**. No topo: **"👋 Bem-vindo, <Nome>"** (todos) e, p/ cliente,
o badge (🎟️ X grátis ou ✨ "∞ UNLIMITED" se VIP). Botão flutuante **💬 Suporte** (WhatsApp) só p/ cliente.

1. **📅 Agenda** — abas Hoje/Amanhã. Só jogos a começar (ao vivo vão pro módulo Ao Vivo; encerrados pro Encerrados).
   Pastas (accordion) por campeonato, busca, filtro, Expandir/Recolher, ⭐ Favoritos, 🔔 Alertas. Times em uma linha
   ("Brasil **VS** Argentina" — o "VS" é um selo CSS inclinado verde→azul, classes `.jl-x`/`.cj-vs`/`.vs-titulo`).
   **Auto-atualiza a cada 10 min** (era 1 min — reduzido pra poupar cota). **Só campeonatos de DESTAQUE** (ver seção 6).
2. **🔴 Ao Vivo** — jogos em andamento; auto-refresh 2 min (cache 90s).
3. **✅ Encerrados** — encerrados (ontem+hoje) com placar.
4. **📈 Placar de Acertos** — compara o `PROGNOSTICO` (Casa/Empate/Fora) da IA com o resultado real → % de acerto.
5. **📄 Relatórios salvos** — **escondido do cliente** (só admin). Reabrir é grátis.
6. **🎮 Placar da Comunidade** — área **gratuita e recreativa** de palpites de placar com XP e ranking (estilo
   Duolingo). NÃO é aposta, sem dinheiro/prêmio (tem avisos de responsabilidade). Acertar placar EXATO = +10 XP;
   errar = −2; pendente/adiado/cancelado = 0; XP nunca negativo (piso 0, **estilo Duolingo — clamp a cada evento**).
   1 palpite/jogo, editável até o início (depois trava), placar 0–20. Faixas/badges: Top3 👑 Hall da Glória, Top10
   🏆 Lenda, Top50 🥈 Mestre, Top100 🛡️ Analista, Top1000 🔭 Observador, resto 🌱 Estreante (selo = melhor faixa).
   Abas: Palpitar, Ranking (pódio Top3 + tabela), Meu desempenho (stats + sparkline + histórico) e **Admin** (só
   admin: registrar resultado/adiar/cancelar, reprocessar, ajustar XP, bloquear, exportar CSV). Processa XP quando o
   jogo encerra (usa `short` FT/AET/PEN do dados_futebol; PST/SUSP=adiado, CANC=cancelado), idempotente.
7. **💬 Chat ao vivo** — **só VIP** (admin sempre entra; cliente não-VIP vê tela 🔒 "só VIP" + botão WhatsApp).
   Polling 4,5s. Botão **DENUNCIE** 🚩 por mensagem: **3 denúncias** de pessoas diferentes ocultam a msg e dão 1
   strike ao autor; **3 strikes** = **suspensão automática** (lê mas não envia). Admin libera VIP/suspende/limpa num
   painel dentro do próprio chat. Moderação leve: palavrões/links/telefones bloqueados; máx 500 chars; anti-flood 2s.
8. **👤 Conta** (todos) — cabeçalho com avatar; status: **VIP com barra de duração (X dias decrescendo)** + data de
   vencimento (quando ≤5 dias, barra vermelha + botão renovar), ou "Plano grátis" com botão "Quero ser VIP". **Trocar
   senha** (só cliente; admin é 403 pois a senha dele vem do env da Render). **Suporte WhatsApp**.
9. **Análise com IA** (botão "🔮 Ver análise completa" p/ cliente / "🧠 Analisar com IA" p/ admin nos Detalhes) — roda
   os agentes e gera o **PAINEL VISUAL** (ver seção 5.1). **Detalhes do jogo são grátis**; só o botão Analisar gasta.
10. **🧾 Cadastro de clientes** — "Criar conta grátis" (nome, CPF, e-mail, senha).
11. **🧠 Tela "100 IAs pensando" (cronômetro 20s)** — ao analisar, **todos** (admin e cliente) veem uma tela cheia,
    impossível de fechar, com fundo `background.png` animado, anel girando, número decrescendo e frases — por **20s**
    no mínimo (se a IA real demorar mais, espera terminar). Pro cliente, isso também disfarça o reaproveitamento.

### 5.1. O RELATÓRIO É UM PAINEL VISUAL (não é mais texto corrido)
A IA (`agentes.py`) devolve um **JSON ESTRUTURADO** e o front (`renderPainelAnalise` em app.js) monta cards `.pa-*`:
barra de **confiança** colorida (com nota 0–100), **barras de probabilidade** (casa/empate/fora), card **"Cenário mais
provável"**, cards de **placar** (principal + alternativos), **artilheiros reais** (nome/time/posição/% de gol/status
Confirmado·Provável·Dúvida/motivo), **leitura do jogo** (frases curtas com ícones ⚽🧱⚡🎯🔄), **o que favorece cada
lado** (2 colunas), **por que a confiança é X**, **indicadores rápidos** (gols/ambas marcam/escanteios/1º tempo/risco)
e botão **"Ver análise completa"** (abre os `detalhes` em markdown). Relatórios antigos (só texto) ainda abrem (fallback
para `markdown(relatorio)`). Campos do JSON: `confianca`(Média/Alta), `confianca_score`(60–90), `confianca_motivos[]`,
`prognostico`, `favorito`, `prob_casa/empate/fora`, `placar_principal`(+motivo), `placares_alt[]`, `artilheiros[]`,
`artilheiros_aviso`, `leitura[]`, `forcas_casa/forcas_fora`, `indicadores{}`, `detalhes`.

---

## 6. REGRAS DE NEGÓCIO
- **Análise é probabilística, NUNCA garantia.**
- **Economia de IA (custa dinheiro por análise):**
  - Análise só roda no botão Analisar. Agenda, detalhes, relatórios salvos e a Conta são grátis.
  - **Jogo encerrado ou de data passada NÃO pode ser analisado** (bloqueado no front e no servidor).
  - **Teto diário global** de análises: env `MAX_ANALISES_DIA` (padrão 30).
  - **REAPROVEITAMENTO (custo zero):** se o jogo **já tem análise salva**, `/api/analisar` devolve a salva **sem
    chamar a IA** (`reaproveitado:True`). A IA só roda na **1ª vez**. Admin força nova via "Refazer" (`forcar:true`,
    só admin obedecido). A tela de 20s disfarça o reaproveitamento para o cliente.
- **Confiança (decisão do dono):** o score é **clampado em 60–90** e o rótulo **NUNCA é "Baixa"** (60–69=Média,
  70–90=Alta) — pra não descredibilizar o sistema (ajustado no prompt e em `agentes._saneia`).
- **Clientes (cadastro):**
  - **Cliente comum (não-VIP):** **3 análises grátis** (env/config `LIMITE_ANALISES_GRATIS`, editável na engrenagem
    via campo `limite_analises_gratis`). **Cada JOGO diferente** gasta 1; **reabrir o MESMO jogo é grátis** (servidor
    guarda `jogos_abertos` no usuário; `analises_usadas`=tamanho da lista). Reaproveitada também conta 1 p/ jogo novo.
  - **Cliente que JÁ comprou** um jogo vê **"📄 Ver análise completa novamente"** (instantâneo, sem cronômetro, sem
    gastar) e a etiqueta "📄 minha análise" na agenda. Front guarda em `MEUS_JOGOS` (vem de `jogos_abertos` no login/
    cadastro/`/api/conta`).
  - **VIP:** análises **ILIMITADAS**; badge "∞ UNLIMITED". VIP é a flag `vip:true` + **validade `vip_ate`** (dura
    `vip_dias` dias — padrão 30, editável na engrenagem via `vip_dias`). `_vip_valido(u)` = admin sempre; vip True e
    não vencido; sem `vip_ate` = vitalício. **Expirado volta a ser cliente comum.** Renovar = admin clica "Tornar VIP"
    de novo. VIP é também a chave do **Chat**.
  - Cliente é **restrito**: não vê ⚙️, não vê "Relatórios salvos", não vê etiqueta "analisado" de outros, nem
    Refazer/Excluir. **CPF** válido (checksum BR) e **único**; e-mail **único**.
- **Campeonatos de DESTAQUE (filtro da agenda/ao vivo):** mostra só **a 1ª divisão** de cada país de destaque
  (whitelist `TOP_DIVISAO` por nome exato em dados_futebol) + **Brasil = Série A, B, C + Copa do Brasil** + as
  **internacionais** (Copa do Mundo, Champions, Europa/Conference League, Libertadores, Sul-Americana, Nations League,
  Euro, Copa América, eliminatórias, amistosos de seleção, Mundial de Clubes). Países de destaque hoje: Brasil,
  Inglaterra, Espanha, França, Alemanha, Itália, Portugal, Holanda, Argentina, Arábia Saudita, EUA/MLS, Bélgica,
  México, Colômbia, Chile, Uruguai, Canadá, China. **Teto `MAX_JOGOS_DIA=100`** (aumentar NÃO gasta cota — a API traz
  tudo numa consulta só; o teto só corta na exibição). Antes existe o filtro `_eh_profissional` (remove base/sub/
  juvenil/reservas/amador/feminino + 3ª divisão pra baixo/regionais).
- **Tudo em português:** seleções/países traduzidos (`TRADUCAO_PAIS`/`traduzir`); `country` interno fica em inglês
  (lógica/flag/prioridade dependem disso — **NÃO traduzir `country`**, use `country_pt` só pra exibir). A liga
  "Friendlies" é EXIBIDA como "Amistosos da Copa do Mundo 2026" (`nomeLiga()` no front; **não renomear `league` interno**).
- **Termo no relatório:** "convocação histórica" é trocado automaticamente por "convocações anteriores"
  (`agentes._corrigir_termos`, pós-IA).

---

## 7. DECISÕES TÉCNICAS (e o porquê)
- **Python stdlib pura:** rodar no PC do Alberto sem instalar dependências (menos erro).
- **Persistência por DISCO permanente (não banco):** mantém o app file-based; `DATA_DIR` aponta os dados pro disco da
  Render. Bem mais simples que reescrever para um banco.
- **Relatório em JSON estruturado:** o pedido era um painel visual, não texto. JSON com parse robusto (`_extrair_json`
  tolera ``` e texto em volta) + `_saneia` (tipos/limites) + **fallback p/ texto** se o JSON falhar (não quebra).
- **XP "recompute":** ranking/XP recalculados dos palpites resolvidos + ajustes → **idempotente** (reprocessar não duplica).
- **Cache com tratamento de COTA:** a API grátis tem ~100 CONSULTAS/dia. Quando estoura, ela responde com a palavra
  "plan" (de "upgrade your plan") — antes o código confundia com "data fora do plano" e **salvava lista vazia no cache,
  apagando os jogos**. Agora `_fixtures_do_dia` separa **cota** ("request limit") de **bloqueado** (data fora do plano)
  e, na cota/erro de rede, **NUNCA sobrescreve o cache** (mantém os últimos jogos) + aviso claro. Cache de "hoje" = 10 min.
- **Bandeiras via flagcdn (PNG):** emoji de bandeira não renderiza no Windows.
- **Login tolerante:** `_login`/`_cadastrar` dão `.strip()` na senha (ignora espaço acidental de autofill/copiar-colar);
  username já era case-insensitive. Token = `hmac(secret, usuario)`; role ausente = "admin" (admin legado).
- **Gravação atômica** (tmp + `os.replace`) em config/cache/chat/comunidade; cada módulo de dados usa `threading.Lock`.
- **Retry de rede no front:** `api()` re-tenta GET 3x em "Failed to fetch"; não re-tenta POST. Servidor
  `ServidorScopeMind` (daemon_threads, fila 128, reuse address).
- **Cache-Control: no-cache** nos arquivos estáticos + SW v3 com limpeza → atualizações chegam sem hard refresh
  (resolveu a "Tabela" que insistia em aparecer por cache).

---

## 8. LIMITES DO PLANO GRÁTIS DA API-FOOTBALL (importante!)
- O **100 é de CONSULTAS/dia, NÃO de jogos** (1 consulta traz todos os jogos do dia). Limitar nº de jogos não economiza cota.
- **O que economiza cota:** consultar menos vezes (por isso agenda 10 min + cache 10 min) e o tratamento de cota
  (serve dados velhos quando estoura, em vez de zerar).
- **Datas:** só ontem/hoje/amanhã. Semana/mês e resultados antigos = plano pago.
- **Tabelas/Classificação:** só temporadas passadas no grátis (por isso o **módulo Tabelas foi REMOVIDO** — o dono não
  quer pagar agora; backend `/api/tabela` e `dados_futebol.tabela` ficaram dormentes).
- **PREÇOS (jun/2026, confirmar no painel deles):** Free=100/dia; **Pro=US$19/mês (~R$110)=7.500/dia**; Ultra US$39
  (75k/dia, +odds); Mega US$99 (150k/dia, +stats de jogador). O Pro já resolve com folga (e libera as Tabelas).
- Chave da API-Football do Alberto está no `config.json` (`football_api_key`) e na env `FOOTBALL_API_KEY` da Render.

---

## 9. HOSPEDAGEM (CONCLUÍDA ✅)
- **No ar:** **https://scopemind-ai.com.br** (HTTPS válido) + **https://scopemind-ai.onrender.com**.
  www.scopemind-ai.com.br redireciona (301) pra raiz.
- **Render:** Web Service **Starter** (~US$7/mês) + **Disco permanente** `/var/data` (1 GB, ~US$0,25/mês).
- **GitHub:** `engenhariamecalbertosouza-wq/scopemind-ai`, branch `main`. Push → deploy automático.
- **Domínio (registro.br):** A da raiz → **216.24.57.1**; CNAME `www` → **scopemind-ai.onrender.com**. (Já configurado
  e verificado pela Render; o cliente tinha um `scopemind.com.br` SEM o "-ai" por engano na lista de Custom Domains —
  inofensivo, ficou lá.) ⚠️ **NUNCA clicar em "Delete Web Service"** (botão vermelho) — apaga o site INTEIRO.
- ⚠️ O dono tem **OUTRO** domínio, `mapmanutencao.com.br` (empresa MAP, na Vercel) — **não mexer** nessa zona DNS.

### Variáveis de ambiente (na Render)
`DATA_DIR=/var/data`, `ANTHROPIC_API_KEY` (secreta), `FOOTBALL_API_KEY` (secreta), `ADMIN_USER`
(=**`admin@scopemind.com.br`** — o dono trocou de "admin" pra esse e-mail), `ADMIN_PASSWORD` (secreta,
=**`Alberto2026`**), `APP_SECRET` (gerada pela Render), `MAX_ANALISES_DIA` (30), `LIMITE_ANALISES_GRATIS` (3),
`VIP_DIAS` (30, opcional), `ANTHROPIC_MODEL` (opcional), `PORT` (injetada), `PYTHON_VERSION` (3.12.10).
**Login admin em produção:** usuário `admin@scopemind.com.br` / senha `Alberto2026`. **Suporte/WhatsApp do dono:** `5582920012133`.

---

## 10. PENDÊNCIAS / PRÓXIMOS PASSOS
1. **Plano pago da API-Football (Pro ~R$110/mês)** quando tiver clientes de verdade usando bastante — libera muitas
   consultas/dia e as datas/temporadas (volta o módulo Tabelas). Hoje o grátis (100/dia) atende uso leve; em uso
   intenso pode estourar (mas agora degrada suave, mantendo os últimos jogos).
2. **Otimização opcional:** pausar a auto-atualização quando a aba está em segundo plano (Page Visibility API) — corta
   muito o consumo de cota. O dono ainda não pediu.
3. **🔔 Alerta de "escalação saiu"** (lineup) — exige polling da API de escalações (custo de cota).
4. Ideias futuras da comunidade: ranking semanal/mensal, missões diárias, sequência, perfil público, comentários,
   compartilhar palpite, conquistas (a estrutura já foi pensada pra escalar).
5. **VIP "novamente"/badge:** o "Ver análise novamente" e a contagem de jogos abertos hoje só populam para **cliente
   comum** (limitado). VIP revê grátis pelo fluxo normal (com cronômetro). Dá pra estender pro VIP se quiser.

---

## 11. CUIDADOS PARA NÃO QUEBRAR (LIÇÕES DESTA SESSÃO)
- ✅ **SEMPRE validar o `web/app.js` no navegador ANTES de publicar.** Um erro de sintaxe (ex.: aspas duplas dentro de
  string) **derruba o front INTEIRO** — login e tudo param, e parece "não faz nada". Já aconteceu (na `comPodio`).
  Como validar sem node/deno (não instalados): subir um preview Python servindo `web/`, abrir uma página `/check` que
  faz `new Function(fetch('/app.js'))` e checar `document.title` (`SINTAXE_OK` ou o erro). O screenshot do preview
  **trava** se o `background.png` estiver com `background-attachment: fixed` — sirva o index com um override de fundo
  sólido, OU use a página `/check` que não carrega o index. A ferramenta de preview às vezes **engasga**: reiniciar o
  preview server resolve; navegar via `location.href` no eval **não funciona** (mundo isolado) — sirva a página alvo na raiz.
- ✅ **Sempre Read antes de Edit** em `app.js`/`server.py`.
- ✅ **Não traduzir `country` interno** nem renomear `league` interno (quebra prioridade/flag/filtro Brasil). Use
  `country_pt` e `nomeLiga()` só pra EXIBIR.
- ✅ **`config.json` tem segredos** (chaves + hash de senhas + secret). NÃO commitar (já no `.gitignore`).
  ⚠️ A chave da Anthropic foi exposta no chat uma vez (o dono optou por **não** trocar). Tokens/segredos do app
  apareceram em prints — evitar mostrar a aba Environment da Render em público.
- ✅ **Análise gasta dinheiro** (mantém: só no botão Analisar, bloqueio em encerrados, cota do cliente, teto diário, reaproveitamento).
- ✅ **Filtros têm camadas:** `_eh_profissional` (campeonato + time) e `_eh_destaque` (1ª divisão dos países + Brasil
  A/B/C + internacionais) + `MAX_JOGOS_DIA`. As listas `TOP_DIVISAO`/`LIGAS_DESTAQUE` são fáceis de editar (o dono
  pede p/ incluir/excluir liga pelo nome).
- ✅ **Cota da API:** NÃO apagar o cache bom quando a API falha; o tratamento de cota já cuida disso.
- ✅ **Render + disco:** deploy tem 502 breve (normal). Disco persiste entre deploys (logo, limpar o cache do disco
  exige cuidado — não há comando fácil; geralmente desnecessário).
- ✅ **Ao testar local:** backup do `config.json`, rode em `PORT=8799`, restaure o config e apague pastas de dados/
  scripts `_*.py` depois.

### Endpoints da API (referência rápida)
- `GET /api/status` · `GET /api/jogos?periodo=hoje|amanha|ontem|aovivo` · `GET /api/placar` ·
  `GET /api/relatorios` · `GET /api/relatorio?chave=`
- `POST /api/login` · `POST /api/cadastrar` · `POST /api/configurar` (admin: `anthropic_api_key`, `football_api_key`,
  `anthropic_model`, `auto_reanalise`, `limite_analises_gratis`, `vip_dias`) · `POST /api/analisar` (campo `forcar`
  só do admin) · `POST /api/excluir-relatorio` · `POST /api/trocar-senha` (cliente) · `GET /api/conta`
- **Chat:** `GET /api/chat?desde=<id>` · `GET /api/chat/usuarios` (admin) · `POST /api/chat/{enviar,denunciar,
  usuario(admin),remover(admin),limpar(admin)}`
- **Comunidade:** `GET /api/comunidade/jogos` · `GET /api/comunidade/ranking?faixa=geral|top1000|top100|top50|top10|top3`
  · `GET /api/comunidade/eu` · `POST /api/comunidade/palpitar` · admin: `GET /api/comunidade/admin/{usuarios,palpites?q=,
  exportar?tipo=ranking|palpites}` · `POST /api/comunidade/admin/{resultado,reprocessar,ajustar-xp,bloquear}`
- Estáticos: `/` (index), `/styles.css`, `/app.js`, `/manifest.json`, `/sw.js`, `/imagens/...`

---

## 12. OBSERVAÇÕES SOBRE O DONO (Alberto)
- **Não programa.** Explicar tudo em **PT-BR simples**. Está construindo de forma **iterativa** (pede features a cada conversa).
- Há **memória automática** do projeto em
  `~/.claude/projects/C--Users-Alberto-Souza-Desktop-Jogo/memory/sistema-analise-esportiva.md` (resumo persistente — vale a leitura).
- Existe um 2º projeto não relacionado: um jogo em Godot ("Eras da Civilização") na mesma pasta `Desktop\Jogo`.
- O caminho da memória usa `Desktop-Jogo`, mas o projeto do app fica em `Desktop\AnaliseFutebol` (são coisas diferentes).

---
*Documento de handoff entre sessões. Mantenha-o atualizado conforme o projeto evoluir.*
