# -*- coding: utf-8 -*-
"""
Modulo de Relatorios: salva cada analise feita em disco, para reabrir
depois SEM gastar com a IA de novo. Um arquivo .json por jogo analisado.
Tambem marca analises "desatualizadas" (jogo futuro analisado ha mais de 12h).
"""
import os
import re
import json
import time
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", "").strip() or BASE_DIR
DIR = os.path.join(DATA_DIR, "relatorios")


def _garante():
    if not os.path.exists(DIR):
        os.makedirs(DIR, exist_ok=True)


def _slug(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60] or "jogo"


def _safe(chave):
    return re.sub(r"[^A-Za-z0-9_\-]", "", chave or "")


def chave_do_jogo(partida):
    if partida.get("id"):
        return "id-%s" % partida["id"]
    return "%s_vs_%s_%s" % (_slug(partida.get("home")),
                            _slug(partida.get("away")),
                            partida.get("data", ""))


def _desatualizado(reg):
    """True se o jogo ainda nao aconteceu e a analise tem mais de 12h."""
    data = reg.get("data") or ""
    hoje = datetime.date.today().isoformat()
    if data and data < hoje:
        return False  # jogo ja passou: analise nao precisa atualizar
    ts = reg.get("analisado_ts") or 0
    return (time.time() - ts) > 12 * 3600


def salvar(partida, resultado):
    _garante()
    chave = chave_do_jogo(partida)
    registro = {
        "chave": chave,
        "home": partida.get("home"), "away": partida.get("away"),
        "league": partida.get("league"), "country": partida.get("country"),
        "country_pt": partida.get("country_pt"),
        "data": partida.get("data"), "time": partida.get("time"),
        "venue": partida.get("venue"), "watch": partida.get("watch"),
        "home_id": partida.get("home_id"), "away_id": partida.get("away_id"),
        "id": partida.get("id"),
        "confianca": resultado.get("confianca"),
        "prognostico": resultado.get("prognostico"),
        "modelo": resultado.get("modelo"),
        "relatorio": resultado.get("relatorio"),
        "dados": resultado.get("dados"),  # JSON estruturado p/ o painel visual
        "analisado_em": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
        "analisado_ts": time.time(),
    }
    with open(os.path.join(DIR, _safe(chave) + ".json"), "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=2)
    return chave


def listar():
    _garante()
    itens = []
    for nome in os.listdir(DIR):
        if not nome.endswith(".json"):
            continue
        try:
            with open(os.path.join(DIR, nome), encoding="utf-8") as f:
                r = json.load(f)
            item = {k: r.get(k) for k in (
                "chave", "home", "away", "league", "country",
                "data", "time", "confianca", "analisado_em")}
            item["desatualizado"] = _desatualizado(r)
            itens.append(item)
        except Exception:
            pass
    itens.sort(key=lambda x: x.get("analisado_em", ""), reverse=True)
    return itens


def todos():
    _garante()
    out = []
    for nome in os.listdir(DIR):
        if not nome.endswith(".json"):
            continue
        try:
            with open(os.path.join(DIR, nome), encoding="utf-8") as f:
                out.append(json.load(f))
        except Exception:
            pass
    return out


def obter(chave):
    p = os.path.join(DIR, _safe(chave) + ".json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            r = json.load(f)
        r["desatualizado"] = _desatualizado(r)
        return r
    return None


def excluir(chave):
    p = os.path.join(DIR, _safe(chave) + ".json")
    if os.path.exists(p):
        os.remove(p)
        return True
    return False


def para_reanalisar(dias=2):
    """Relatorios de jogos que ainda vao acontecer (hoje ate hoje+dias),
    para a reanalise automatica (quando o usuario habilita)."""
    _garante()
    hoje = datetime.date.today()
    hoje_iso = hoje.isoformat()
    limite = (hoje + datetime.timedelta(days=dias)).isoformat()
    out = []
    for nome in os.listdir(DIR):
        if not nome.endswith(".json"):
            continue
        try:
            with open(os.path.join(DIR, nome), encoding="utf-8") as f:
                r = json.load(f)
            if r.get("data") and hoje_iso <= r["data"] <= limite:
                out.append(r)
        except Exception:
            pass
    return out
