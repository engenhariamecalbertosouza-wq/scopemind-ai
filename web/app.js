// ===================== Estado e utilidades =====================
let TOKEN = localStorage.getItem("token") || "";
let ROLE = localStorage.getItem("role") || "admin";
let ANALISES_REST = (function () { const r = localStorage.getItem("rest"); return (r === null || r === "") ? null : parseInt(r); })();
let PERIODO = "hoje";
let JOGOS = [];                // últimos jogos carregados (para filtrar localmente)
let ABERTAS = new Set();       // campeonatos (pastas) expandidos
let ABERTAS_ENC = new Set();   // pastas expandidas no módulo Encerrados
let ABERTAS_AV = new Set();    // pastas expandidas no Ao Vivo
let LISTA_AOVIVO = [];
let LISTA_ENC = [];
let SO_FAVORITOS = false;
let timerAoVivo = null;
let timerAgenda = null;
let ALERTAS_ON = localStorage.getItem("alertas") === "1";
let ALERTADOS = new Set();
let FAV_LIGAS = new Set(JSON.parse(localStorage.getItem("fav_ligas") || "[]"));
let FAV_TIMES = new Set(JSON.parse(localStorage.getItem("fav_times") || "[]"));
let JOGO_ATUAL = null;
let REL_ATUAL_CHAVE = "";
let REL_ATUAL_JOGO = null;
let REPORTS_SET = new Set();
let timerCarregando = null;
let prepTimer = null;         // cronômetro dramático do cliente (30s)
let VIP = localStorage.getItem("vip") === "1";
let NOME = localStorage.getItem("nome") || "";
let MEUS_JOGOS = new Set(JSON.parse(localStorage.getItem("meus_jogos") || "[]")); // jogos que o cliente já analisou (comprou)
let timerChat = null;
let CHAT_ULTIMO = 0;          // maior id de mensagem já recebido
let CHAT_EU = null;           // quem sou eu no chat (vem do servidor)
let CHAT_IDS = new Set();     // ids já desenhados na tela (evita duplicar)
let CHAT_ADMIN_CARREGADO = false;
let COM_JOGOS = [];           // jogos carregados no Placar da Comunidade
let COM_FAIXA = "geral";      // faixa do ranking selecionada
let COM_SUBTAB = "palpitar";  // aba interna ativa da comunidade

const $ = (sel) => document.querySelector(sel);

const PRIORIDADE = [
  "Brasileirao Serie A", "Brasileirao Serie B", "Brasileirao Serie C",
  "Copa do Brasil", "Libertadores", "Sul-Americana",
  "Champions League", "Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1",
];

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), 3400);
}
async function api(rota, opcoes = {}) {
  opcoes.headers = Object.assign(
    { "Content-Type": "application/json", "X-Auth-Token": TOKEN }, opcoes.headers || {});
  const metodo = (opcoes.method || "GET").toUpperCase();
  const tentativas = metodo === "GET" ? 3 : 1; // re-tenta só leituras (GET); não repete análise/cadastro
  let erroFinal;
  for (let t = 0; t < tentativas; t++) {
    try {
      const resp = await fetch(rota, opcoes);
      let dados = {};
      try { dados = await resp.json(); } catch (e) {}
      if (resp.status === 401 && rota !== "/api/login") { sair(); throw new Error(dados.erro || "Sessão expirada."); }
      if (!resp.ok) throw new Error(dados.erro || ("Erro " + resp.status));
      return dados;
    } catch (err) {
      erroFinal = err;
      if (!(err instanceof TypeError) || t === tentativas - 1) throw err; // re-tenta só erro de rede
      await new Promise((r) => setTimeout(r, 700));
    }
  }
  throw erroFinal;
}
function esc(s) {
  return (s || "").toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function formatarData(iso) {
  const p = (iso || "").split("-");
  return p.length === 3 ? (p[2] + "/" + p[1] + "/" + p[0]) : iso;
}
function nomeLiga(liga) {
  if (liga === "Friendlies") return "Amistosos da Copa do Mundo 2026";
  return liga || "";
}
function slug(s) {
  s = (s || "").toString().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return s.slice(0, 60) || "jogo";
}
function chaveJogo(j) {
  return j.id ? ("id-" + j.id) : (slug(j.home) + "_vs_" + slug(j.away) + "_" + (j.data || ""));
}

// ===================== Login =====================
function aplicarSessao(d) {
  TOKEN = d.token || "";
  ROLE = d.role || "admin";
  VIP = !!d.vip;
  NOME = d.usuario || "";
  ANALISES_REST = (d.analises_restantes === undefined ? null : d.analises_restantes);
  localStorage.setItem("token", TOKEN);
  localStorage.setItem("role", ROLE);
  localStorage.setItem("vip", VIP ? "1" : "0");
  localStorage.setItem("nome", NOME);
  if (d.jogos_abertos) { MEUS_JOGOS = new Set(d.jogos_abertos); localStorage.setItem("meus_jogos", JSON.stringify([...MEUS_JOGOS])); }
  localStorage.setItem("rest", ANALISES_REST === null ? "" : ANALISES_REST);
}
function setRest(n) {
  ANALISES_REST = n;
  localStorage.setItem("rest", n === null ? "" : n);
  aplicarPapel();
}
function ehCliente() { return ROLE === "cliente"; }
function aplicarPapel() {
  const cliente = ROLE === "cliente";
  $("#btn-config").classList.toggle("hidden", cliente);
  // Cliente NÃO vê o módulo "Relatórios salvos" (evita ver/abrir análises de graça).
  const miRel = document.querySelector('.menu-item[data-secao="relatorios"]');
  if (miRel) miRel.classList.toggle("hidden", cliente);
  const wf = $("#wpp-flutuante"); if (wf) wf.classList.toggle("hidden", !cliente);  // suporte WhatsApp só p/ cliente
  const b = $("#badge-cliente");
  b.className = "badge-cliente";
  if (cliente && VIP) {
    b.innerHTML = '<span class="unl-inf">∞</span> UNLIMITED';
    b.classList.add("badge-unlimited");
  } else if (cliente && ANALISES_REST !== null) {
    b.textContent = "🎟️ " + ANALISES_REST + " análise(s) grátis";
  } else {
    b.classList.add("hidden");
  }
}
$("#form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#erro-login").textContent = "";
  try {
    const d = await api("/api/login", {
      method: "POST", body: JSON.stringify({ usuario: $("#in-usuario").value, senha: $("#in-senha").value }) });
    aplicarSessao(d);
    entrarNoApp();
  } catch (err) { $("#erro-login").textContent = err.message; }
});
$("#ir-cadastro").addEventListener("click", () => {
  $("#form-login").classList.add("hidden"); $("#wrap-ir-cadastro").classList.add("hidden");
  $("#form-cadastro").classList.remove("hidden"); $("#wrap-ir-login").classList.remove("hidden");
});
$("#ir-login").addEventListener("click", () => {
  $("#form-cadastro").classList.add("hidden"); $("#wrap-ir-login").classList.add("hidden");
  $("#form-login").classList.remove("hidden"); $("#wrap-ir-cadastro").classList.remove("hidden");
});
$("#form-cadastro").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("#erro-cadastro").textContent = "";
  try {
    const d = await api("/api/cadastrar", { method: "POST", body: JSON.stringify({
      nome: $("#cad-nome").value, cpf: $("#cad-cpf").value,
      email: $("#cad-email").value, senha: $("#cad-senha").value }) });
    aplicarSessao(d);
    entrarNoApp();
  } catch (err) { $("#erro-cadastro").textContent = err.message; }
});
function sair() {
  TOKEN = ""; ROLE = "admin"; ANALISES_REST = null; VIP = false; NOME = ""; MEUS_JOGOS = new Set();
  pararChat(); pararAoVivo(); pararAgendaAuto();
  localStorage.removeItem("token"); localStorage.removeItem("role"); localStorage.removeItem("rest"); localStorage.removeItem("vip"); localStorage.removeItem("nome"); localStorage.removeItem("meus_jogos");
  if ($("#saudacao")) $("#saudacao").textContent = "";
  $("#tela-app").classList.add("hidden"); $("#tela-login").classList.remove("hidden");
}
$("#btn-sair").addEventListener("click", sair);

// ===================== Entrada =====================
function preencherDatasAbas() {
  const DIAS = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];
  const fmt = (d) => "· " + DIAS[d.getDay()] + " " +
    String(d.getDate()).padStart(2, "0") + "/" + String(d.getMonth() + 1).padStart(2, "0");
  const hoje = new Date();
  const amanha = new Date(); amanha.setDate(hoje.getDate() + 1);
  if ($("#data-hoje")) $("#data-hoje").textContent = fmt(hoje);
  if ($("#data-amanha")) $("#data-amanha").textContent = fmt(amanha);
}
// Tela inicial: Cérebro de Análise ao Vivo (carregado isolado num iframe)
function mostrarCerebro() {
  const ov = $("#cerebro-overlay"), fr = $("#cerebro-frame");
  if (!ov || !fr) return;
  fr.src = "cerebro.html?t=" + Date.now();   // recarrega a animação do zero
  ov.classList.remove("hidden");
}
function esconderCerebro() {
  const ov = $("#cerebro-overlay"), fr = $("#cerebro-frame");
  if (ov) ov.classList.add("hidden");
  if (fr) fr.src = "about:blank";             // para a animação e libera CPU
}
window.addEventListener("message", (e) => {
  if (e.origin === window.location.origin && e.data === "cerebro-entrar") esconderCerebro();
});

async function entrarNoApp() {
  mostrarCerebro();
  $("#tela-login").classList.add("hidden");
  $("#tela-app").classList.remove("hidden");
  aplicarPapel();
  const nm = (ROLE === "admin") ? "Admin" : (NOME || "");
  if ($("#saudacao")) $("#saudacao").textContent = nm ? ("👋 Bem-vindo, " + nm) : "";
  $("#btn-alertas").classList.toggle("ativo", ALERTAS_ON);
  preencherDatasAbas();
  await atualizarStatus();
  await carregarRelatoriosSet();
  if (ehCliente()) await carregarMeusJogos();
  carregarJogos();
  iniciarAgendaAuto();
}
async function atualizarStatus() {
  try {
    const s = await api("/api/status");
    const badge = $("#badge-modo");
    if (s.ao_vivo_dados) { badge.textContent = "dados ao vivo"; badge.className = "badge badge-vivo"; }
    else { badge.textContent = "modo demonstração"; badge.className = "badge badge-demo"; }
    $("#cfg-modelo").value = s.modelo || "claude-opus-4-8";
    $("#cfg-auto").checked = !!s.auto_reanalise;
    if (s.limite_analises_gratis !== undefined && $("#cfg-limite")) $("#cfg-limite").value = s.limite_analises_gratis;
    if (s.vip_dias !== undefined && $("#cfg-vipdias")) $("#cfg-vipdias").value = s.vip_dias;
    $("#cfg-ultima").textContent = s.ultima_atualizacao && s.ultima_atualizacao !== "ainda nao"
      ? ("Última atualização automática: " + s.ultima_atualizacao) : "";
  } catch (e) {}
}

// ===================== Menu principal =====================
document.querySelectorAll(".menu-item").forEach((mi) => {
  mi.addEventListener("click", () => {
    document.querySelectorAll(".menu-item").forEach((x) => x.classList.remove("ativa"));
    mi.classList.add("ativa");
    const secao = mi.dataset.secao;
    $("#secao-agenda").classList.toggle("hidden", secao !== "agenda");
    $("#secao-aovivo").classList.toggle("hidden", secao !== "aovivo");
    $("#secao-encerrados").classList.toggle("hidden", secao !== "encerrados");
    $("#secao-placar").classList.toggle("hidden", secao !== "placar");
    $("#secao-relatorios").classList.toggle("hidden", secao !== "relatorios");
    $("#secao-comunidade").classList.toggle("hidden", secao !== "comunidade");
    $("#secao-chat").classList.toggle("hidden", secao !== "chat");
    $("#secao-conta").classList.toggle("hidden", secao !== "conta");
    if (secao === "relatorios") carregarRelatorios();
    if (secao === "encerrados") carregarEncerrados();
    if (secao === "placar") carregarPlacar();
    if (secao === "comunidade") iniciarComunidade();
    if (secao === "conta") carregarConta();
    if (secao === "aovivo") iniciarAoVivo(); else pararAoVivo();
    if (secao === "agenda") iniciarAgendaAuto(); else pararAgendaAuto();
    if (secao === "chat") iniciarChat(); else pararChat();
  });
});

// ===================== Abas de período + busca/filtro =====================
document.querySelectorAll(".aba").forEach((aba) => {
  aba.addEventListener("click", () => {
    document.querySelectorAll(".aba").forEach((a) => a.classList.remove("ativa"));
    aba.classList.add("ativa");
    PERIODO = aba.dataset.periodo;
    carregarJogos();
  });
});
$("#btn-atualizar").addEventListener("click", carregarJogos);
$("#busca").addEventListener("input", renderAgenda);
$("#filtro-liga").addEventListener("change", renderAgenda);
$("#btn-expandir").addEventListener("click", () => { ABERTAS = new Set(JOGOS.map(chaveGrupo)); renderAgenda(); });
$("#btn-recolher").addEventListener("click", () => { ABERTAS = new Set(); renderAgenda(); });
$("#btn-favoritos").addEventListener("click", () => {
  SO_FAVORITOS = !SO_FAVORITOS;
  $("#btn-favoritos").classList.toggle("ativo", SO_FAVORITOS);
  reRenderAtual();
});

// ===================== AGENDA =====================
async function carregarJogos(silencioso) {
  const lista = $("#lista-jogos");
  if (!silencioso) { lista.innerHTML = '<div class="vazio">Carregando jogos…</div>'; $("#info-periodo").textContent = ""; }
  try {
    const dados = await api("/api/jogos?periodo=" + PERIODO);
    JOGOS = dados.jogos || [];
    let info;
    if (dados.modo === "demo") {
      info = "🔸 <b>Modo demonstração</b> — jogos de exemplo. Cole a chave de dados (⚙️) para ver os jogos reais.";
    } else {
      const aComecar = JOGOS.filter((j) => !ehFim(j.status) && !ehVivo(j.status));
      const nLigas = [...new Set(aComecar.map((j) => j.league).filter(Boolean))].length;
      info = "<b>" + aComecar.length + "</b> jogo(s) a começar em <b>" + nLigas + "</b> campeonatos · 🔄 atualiza sozinho a cada 10 min (os ao vivo vão pro módulo Ao Vivo).";
    }
    if (dados.aviso) info += '<br><span class="aviso-plano">📌 ' + esc(dados.aviso) + "</span>";
    $("#info-periodo").innerHTML = info;
    renderResumo(JOGOS);
    preencherFiltroLigas();
    renderAgenda();
    checkAlertas();
  } catch (err) {
    if (!silencioso) {
      const rede = err instanceof TypeError;
      $("#lista-jogos").innerHTML = '<div class="vazio">' + (rede
        ? "⚠️ Sem conexão com o servidor. Confira se a janela preta (o servidor) está aberta e toque em ↻ Atualizar."
        : "Erro ao carregar: " + err.message) + "</div>";
    }
  }
}
function ehVivo(s) { return /tempo|intervalo|vivo|prorrog|p[eê]naltis/i.test(s || ""); }
function ehFim(s) { return /encerrado/i.test(s || ""); }
function renderResumo(jogos) {
  const ativos = jogos.filter((j) => !ehFim(j.status));
  const vivo = ativos.filter((j) => ehVivo(j.status)).length;
  const prox = ativos.length - vivo;
  const fim = jogos.filter((j) => ehFim(j.status)).length;
  const card = (n, rot, cls) =>
    '<div class="card-resumo ' + cls + '"><div class="cr-num">' + n + '</div><div class="cr-rot">' + rot + "</div></div>";
  $("#resumo").innerHTML =
    card(ativos.length, "a disputar", "") +
    card(vivo, "🔴 ao vivo", "cr-vivo") +
    card(prox, "⏱️ a começar", "cr-prox") +
    '<div class="card-resumo cr-fim" id="card-encerrados" title="Ver módulo de encerrados">' +
      '<div class="cr-num">' + fim + '</div><div class="cr-rot">✅ encerrados ›</div></div>';
  const ce = $("#card-encerrados");
  if (ce) ce.addEventListener("click", () => $('.menu-item[data-secao="encerrados"]').click());
}
function preencherFiltroLigas() {
  const sel = $("#filtro-liga");
  const atual = sel.value;
  const ligas = [...new Set(JOGOS.map((j) => j.league).filter(Boolean))].sort(ordenarLigas);
  sel.innerHTML = '<option value="">Todos os campeonatos</option>' +
    ligas.map((l) => '<option value="' + esc(l) + '">' + esc(nomeLiga(l)) + "</option>").join("");
  sel.value = atual;
}
function ordenarLigas(a, b) {
  const ia = PRIORIDADE.findIndex((p) => (a || "").includes(p));
  const ib = PRIORIDADE.findIndex((p) => (b || "").includes(p));
  const pa = ia === -1 ? 999 : ia, pb = ib === -1 ? 999 : ib;
  if (pa !== pb) return pa - pb;
  return (a || "").localeCompare(b || "");
}
const PAIS_ISO = {
  "Brazil": "br", "Brasil": "br", "England": "gb-eng", "Scotland": "gb-sct", "Wales": "gb-wls",
  "Spain": "es", "Italy": "it", "Germany": "de", "France": "fr", "Portugal": "pt",
  "Argentina": "ar", "Netherlands": "nl", "Belgium": "be", "USA": "us", "Mexico": "mx",
  "Colombia": "co", "Chile": "cl", "Uruguay": "uy", "Paraguay": "py", "Ecuador": "ec",
  "Peru": "pe", "Bolivia": "bo", "Venezuela": "ve", "Japan": "jp", "South-Korea": "kr",
  "Saudi-Arabia": "sa", "Turkey": "tr", "Greece": "gr", "Russia": "ru", "Ukraine": "ua",
  "Austria": "at", "Switzerland": "ch", "Denmark": "dk", "Sweden": "se", "Norway": "no",
  "Poland": "pl", "Croatia": "hr", "Egypt": "eg", "Morocco": "ma", "Nigeria": "ng",
  "Ethiopia": "et", "Algeria": "dz", "Australia": "au", "China": "cn", "Europe": "eu",
};
function isoDaBandeira(flag) {
  // extrai o codigo do pais do link de bandeira da API (ex: .../flags/br.svg -> "br")
  const m = (flag || "").match(/\/flags\/([a-z]{2}(?:-[a-z]+)?)\.svg/i);
  return m ? m[1].toLowerCase() : "";
}
function urlBandeira(flag, pais) {
  const iso = isoDaBandeira(flag) || PAIS_ISO[pais] || "";
  return iso ? ("https://flagcdn.com/w80/" + iso + ".png") : "";  // flagcdn (.png) sempre carrega
}
function flagHtml(flag, pais) {
  const u = urlBandeira(flag, pais);
  return u
    ? '<img class="pasta-bandeira" loading="lazy" src="' + esc(u) + '" alt="" onerror="this.style.display=\'none\'"/>'
    : '<span class="pasta-globo">🌍</span>';
}
function chaveGrupo(j) {
  return j.league_id ? ("L" + j.league_id) : ((j.league || "Outros") + "|" + (j.country || ""));
}

// Prioridade dos campeonatos (menor = mais no topo):
// Brasil 1o, Copa do Mundo 2o, depois Inglaterra, Espanha, Franca, Italia, Alemanha, etc.
function prioridadeGrupo(g) {
  const pais = (g.pais || "").toLowerCase();
  const liga = (g.liga || "").toLowerCase();
  // Copa do Mundo SEMPRE no topo quando houver jogos dela
  if ((liga.includes("world cup") || liga.includes("copa do mundo")) &&
      !liga.includes("qualif") && !liga.includes("women"))
    return -100;
  // Amistosos de seleções (preparação da Copa do Mundo) — logo abaixo da Copa
  if ((liga.includes("friendl") || liga.includes("amistoso")) &&
      (pais === "world" || pais === "internacional" || pais === "mundo" || pais === ""))
    return -50;
  if (pais === "brazil" || pais === "brasil") {
    if (liga.includes("serie a")) return 0;
    if (liga.includes("serie b")) return 1;
    if (liga.includes("serie c")) return 2;
    if (liga.includes("serie d")) return 3;
    if (liga.includes("copa do bra")) return 4;
    return 5;  // estaduais e demais do Brasil
  }
  const grandes = [
    ["premier league", "england"], ["la liga", "spain"], ["ligue 1", "france"],
    ["serie a", "italy"], ["bundesliga", "germany"], ["primeira liga", "portugal"],
    ["eredivisie", "netherlands"], ["champions league", ""], ["libertadores", ""],
    ["europa league", ""], ["copa america", ""], ["world cup", ""],
  ];
  for (let i = 0; i < grandes.length; i++) {
    if (liga.includes(grandes[i][0]) && (!grandes[i][1] || pais === grandes[i][1])) return 20 + i;
  }
  return 100;  // demais campeonatos
}
function ordenarGrupo(a, b) {
  const pa = prioridadeGrupo(a), pb = prioridadeGrupo(b);
  if (pa !== pb) return pa - pb;
  return (a.liga || "").localeCompare(b.liga || "");
}

// ===================== Favoritos =====================
function salvarFavs() {
  localStorage.setItem("fav_ligas", JSON.stringify([...FAV_LIGAS]));
  localStorage.setItem("fav_times", JSON.stringify([...FAV_TIMES]));
}
function ehFavLiga(liga) { return FAV_LIGAS.has(liga); }
function ehFavTime(time) { return FAV_TIMES.has(time); }
function toggleFavLiga(liga) {
  if (FAV_LIGAS.has(liga)) FAV_LIGAS.delete(liga); else FAV_LIGAS.add(liga);
  salvarFavs(); reRenderAtual();
}
function toggleFavTime(time) {
  if (FAV_TIMES.has(time)) FAV_TIMES.delete(time); else FAV_TIMES.add(time);
  salvarFavs(); reRenderAtual();
}
function jogoTemFav(j) { return ehFavLiga(j.league) || ehFavTime(j.home) || ehFavTime(j.away); }
function estrelaTime(t) {
  const on = ehFavTime(t);
  return '<span class="estrela estrela-time ' + (on ? "on" : "") + '" data-time="' + esc(t) + '">' + (on ? "★" : "☆") + "</span>";
}
function reRenderAtual() {
  if (!$("#secao-agenda").classList.contains("hidden")) renderAgenda();
  else if (!$("#secao-aovivo").classList.contains("hidden")) renderFolders($("#lista-aovivo"), LISTA_AOVIVO, ABERTAS_AV, true);
  else if (!$("#secao-encerrados").classList.contains("hidden")) renderFolders($("#lista-encerrados"), LISTA_ENC, ABERTAS_ENC, false);
}

function renderFolders(container, jogos, abertasSet, abrirForcado) {
  if (SO_FAVORITOS) jogos = jogos.filter(jogoTemFav);
  if (!jogos.length) {
    container.innerHTML = '<div class="vazio">' +
      (SO_FAVORITOS ? "Nenhum favorito por aqui. Toque na ⭐ de um campeonato ou time." : "Nenhum jogo encontrado.") + "</div>";
    return;
  }
  const grupos = {};
  jogos.forEach((j) => {
    const k = chaveGrupo(j);
    if (!grupos[k]) grupos[k] = { chave: k, liga: j.league || "Outros", pais: j.country || "", pais_pt: j.country_pt || j.country || "", flag: j.flag || "", jogos: [] };
    grupos[k].jogos.push(j);
  });
  // FAVORITOS primeiro, depois a ordem de prioridade normal
  const chaves = Object.keys(grupos).sort((a, b) => {
    const fa = ehFavLiga(grupos[a].liga) ? 0 : 1, fb = ehFavLiga(grupos[b].liga) ? 0 : 1;
    if (fa !== fb) return fa - fb;
    return ordenarGrupo(grupos[a], grupos[b]);
  });
  container.innerHTML = "";
  chaves.forEach((k) => {
    const g = grupos[k];
    const arr = g.jogos.sort((a, b) => {
      const fa = (ehFavTime(a.home) || ehFavTime(a.away)) ? 0 : 1;
      const fb = (ehFavTime(b.home) || ehFavTime(b.away)) ? 0 : 1;
      if (fa !== fb) return fa - fb;
      return (a.data + a.time).localeCompare(b.data + b.time);
    });
    const favLiga = ehFavLiga(g.liga);
    const aberta = abrirForcado || abertasSet.has(k) || favLiga;
    const vivos = arr.filter((j) => ehVivo(j.status)).length;
    const pasta = document.createElement("div");
    pasta.className = "pasta" + (aberta ? " aberta" : "") + (favLiga ? " pasta-fav" : "");
    pasta.innerHTML =
      '<div class="pasta-cabeca">' +
        flagHtml(g.flag, g.pais) +
        '<span class="pasta-nome">' + esc(nomeLiga(g.liga)) +
          (g.pais_pt ? '<span class="pasta-pais">' + esc(g.pais_pt) + "</span>" : "") + "</span>" +
        (vivos ? '<span class="pasta-vivo">🔴 ' + vivos + " ao vivo</span>" : "") +
        '<span class="estrela estrela-liga ' + (favLiga ? "on" : "") + '" title="Favoritar campeonato">' + (favLiga ? "★" : "☆") + "</span>" +
        '<span class="pasta-contagem">' + arr.length + "</span>" +
        '<span class="pasta-seta">▸</span>' +
      "</div>" +
      '<div class="pasta-corpo"><div class="jogos-lista"></div></div>';
    const grade = pasta.querySelector(".jogos-lista");
    arr.forEach((j) => grade.appendChild(cartaoJogo(j)));
    pasta.querySelector(".pasta-cabeca").addEventListener("click", (e) => {
      if (e.target.classList.contains("estrela-liga")) { e.stopPropagation(); toggleFavLiga(g.liga); return; }
      const ab = pasta.classList.toggle("aberta");
      if (ab) abertasSet.add(k); else abertasSet.delete(k);
    });
    container.appendChild(pasta);
  });
}

function renderAgenda() {
  const termo = $("#busca").value.trim().toLowerCase();
  const ligaFiltro = $("#filtro-liga").value;
  let jogos = JOGOS.filter((j) => !ehFim(j.status) && !ehVivo(j.status));   // Agenda = só jogos a começar (ao vivo vai pro módulo Ao Vivo)
  if (ligaFiltro) jogos = jogos.filter((j) => j.league === ligaFiltro);
  if (termo) jogos = jogos.filter((j) =>
    (j.home + " " + j.away + " " + j.league + " " + (j.country || "")).toLowerCase().includes(termo));
  renderFolders($("#lista-jogos"), jogos, ABERTAS, !!termo || !!ligaFiltro);
}

async function carregarEncerrados() {
  const lista = $("#lista-encerrados");
  lista.innerHTML = '<div class="vazio">Carregando resultados…</div>';
  try {
    const [h, o] = await Promise.all([
      api("/api/jogos?periodo=hoje"),
      api("/api/jogos?periodo=ontem"),
    ]);
    const vistos = new Set();
    const jogos = [...(h.jogos || []), ...(o.jogos || [])]
      .filter((j) => ehFim(j.status))
      .filter((j) => { const k = chaveJogo(j); if (vistos.has(k)) return false; vistos.add(k); return true; });
    LISTA_ENC = jogos;
    $("#info-encerrados").innerHTML = jogos.length
      ? ("<b>" + jogos.length + "</b> jogos encerrados (ontem e hoje) · com placar final · agrupados por campeonato.")
      : "Nenhum jogo encerrado encontrado em ontem/hoje.";
    renderFolders(lista, LISTA_ENC, ABERTAS_ENC, false);
  } catch (err) {
    lista.innerHTML = '<div class="vazio">Erro: ' + err.message + "</div>";
  }
}
function logo(url) {
  return url ? '<img class="cj-escudo" loading="lazy" src="' + esc(url) + '" alt="" onerror="this.style.display=\'none\'"/>' : "";
}
function cartaoJogo(j) {
  const div = document.createElement("div");
  const vivo = ehVivo(j.status), fim = ehFim(j.status);
  div.className = "jogo" + (vivo ? " jogo-vivo" : "");
  const escudo = (u) => u ? '<img class="jt-escudo" loading="lazy" src="' + esc(u) + '" onerror="this.style.visibility=\'hidden\'"/>' : "";
  const placar = (j.score && j.score.indexOf(" - ") >= 0) ? '<span class="jl-placar">' + esc(j.score) + "</span>" : "";
  let quando;
  if (vivo) quando = '<span class="jr-quando vivo">🔴 ' + esc(j.status) + "</span>";
  else if (fim) quando = '<span class="jr-quando fim">✅ ' + esc(j.status) + "</span>";
  else {
    const d = (PERIODO !== "hoje" && j.data) ? esc(formatarData(j.data).slice(0, 5)) + " · " : "";
    quando = '<span class="jr-quando">🕒 ' + d + esc(j.time || "--:--") + "</span>";
  }
  const temMinha = ehCliente() ? MEUS_JOGOS.has(chaveJogo(j)) : REPORTS_SET.has(chaveJogo(j));
  const analisado = temMinha ? '<span class="jr-analisado">📄 ' + (ehCliente() ? "minha análise" : "analisado") + "</span>" : "";
  div.innerHTML =
    '<div class="jogo-linha">' +
      '<span class="jl-time">' + escudo(j.home_logo) + '<span class="jl-nome">' + esc(j.home) + "</span>" + estrelaTime(j.home) + "</span>" +
      '<span class="jl-x">VS</span>' +
      '<span class="jl-time">' + estrelaTime(j.away) + '<span class="jl-nome">' + esc(j.away) + "</span>" + escudo(j.away_logo) + "</span>" +
      placar +
    "</div>" +
    '<div class="jogo-rodape">' + quando + analisado +
      '<span class="jr-tv">📺 ' + esc(j.watch || "") + "</span></div>";
  div.addEventListener("click", (e) => {
    const est = e.target.closest(".estrela-time");
    if (est) { e.stopPropagation(); toggleFavTime(est.dataset.time); return; }
    if (!ehCliente() && REPORTS_SET.has(chaveJogo(j))) verSalvo(chaveJogo(j));
    else abrirDetalhes(j);
  });
  return div;
}

// ===================== DETALHES (grátis) =====================
function abrirDetalhes(j) {
  JOGO_ATUAL = j;
  $("#det-titulo").innerHTML = esc(j.home) + '<span class="vs-titulo">VS</span>' + esc(j.away);
  $("#det-info").innerHTML =
    '<div class="det-linha">🏆 <b>Competição:</b> ' + esc(j.league ? nomeLiga(j.league) : "—") +
        ((j.country_pt || j.country) ? " (" + esc(j.country_pt || j.country) + ")" : "") + "</div>" +
    '<div class="det-linha">📅 <b>Dia:</b> ' + esc(j.data ? formatarData(j.data) : "—") + "</div>" +
    '<div class="det-linha">🕒 <b>Hora:</b> ' + esc(j.time || "--:--") + " (Brasília)</div>" +
    (j.venue ? '<div class="det-linha">🏟️ <b>Estádio:</b> ' + esc(j.venue) + "</div>" : "") +
    '<div class="det-linha">📺 <b>Onde assistir:</b> ' + esc(j.watch || "—") + "</div>" +
    '<div class="det-linha">⚪ <b>Situação:</b> ' + esc(j.status || "—") +
        (j.score ? " · <b>" + esc(j.score) + "</b>" : "") + "</div>";
  const cli = ehCliente();
  const temSalvo = !cli && REPORTS_SET.has(chaveJogo(j));   // cliente nunca vê o atalho "salvo"
  $("#det-tem-salvo").classList.toggle("hidden", !temSalvo);
  $("#btn-ver-salvo").classList.toggle("hidden", !temSalvo);
  $("#det-custo-aviso").classList.toggle("hidden", cli);     // esconde o aviso de custo do cliente
  const encerrado = ehFim(j.status);
  $("#btn-analisar-ia").classList.toggle("hidden", encerrado);
  const jaComprou = cli && MEUS_JOGOS.has(chaveJogo(j));
  $("#btn-analisar-ia").textContent = cli
    ? (jaComprou ? "📄 Ver análise completa novamente" : "🔮 Ver análise completa")
    : "🧠 Analisar com IA";
  $("#det-encerrado").classList.toggle("hidden", !encerrado);
  abrir("modal-detalhes");
}
$("#btn-analisar-ia").addEventListener("click", () => {
  if (ehCliente()) {
    if (MEUS_JOGOS.has(chaveJogo(JOGO_ATUAL))) verMinhaAnalise(JOGO_ATUAL);  // já comprou: instantâneo, grátis
    else rodarAnaliseCliente(JOGO_ATUAL);
  } else rodarAnalise(JOGO_ATUAL);
});
$("#btn-ver-salvo").addEventListener("click", () => verSalvo(chaveJogo(JOGO_ATUAL)));

// ===================== Análise (IA — custa) =====================
const NOMES_AGENTES = [
  "Agente de Monitoramento checando notícias e escalações…",
  "Agente Estatístico cruzando números…",
  "Agente Tático estudando o confronto de estilos…",
  "Agente de Elenco avaliando desfalques…",
  "Agente de Classificação medindo a motivação…",
  "Agente de Histórico revisando confrontos diretos…",
  "Agente de Contexto avaliando fatores externos e humanos…",
  "Agente de Risco apontando incertezas…",
  "Agente de Cenários montando as possibilidades e mercados…",
  "Agente de Consenso fechando a conclusão…",
];
async function rodarAnalise(j) {
  if (!j) return;
  fechar("modal-detalhes");
  abrirPreparando(j);                 // mesma tela bonita "100 IAs" (20s) p/ admin também
  const inicio = Date.now();
  let r = null, err = null;
  try { r = await api("/api/analisar", { method: "POST", body: JSON.stringify(j) }); }
  catch (e) { err = e; }
  if (err) { fecharPreparando(); toast("⚠️ " + err.message); abrirDetalhes(j); return; }
  const faltam = Math.max(0, 20000 - (Date.now() - inicio));   // mínimo de 20s na tela
  await new Promise((res) => setTimeout(res, faltam));
  fecharPreparando();
  if (r.chave) REPORTS_SET.add(r.chave);
  if (r.analises_restantes !== undefined) setRest(r.analises_restantes);
  abrirModalRelatorio(j);
  preencherRelatorio(Object.assign({}, j, { confianca: r.confianca, relatorio: r.relatorio, dados: r.dados, chave: r.chave, desatualizado: false }));
}

// ===================== Análise do CLIENTE (cronômetro de 30s) =====================
// O cliente sempre vê uma tela "100 IAs pensando" por (no mínimo) 30s. Por trás:
// se o jogo já tem análise salva, o servidor REAPROVEITA (custo zero); senão, roda
// de verdade. O cliente não percebe a diferença — recebe sempre algo profissional.
const PREP_FASES = [
  "Cruzando estatísticas e escalações…",
  "Avaliando o momento e a motivação dos times…",
  "Estudando a tática e os confrontos diretos…",
  "Pesando lesões, desfalques e fatores externos…",
  "Simulando cenários e probabilidades de mercado…",
  "Fechando o consenso dos 100 agentes…",
];
function abrirPreparando(j) {
  $("#prep-jogo").innerHTML = esc(j.home || "") + '<span class="vs-titulo">VS</span>' + esc(j.away || "");
  $("#prep-fase").textContent = PREP_FASES[0];
  $("#prep-num").textContent = "20";
  $("#prep-barra-fill").style.width = "0%";
  $("#modal-preparando").classList.remove("hidden");
  let n = 20, fi = 0;
  if (prepTimer) clearInterval(prepTimer);
  prepTimer = setInterval(() => {
    n--;
    if (n <= 0) {
      $("#prep-num").textContent = "✓";
      $("#prep-fase").textContent = "Finalizando os últimos detalhes…";
      $("#prep-barra-fill").style.width = "100%";
    } else {
      $("#prep-num").textContent = n;
      $("#prep-barra-fill").style.width = Math.round((20 - n) / 20 * 100) + "%";
      if (n % 5 === 0) { fi = (fi + 1) % PREP_FASES.length; $("#prep-fase").textContent = PREP_FASES[fi]; }
    }
  }, 1000);
}
function fecharPreparando() {
  if (prepTimer) { clearInterval(prepTimer); prepTimer = null; }
  $("#modal-preparando").classList.add("hidden");
}
async function rodarAnaliseCliente(j) {
  if (!j) return;
  fechar("modal-detalhes");
  abrirPreparando(j);
  const inicio = Date.now();
  let resp = null, err = null;
  try {
    resp = await api("/api/analisar", { method: "POST", body: JSON.stringify(j) });
  } catch (e) { err = e; }
  if (err) {                       // erro (ex.: acabou o crédito): não prende o cliente 30s
    fecharPreparando();
    if (/grátis|gratuit|VIP|ilimitad/i.test(err.message || "")) {   // acabou o limite grátis
      mostrarOfertaVip("Você usou todas as suas rodadas gratuitas. Para continuar sem interrupções, ative o plano VIP e tenha rodadas ilimitadas. O pagamento é seguro via Mercado Pago e a liberação acontece automaticamente.");
      return;
    }
    toast("⚠️ " + err.message);
    abrirDetalhes(j);
    return;
  }
  // sucesso: garante o mínimo de 20s de "preparação" (mesmo se reaproveitou na hora)
  const faltam = Math.max(0, 20000 - (Date.now() - inicio));
  await new Promise((r) => setTimeout(r, faltam));
  fecharPreparando();
  if (resp.chave) REPORTS_SET.add(resp.chave);
  MEUS_JOGOS.add(chaveJogo(j)); localStorage.setItem("meus_jogos", JSON.stringify([...MEUS_JOGOS]));
  if (resp.analises_restantes !== undefined) setRest(resp.analises_restantes);
  abrirModalRelatorio(j);
  preencherRelatorio(Object.assign({}, j, {
    confianca: resp.confianca, relatorio: resp.relatorio, dados: resp.dados, chave: resp.chave, desatualizado: false,
  }));
}
// Cliente revendo uma análise que JÁ comprou: sem cronômetro, sem custo (instantâneo).
async function verMinhaAnalise(j) {
  if (!j) return;
  fechar("modal-detalhes");
  abrirModalRelatorio(j);
  $("#rel-conteudo").classList.add("hidden");
  $("#rel-carregando").classList.remove("hidden");
  $("#carregando-texto").textContent = "Abrindo a sua análise…";
  try {
    const r = await api("/api/analisar", { method: "POST", body: JSON.stringify(j) });
    if (r.chave) REPORTS_SET.add(r.chave);
    if (r.analises_restantes !== undefined) setRest(r.analises_restantes);
    preencherRelatorio(Object.assign({}, j, {
      confianca: r.confianca, relatorio: r.relatorio, dados: r.dados, chave: r.chave, desatualizado: false,
    }));
  } catch (e) {
    fechar("modal-relatorio"); toast("⚠️ " + e.message); abrirDetalhes(j);
  }
}

// ===================== Ver / refazer / excluir =====================
async function verSalvo(chave) {
  try {
    const r = await api("/api/relatorio?chave=" + encodeURIComponent(chave));
    abrirModalRelatorio(r);
    preencherRelatorio(r);
  } catch (err) { toast("⚠️ " + err.message); }
}
$("#btn-refazer-rel").addEventListener("click", () => {
  if (REL_ATUAL_JOGO) rodarAnalise(Object.assign({}, REL_ATUAL_JOGO, { forcar: true }));
});
$("#btn-excluir-rel").addEventListener("click", async () => {
  if (!REL_ATUAL_CHAVE) return;
  try {
    await api("/api/excluir-relatorio", { method: "POST", body: JSON.stringify({ chave: REL_ATUAL_CHAVE }) });
    REPORTS_SET.delete(REL_ATUAL_CHAVE);
    fechar("modal-relatorio");
    toast("Análise excluída.");
    if (!$("#secao-relatorios").classList.contains("hidden")) carregarRelatorios();
  } catch (err) { toast("⚠️ " + err.message); }
});
function abrirModalRelatorio(j) {
  $("#rel-titulo").innerHTML = esc(j.home) + '<span class="vs-titulo">VS</span>' + esc(j.away);
  $("#rel-meta").innerHTML =
    "<b>" + esc(nomeLiga(j.league || "")) + "</b> · " + esc(j.country_pt || j.country || "") + "<br>" +
    "📅 " + esc(j.data ? formatarData(j.data) : "") + " · 🕒 " + esc(j.time || "--:--") + " (Brasília)" +
    (j.venue ? "<br>🏟️ " + esc(j.venue) : "") +
    "<br>📺 " + esc(j.watch || "") +
    (j.analisado_em ? '<br><span class="meta-mini">📄 Análise salva em ' + esc(j.analisado_em) + "</span>" : "");
  $("#rel-badge-conf").innerHTML = "";
  $("#rel-corpo").innerHTML = "";
  $("#rel-desatualizado").classList.add("hidden");
  $("#btn-excluir-rel").classList.add("hidden");
  $("#btn-refazer-rel").classList.add("hidden");
  $("#rel-conteudo").classList.add("hidden");
  $("#rel-carregando").classList.add("hidden");
  abrir("modal-relatorio");
}
function preencherRelatorio(dados) {
  const conf = dados.confianca || "Média";
  const painel = dados.dados;
  if (painel && typeof painel === "object") {
    $("#rel-badge-conf").innerHTML = "";   // o painel já mostra a confiança
    $("#rel-corpo").innerHTML = renderPainelAnalise(painel, dados);
  } else {
    $("#rel-badge-conf").innerHTML =
      '<span class="tag-conf conf-' + conf + '">Grau de confiança: ' + conf + "</span>";
    $("#rel-corpo").innerHTML = markdown(dados.relatorio || "");
  }
  REL_ATUAL_CHAVE = dados.chave || "";
  REL_ATUAL_JOGO = dados;
  const cli = ehCliente();   // cliente não refaz nem exclui (e não vê aviso de "refazer")
  $("#rel-desatualizado").classList.toggle("hidden", cli || !dados.desatualizado);
  $("#btn-excluir-rel").classList.toggle("hidden", cli || !REL_ATUAL_CHAVE);
  $("#btn-refazer-rel").classList.toggle("hidden", cli || !(dados.home && dados.away));
  $("#rel-carregando").classList.add("hidden");
  $("#rel-conteudo").classList.remove("hidden");
}

// ===================== RELATÓRIOS (seção) =====================
async function carregarRelatoriosSet() {
  try { const d = await api("/api/relatorios"); REPORTS_SET = new Set((d.relatorios || []).map((r) => r.chave)); } catch (e) {}
}
async function carregarMeusJogos() {
  try {
    const d = await api("/api/conta");
    if (d.jogos_abertos) { MEUS_JOGOS = new Set(d.jogos_abertos); localStorage.setItem("meus_jogos", JSON.stringify([...MEUS_JOGOS])); }
  } catch (e) {}
}
async function carregarRelatorios() {
  const lista = $("#lista-relatorios");
  lista.innerHTML = '<div class="vazio">Carregando…</div>';
  try {
    const d = await api("/api/relatorios");
    const rs = d.relatorios || [];
    REPORTS_SET = new Set(rs.map((r) => r.chave));
    if (!rs.length) {
      lista.innerHTML = '<div class="vazio">Nenhuma análise salva ainda.<br>' +
        'Vá na <b>Agenda</b>, clique num jogo e em <b>"Analisar com IA"</b>.</div>';
      return;
    }
    lista.innerHTML = "";
    rs.forEach((r) => lista.appendChild(cardRelatorio(r)));
  } catch (err) { lista.innerHTML = '<div class="vazio">Erro: ' + err.message + "</div>"; }
}
function cardRelatorio(r) {
  const div = document.createElement("div");
  div.className = "cartao-jogo";
  const conf = r.confianca || "Moderada";
  const stale = r.desatualizado ? '<div class="cj-analisado" style="color:var(--amarelo)">⚠️ pode estar desatualizada</div>' : "";
  div.innerHTML =
    '<div class="cj-liga"><span>' + esc(nomeLiga(r.league || "")) + "</span>" +
      '<span class="pais">' + esc(r.country_pt || r.country || "") + "</span></div>" +
    '<div class="cj-times"><div class="cj-time"><span>' + esc(r.home) + "</span></div>" +
      '<span class="cj-vs">VS</span>' +
      '<div class="cj-time fora"><span>' + esc(r.away) + "</span></div></div>" +
    stale +
    '<div class="cj-rodape"><span class="cj-status">📅 jogo: ' + esc(r.data ? formatarData(r.data).slice(0, 5) : "—") + "</span>" +
      '<span class="tag-conf-mini conf-' + conf + '">' + esc(conf) + "</span></div>" +
    '<div class="cj-tv">🧠 Analisado em ' + esc(r.analisado_em || "") + "</div>";
  div.addEventListener("click", () => verSalvo(r.chave));
  return div;
}

// ===================== Ao Vivo =====================
async function carregarAoVivo() {
  const lista = $("#lista-aovivo");
  if (!LISTA_AOVIVO.length) lista.innerHTML = '<div class="vazio">Carregando jogos ao vivo…</div>';
  try {
    const d = await api("/api/jogos?periodo=aovivo");
    LISTA_AOVIVO = d.jogos || [];
    $("#info-aovivo").innerHTML = LISTA_AOVIVO.length
      ? ("🔴 <b>" + LISTA_AOVIVO.length + "</b> jogo(s) ao vivo agora · atualiza sozinho a cada 2 min.")
      : "Nenhum jogo profissional ao vivo neste momento. (A tela atualiza sozinha a cada 2 min.)";
    renderFolders(lista, LISTA_AOVIVO, ABERTAS_AV, true);
  } catch (err) {
    lista.innerHTML = '<div class="vazio">Erro: ' + err.message + "</div>";
  }
}
function iniciarAoVivo() {
  pararAoVivo();
  carregarAoVivo();
  timerAoVivo = setInterval(carregarAoVivo, 120000); // 2 min (respeita o limite do plano grátis)
}
function pararAoVivo() {
  if (timerAoVivo) { clearInterval(timerAoVivo); timerAoVivo = null; }
}

// ===================== Agenda: atualização automática (1x/min) =====================
function iniciarAgendaAuto() {
  pararAgendaAuto();
  timerAgenda = setInterval(() => carregarJogos(true), 600000);  // 10 min (poupa a cota da API)
}
function pararAgendaAuto() {
  if (timerAgenda) { clearInterval(timerAgenda); timerAgenda = null; }
}

// ===================== Alertas (jogo do favorito começando) =====================
$("#btn-alertas").addEventListener("click", async () => {
  if (!ALERTAS_ON) {
    if ("Notification" in window && Notification.permission !== "granted") {
      try { await Notification.requestPermission(); } catch (e) {}
    }
    ALERTAS_ON = true; localStorage.setItem("alertas", "1");
    toast("🔔 Alertas ativados! Avisaremos quando um jogo favorito for começar.");
  } else {
    ALERTAS_ON = false; localStorage.setItem("alertas", "0");
    toast("🔕 Alertas desativados.");
  }
  $("#btn-alertas").classList.toggle("ativo", ALERTAS_ON);
});
function checkAlertas() {
  if (!ALERTAS_ON) return;
  const agora = new Date();
  JOGOS.forEach((j) => {
    if (ehFim(j.status) || ehVivo(j.status) || !jogoTemFav(j) || !j.data || !j.time) return;
    const ini = new Date(j.data + "T" + j.time + ":00");
    const min = (ini - agora) / 60000;
    const k = chaveJogo(j);
    if (min > 0 && min <= 15 && !ALERTADOS.has(k)) {
      ALERTADOS.add(k);
      const msg = j.home + " x " + j.away + " começa em " + Math.round(min) + " min!";
      toast("🔔 " + msg);
      if ("Notification" in window && Notification.permission === "granted") {
        try { new Notification("⚽ ScopeMind AI", { body: msg }); } catch (e) {}
      }
    }
  });
}

// ===================== Placar de Acertos =====================
async function carregarPlacar() {
  const cont = $("#placar-lista");
  cont.innerHTML = '<div class="vazio">Carregando…</div>';
  try {
    const d = await api("/api/placar");
    const itens = d.itens || [];
    const pendentes = itens.length - d.total;
    $("#placar-resumo").innerHTML =
      '<div class="card-resumo"><div class="cr-num">' + (d.pct === null ? "—" : d.pct + "%") + '</div><div class="cr-rot">de acerto</div></div>' +
      '<div class="card-resumo cr-fim"><div class="cr-num">' + d.acertos + '</div><div class="cr-rot">✅ acertos</div></div>' +
      '<div class="card-resumo cr-vivo"><div class="cr-num">' + d.erros + '</div><div class="cr-rot">❌ erros</div></div>' +
      '<div class="card-resumo cr-prox"><div class="cr-num">' + pendentes + '</div><div class="cr-rot">⏳ aguardando</div></div>';
    if (!itens.length) {
      cont.innerHTML = '<div class="vazio">Você ainda não fez análises. Analise um jogo na Agenda e volte aqui depois que ele terminar! 📈</div>';
      return;
    }
    cont.innerHTML = "";
    itens.forEach((it) => cont.appendChild(cardPlacar(it)));
  } catch (err) { cont.innerHTML = '<div class="vazio">Erro: ' + err.message + "</div>"; }
}
function palpitePlacar(it) {
  // Converte Casa/Fora/Empate no NOME do time (ou "Empate")
  const p = (it.prognostico || "").toString().trim().toLowerCase();
  if (p === "casa") return it.home || "Casa";
  if (p === "fora") return it.away || "Fora";
  if (p === "empate") return "Empate";
  return it.prognostico || "—";
}
function cardPlacar(it) {
  const div = document.createElement("div");
  div.className = "cartao-jogo";
  const M = { acerto: ["✅ Acertou", "var(--verde)"], erro: ["❌ Errou", "var(--vermelho)"],
              pendente: ["⏳ Aguardando o jogo", "var(--texto-fraco)"], encerrado: ["✔️ Encerrado", "var(--texto-fraco)"] };
  const m = M[it.situacao] || M.pendente;
  div.innerHTML =
    '<div class="cj-liga"><span>' + esc(nomeLiga(it.league || "")) + '</span><span class="pais">' + esc(it.country_pt || "") + "</span></div>" +
    '<div class="cj-times"><div class="cj-time"><span>' + esc(it.home) + '</span></div><span class="cj-vs">VS</span><div class="cj-time fora"><span>' + esc(it.away) + "</span></div></div>" +
    '<div class="cj-rodape"><span>Palpite: <b>' + esc(palpitePlacar(it)) + "</b>" + (it.placar ? ' · Real: <b>' + esc(it.placar) + "</b>" : "") + "</span>" +
      '<span style="color:' + m[1] + ';font-weight:700">' + m[0] + "</span></div>";
  return div;
}

// ===================== Chat ao vivo =====================
function iniciarChat() {
  pararChat();
  CHAT_ULTIMO = 0; CHAT_IDS = new Set(); CHAT_ADMIN_CARREGADO = false;
  $("#chat-mensagens").innerHTML = '<div class="vazio">Carregando o chat…</div>';
  pollChat();
  timerChat = setInterval(pollChat, 4500);   // atualiza o chat a cada 4,5s
}
function pararChat() {
  if (timerChat) { clearInterval(timerChat); timerChat = null; }
}
async function pollChat() {
  try {
    const d = await api("/api/chat?desde=" + CHAT_ULTIMO);
    CHAT_EU = d.eu || null;
    aplicarChatUI(d);
    if (!d.acesso) return;
    const cont = $("#chat-mensagens");
    const ph = cont.querySelector(".vazio"); if (ph) ph.remove();
    // remove da tela as mensagens ocultadas por denúncia
    (d.ocultos || []).forEach((id) => {
      const el = document.getElementById("msg-" + id);
      if (el) el.remove();
      CHAT_IDS.delete(id);
    });
    const perto = (cont.scrollHeight - cont.scrollTop - cont.clientHeight) < 90;
    (d.mensagens || []).forEach((m) => {
      if (CHAT_IDS.has(m.id)) return;
      CHAT_IDS.add(m.id);
      cont.appendChild(msgChatEl(m));
    });
    if (typeof d.ultimo_id === "number" && d.ultimo_id > CHAT_ULTIMO) CHAT_ULTIMO = d.ultimo_id;
    if (!cont.children.length) {
      cont.innerHTML = '<div class="vazio">Ninguém falou ainda. Comece a conversa sobre os jogos! ⚽</div>';
    } else if (perto) {
      cont.scrollTop = cont.scrollHeight;
    }
  } catch (e) { /* silencioso — tenta de novo no próximo ciclo */ }
}
function aplicarChatUI(d) {
  const eu = d.eu || {};
  const admin = !!eu.admin;
  $("#chat-admin").classList.toggle("hidden", !admin);
  if (admin && !CHAT_ADMIN_CARREGADO) { CHAT_ADMIN_CARREGADO = true; carregarChatUsuarios(); }
  const bloqueado = !d.acesso;
  $("#chat-bloqueado").classList.toggle("hidden", !bloqueado);
  $("#chat-area").classList.toggle("hidden", bloqueado);
  if (bloqueado) return;
  const suspenso = !!eu.suspenso;
  $("#chat-suspenso").classList.toggle("hidden", !suspenso);
  const inp = $("#chat-input");
  const btn = $("#chat-form").querySelector("button");
  inp.disabled = suspenso; btn.disabled = suspenso;
  inp.placeholder = suspenso ? "Conta suspensa — somente leitura" : "Escreva sobre os jogos…";
}
function msgChatEl(m) {
  const div = document.createElement("div");
  const meu = CHAT_EU && m.usuario === CHAT_EU.usuario;
  div.className = "chat-msg" + (meu ? " meu" : "") + (m.role === "admin" ? " de-admin" : "");
  div.id = "msg-" + m.id;
  const tag = m.role === "admin" ? '<span class="chat-tag-admin">👑 ADMIN</span>' : "";
  const den = (!meu && CHAT_EU) ? '<button class="chat-denuncia" data-id="' + m.id + '" title="Denunciar mensagem imprópria">🚩</button>' : "";
  div.innerHTML =
    '<div class="chat-cab">' +
      '<span class="chat-nome">' + esc(m.nome) + "</span>" + tag +
      '<span class="chat-hora">' + esc(m.hora) + "</span>" + den +
    "</div>" +
    '<div class="chat-texto">' + esc(m.texto) + "</div>";
  return div;
}
async function carregarChatUsuarios() {
  const cont = $("#chat-admin-lista");
  try {
    const d = await api("/api/chat/usuarios");
    const us = d.usuarios || [];
    if (!us.length) {
      cont.innerHTML = '<div class="chat-admin-vazio">Nenhum cliente cadastrado ainda. Quando alguém criar conta, aparece aqui para você liberar o VIP.</div>';
      return;
    }
    cont.innerHTML = us.map(adminLinhaUsuario).join("");
  } catch (err) {
    cont.innerHTML = '<div class="chat-admin-vazio">Erro ao carregar: ' + esc(err.message) + "</div>";
  }
}
function adminLinhaUsuario(u) {
  const strikes = u.strikes ? '<span class="cai-strikes">⚠️ ' + u.strikes + " denúncia(s)</span>" : "";
  return '<div class="chat-admin-item">' +
    '<div class="cai-info"><b>' + esc(u.nome) + "</b>" +
      '<span class="cai-email">' + esc(u.email) + "</span>" + strikes + "</div>" +
    '<div class="cai-acoes">' +
      '<button class="btn-mini ' + (u.vip ? "ativo" : "") + '" data-acao="vip" data-email="' + esc(u.email) +
        '" data-val="' + (u.vip ? "0" : "1") + '">' + (u.vip ? "⭐ VIP (remover)" : "Tornar VIP") + "</button>" +
      '<button class="btn-mini ' + (u.suspenso ? "perigo" : "") + '" data-acao="susp" data-email="' + esc(u.email) +
        '" data-val="' + (u.suspenso ? "0" : "1") + '">' + (u.suspenso ? "🚫 Reativar" : "Suspender") + "</button>" +
    "</div></div>";
}
$("#chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const inp = $("#chat-input");
  const txt = inp.value.trim();
  if (!txt) return;
  inp.value = "";
  try {
    await api("/api/chat/enviar", { method: "POST", body: JSON.stringify({ texto: txt }) });
    pollChat();
  } catch (err) { toast("⚠️ " + err.message); inp.value = txt; }
});
$("#chat-mensagens").addEventListener("click", async (e) => {
  const b = e.target.closest(".chat-denuncia");
  if (!b) return;
  const id = parseInt(b.dataset.id);
  if (!confirm("Denunciar esta mensagem por conteúdo impróprio?\n\nApós 3 denúncias a mensagem é removida automaticamente.")) return;
  try {
    const r = await api("/api/chat/denunciar", { method: "POST", body: JSON.stringify({ id }) });
    toast(r.removida ? "🚩 Mensagem denunciada e removida. Obrigado!" : "🚩 Denúncia registrada. Obrigado por ajudar!");
    pollChat();
  } catch (err) { toast("⚠️ " + err.message); }
});
$("#chat-admin-lista").addEventListener("click", async (e) => {
  const b = e.target.closest("button[data-acao]");
  if (!b) return;
  const corpo = { email: b.dataset.email };
  if (b.dataset.acao === "vip") corpo.vip = b.dataset.val === "1";
  if (b.dataset.acao === "susp") corpo.suspenso = b.dataset.val === "1";
  try {
    await api("/api/chat/usuario", { method: "POST", body: JSON.stringify(corpo) });
    toast("✅ Atualizado!");
    carregarChatUsuarios();
  } catch (err) { toast("⚠️ " + err.message); }
});
$("#btn-admin-recarregar").addEventListener("click", carregarChatUsuarios);
$("#btn-chat-limpar").addEventListener("click", async () => {
  if (!confirm("Apagar TODO o histórico do chat? Isso não tem volta.")) return;
  try {
    await api("/api/chat/limpar", { method: "POST", body: JSON.stringify({}) });
    CHAT_ULTIMO = 0; CHAT_IDS = new Set();
    $("#chat-mensagens").innerHTML = '<div class="vazio">Chat limpo. 🧹</div>';
    toast("🗑️ Histórico do chat apagado.");
  } catch (err) { toast("⚠️ " + err.message); }
});

// ===================== Placar da Comunidade =====================
const COM_LIVE = ["1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"];
const COM_FIN = ["FT", "AET", "PEN"];
const COM_ADIA = ["PST", "SUSP", "TBD"];
const COM_CANC = ["CANC", "ABD", "AWD", "WO"];

function comComecou(j) {
  if (COM_LIVE.includes(j.short) || COM_FIN.includes(j.short)) return true;
  if (!j.data || !j.time) return false;
  return new Date(j.data + "T" + j.time + ":00") <= new Date();
}
function comAberto(j) {
  return !comComecou(j) && !COM_CANC.includes(j.short) && !COM_ADIA.includes(j.short);
}
function comAvatar(nome) {
  const ini = (nome || "?").trim().charAt(0).toUpperCase() || "?";
  return '<span class="com-avatar">' + esc(ini) + "</span>";
}
function comBadge(b, mini) {
  if (!b) return "";
  return '<span class="com-badge com-cor-' + esc(b.cor) + (mini ? " mini" : "") +
    '" title="' + esc(b.descricao || "") + '">' + b.icone + " " + esc(b.nome) + "</span>";
}
function comResultadoChip(p) {
  const M = { correct: ["✅ +10 XP", "verde"], wrong: ["❌ -2 XP", "vermelho"],
    pending: ["⏳ Pendente", "fraco"], locked: ["🔒 Bloqueado", "fraco"],
    cancelled: ["✖️ Cancelado", "fraco"], postponed: ["⏸️ Adiado", "fraco"] };
  const m = M[p.status] || M.pending;
  return '<span class="com-chip com-chip-' + m[1] + '">' + m[0] + "</span>";
}

function iniciarComunidade() {
  const adminTab = document.querySelector(".com-so-admin");
  if (adminTab) adminTab.classList.toggle("hidden", ehCliente());
  carregarComXP();
  comSubtab(COM_SUBTAB || "palpitar");
}
function comSubtab(nome) {
  COM_SUBTAB = nome;
  document.querySelectorAll(".com-subtab").forEach((b) => b.classList.toggle("ativa", b.dataset.subtab === nome));
  ["palpitar", "ranking", "desempenho", "admin"].forEach((p) =>
    $("#com-pane-" + p).classList.toggle("hidden", p !== nome));
  if (nome === "palpitar") carregarComJogos();
  if (nome === "ranking") carregarComRanking();
  if (nome === "desempenho") carregarComDesempenho();
  if (nome === "admin") { carregarComAdminUsuarios(); carregarComAdminPalpites(); }
}

// ---- Card de XP do usuário ----
async function carregarComXP() {
  try {
    const d = await api("/api/comunidade/eu");
    renderComXP(d);
    const ant = localStorage.getItem("com_xp");
    if (ant !== null && ant !== "" && d.xp > parseInt(ant)) {
      toast("🎉 Você ganhou " + (d.xp - parseInt(ant)) + " XP! Mandou bem!");
      const c = $("#com-xpcard"); c.classList.add("pulsar"); setTimeout(() => c.classList.remove("pulsar"), 1300);
    }
    localStorage.setItem("com_xp", d.xp);
  } catch (e) {
    $("#com-xpcard").innerHTML = '<div class="vazio">Erro ao carregar perfil: ' + esc(e.message) + "</div>";
  }
}
function renderComXP(d) {
  const b = d.badge || {};
  const posTxt = d.pos ? ("#" + d.pos + " no ranking geral") : "Sem ranking ainda — faça seu 1º palpite!";
  let barra = "";
  if (d.proxima && d.proxima.faltam && d.proxima.faixa)
    barra = '<div class="com-prox">Faltam <b>' + d.proxima.faltam + " XP</b> para <b>" + esc(d.proxima.faixa) + "</b> 🚀</div>";
  else if (d.pos && d.pos <= 3)
    barra = '<div class="com-prox">🏅 Você está no topo da comunidade!</div>';
  $("#com-xpcard").innerHTML =
    '<div class="com-xp-esq">' + comAvatar(d.nome) +
      '<div class="com-xp-id"><div class="com-xp-nome">' + esc(d.nome) + "</div>" + comBadge(b) + "</div></div>" +
    '<div class="com-xp-mid"><div class="com-xp-num">' + d.xp + " <span>XP</span></div>" +
      '<div class="com-xp-pos">' + esc(posTxt) + "</div>" + barra + "</div>" +
    '<div class="com-xp-dir">' +
      '<div class="com-mini"><b>' + d.palpites + "</b><span>palpites</span></div>" +
      '<div class="com-mini"><b>' + d.acertos + "</b><span>acertos</span></div>" +
      '<div class="com-mini"><b>' + d.taxa + "%</b><span>de acerto</span></div></div>";
}

// ---- Palpitar ----
async function carregarComJogos() {
  const cont = $("#com-jogos");
  cont.innerHTML = '<div class="vazio">Carregando jogos…</div>';
  try {
    const d = await api("/api/comunidade/jogos");
    COM_JOGOS = d.jogos || [];
    const sel = $("#com-filtro-liga"), atual = sel.value;
    const ligas = [...new Set(COM_JOGOS.map((j) => j.league).filter(Boolean))].sort();
    sel.innerHTML = '<option value="">Todas as competições</option>' +
      ligas.map((l) => '<option value="' + esc(l) + '">' + esc(nomeLiga(l)) + "</option>").join("");
    sel.value = atual;
    renderComJogos();
  } catch (e) { cont.innerHTML = '<div class="vazio">Erro: ' + esc(e.message) + "</div>"; }
}
function renderComJogos() {
  const cont = $("#com-jogos");
  const liga = $("#com-filtro-liga").value, status = $("#com-filtro-status").value;
  let js = COM_JOGOS.slice();
  if (liga) js = js.filter((j) => j.league === liga);
  js = js.filter((j) => {
    if (status === "todos") return true;
    if (status === "abertos") return comAberto(j);
    if (status === "andamento") return COM_LIVE.includes(j.short);
    if (status === "finalizados") return COM_FIN.includes(j.short) || COM_CANC.includes(j.short) || COM_ADIA.includes(j.short);
    return true;
  });
  js.sort((a, b) => ((a.data || "") + (a.time || "")).localeCompare((b.data || "") + (b.time || "")));
  if (!js.length) { cont.innerHTML = '<div class="vazio">Nenhum jogo nesse filtro. Tente "Todos os jogos".</div>'; return; }
  cont.innerHTML = ""; js.forEach((j) => cont.appendChild(comCardJogo(j)));
}
function comCardJogo(j) {
  const meu = j.meu;
  const aberto = comAberto(j);
  const div = document.createElement("div");
  div.className = "com-card" + (COM_LIVE.includes(j.short) ? " live" : "");
  const escudo = (u) => u ? '<img class="com-escudo" loading="lazy" src="' + esc(u) + '" onerror="this.style.visibility=\'hidden\'"/>' : "";
  let chip;
  if (meu && ["correct", "wrong", "cancelled", "postponed"].includes(meu.status)) chip = comResultadoChip(meu);
  else if (aberto) chip = '<span class="com-chip com-chip-verde">🟢 Aberto p/ palpite</span>';
  else if (COM_LIVE.includes(j.short)) chip = '<span class="com-chip com-chip-vermelho">🔴 Ao vivo</span>';
  else if (COM_ADIA.includes(j.short)) chip = '<span class="com-chip com-chip-fraco">⏸️ Adiado</span>';
  else if (COM_CANC.includes(j.short)) chip = '<span class="com-chip com-chip-fraco">✖️ Cancelado</span>';
  else if (COM_FIN.includes(j.short)) chip = '<span class="com-chip com-chip-fraco">✅ Finalizado</span>';
  else chip = '<span class="com-chip com-chip-fraco">🔒 Encerrado p/ palpite</span>';
  let corpo;
  if (aberto) {
    const ph = (meu && meu.ph != null) ? meu.ph : "", pa = (meu && meu.pa != null) ? meu.pa : "";
    corpo = '<div class="com-palpite-form">' +
      '<input type="number" class="com-in-h" min="0" max="20" value="' + ph + '" inputmode="numeric" />' +
      '<span class="com-vs2">VS</span>' +
      '<input type="number" class="com-in-a" min="0" max="20" value="' + pa + '" inputmode="numeric" />' +
      '<button class="btn-primario com-enviar">' + (meu ? "Editar palpite" : "Enviar palpite") + "</button></div>";
  } else if (meu) {
    corpo = '<div class="com-palpite-feito">Seu palpite: <b>' + meu.ph + " x " + meu.pa + "</b>" +
      (meu.placar_real ? ' · Resultado real: <b>' + esc(meu.placar_real) + "</b>" : "") + "</div>";
  } else {
    corpo = '<div class="com-palpite-feito fraco">Os palpites para este jogo foram encerrados.</div>';
  }
  div.innerHTML =
    '<div class="com-card-top"><span class="com-card-liga">' + esc(nomeLiga(j.league || "")) +
      (j.country_pt ? " · " + esc(j.country_pt) : "") + "</span>" + chip + "</div>" +
    '<div class="com-card-times">' +
      '<span class="com-time">' + escudo(j.home_logo) + "<span>" + esc(j.home) + "</span></span>" +
      '<span class="com-vs2">VS</span>' +
      '<span class="com-time fora"><span>' + esc(j.away) + "</span>" + escudo(j.away_logo) + "</span></div>" +
    '<div class="com-card-quando">🕒 ' + esc(j.data ? formatarData(j.data).slice(0, 5) : "") + " " + esc(j.time || "") +
      (j.score ? ' · placar: <b>' + esc(j.score) + "</b>" : "") + "</div>" + corpo;
  if (aberto) {
    div.querySelector(".com-enviar").addEventListener("click", () => {
      enviarPalpite(j, div.querySelector(".com-in-h").value, div.querySelector(".com-in-a").value, div);
    });
  }
  return div;
}
async function enviarPalpite(j, ph, pa, div) {
  if (ph === "" || pa === "") { toast("Informe o placar dos dois times."); return; }
  const btn = div.querySelector(".com-enviar"); if (btn) btn.disabled = true;
  try {
    const r = await api("/api/comunidade/palpitar", { method: "POST",
      body: JSON.stringify({ jogo: j, ph: parseInt(ph), pa: parseInt(pa) }) });
    j.meu = r.palpite;
    toast("✅ Palpite registrado: " + j.home + " " + parseInt(ph) + " x " + parseInt(pa) + " " + j.away);
    renderComJogos();
  } catch (e) { toast("⚠️ " + e.message); if (btn) btn.disabled = false; }
}

// ---- Ranking ----
async function carregarComRanking() {
  const cont = $("#com-ranking-tabela"), pod = $("#com-podio");
  cont.innerHTML = '<div class="vazio">Carregando ranking…</div>'; pod.innerHTML = "";
  try {
    const d = await api("/api/comunidade/ranking?faixa=" + COM_FAIXA);
    const r = d.ranking || [];
    if (!r.length) { cont.innerHTML = '<div class="vazio">Ninguém pontuou ainda por aqui. Seja o primeiro! 🏆</div>'; return; }
    if (["geral", "top3", "top10"].includes(COM_FAIXA)) pod.innerHTML = comPodio(r.slice(0, 3), d.eu);
    cont.innerHTML = comTabelaRanking(r, d.eu);
  } catch (e) { cont.innerHTML = '<div class="vazio">Erro: ' + esc(e.message) + "</div>"; }
}
function comPodio(top, eu) {
  const ordem = [top[1], top[0], top[2]].filter(Boolean);
  return '<div class="podio-wrap">' + ordem.map((d) =>
    '<div class="podio-col lugar-' + d.pos + (d.usuario === eu ? " eu" : "") + '">' +
      '<div class="podio-medalha">' + (d.pos === 1 ? "🥇" : d.pos === 2 ? "🥈" : "🥉") + "</div>" +
      comAvatar(d.nome) + '<div class="podio-nome">' + esc(d.nome) + "</div>" + comBadge(d.badge, true) +
      '<div class="podio-xp">' + d.xp + ' XP</div><div class="podio-base">' + d.pos + "º</div></div>").join("") + "</div>";
}
function comTabelaRanking(r, eu) {
  let h = '<table class="com-rank"><thead><tr><th>#</th><th class="esq">Usuário</th><th>XP</th>' +
    "<th>Palp.</th><th>✅</th><th>❌</th><th>%</th></tr></thead><tbody>";
  r.forEach((d) => {
    h += '<tr class="' + (d.usuario === eu ? "eu" : "") + '"><td class="pos">' + d.pos + "</td>" +
      '<td class="usr">' + comAvatar(d.nome) + '<span class="urn">' + esc(d.nome) + "</span>" + comBadge(d.badge, true) + "</td>" +
      '<td class="xp">' + d.xp + "</td><td>" + d.palpites + "</td><td>" + d.acertos + "</td><td>" + d.erros + "</td><td>" + d.taxa + "%</td></tr>";
  });
  return h + "</tbody></table>";
}

// ---- Meu desempenho ----
async function carregarComDesempenho() {
  const cont = $("#com-desempenho");
  cont.innerHTML = '<div class="vazio">Carregando…</div>';
  try { cont.innerHTML = comDesempenhoHTML(await api("/api/comunidade/eu")); }
  catch (e) { cont.innerHTML = '<div class="vazio">Erro: ' + esc(e.message) + "</div>"; }
}
function comStat(v, r) { return '<div class="com-stat"><b>' + v + "</b><span>" + r + "</span></div>"; }
function comDesempenhoHTML(d) {
  const ev = d.evolucao || [];
  const max = Math.max(1, ...ev);
  const spark = ev.length
    ? '<div class="com-spark">' + ev.map((v) => '<span style="height:' + Math.round(6 + (v / max) * 54) + 'px" title="' + v + ' XP"></span>').join("") + "</div>"
    : '<div class="aviso-pequeno">Sem evolução ainda — faça palpites e veja seu XP subir! 📈</div>';
  const hist = (d.historico || []).map(comHistItem).join("") || '<div class="vazio">Você ainda não fez palpites.</div>';
  const prox = (d.proxima && d.proxima.faltam && d.proxima.faixa)
    ? ("Faltam <b>" + d.proxima.faltam + " XP</b> para <b>" + esc(d.proxima.faixa) + "</b> 🚀")
    : (d.pos && d.pos <= 3 ? "🏅 Você está no topo da comunidade!" : "Continue palpitando para entrar no ranking.");
  return '<div class="com-des-top">' + comBadge(d.badge) +
      '<div class="com-des-stats">' + comStat(d.xp, "XP total") + comStat(d.pos ? ("#" + d.pos) : "—", "Posição") +
        comStat(d.palpites, "Palpites") + comStat(d.acertos, "Acertos") + comStat(d.erros, "Erros") + comStat(d.taxa + "%", "Taxa") +
      "</div></div>" +
    '<div class="com-prox grande">' + prox + "</div>" +
    '<h4 class="com-h4">📈 Evolução de XP</h4>' + spark +
    '<h4 class="com-h4">🕘 Últimos palpites</h4><div class="com-hist">' + hist + "</div>";
}
function comHistItem(p) {
  return '<div class="com-hist-item"><div class="chi-jogo">' + esc(p.home) + ' <i>' + p.ph + "x" + p.pa + "</i> " + esc(p.away) +
    (p.placar_real ? ' · <span class="chi-real">real ' + esc(p.placar_real) + "</span>" : "") + "</div>" +
    '<div class="chi-meta"><span>' + esc(nomeLiga(p.league || "")) + " · " + esc(p.data ? formatarData(p.data).slice(0, 5) : "") + "</span>" +
    comResultadoChip(p) + "</div></div>";
}

// ---- Admin ----
async function carregarComAdminUsuarios() {
  const cont = $("#com-admin-usuarios");
  try {
    const d = await api("/api/comunidade/admin/usuarios");
    const us = d.usuarios || [];
    if (!us.length) { cont.innerHTML = '<div class="chat-admin-vazio">Nenhum participante ainda.</div>'; return; }
    cont.innerHTML = us.map((u) =>
      '<div class="com-adm-item"><div class="cai-info"><b>' + esc(u.nome) + "</b>" +
        '<span class="cai-email">' + esc(u.usuario) + "</span></div>" +
      '<div class="com-adm-num">' + (u.pos ? "#" + u.pos : "—") + " · " + u.xp + " XP · " + u.acertos + "✅ " + u.erros + "❌" +
        (u.bloqueado ? ' · <span class="com-bloq">BLOQUEADO</span>' : "") + "</div></div>").join("");
  } catch (e) { cont.innerHTML = '<div class="chat-admin-vazio">Erro: ' + esc(e.message) + "</div>"; }
}
async function carregarComAdminPalpites() {
  const cont = $("#com-admin-palpites");
  const f = $("#com-admin-busca-palpite").value.trim();
  try {
    const d = await api("/api/comunidade/admin/palpites" + (f ? ("?q=" + encodeURIComponent(f)) : ""));
    const ps = d.palpites || [];
    if (!ps.length) { cont.innerHTML = '<div class="chat-admin-vazio">Nenhum palpite.</div>'; return; }
    cont.innerHTML = ps.slice(0, 100).map((p) =>
      '<div class="com-adm-item"><div class="cai-info"><b>' + esc(p.home) + " " + p.ph + "x" + p.pa + " " + esc(p.away) + "</b>" +
        '<span class="cai-email">' + esc(p.nome) + ' · chave: <code>' + esc(p.jogo) + "</code></span></div>" +
      comResultadoChip(p) + "</div>").join("");
  } catch (e) { cont.innerHTML = '<div class="chat-admin-vazio">Erro: ' + esc(e.message) + "</div>"; }
}
async function comAdminResultado(marcar) {
  const chave = $("#com-adm-chave").value.trim();
  if (!chave) { toast("Cole a chave do jogo."); return; }
  const body = { chave: chave, marcar: marcar };
  if (!marcar) { body.home_score = $("#com-adm-h").value; body.away_score = $("#com-adm-a").value; }
  try {
    const r = await api("/api/comunidade/admin/resultado", { method: "POST", body: JSON.stringify(body) });
    toast("✅ Registrado. " + r.processados + " palpite(s) processados.");
    carregarComAdminPalpites(); carregarComAdminUsuarios();
  } catch (e) { toast("⚠️ " + e.message); }
}
async function comAdminBloquear(b) {
  const usuario = $("#com-adm-usuario").value.trim();
  if (!usuario) { toast("Informe o e-mail do usuário."); return; }
  try {
    await api("/api/comunidade/admin/bloquear", { method: "POST", body: JSON.stringify({ usuario: usuario, bloquear: b }) });
    toast(b ? "🚫 Usuário bloqueado." : "✅ Usuário desbloqueado.");
    carregarComAdminUsuarios();
  } catch (e) { toast("⚠️ " + e.message); }
}
async function comExportar(tipo) {
  try {
    const d = await api("/api/comunidade/admin/exportar?tipo=" + tipo);
    const blob = new Blob([d.csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "comunidade_" + tipo + ".csv"; a.click();
    URL.revokeObjectURL(url);
    toast("⬇️ CSV gerado.");
  } catch (e) { toast("⚠️ " + e.message); }
}

// listeners do módulo (anexados uma vez no carregamento)
document.querySelectorAll(".com-subtab").forEach((b) => b.addEventListener("click", () => comSubtab(b.dataset.subtab)));
document.querySelectorAll(".com-faixa").forEach((b) => b.addEventListener("click", () => {
  COM_FAIXA = b.dataset.faixa;
  document.querySelectorAll(".com-faixa").forEach((x) => x.classList.toggle("ativa", x === b));
  carregarComRanking();
}));
$("#com-filtro-liga").addEventListener("change", renderComJogos);
$("#com-filtro-status").addEventListener("change", renderComJogos);
$("#com-atualizar").addEventListener("click", () => { carregarComJogos(); carregarComXP(); });
$("#com-admin-reprocessar").addEventListener("click", async () => {
  try {
    const r = await api("/api/comunidade/admin/reprocessar", { method: "POST", body: JSON.stringify({}) });
    toast("🔄 Reprocessado: " + r.processados + " palpite(s).");
    carregarComAdminPalpites(); carregarComAdminUsuarios();
  } catch (e) { toast("⚠️ " + e.message); }
});
$("#com-adm-resultado").addEventListener("click", () => comAdminResultado(""));
$("#com-adm-adiar").addEventListener("click", () => comAdminResultado("postponed"));
$("#com-adm-cancelar").addEventListener("click", () => comAdminResultado("cancelled"));
$("#com-adm-ajustar").addEventListener("click", async () => {
  const usuario = $("#com-adm-usuario").value.trim(), amount = $("#com-adm-xp").value, motivo = $("#com-adm-motivo").value.trim();
  if (!usuario || amount === "") { toast("Informe usuário e XP."); return; }
  try {
    await api("/api/comunidade/admin/ajustar-xp", { method: "POST", body: JSON.stringify({ usuario: usuario, amount: parseInt(amount), motivo: motivo }) });
    toast("✅ XP ajustado."); carregarComAdminUsuarios();
  } catch (e) { toast("⚠️ " + e.message); }
});
$("#com-adm-bloquear").addEventListener("click", () => comAdminBloquear(true));
$("#com-adm-desbloquear").addEventListener("click", () => comAdminBloquear(false));
$("#com-admin-busca-palpite").addEventListener("input", () => { clearTimeout(window._cbp); window._cbp = setTimeout(carregarComAdminPalpites, 300); });
$("#com-admin-exp-ranking").addEventListener("click", () => comExportar("ranking"));
$("#com-admin-exp-palpites").addEventListener("click", () => comExportar("palpites"));

// ===================== Conta =====================
async function carregarConta() {
  try {
    const d = await api("/api/conta");
    $("#conta-nome").textContent = d.nome || d.usuario || "—";
    $("#conta-email").textContent = d.email || "";
    $("#conta-avatar").textContent = ((d.nome || "?").trim().charAt(0) || "?").toUpperCase();
    let badge;
    if (d.admin) badge = '<span class="conta-tag tag-admin">👑 Administrador</span>';
    else if (d.vip) badge = '<span class="conta-tag tag-vip"><span class="unl-inf">∞</span> UNLIMITED · VIP</span>';
    else badge = '<span class="conta-tag tag-free">🎟️ Plano grátis</span>';
    $("#conta-badge").innerHTML = badge;
    $("#conta-vip").innerHTML = renderContaVip(d);
    $("#conta-senha-card").classList.toggle("hidden", !d.pode_trocar_senha);
    $("#conta-senha-msg").textContent = "";
    carregarPagamentos(d);
  } catch (e) {
    $("#conta-vip").innerHTML = '<div class="vazio">Erro: ' + esc(e.message) + "</div>";
  }
}
function renderContaVip(d) {
  if (d.admin) {
    return '<h3>👑 Acesso de administrador</h3>' +
      '<p class="aviso-pequeno">Você tem acesso <b>total</b> ao sistema: análises ilimitadas, chat e o painel de administração.</p>';
  }
  if (d.vip) {
    const total = d.vip_dias_total || 30;
    const rest = (d.vip_dias_restantes == null) ? total : d.vip_dias_restantes;
    const pct = Math.max(0, Math.min(100, Math.round(rest / total * 100)));
    const baixo = rest <= 5 ? " vip-bar-fill-baixo" : "";
    const fim = d.vip_ate_data ? (' · vence em <b>' + esc(d.vip_ate_data) + '</b>') : '';
    return '<h3>⭐ Você é VIP — análises <b>ILIMITADAS</b></h3>' +
      '<p class="aviso-pequeno">Seu VIP dura <b>' + total + ' dias</b>' + fim +
        '. Quando a barra zerar, é só renovar com o suporte. 🚀</p>' +
      '<div class="vip-bar"><div class="vip-bar-fill' + baixo + '" style="width:' + pct + '%"></div></div>' +
      '<div class="vip-dias"><b>' + rest + '</b> de ' + total + ' dias restantes</div>' +
      (rest <= 5 ? '<a class="btn-wpp" style="margin-top:12px" target="_blank" rel="noopener" href="https://wa.me/5582920012133?text=Ola%2C%20quero%20renovar%20meu%20VIP%20no%20ScopeMind%20AI.">💬 Renovar VIP</a>' : '');
  }
  const rest = (d.analises_restantes == null) ? "" : (' Você tem <b>' + d.analises_restantes + '</b> análise(s) grátis restantes.');
  return '<h3>🎟️ Plano grátis</h3>' +
    '<p class="aviso-pequeno">Você ainda não é VIP.' + rest +
      ' Vire <b>VIP</b> para ter análises <b>ilimitadas</b> e acesso ao <b>Chat ao vivo</b>.</p>' +
    '<button class="btn-primario" onclick="irParaPagamento()">⭐ Ativar VIP agora</button>';
}

// ===================== Pagamentos e Assinatura VIP =====================
let PAG_ID = null, PAG_POLL = null, PAG_POLL_N = 0;
function reais(v) { return (Math.round((+v || 0) * 100) / 100).toFixed(2).replace(".", ","); }

function irParaPagamento() {
  const mi = document.querySelector('.menu-item[data-secao="conta"]');
  if (mi) mi.click();
  setTimeout(() => {
    const c = $("#pagamento-card");
    if (c) { c.classList.remove("hidden"); c.scrollIntoView({ behavior: "smooth", block: "start" }); }
  }, 450);
}
function mostrarOfertaVip(msg) {
  if (typeof toast === "function") toast(msg || "Suas rodadas gratuitas acabaram. Ative o VIP para acesso ilimitado.");
  irParaPagamento();
}

async function carregarPagamentos(conta) {
  const card = $("#pagamento-card"), admCard = $("#pag-admin-card");
  if (!card) return;
  if (conta && conta.admin) {            // admin vê o painel de pagamentos
    card.classList.add("hidden");
    if (admCard) { admCard.classList.remove("hidden"); carregarPagAdmin(); }
    return;
  }
  if (admCard) admCard.classList.add("hidden");
  try {
    const d = await api("/api/mp/info");
    const p = d.plano || {};
    $("#pag-de").textContent = "R$ " + reais(p.preco_de || 99.9);
    $("#pag-por").textContent = "R$ " + reais(p.preco || 49.9);
    $("#pag-promo").textContent = p.promo || "";
    $("#pag-beneficios").innerHTML = (p.beneficios || []).map((b) => "<li>✅ " + esc(b) + "</li>").join("");
    renderPagStatus(d);
    card.classList.remove("hidden");
  } catch (e) { card.classList.add("hidden"); }
}

function renderPagStatus(d) {
  const st = $("#pag-status"), acoes = $("#pag-acoes");
  if (d.vip) {
    st.className = "pag-status ok";
    st.innerHTML = "⭐ <b>VIP ativo</b> — você já tem acesso ilimitado. Obrigado! 🚀";
    acoes.classList.add("hidden"); $("#pag-pix-area").classList.add("hidden");
    return;
  }
  if (!d.mp_ok) {
    st.className = "pag-status";
    st.innerHTML = "⚙️ O pagamento automático ainda está sendo configurado. Fale com o suporte para virar VIP.";
    acoes.classList.add("hidden");
    return;
  }
  acoes.classList.remove("hidden");
  const pg = d.pagamento;
  if (pg && pg.status === "pending") {
    st.className = "pag-status pend";
    st.innerHTML = "⏳ <b>Aguardando pagamento.</b> Assim que o Mercado Pago confirmar, seu VIP é liberado automaticamente.";
  } else if (pg && (pg.status === "rejected" || pg.status === "cancelled")) {
    st.className = "pag-status err";
    st.innerHTML = "❌ <b>Pagamento recusado.</b> Tente novamente ou use outra forma de pagamento.";
  } else {
    st.className = "pag-status";
    st.innerHTML = "🎟️ Você está no plano <b>grátis</b>. Ative o VIP para rodadas ilimitadas.";
  }
}

async function gerarPix() {
  const msg = $("#pag-msg"); msg.className = "pag-msg"; msg.textContent = "Abrindo o Pix no Mercado Pago…";
  $("#btn-pix").disabled = true;
  try {
    const r = await api("/api/mp/pix", { method: "POST", body: JSON.stringify({}) });
    if (r.checkout_url) { window.location.href = r.checkout_url; }
    else { msg.className = "pag-msg erro"; msg.textContent = "Não consegui abrir o Pix. Tente o cartão."; }
  } catch (e) { msg.className = "pag-msg erro"; msg.textContent = "⚠️ " + e.message; }
  $("#btn-pix").disabled = false;
}

async function pagarCartao() {
  const msg = $("#pag-msg"); msg.className = "pag-msg"; msg.textContent = "Abrindo o pagamento seguro do Mercado Pago…";
  $("#btn-cartao").disabled = true;
  try {
    const r = await api("/api/mp/cartao", { method: "POST", body: JSON.stringify({}) });
    if (r.checkout_url) { window.location.href = r.checkout_url; }
    else { msg.className = "pag-msg erro"; msg.textContent = "Não consegui abrir o checkout. Tente o Pix."; }
  } catch (e) { msg.className = "pag-msg erro"; msg.textContent = "⚠️ " + e.message; }
  $("#btn-cartao").disabled = false;
}

async function verificarPagamento(silencioso) {
  if (!PAG_ID) return;
  const msg = $("#pag-msg");
  if (!silencioso) { msg.className = "pag-msg"; msg.textContent = "Verificando seu pagamento…"; }
  try {
    const r = await api("/api/mp/verificar", { method: "POST", body: JSON.stringify({ id: PAG_ID }) });
    if (r.vip) {
      pararPollPix();
      msg.className = "pag-msg ok";
      msg.innerHTML = "✅ <b>Pagamento confirmado!</b> Seu plano VIP foi ativado com sucesso. Atualizando…";
      VIP = true; localStorage.setItem("vip", "1");
      setTimeout(() => location.reload(), 1600);
    } else if (r.status === "rejected" || r.status === "cancelled") {
      pararPollPix();
      msg.className = "pag-msg erro";
      msg.textContent = "❌ Não conseguimos confirmar seu pagamento. Verifique os dados ou tente outra forma.";
    } else if (!silencioso) {
      msg.className = "pag-msg pend";
      msg.textContent = "⏳ Seu pagamento ainda está pendente. Assim que o Mercado Pago confirmar, o VIP é liberado automaticamente.";
    }
  } catch (e) { if (!silencioso) { msg.className = "pag-msg erro"; msg.textContent = "⚠️ " + e.message; } }
}
function iniciarPollPix() { pararPollPix(); PAG_POLL_N = 0; PAG_POLL = setInterval(() => { PAG_POLL_N++; if (PAG_POLL_N > 50) { pararPollPix(); return; } verificarPagamento(true); }, 6000); }
function pararPollPix() { if (PAG_POLL) { clearInterval(PAG_POLL); PAG_POLL = null; } }

async function carregarPagAdmin() {
  const cont = $("#pag-admin-lista"); cont.innerHTML = '<div class="vazio">Carregando…</div>';
  try {
    const d = await api("/api/mp/admin/pagamentos");
    const ps = d.pagamentos || [];
    if (!ps.length) { cont.innerHTML = '<div class="vazio">Nenhum pagamento ainda.</div>'; return; }
    cont.innerHTML = '<table class="pag-tab"><thead><tr><th>Cliente</th><th>Valor</th><th>Forma</th><th>Status</th><th>Data</th><th>ID Mercado Pago</th></tr></thead><tbody>' +
      ps.map((p) => '<tr><td>' + esc(p.usuario || "") + '</td><td>R$ ' + reais(p.amount) + '</td><td>' + esc(p.payment_method || "") + '</td><td>' + pagStatusTxt(p.status, p.vip_liberado) + '</td><td>' + esc(p.paid_at || p.created_at || "") + '</td><td class="pag-mono">' + esc(p.provider_payment_id || "") + '</td></tr>').join("") +
      '</tbody></table>';
  } catch (e) { cont.innerHTML = '<div class="vazio">Erro: ' + esc(e.message) + "</div>"; }
}
function pagStatusTxt(s, lib) {
  if (s === "approved") return lib ? "✅ aprovado · VIP" : "✅ aprovado";
  if (s === "pending") return "⏳ pendente";
  if (s === "rejected") return "❌ recusado";
  if (s === "cancelled") return "🚫 cancelado";
  return s || "—";
}

if ($("#btn-pix")) $("#btn-pix").addEventListener("click", gerarPix);
if ($("#btn-cartao")) $("#btn-cartao").addEventListener("click", pagarCartao);
if ($("#btn-verificar")) $("#btn-verificar").addEventListener("click", () => verificarPagamento(false));
if ($("#btn-copiar-pix")) $("#btn-copiar-pix").addEventListener("click", () => {
  const t = $("#pag-pix-codigo"); t.select();
  try { navigator.clipboard.writeText(t.value); } catch (e) { try { document.execCommand("copy"); } catch (_) {} }
  const m = $("#pag-msg"); m.className = "pag-msg ok"; m.textContent = "📋 Código Pix copiado! Cole no app do seu banco.";
});
if ($("#btn-liberar-vip")) $("#btn-liberar-vip").addEventListener("click", async () => {
  const email = ($("#pag-admin-email").value || "").trim().toLowerCase();
  const m = $("#pag-admin-msg");
  if (!email) { m.className = "erro"; m.textContent = "Informe o e-mail do cliente."; return; }
  try {
    await api("/api/mp/admin/liberar", { method: "POST", body: JSON.stringify({ email }) });
    m.className = "ok"; m.textContent = "✅ VIP liberado para " + email;
    $("#pag-admin-email").value = ""; carregarPagAdmin();
  } catch (e) { m.className = "erro"; m.textContent = "⚠️ " + e.message; }
});
// Retorno do Checkout Pro (cartão): ?vip=ok/pendente/falhou
(function () {
  const v = new URLSearchParams(location.search).get("vip");
  if (!v) return;
  window.addEventListener("load", () => setTimeout(() => {
    if (typeof toast === "function") {
      if (v === "ok") toast("✅ Pagamento recebido! Seu VIP libera automaticamente. Veja em Conta > Pagamentos.");
      else if (v === "pendente") toast("⏳ Pagamento pendente. Assim que confirmar, o VIP é liberado.");
      else toast("❌ Pagamento não concluído. Você pode tentar de novo em Conta > Pagamentos.");
    }
    history.replaceState(null, "", location.pathname);
  }, 1200));
})();

$("#btn-trocar-senha").addEventListener("click", async () => {
  const atual = $("#conta-senha-atual").value, nova = $("#conta-senha-nova").value;
  const msg = $("#conta-senha-msg");
  msg.className = "ok"; msg.textContent = "";
  if (!nova || nova.length < 4) { msg.className = "erro"; msg.textContent = "A nova senha precisa ter ao menos 4 caracteres."; return; }
  try {
    await api("/api/trocar-senha", { method: "POST", body: JSON.stringify({ senha_atual: atual, nova_senha: nova }) });
    msg.className = "ok"; msg.textContent = "✅ Senha alterada com sucesso!";
    $("#conta-senha-atual").value = ""; $("#conta-senha-nova").value = "";
  } catch (e) { msg.className = "erro"; msg.textContent = "⚠️ " + e.message; }
});

// ===================== Painel visual de análise =====================
function paNum(x) { const n = parseInt(x, 10); return isNaN(n) ? 0 : Math.max(0, Math.min(100, n)); }
function paProbBar(nome, pct, cls) {
  return '<div class="pa-prob"><div class="pa-prob-top"><span class="pa-prob-nome">' + esc(nome) +
    '</span><span class="pa-prob-pct">' + pct + '%</span></div>' +
    '<div class="pa-prob-bar"><div class="pa-prob-fill pa-' + cls + '" style="width:' + pct + '%"></div></div></div>';
}
function paPlacar(placar, rotulo, motivo, principal) {
  return '<div class="pa-placar' + (principal ? ' principal' : '') + '">' +
    '<div class="pa-placar-rot">' + esc(rotulo || '') + '</div>' +
    '<div class="pa-placar-num">' + esc(placar || '—') + '</div>' +
    (motivo ? '<div class="pa-placar-mot">' + esc(motivo) + '</div>' : '') + '</div>';
}
function paScorer(a, pos) {
  const prob = paNum(a.prob_gol);
  const st = a.status || '';
  const stCls = /confirm/i.test(st) ? 'st-ok' : (/d[úu]vid/i.test(st) ? 'st-duvida' : 'st-prov');
  const stTag = st ? '<span class="pa-scorer-status ' + stCls + '">' + esc(st) + '</span>' : '';
  return '<div class="pa-scorer"><div class="pa-scorer-pos">' + pos + '</div>' +
    '<div class="pa-scorer-info">' +
      '<div class="pa-scorer-nome">' + esc(a.nome || '') + stTag + '</div>' +
      '<div class="pa-scorer-meta">' + esc(a.time || '') + (a.posicao ? ' · ' + esc(a.posicao) : '') + '</div>' +
      (a.motivo ? '<div class="pa-scorer-mot">' + esc(a.motivo) + '</div>' : '') +
      '<div class="pa-prob-bar mini"><div class="pa-prob-fill pa-gol" style="width:' + prob + '%"></div></div>' +
    '</div><div class="pa-scorer-pct">' + prob + '%</div></div>';
}
function paForcas(titulo, lista, cor) {
  if (!lista || !lista.length) return '';
  return '<div class="pa-card pa-forcas pa-forcas-' + cor + '"><div class="pa-card-titulo">' + esc(titulo) +
    '</div><ul>' + lista.map((x) => '<li>' + esc(x) + '</li>').join('') + '</ul></div>';
}
function paInd(rot, val) {
  if (val === null || val === undefined || val === '') return '';
  return '<div class="pa-ind-card"><div class="pa-ind-val">' + esc(String(val)) + '</div><div class="pa-ind-rot">' + esc(rot) + '</div></div>';
}
function renderPainelAnalise(p, info) {
  const home = info.home || '', away = info.away || '';
  const conf = p.confianca || 'Média';
  const confScore = paNum(p.confianca_score);
  const confCls = conf === 'Alta' ? 'pa-conf-alta' : (conf === 'Baixa' ? 'pa-conf-baixa' : 'pa-conf-media');
  const pc = paNum(p.prob_casa), pe = paNum(p.prob_empate), pf = paNum(p.prob_fora);
  const favProb = Math.max(pc, pe, pf);
  const favNome = p.favorito || (pc >= pe && pc >= pf ? home : (pf >= pe ? away : 'Empate'));
  let h = '<div class="pa">';
  h += '<div class="pa-conf ' + confCls + '"><div class="pa-conf-row"><span>Confiança da análise</span>' +
    '<span class="pa-conf-tag">' + esc(conf.toUpperCase()) + ' · ' + confScore + '/100</span></div>' +
    '<div class="pa-conf-bar"><div class="pa-conf-fill" style="width:' + confScore + '%"></div></div></div>';
  h += '<div class="pa-card"><div class="pa-card-titulo">📊 Probabilidades</div>' +
    paProbBar(home, pc, 'casa') + paProbBar('Empate', pe, 'empate') + paProbBar(away, pf, 'fora') + '</div>';
  h += '<div class="pa-card pa-destaque"><div class="pa-dest-rot">⭐ Cenário mais provável</div>' +
    '<div class="pa-dest-fav">' + esc(favNome) + '</div><div class="pa-dest-grid">' +
      '<div><div class="pa-dest-num">' + favProb + '%</div><div class="pa-dest-sub">probabilidade</div></div>' +
      '<div><div class="pa-dest-num">' + esc(p.placar_principal || '—') + '</div><div class="pa-dest-sub">placar mais provável</div></div>' +
    '</div></div>';
  if (p.placar_principal) {
    h += '<div class="pa-card"><div class="pa-card-titulo">🎯 Placar mais provável</div><div class="pa-placares">' +
      paPlacar(p.placar_principal, 'Principal', p.placar_principal_motivo, true) +
      (p.placares_alt || []).map((a) => paPlacar(a.placar, a.rotulo || 'Alternativo', a.motivo, false)).join('') +
      '</div></div>';
  }
  h += '<div class="pa-card"><div class="pa-card-titulo">⚽ Mais prováveis para marcar</div>';
  if ((p.artilheiros || []).length) {
    h += p.artilheiros.map((a, i) => paScorer(a, i + 1)).join('');
    if (p.artilheiros_aviso) h += '<div class="pa-aviso-dados">ℹ️ ' + esc(p.artilheiros_aviso) + '</div>';
  } else {
    h += '<div class="pa-aviso-dados">ℹ️ ' + esc(p.artilheiros_aviso || 'Dados insuficientes para apontar artilheiros com segurança.') + '</div>';
  }
  h += '</div>';
  if ((p.leitura || []).length) {
    h += '<div class="pa-card"><div class="pa-card-titulo">🧠 Como o jogo tende a acontecer</div><div class="pa-leitura">' +
      p.leitura.map((l) => '<div class="pa-leitura-item"><span class="pa-leitura-ic">' + esc(l.icone || '•') +
        '</span><span>' + esc(l.texto || '') + '</span></div>').join('') + '</div></div>';
  }
  h += '<div class="pa-cols">' + paForcas('🟢 Favorece ' + home, p.forcas_casa, 'verde') +
    paForcas('🔵 Favorece ' + away, p.forcas_fora, 'azul') + '</div>';
  if ((p.confianca_motivos || []).length) {
    h += paForcas('⚠️ Por que a confiança é ' + conf.toLowerCase(), p.confianca_motivos, 'amarelo');
  }
  const ind = p.indicadores || {};
  const indHtml = paInd('Tendência de gols', ind.gols) +
    paInd('Ambas marcam', (ind.ambas_marcam != null && ind.ambas_marcam !== '') ? (paNum(ind.ambas_marcam) + '%') : '') +
    paInd('Escanteios', ind.escanteios) + paInd('1º tempo', ind.primeiro_tempo) +
    paInd('Risco de zebra', ind.risco_zebra);
  if (indHtml) h += '<div class="pa-card"><div class="pa-card-titulo">⚡ Indicadores rápidos</div><div class="pa-ind">' + indHtml + '</div></div>';
  if (info.relatorio && info.relatorio.trim()) {
    h += '<div class="pa-detalhes"><button type="button" class="pa-ver-detalhes">📄 Ver análise completa</button>' +
      '<div class="pa-detalhes-corpo hidden">' + markdown(info.relatorio) + '</div></div>';
  }
  h += '</div>';
  return h;
}
$("#rel-corpo").addEventListener("click", (e) => {
  const b = e.target.closest(".pa-ver-detalhes");
  if (!b) return;
  const corpo = b.parentElement.querySelector(".pa-detalhes-corpo");
  if (!corpo) return;
  const agoraOculto = corpo.classList.toggle("hidden");
  b.textContent = agoraOculto ? "📄 Ver análise completa" : "📄 Ocultar análise completa";
});

// ===================== Mini Markdown =====================
function markdown(txt) {
  const linhas = esc(txt).split("\n");
  let html = "", emLista = false;
  const fechaLista = () => { if (emLista) { html += "</ul>"; emLista = false; } };
  for (let linha of linhas) {
    const l = linha.trim();
    if (l === "") { fechaLista(); continue; }
    let m;
    if ((m = l.match(/^##\s+(.*)/))) { fechaLista(); html += "<h2>" + inline(m[1]) + "</h2>"; }
    else if ((m = l.match(/^###\s+(.*)/))) { fechaLista(); html += "<h3>" + inline(m[1]) + "</h3>"; }
    else if ((m = l.match(/^[-*]\s+(.*)/))) {
      if (!emLista) { html += "<ul>"; emLista = true; }
      html += "<li>" + inline(m[1]) + "</li>";
    } else { fechaLista(); html += "<p>" + inline(l) + "</p>"; }
  }
  fechaLista();
  return html;
}
function inline(s) { return s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>"); }

// ===================== Configurações =====================
$("#btn-config").addEventListener("click", () => { $("#config-ok").textContent = ""; abrir("modal-config"); });
$("#btn-salvar-config").addEventListener("click", async () => {
  const corpo = { anthropic_model: $("#cfg-modelo").value, auto_reanalise: $("#cfg-auto").checked };
  if ($("#cfg-anthropic").value.trim()) corpo.anthropic_api_key = $("#cfg-anthropic").value.trim();
  if ($("#cfg-football").value.trim()) corpo.football_api_key = $("#cfg-football").value.trim();
  if ($("#cfg-limite").value !== "") corpo.limite_analises_gratis = parseInt($("#cfg-limite").value);
  if ($("#cfg-vipdias").value !== "") corpo.vip_dias = parseInt($("#cfg-vipdias").value);
  try {
    await api("/api/configurar", { method: "POST", body: JSON.stringify(corpo) });
    $("#config-ok").textContent = "✅ Salvo! Atualizando…";
    $("#cfg-anthropic").value = ""; $("#cfg-football").value = "";
    await atualizarStatus();
    setTimeout(() => { fechar("modal-config"); carregarJogos(); }, 800);
  } catch (err) { toast("⚠️ " + err.message); }
});

// ===================== Modais =====================
function abrir(id) { $("#" + id).classList.remove("hidden"); }
function fechar(id) { $("#" + id).classList.add("hidden"); }
document.querySelectorAll("[data-fechar]").forEach((b) => b.addEventListener("click", () => fechar(b.dataset.fechar)));
document.querySelectorAll(".modal").forEach((m) => m.addEventListener("click", (e) => { if (e.target === m) m.classList.add("hidden"); }));

// ===================== Início =====================
if (TOKEN) { entrarNoApp().catch(sair); }

// ===================== PWA (app instalável) =====================
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
}
