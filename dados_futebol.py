# -*- coding: utf-8 -*-
"""
Busca de jogos (hoje / semana / mes) e coleta de contexto para os agentes.
Fonte ao vivo: API-Football (api-sports.io) - plano gratuito.
Sem chave -> entra em "modo demonstracao" com jogos de exemplo.
Usa apenas urllib (biblioteca padrao). Horarios no fuso de Brasilia.
"""
import os
import re
import json
import datetime
import urllib.request
import urllib.error

API_BASE = "https://v3.football.api-sports.io"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", "").strip() or BASE_DIR
CACHE_DIR = os.path.join(DATA_DIR, "cache")

STATUS_PT = {
    "NS": "A iniciar", "TBD": "A confirmar",
    "1H": "1o tempo", "HT": "Intervalo", "2H": "2o tempo",
    "ET": "Prorrogacao", "P": "Penaltis", "LIVE": "Ao vivo",
    "FT": "Encerrado", "AET": "Encerrado (prorrog.)", "PEN": "Encerrado (penaltis)",
    "PST": "Adiado", "CANC": "Cancelado", "SUSP": "Suspenso",
}

# Status que contam como "ao vivo" (jogo em andamento)
LIVE_PT = {"1o tempo", "Intervalo", "2o tempo", "Prorrogacao", "Penaltis", "Ao vivo"}

# Traducao de paises/selecoes (ingles -> portugues). Cobre os nomes de selecoes e a
# origem do campeonato. Times de clube (nao listados) ficam com o nome original.
TRADUCAO_PAIS = {
    "World": "Mundo", "Europe": "Europa", "South America": "América do Sul",
    "North America": "América do Norte", "Africa": "África", "Asia": "Ásia", "Oceania": "Oceania",
    "Brazil": "Brasil", "Argentina": "Argentina", "England": "Inglaterra", "Spain": "Espanha",
    "Italy": "Itália", "Germany": "Alemanha", "France": "França", "Portugal": "Portugal",
    "Netherlands": "Holanda", "Belgium": "Bélgica", "USA": "Estados Unidos", "Mexico": "México",
    "Colombia": "Colômbia", "Chile": "Chile", "Uruguay": "Uruguai", "Paraguay": "Paraguai",
    "Ecuador": "Equador", "Peru": "Peru", "Bolivia": "Bolívia", "Venezuela": "Venezuela",
    "Japan": "Japão", "South-Korea": "Coreia do Sul", "South Korea": "Coreia do Sul",
    "Korea Republic": "Coreia do Sul", "Saudi-Arabia": "Arábia Saudita", "Saudi Arabia": "Arábia Saudita",
    "Turkey": "Turquia", "Greece": "Grécia", "Russia": "Rússia", "Ukraine": "Ucrânia",
    "Austria": "Áustria", "Switzerland": "Suíça", "Denmark": "Dinamarca", "Sweden": "Suécia",
    "Norway": "Noruega", "Poland": "Polônia", "Croatia": "Croácia", "Egypt": "Egito",
    "Morocco": "Marrocos", "Nigeria": "Nigéria", "Ethiopia": "Etiópia", "Algeria": "Argélia",
    "Australia": "Austrália", "China": "China", "China PR": "China", "India": "Índia",
    "Cameroon": "Camarões", "Ghana": "Gana", "Senegal": "Senegal", "Tunisia": "Tunísia",
    "Ivory Coast": "Costa do Marfim", "Iran": "Irã", "Iraq": "Iraque", "Qatar": "Catar",
    "Scotland": "Escócia", "Wales": "País de Gales", "Ireland": "Irlanda",
    "Northern Ireland": "Irlanda do Norte", "Czech-Republic": "República Tcheca",
    "Czech Republic": "República Tcheca", "Czechia": "Tchéquia", "Slovakia": "Eslováquia",
    "Slovenia": "Eslovênia", "Hungary": "Hungria", "Romania": "Romênia", "Bulgaria": "Bulgária",
    "Serbia": "Sérvia", "Bosnia": "Bósnia", "Bosnia and Herzegovina": "Bósnia e Herzegovina",
    "Finland": "Finlândia", "Iceland": "Islândia", "Cyprus": "Chipre", "Israel": "Israel",
    "Philippines": "Filipinas", "Guam": "Guam", "Gibraltar": "Gibraltar", "Maldives": "Maldivas",
    "Pakistan": "Paquistão", "Cambodia": "Camboja", "Bhutan": "Butão", "Lesotho": "Lesoto",
    "Kenya": "Quênia", "Guinea": "Guiné", "Burundi": "Burundi", "Mali": "Mali",
    "Equatorial Guinea": "Guiné Equatorial", "Congo DR": "Congo (RD)", "Congo": "Congo",
    "DR Congo": "Congo (RD)", "British Virgin Islands": "Ilhas Virgens Britânicas",
    "Andorra": "Andorra", "Liechtenstein": "Liechtenstein", "Guatemala": "Guatemala",
    "Luxembourg": "Luxemburgo", "Estonia": "Estônia", "Latvia": "Letônia", "Lithuania": "Lituânia",
    "Albania": "Albânia", "Armenia": "Armênia", "Georgia": "Geórgia", "Azerbaijan": "Azerbaijão",
    "Kazakhstan": "Cazaquistão", "Uzbekistan": "Uzbequistão", "Jordan": "Jordânia",
    "Lebanon": "Líbano", "Yemen": "Iêmen", "Oman": "Omã", "Bahrain": "Bahrein", "Kuwait": "Kuwait",
    "Syria": "Síria", "Vietnam": "Vietnã", "Thailand": "Tailândia", "Indonesia": "Indonésia",
    "Malaysia": "Malásia", "Singapore": "Singapura", "Myanmar": "Mianmar", "Nepal": "Nepal",
    "Bangladesh": "Bangladesh", "Sri Lanka": "Sri Lanka", "Hong Kong": "Hong Kong",
    "Fiji": "Fiji", "New Zealand": "Nova Zelândia", "Canada": "Canadá", "Panama": "Panamá",
    "Costa Rica": "Costa Rica", "Honduras": "Honduras", "El Salvador": "El Salvador",
    "Jamaica": "Jamaica", "Haiti": "Haiti", "Dominican Republic": "República Dominicana",
    "South Africa": "África do Sul", "Angola": "Angola", "Mozambique": "Moçambique",
    "Zambia": "Zâmbia", "Zimbabwe": "Zimbábue", "Uganda": "Uganda", "Tanzania": "Tanzânia",
    "Sudan": "Sudão", "Libya": "Líbia", "Gabon": "Gabão", "Togo": "Togo", "Benin": "Benim",
    "Burkina Faso": "Burkina Faso", "Cape Verde": "Cabo Verde", "Madagascar": "Madagascar",
    "Mauritania": "Mauritânia", "Niger": "Níger", "Rwanda": "Ruanda", "Malawi": "Malaui",
    "Botswana": "Botsuana", "Namibia": "Namíbia", "Sierra Leone": "Serra Leoa",
    "Liberia": "Libéria", "Gambia": "Gâmbia", "Comoros": "Comores",
}


def traduzir(nome):
    return TRADUCAO_PAIS.get((nome or "").strip(), nome or "")

# Padrao para excluir o que NAO eh campeonato profissional de destaque:
# base/juvenil, reservas, amadoras E divisoes inferiores (3a divisao pra baixo, regionais).
# Mantem 1a e 2a divisoes nacionais, copas e competicoes internacionais.
PADRAO_NAO_PRO = re.compile(
    # base / juvenil / reservas / amador
    r"\bu-?\s?\d{1,2}\b|\bsub-?\s?\d{1,2}\b|youth|junior|\bjr\.?\b|juvenil|primavera|jugend|"
    r"cadet|infantil|\breserves?\b|amateur|amador|"
    # futebol feminino
    r"women|femenin|f[eé]minin|frauen|\bnwsl\b|\bwsl\b|\bw\s?league\b|damallsvenskan|kvinnor|"
    # 3a divisao pra baixo (varios idiomas)
    r"\b[3-9]\.?\s?(liga|division|divisi[oó]n|deild|lig|liga pro)\b|\bdivision\s?[2-9]\b|"
    r"\bliga\s?[3-9]\b|\b3rd\b|\b4th\b|tercera|cuarta|segunda\s?b\b|primera\s?rfef|"
    r"\bserie\s?d\b|\bserie\s?c2\b|"
    # ligas regionais/amadoras tipicas
    r"regionalliga|oberliga|verbandsliga|landesliga|kreisliga|\bettan\b|\btv[aå]an\b|"
    r"kakkonen|kolmonen|\bleague\s(one|two)\b|"
    r"\bnational league\b|\bintermedia\b|g[oö]taland|\bnorra\b|\bs[oö]dra\b|"
    # estaduais/regionais com sufixo numerico de divisao (ex.: "Maranhense - 2")
    r"\s-\s?[2-9]\b",
    re.IGNORECASE,
)

# Padrao para NOMES DE TIME nao-profissionais (base/juvenil e feminino) — usado nos amistosos
PADRAO_TIME_NAO_PRO = re.compile(
    r"\bu-?\s?\d{1,2}\b|\bsub-?\s?\d{1,2}\b|youth|junior|\bjr\b|juvenil|women|femenin|f[eé]minin|frauen", re.IGNORECASE)


def _eh_profissional(liga, pais="", home="", away=""):
    if PADRAO_NAO_PRO.search(liga or ""):
        return False
    if PADRAO_TIME_NAO_PRO.search(home or "") or PADRAO_TIME_NAO_PRO.search(away or ""):
        return False
    l = (liga or "").lower()
    p = (pais or "").lower()
    # Brasil: só campeonatos nacionais de destaque (Série A/B/C/D, Copa do Brasil, Copa do Nordeste).
    # Remove estaduais e copas regionais (Carioca, Paulista, Copa Gaúcha, Copa Espírito Santo, etc.).
    if p in ("brazil", "brasil"):
        return any(x in l for x in ("serie a", "serie b", "serie c", "serie d", "copa do bra", "nordeste"))
    return True


# ---------------------------------------------------------------------------
# Onde assistir (mapa por competicao - "geralmente", sujeito a confirmacao)
# ---------------------------------------------------------------------------
def onde_assistir(liga, pais):
    l = (liga or "").lower()
    p = (pais or "").lower()
    if "world cup" in l or "copa do mundo" in l:
        return "Globo, SporTV, CazeTV (geralmente)"
    if "friendl" in l or "amistoso" in l:
        return "ESPN, Disney+, SporTV (varia por jogo)"
    if "champions" in l:
        return "TNT, HBO Max, Space (geralmente)"
    if "europa league" in l:
        return "ESPN, Disney+ (geralmente)"
    if "libertadores" in l:
        return "Paramount+, SBT, ESPN (geralmente)"
    if "sudamericana" in l or "sul-americana" in l:
        return "Paramount+, ESPN (geralmente)"
    if "copa do brasil" in l:
        return "Amazon Prime, SporTV, Globo (geralmente)"
    if "premier league" in l and "brazil" not in p:
        return "ESPN, Disney+ (geralmente)"
    if "la liga" in l or "laliga" in l:
        return "ESPN, Disney+ (geralmente)"
    if "bundesliga" in l:
        return "CazeTV, OneFootball (geralmente)"
    if "ligue 1" in l:
        return "CazeTV, OneFootball (geralmente)"
    if "serie a" in l and "italy" in p:
        return "ESPN, Disney+, CazeTV (geralmente)"
    if "brazil" in p or "brasileir" in l:
        return "Premiere, SporTV, Globo, Amazon (geralmente)"
    return "Consulte a programacao local (varia por regiao)"


# ---------------------------------------------------------------------------
# Chamada a API + cache em disco
# ---------------------------------------------------------------------------
def _api_get(caminho, params, chave):
    qs = "&".join("%s=%s" % (k, v) for k, v in params.items())
    url = "%s%s?%s" % (API_BASE, caminho, qs)
    req = urllib.request.Request(url, method="GET")
    req.add_header("x-apisports-key", chave)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _cache_path(nome):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, nome)


def _fixtures_do_dia(data_iso, chave):
    """Retorna (lista de jogos normalizados, bloqueado_pelo_plano) de um dia, com cache."""
    cache = _cache_path("fixtures_%s.json" % data_iso)
    hoje_iso = datetime.date.today().isoformat()
    # cache: dias passados/futuros valem muito tempo; hoje vale 20 min
    if os.path.exists(cache):
        idade = datetime.datetime.now().timestamp() - os.path.getmtime(cache)
        valido = (data_iso != hoje_iso) or (idade < 60)
        if valido:
            try:
                with open(cache, "r", encoding="utf-8") as f:
                    c = json.load(f)
                if isinstance(c, dict):
                    return c.get("jogos", []), c.get("bloqueado", False)
                return c, False  # cache antigo (lista pura)
            except Exception:
                pass
    dados = _api_get("/fixtures", {"date": data_iso, "timezone": "America/Sao_Paulo"}, chave)
    erros = dados.get("errors")
    bloqueado = False
    if isinstance(erros, dict) and erros:
        txt = " ".join(str(v) for v in erros.values()).lower()
        if "plan" in txt or "access" in txt:
            bloqueado = True
    jogos = [_normalizar(item) for item in dados.get("response", [])]
    try:
        tmp = cache + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"jogos": jogos, "bloqueado": bloqueado}, f, ensure_ascii=False)
        os.replace(tmp, cache)
    except Exception:
        pass
    return jogos, bloqueado


def _normalizar(item):
    fx = item.get("fixture", {})
    lg = item.get("league", {})
    tm = item.get("teams", {})
    gl = item.get("goals", {})
    iso = fx.get("date", "")
    data = iso[:10]
    hora = iso[11:16] if len(iso) >= 16 else ""
    short = (fx.get("status") or {}).get("short", "NS")
    placar = ""
    if short not in ("NS", "TBD", "PST", "CANC") and gl.get("home") is not None:
        placar = "%s - %s" % (gl.get("home"), gl.get("away"))
    venue = (fx.get("venue") or {}).get("name") or ""
    cidade = (fx.get("venue") or {}).get("city") or ""
    if cidade and venue:
        venue = "%s (%s)" % (venue, cidade)
    return {
        "id": fx.get("id"),
        "data": data,
        "time": hora,
        "league": lg.get("name", ""),
        "country": lg.get("country", ""),
        "country_pt": traduzir(lg.get("country", "")),
        "round": lg.get("round", ""),
        "season": lg.get("season"),
        "league_id": lg.get("id"),
        "flag": lg.get("flag") or "",
        "league_logo": lg.get("logo") or "",
        "home": traduzir((tm.get("home") or {}).get("name", "")),
        "away": traduzir((tm.get("away") or {}).get("name", "")),
        "home_id": (tm.get("home") or {}).get("id"),
        "away_id": (tm.get("away") or {}).get("id"),
        "home_logo": (tm.get("home") or {}).get("logo", ""),
        "away_logo": (tm.get("away") or {}).get("logo", ""),
        "venue": venue,
        "status": STATUS_PT.get(short, short),
        "short": short,
        "score": placar,
        "watch": onde_assistir(lg.get("name", ""), lg.get("country", "")),
    }


def _fixtures_live(chave):
    """Jogos de hoje com cache curto (90s), para a aba Ao Vivo."""
    cache = _cache_path("fixtures_live.json")
    if os.path.exists(cache):
        idade = datetime.datetime.now().timestamp() - os.path.getmtime(cache)
        if idade < 90:
            try:
                with open(cache, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    hoje = datetime.date.today().isoformat()
    dados = _api_get("/fixtures", {"date": hoje, "timezone": "America/Sao_Paulo"}, chave)
    jogos = [_normalizar(item) for item in dados.get("response", [])]
    try:
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(jogos, f, ensure_ascii=False)
    except Exception:
        pass
    return jogos


def _intervalo_datas(periodo):
    hoje = datetime.date.today()
    if periodo == "ontem":
        return [hoje - datetime.timedelta(days=1)]
    if periodo == "amanha":
        return [hoje + datetime.timedelta(days=1)]
    if periodo == "semana":
        return [hoje + datetime.timedelta(days=i) for i in range(7)]
    if periodo == "mes":
        return [hoje + datetime.timedelta(days=i) for i in range(30)]
    return [hoje]


def listar_jogos(periodo, cfg):
    chave = cfg.get("football_api_key", "").strip()
    if not chave:
        return _demo(periodo), "demo", ""
    if periodo == "aovivo":
        try:
            jogos = _fixtures_live(chave)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise RuntimeError("Chave de dados de futebol invalida ou sem permissao.")
            jogos = []
        except Exception:
            jogos = []
        jogos = [j for j in jogos if j.get("status") in LIVE_PT
                 and _eh_profissional(j.get("league", ""), j.get("country", ""), j.get("home", ""), j.get("away", ""))]
        jogos.sort(key=lambda j: (j.get("data", ""), j.get("time", "")))
        return jogos, "ao_vivo", ""
    datas = _intervalo_datas(periodo)
    todos = []
    bloqueio = False
    for d in datas:
        try:
            jogos, bloq = _fixtures_do_dia(d.isoformat(), chave)
            todos.extend(jogos)
            bloqueio = bloqueio or bloq
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise RuntimeError("Chave de dados de futebol invalida ou sem permissao.")
        except Exception:
            pass
    todos = [j for j in todos if _eh_profissional(j.get("league", ""), j.get("country", ""), j.get("home", ""), j.get("away", ""))]
    todos.sort(key=lambda j: (j.get("data", ""), j.get("time", "")))
    aviso = ""
    if bloqueio:
        aviso = ("O plano gratuito da API-Football cobre apenas ontem, hoje e amanha. "
                 "Para ver a semana/mes completos e resultados antigos, seria preciso um plano pago.")
    return todos, "ao_vivo", aviso


# ---------------------------------------------------------------------------
# Contexto adicional para a analise (melhor esforco; nao quebra se falhar)
# ---------------------------------------------------------------------------
def _resumo_resultados(lista, limite=6):
    linhas = []
    for item in lista[:limite]:
        n = _normalizar(item)
        placar = n["score"] or "x"
        linhas.append("  %s: %s %s %s (%s)" % (n["data"], n["home"], placar, n["away"], n["league"]))
    return "\n".join(linhas)


def tabela(league_id, season, cfg):
    """Classificacao de um campeonato (API-Football /standings)."""
    chave = cfg.get("football_api_key", "").strip()
    if not chave or not league_id:
        return []
    params = {"league": league_id}
    if season:
        params["season"] = season
    dados = _api_get("/standings", params, chave)
    resp = dados.get("response", [])
    if not resp:
        return []
    try:
        grupos = resp[0]["league"]["standings"]
        linhas = grupos[0] if grupos else []
    except Exception:
        return []
    out = []
    for t in linhas:
        allp = t.get("all", {}) or {}
        gols = allp.get("goals", {}) or {}
        time = t.get("team", {}) or {}
        out.append({
            "rank": t.get("rank"), "time": time.get("name", ""), "logo": time.get("logo", ""),
            "pts": t.get("points"), "j": allp.get("played"), "v": allp.get("win"),
            "e": allp.get("draw"), "d": allp.get("lose"),
            "gp": gols.get("for"), "gc": gols.get("against"), "sg": t.get("goalsDiff"),
        })
    return out


def coletar_contexto(partida, cfg):
    chave = cfg.get("football_api_key", "").strip()
    if not chave:
        return ""
    blocos = []
    hid = partida.get("home_id")
    aid = partida.get("away_id")
    try:
        if hid and aid:
            h2h = _api_get("/fixtures/headtohead",
                           {"h2h": "%s-%s" % (hid, aid), "last": 6, "timezone": "America/Sao_Paulo"}, chave)
            r = _resumo_resultados(h2h.get("response", []))
            if r:
                blocos.append("Confrontos diretos recentes:\n" + r)
    except Exception:
        pass
    for lado, tid, nome in [("Time A", hid, partida.get("home")), ("Time B", aid, partida.get("away"))]:
        try:
            if tid:
                ult = _api_get("/fixtures", {"team": tid, "last": 6, "timezone": "America/Sao_Paulo"}, chave)
                r = _resumo_resultados(ult.get("response", []))
                if r:
                    blocos.append("Ultimos jogos do %s (%s):\n%s" % (lado, nome, r))
        except Exception:
            pass
    return "\n\n".join(blocos)


# ---------------------------------------------------------------------------
# Modo demonstracao (sem chave de dados) - jogos de exemplo
# ---------------------------------------------------------------------------
def _ex(dia, hora, liga, pais, casa, fora):
    return {
        "id": None, "data": dia.isoformat(), "time": hora,
        "league": liga, "country": pais, "round": "", "season": None, "league_id": None,
        "home": casa, "away": fora, "home_id": None, "away_id": None,
        "home_logo": "", "away_logo": "", "venue": "",
        "status": "A iniciar", "score": "",
        "watch": onde_assistir(liga, pais),
    }


def _demo(periodo):
    hoje = datetime.date.today()
    d1 = hoje + datetime.timedelta(days=1)
    d2 = hoje + datetime.timedelta(days=2)
    d3 = hoje + datetime.timedelta(days=3)
    jogos = [
        # Selecoes (hoje)
        _ex(hoje, "16:00", "Amistoso Internacional", "Mundo", "Espanha", "Iraque"),
        _ex(hoje, "16:10", "Amistoso Internacional", "Mundo", "Franca", "Costa do Marfim"),
        _ex(hoje, "21:00", "Amistoso Internacional", "Mundo", "Rep. Tcheca", "Guatemala"),
        # Brasileirao Serie A (hoje)
        _ex(hoje, "19:00", "Brasileirao Serie A", "Brazil", "Flamengo", "Palmeiras"),
        _ex(hoje, "21:30", "Brasileirao Serie A", "Brazil", "Corinthians", "Sao Paulo"),
        # Brasileirao Serie B (hoje)
        _ex(hoje, "19:00", "Brasileirao Serie B", "Brazil", "Santos", "Novorizontino"),
        _ex(hoje, "20:30", "Brasileirao Serie B", "Brazil", "Chapecoense", "Coritiba"),
        # Brasileirao Serie C (hoje)
        _ex(hoje, "19:30", "Brasileirao Serie C", "Brazil", "Ypiranga", "Floresta"),
        # Copa do Brasil (hoje)
        _ex(hoje, "20:00", "Copa do Brasil", "Brazil", "Anapolis", "Paysandu"),
    ]
    if periodo in ("semana", "mes"):
        jogos += [
            _ex(d1, "16:00", "Premier League", "England", "Arsenal", "Chelsea"),
            _ex(d1, "18:30", "Bundesliga", "Germany", "Bayern", "Dortmund"),
            _ex(d1, "21:30", "Brasileirao Serie A", "Brazil", "Gremio", "Internacional"),
            _ex(d2, "16:00", "La Liga", "Spain", "Real Madrid", "Barcelona"),
            _ex(d2, "16:00", "Serie A", "Italy", "Inter", "Juventus"),
            _ex(d2, "19:00", "Brasileirao Serie B", "Brazil", "Cruzeiro", "Vila Nova"),
            _ex(d3, "16:00", "Champions League", "Europe", "Manchester City", "PSG"),
            _ex(d3, "21:00", "Brasileirao Serie A", "Brazil", "Atletico-MG", "Fluminense"),
        ]
    return jogos
