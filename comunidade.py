# -*- coding: utf-8 -*-
"""
Modulo PLACAR DA COMUNIDADE do ScopeMind AI.

Area recreativa e GRATUITA de palpites de placar com XP e ranking (estilo
Duolingo). NAO envolve dinheiro, apostas, premios financeiros nem promessas.

Usa SOMENTE a biblioteca padrao. Armazena em arquivos (pasta comunidade/):
  - palpites.json : todos os palpites (1 por usuario por jogo)
  - admin.json    : bloqueios, ajustes manuais de XP e resultados manuais

XP e RANKING sao RECALCULADOS a partir dos palpites resolvidos + ajustes
manuais (modelo "recompute"): por isso o processamento e naturalmente
IDEMPOTENTE — reprocessar um jogo nunca pontua duas vezes.

Pontuacao: acertou o placar EXATO = +10 XP; errou = -2 XP; pendente/adiado/
cancelado = 0. XP nunca fica negativo (minimo 0).
"""
import os
import re
import csv
import json
import time
import io
import threading
import datetime

import relatorios        # reaproveita a mesma "chave do jogo" do resto do app
import dados_futebol     # para buscar resultados oficiais (ontem/hoje)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", "").strip() or BASE_DIR
DIR = os.path.join(DATA_DIR, "comunidade")
ARQ_PALP = os.path.join(DIR, "palpites.json")
ARQ_ADMIN = os.path.join(DIR, "admin.json")

_LOCK = threading.RLock()
_ULTIMO_PROC = [0.0]            # epoch do ultimo processamento automatico (throttle)

XP_ACERTO = 10
XP_ERRO = -2
PLACAR_MAX = 20
PROC_INTERVALO = 90            # segundos minimos entre processamentos automaticos

FINISHED = ("FT", "AET", "PEN")
ADIADO = ("PST", "SUSP", "TBD")
CANCELADO = ("CANC", "ABD", "AWD", "WO")
# jogos ja comecados/encerrados (nao aceitam mais palpite)
EM_ANDAMENTO = ("1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT")

# Faixas de destaque (selo principal = SEMPRE a melhor faixa que a posicao alcanca)
BADGES = [
    {"faixa": "top3",    "nome": "Hall da Glória",       "icone": "👑", "cor": "ouro",     "min": 1,    "max": 3,    "descricao": "Os 3 melhores da comunidade."},
    {"faixa": "top10",   "nome": "Lenda da Comunidade",  "icone": "🏆", "cor": "dourado",  "min": 4,    "max": 10,   "descricao": "Entre os 10 melhores da comunidade."},
    {"faixa": "top50",   "nome": "Mestre da Leitura",    "icone": "🥈", "cor": "prata",    "min": 11,   "max": 50,   "descricao": "Entre os 50 melhores da comunidade."},
    {"faixa": "top100",  "nome": "Analista de Elite",    "icone": "🛡️", "cor": "azul",     "min": 51,   "max": 100,  "descricao": "Entre os 100 melhores do ranking."},
    {"faixa": "top1000", "nome": "Observador Tático",    "icone": "🔭", "cor": "azulclaro","min": 101,  "max": 1000, "descricao": "Entre os 1000 melhores da comunidade."},
    {"faixa": "base",    "nome": "Estreante",            "icone": "🌱", "cor": "base",     "min": 1001, "max": 10 ** 9, "descricao": "Faça palpites e suba no ranking!"},
]
# limites das faixas (melhor posicao de cada faixa de destaque), p/ "quanto falta"
LIMIARES = [3, 10, 50, 100, 1000]


def badge_para_posicao(pos):
    if not pos:
        return dict(BADGES[-1])   # Estreante (sem ranking ainda)
    for b in BADGES:
        if b["min"] <= pos <= b["max"]:
            return dict(b)
    return dict(BADGES[-1])


# ----------------------------------------------------------------------------
# Armazenamento (atomico + Lock)
# ----------------------------------------------------------------------------
def _garante():
    if not os.path.exists(DIR):
        os.makedirs(DIR, exist_ok=True)


def _ler(arq, vazio):
    _garante()
    if not os.path.exists(arq):
        return dict(vazio)
    try:
        with open(arq, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(vazio)


def _salvar(arq, obj):
    _garante()
    tmp = arq + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, arq)


def _ler_palpites():
    e = _ler(ARQ_PALP, {"prox_id": 1, "palpites": []})
    e.setdefault("prox_id", 1)
    e.setdefault("palpites", [])
    return e


def _ler_admin():
    a = _ler(ARQ_ADMIN, {"bloqueados": [], "ajustes": [], "resultados_manuais": {}, "prox_aj": 1})
    a.setdefault("bloqueados", [])
    a.setdefault("ajustes", [])
    a.setdefault("resultados_manuais", {})
    a.setdefault("prox_aj", 1)
    return a


# ----------------------------------------------------------------------------
# Utilidades de jogo / tempo
# ----------------------------------------------------------------------------
def chave_jogo(j):
    return relatorios.chave_do_jogo(j)


def _kickoff(p):
    iso = p.get("inicio_iso") or ((p.get("data") or "") + "T" + (p.get("time") or "23:59"))
    for tentativa in (iso, (p.get("data") or "") + "T23:59"):
        try:
            return datetime.datetime.fromisoformat(tentativa)
        except Exception:
            continue
    return None


def _comecou(p):
    k = _kickoff(p)
    return k is not None and datetime.datetime.now() >= k


def _status_exibicao(p):
    """Status que o usuario ve. Se ja foi processado, usa o resultado salvo;
    senao, 'locked' (bloqueado) se a partida ja comecou, ou 'pending'."""
    if p.get("processed_ts"):
        return p.get("status", "pending")
    return "locked" if _comecou(p) else "pending"


def _publico(p):
    d = {k: p.get(k) for k in (
        "id", "usuario", "nome", "jogo", "home", "away", "league", "country_pt",
        "home_logo", "away_logo", "data", "time", "ph", "pa", "placar_real",
        "submitted_at", "updated_at", "processed_at")}
    d["status"] = _status_exibicao(p)
    d["editavel"] = (not p.get("processed_ts")) and (not _comecou(p))
    d["xp_result"] = _xp_do_status(d["status"])
    return d


def _xp_do_status(status):
    if status == "correct":
        return XP_ACERTO
    if status == "wrong":
        return XP_ERRO
    return 0


# ----------------------------------------------------------------------------
# Palpites (criar / editar)
# ----------------------------------------------------------------------------
def esta_bloqueado(usuario):
    return usuario in _ler_admin().get("bloqueados", [])


def meu_palpite(usuario, chave):
    for p in _ler_palpites().get("palpites", []):
        if p.get("usuario") == usuario and p.get("jogo") == chave:
            return _publico(p)
    return None


def _valida_placar(v):
    try:
        v = int(v)
    except Exception:
        raise ValueError("Placar inválido — use apenas números.")
    if v < 0 or v > PLACAR_MAX:
        raise ValueError("O placar de cada time deve ser de 0 a %d." % PLACAR_MAX)
    return v


def palpitar(usuario, nome, jogo, ph, pa):
    ph = _valida_placar(ph)
    pa = _valida_placar(pa)
    if esta_bloqueado(usuario):
        raise ValueError("Sua conta está bloqueada no Placar da Comunidade.")
    short = (jogo.get("short") or "").upper()
    if short in FINISHED or short in EM_ANDAMENTO or short in CANCELADO:
        raise ValueError("Os palpites para este jogo foram encerrados porque a partida já começou.")
    chave = chave_jogo(jogo)
    data = jogo.get("data") or ""
    hora = jogo.get("time") or "23:59"
    inicio_iso = (data + "T" + hora) if data else ""
    agora = datetime.datetime.now()
    inicio = None
    try:
        inicio = datetime.datetime.fromisoformat(inicio_iso) if inicio_iso else None
    except Exception:
        inicio = None
    if inicio is not None and agora >= inicio:
        raise ValueError("Os palpites para este jogo foram encerrados porque a partida já começou.")

    agora_iso = agora.strftime("%d/%m/%Y %H:%M")
    with _LOCK:
        estado = _ler_palpites()
        alvo = None
        for p in estado["palpites"]:
            if p.get("usuario") == usuario and p.get("jogo") == chave:
                alvo = p
                break
        if alvo is not None:
            if alvo.get("processed_ts") or _comecou(alvo):
                raise ValueError("Este palpite já está bloqueado e não pode mais ser editado.")
            alvo["ph"] = ph
            alvo["pa"] = pa
            alvo["updated_at"] = agora_iso
            alvo["updated_ts"] = time.time()
            novo = alvo
        else:
            novo = {
                "id": estado["prox_id"],
                "usuario": usuario,
                "nome": nome or usuario,
                "jogo": chave,
                "home": jogo.get("home"), "away": jogo.get("away"),
                "league": jogo.get("league"), "country_pt": jogo.get("country_pt") or jogo.get("country"),
                "home_logo": jogo.get("home_logo"), "away_logo": jogo.get("away_logo"),
                "data": data, "time": jogo.get("time") or "",
                "inicio_iso": inicio_iso,
                "ph": ph, "pa": pa,
                "status": "pending",
                "placar_real": None,
                "submitted_at": agora_iso, "submitted_ts": time.time(),
                "updated_at": agora_iso, "updated_ts": time.time(),
                "processed_at": None, "processed_ts": None,
            }
            estado["palpites"].append(novo)
            estado["prox_id"] += 1
        _salvar(ARQ_PALP, estado)
    return _publico(novo)


def historico(usuario, limite=60):
    out = [_publico(p) for p in _ler_palpites().get("palpites", []) if p.get("usuario") == usuario]
    out.sort(key=lambda x: x.get("id", 0), reverse=True)
    return out[:limite]


# ----------------------------------------------------------------------------
# Processamento de resultados -> status dos palpites
# ----------------------------------------------------------------------------
def _resolver(p, short, score):
    """Define o status final de um palpite a partir do resultado do jogo.
    Retorna True se alterou algo."""
    short = (short or "").upper()
    if short in FINISHED and score and " - " in score:
        try:
            hr, ar = [int(x) for x in score.split(" - ")]
        except Exception:
            return False
        acertou = (p.get("ph") == hr and p.get("pa") == ar)
        p["status"] = "correct" if acertou else "wrong"
        p["placar_real"] = "%d - %d" % (hr, ar)
    elif short in CANCELADO:
        p["status"] = "cancelled"
        p["placar_real"] = None
    elif short in ADIADO:
        p["status"] = "postponed"
        p["placar_real"] = None
    else:
        return False
    p["processed_at"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    p["processed_ts"] = time.time()
    return True


def _mapa_resultados(cfg):
    """Resultados oficiais recentes (ontem + hoje) + resultados manuais do admin."""
    resultados = {}
    for per in ("ontem", "hoje"):
        try:
            jogos, _, _ = dados_futebol.listar_jogos(per, cfg)
            for j in jogos:
                resultados[chave_jogo(j)] = {"short": j.get("short"), "score": j.get("score")}
        except Exception:
            pass
    # resultados manuais do admin têm prioridade
    for chave, r in _ler_admin().get("resultados_manuais", {}).items():
        resultados[chave] = {"short": r.get("short"), "score": r.get("score")}
    return resultados


def processar_pendentes(cfg, forcar=False):
    """Resolve os palpites cujos jogos ja terminaram. Throttle de 90s."""
    agora = time.time()
    if not forcar and (agora - _ULTIMO_PROC[0]) < PROC_INTERVALO:
        return 0
    _ULTIMO_PROC[0] = agora
    try:
        resultados = _mapa_resultados(cfg)
    except Exception:
        resultados = {}
    if not resultados:
        return 0
    n = 0
    with _LOCK:
        estado = _ler_palpites()
        for p in estado["palpites"]:
            if p.get("processed_ts"):
                continue
            r = resultados.get(p.get("jogo"))
            if not r:
                continue
            if _resolver(p, r.get("short"), r.get("score")):
                n += 1
        if n:
            _salvar(ARQ_PALP, estado)
    return n


def reprocessar(cfg, chave=None):
    """ADMIN: re-avalia os palpites (de um jogo ou de todos) contra o resultado
    atual — util se o admin corrigiu um placar. Idempotente."""
    resultados = _mapa_resultados(cfg)
    n = 0
    with _LOCK:
        estado = _ler_palpites()
        for p in estado["palpites"]:
            if chave and p.get("jogo") != chave:
                continue
            r = resultados.get(p.get("jogo"))
            if not r:
                continue
            # reset p/ reavaliar do zero
            p["processed_ts"] = None
            p["processed_at"] = None
            p["status"] = "pending"
            p["placar_real"] = None
            if _resolver(p, r.get("short"), r.get("score")):
                n += 1
        if n or chave:
            _salvar(ARQ_PALP, estado)
    return n


# ----------------------------------------------------------------------------
# Ranking / estatisticas (recompute a partir dos palpites + ajustes)
# ----------------------------------------------------------------------------
def _agregar():
    """XP = soma cronológica dos eventos (acerto +10, erro -2, ajuste manual),
    com piso 0 a CADA passo (estilo Duolingo: nunca fica negativo; um erro com
    0 XP não tira nada). Isso deixa ranking e 'evolução' consistentes."""
    estado = _ler_palpites()
    admin = _ler_admin()
    bloqueados = set(admin.get("bloqueados", []))
    meta = {}        # usuario -> contadores
    eventos = {}     # usuario -> lista de (ts, delta)
    for p in estado["palpites"]:
        u = p.get("usuario")
        m = meta.setdefault(u, {"usuario": u, "nome": p.get("nome") or u, "palpites": 0,
                                "acertos": 0, "erros": 0, "since_ts": p.get("submitted_ts") or time.time()})
        m["palpites"] += 1
        m["nome"] = p.get("nome") or m["nome"]
        m["since_ts"] = min(m["since_ts"], p.get("submitted_ts") or m["since_ts"])
        st = _status_exibicao(p)
        if st == "correct":
            m["acertos"] += 1
            eventos.setdefault(u, []).append((p.get("processed_ts") or 0, XP_ACERTO))
        elif st == "wrong":
            m["erros"] += 1
            eventos.setdefault(u, []).append((p.get("processed_ts") or 0, XP_ERRO))
    for a in admin.get("ajustes", []):
        eventos.setdefault(a["usuario"], []).append((a.get("ts") or 0, int(a.get("amount", 0))))
    saida = []
    for u, m in meta.items():
        if u in bloqueados:
            continue
        xp = 0
        for _ts, delta in sorted(eventos.get(u, []), key=lambda e: e[0]):
            xp = max(0, xp + delta)
        decididos = m["acertos"] + m["erros"]
        m["xp"] = xp
        m["taxa"] = round(100 * m["acertos"] / decididos) if decididos else 0
        saida.append(m)
    return saida


def _ordenar(lista):
    # XP desc, acertos desc, taxa desc, palpites desc, mais antigo, nome A-Z
    lista.sort(key=lambda d: ((d.get("nome") or "").lower(),))
    lista.sort(key=lambda d: (
        -d["xp"], -d["acertos"], -d["taxa"], -d["palpites"], d["since_ts"]))
    return lista


def ranking_completo():
    lista = _ordenar(_agregar())
    for i, d in enumerate(lista, start=1):
        d["pos"] = i
        d["badge"] = badge_para_posicao(i)
    return lista


def ranking(faixa="geral", limite=200):
    full = ranking_completo()
    teto = {"top3": 3, "top10": 10, "top50": 50, "top100": 100, "top1000": 1000}.get(faixa)
    if teto:
        full = [d for d in full if d["pos"] <= teto]
    return full[:limite]


def _faltam_proxima(full, pos, xp):
    """Quantos XP faltam para alcançar a próxima faixa de destaque."""
    if not pos or pos <= 3:
        return {"faixa": None, "faltam": 0}
    alvo_pos = None
    for lim in sorted(LIMIARES):           # 3,10,50,100,1000
        if lim < pos:
            alvo_pos = lim                 # maior limiar abaixo da minha posicao
    if not alvo_pos or alvo_pos > len(full):
        return {"faixa": None, "faltam": None}
    xp_alvo = full[alvo_pos - 1]["xp"]     # XP de quem esta na posicao limiar
    faltam = max(0, xp_alvo - xp) + 1
    return {"faixa": badge_para_posicao(alvo_pos)["nome"], "faltam": faltam}


def estatisticas(usuario, nome_fallback=""):
    full = ranking_completo()
    eu = next((d for d in full if d["usuario"] == usuario), None)
    hist = historico(usuario, 12)
    # evolucao de XP (soma cumulativa sobre os palpites resolvidos, em ordem)
    resolvidos = [p for p in _ler_palpites().get("palpites", [])
                  if p.get("usuario") == usuario and p.get("processed_ts")]
    resolvidos.sort(key=lambda p: p.get("processed_ts") or 0)
    ev, acc = [], 0
    for p in resolvidos:
        acc = max(0, acc + _xp_do_status(_status_exibicao(p)))
        ev.append(acc)
    ev = ev[-20:]
    if eu:
        prox = _faltam_proxima(full, eu["pos"], eu["xp"])
        return {
            "usuario": usuario, "nome": eu["nome"], "xp": eu["xp"], "pos": eu["pos"],
            "palpites": eu["palpites"], "acertos": eu["acertos"], "erros": eu["erros"],
            "taxa": eu["taxa"], "badge": eu["badge"], "total_ranking": len(full),
            "proxima": prox, "historico": hist, "evolucao": ev,
            "bloqueado": esta_bloqueado(usuario),
        }
    return {
        "usuario": usuario, "nome": nome_fallback or usuario, "xp": 0, "pos": None,
        "palpites": len(hist), "acertos": 0, "erros": 0, "taxa": 0,
        "badge": badge_para_posicao(None), "total_ranking": len(full),
        "proxima": {"faixa": "Observador Tático", "faltam": None},
        "historico": hist, "evolucao": ev, "bloqueado": esta_bloqueado(usuario),
    }


# ----------------------------------------------------------------------------
# Administração
# ----------------------------------------------------------------------------
def admin_listar_palpites(busca=""):
    b = (busca or "").lower().strip()
    out = []
    for p in _ler_palpites().get("palpites", []):
        if b:
            campo = " ".join(str(x or "") for x in (
                p.get("usuario"), p.get("nome"), p.get("home"), p.get("away"), p.get("jogo"))).lower()
            if b not in campo:
                continue
        out.append(_publico(p))
    out.sort(key=lambda x: x.get("id", 0), reverse=True)
    return out


def admin_set_resultado(cfg, chave, home_score, away_score, marcar=""):
    """ADMIN: registra um resultado manual (ou marca adiado/cancelado) e processa.
    marcar: '' (placar normal), 'cancelled' ou 'postponed'."""
    with _LOCK:
        admin = _ler_admin()
        if marcar == "cancelled":
            admin["resultados_manuais"][chave] = {"short": "CANC", "score": ""}
        elif marcar == "postponed":
            admin["resultados_manuais"][chave] = {"short": "PST", "score": ""}
        else:
            h = _valida_placar(home_score)
            a = _valida_placar(away_score)
            admin["resultados_manuais"][chave] = {"short": "FT", "score": "%d - %d" % (h, a)}
        _salvar(ARQ_ADMIN, admin)
    return reprocessar(cfg, chave)


def admin_ajustar_xp(usuario, amount, motivo, por):
    try:
        amount = int(amount)
    except Exception:
        raise ValueError("Valor de XP inválido.")
    with _LOCK:
        admin = _ler_admin()
        admin["ajustes"].append({
            "id": admin["prox_aj"], "usuario": usuario, "amount": amount,
            "motivo": motivo or "ajuste manual", "por": por,
            "data": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "ts": time.time(),
            "reason": "manual_adjustment",
        })
        admin["prox_aj"] += 1
        _salvar(ARQ_ADMIN, admin)
    return True


def admin_bloquear(usuario, bloquear=True):
    with _LOCK:
        admin = _ler_admin()
        bl = set(admin.get("bloqueados", []))
        if bloquear:
            bl.add(usuario)
        else:
            bl.discard(usuario)
        admin["bloqueados"] = sorted(bl)
        _salvar(ARQ_ADMIN, admin)
    return True


def admin_lista_usuarios():
    """Resumo de todos os participantes (p/ o painel admin)."""
    full = ranking_completo()
    bloqueados = set(_ler_admin().get("bloqueados", []))
    # inclui tambem os bloqueados (que saem do ranking)
    vistos = {d["usuario"] for d in full}
    extra = []
    for p in _ler_palpites().get("palpites", []):
        u = p.get("usuario")
        if u in bloqueados and u not in vistos:
            extra.append({"usuario": u, "nome": p.get("nome") or u, "xp": 0,
                          "pos": None, "palpites": 0, "acertos": 0, "erros": 0, "taxa": 0})
            vistos.add(u)
    saida = []
    for d in full + extra:
        saida.append({"usuario": d["usuario"], "nome": d["nome"], "xp": d.get("xp", 0),
                      "pos": d.get("pos"), "palpites": d.get("palpites", 0),
                      "acertos": d.get("acertos", 0), "erros": d.get("erros", 0),
                      "taxa": d.get("taxa", 0), "bloqueado": d["usuario"] in bloqueados})
    return saida


def exportar_csv(tipo):
    buf = io.StringIO()
    w = csv.writer(buf)
    if tipo == "palpites":
        w.writerow(["id", "usuario", "nome", "jogo", "casa", "fora", "palpite_casa",
                    "palpite_fora", "placar_real", "status", "xp", "enviado_em", "processado_em"])
        for p in _ler_palpites().get("palpites", []):
            st = _status_exibicao(p)
            w.writerow([p.get("id"), p.get("usuario"), p.get("nome"), p.get("jogo"),
                        p.get("home"), p.get("away"), p.get("ph"), p.get("pa"),
                        p.get("placar_real") or "", st, _xp_do_status(st),
                        p.get("submitted_at"), p.get("processed_at") or ""])
    else:  # ranking
        w.writerow(["posicao", "usuario", "nome", "xp", "palpites", "acertos", "erros", "taxa_%", "faixa"])
        for d in ranking_completo():
            w.writerow([d["pos"], d["usuario"], d["nome"], d["xp"], d["palpites"],
                        d["acertos"], d["erros"], d["taxa"], d["badge"]["nome"]])
    return buf.getvalue()
