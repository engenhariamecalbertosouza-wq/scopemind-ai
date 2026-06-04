# -*- coding: utf-8 -*-
"""
Modulo de CHAT AO VIVO do ScopeMind AI.

Guarda as mensagens em disco (chat/mensagens.json) e cuida das DENUNCIAS.
Usa SOMENTE a biblioteca padrao do Python. A gravacao e protegida por um
Lock (varias requisicoes chegam ao mesmo tempo, em threads diferentes).

Quem pode FALAR (VIP/admin) e quem fica SUSPENSO e decidido no server.py
(porque isso vive no config.json, junto da conta). Aqui cuidamos so das
mensagens: enviar, listar as recentes e registrar denuncias.
"""
import os
import re
import json
import time
import threading
import datetime
import unicodedata

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", "").strip() or BASE_DIR
DIR = os.path.join(DATA_DIR, "chat")
ARQ = os.path.join(DIR, "mensagens.json")

_LOCK = threading.RLock()          # serializa leitura+gravacao do arquivo
_ULTIMO_ENVIO = {}                 # usuario -> epoch do ultimo envio (anti-flood, em memoria)

# ---- regras (faceis de ajustar) ----
MAX_MENSAGENS = 400                # guarda so as ultimas (evita arquivo gigante)
MAX_TAM = 500                      # tamanho maximo de uma mensagem (caracteres)
DENUNCIAS_P_OCULTAR = 3            # denuncias (de pessoas diferentes) p/ ocultar a mensagem
STRIKES_P_SUSPENDER = 3            # mensagens ocultadas (strikes) p/ suspender a conta
INTERVALO_MIN = 2.0               # segundos minimos entre uma mensagem e a seguinte (anti-flood)
JANELA_PADRAO = 120                # quantas mensagens recentes consideramos por consulta

# Lista enxuta de palavras ofensivas (bloqueio basico). A moderacao principal
# e a DENUNCIE + suspensao automatica. Mantenha em minusculo e sem acento.
PALAVROES = [
    "merda", "porra", "caralho", "bosta", "puta", "puto", "viado", "viadinho",
    "corno", "arrombado", "arrombada", "fdp", "vsf", "vtnc", "cuzao", "cuzona",
    "buceta", "boceta", "piroca", "rola", "otario", "otaria", "imbecil",
    "idiota", "retardado", "babaca", "desgraca", "desgracado", "filho da puta",
    "vai se foder", "vai tomar no", "racista", "macaco",
]


def _garante():
    if not os.path.exists(DIR):
        os.makedirs(DIR, exist_ok=True)


def _ler():
    """Le o estado do disco. Deve ser chamado com o _LOCK ja adquirido."""
    _garante()
    if not os.path.exists(ARQ):
        return {"prox_id": 1, "mensagens": []}
    try:
        with open(ARQ, encoding="utf-8") as f:
            estado = json.load(f)
        estado.setdefault("prox_id", 1)
        estado.setdefault("mensagens", [])
        return estado
    except Exception:
        return {"prox_id": 1, "mensagens": []}


def _salvar(estado):
    """Gravacao atomica (tmp + os.replace). Chamar com o _LOCK adquirido."""
    _garante()
    tmp = ARQ + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ARQ)


def _norm(s):
    """minusculo e sem acento, p/ comparar palavras."""
    s = (s or "").lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _conteudo_proibido(texto):
    """Retorna um aviso (string) se a mensagem deve ser barrada; senao, ''."""
    low = _norm(texto)
    for termo in PALAVROES:
        # palavra inteira (com fronteiras) — evita pegar pedaco de outra palavra
        if re.search(r"(?:^|[^a-z])" + re.escape(termo) + r"(?:$|[^a-z])", low):
            return "Vamos manter o respeito 🙂 Mensagem com palavra ofensiva foi bloqueada."
    if re.search(r"https?://|www\.|t\.me/|wa\.me/|bit\.ly", texto, re.I):
        return "Links não são permitidos no chat (evita spam). Fale sobre os jogos. ⚽"
    if re.search(r"\d[\d\s().-]{8,}\d", texto):
        return "Não compartilhe telefones/contatos aqui. O chat é só sobre os jogos. 📵"
    return ""


def _publico(m):
    """Versao da mensagem que vai para o navegador (sem a lista de quem denunciou)."""
    return {
        "id": m["id"],
        "usuario": m["usuario"],
        "nome": m.get("nome") or m["usuario"],
        "role": m.get("role", "vip"),
        "texto": m.get("texto", ""),
        "hora": m.get("hora", ""),
        "data": m.get("data", ""),
        "denuncias": len(m.get("denuncias", [])),
    }


def enviar(usuario, nome, role, texto):
    """Valida e grava uma mensagem. Levanta ValueError com um aviso amigavel
    quando a mensagem nao pode ser enviada (vazia, longa, ofensiva, flood)."""
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Escreva uma mensagem.")
    if len(texto) > MAX_TAM:
        raise ValueError("Mensagem muito longa (máximo de %d caracteres)." % MAX_TAM)
    motivo = _conteudo_proibido(texto)
    if motivo:
        raise ValueError(motivo)
    agora = time.time()
    with _LOCK:
        ult = _ULTIMO_ENVIO.get(usuario, 0)
        if agora - ult < INTERVALO_MIN:
            raise ValueError("Calma! Espere um instante antes de enviar de novo.")
        estado = _ler()
        mid = estado.get("prox_id", 1)
        msg = {
            "id": mid,
            "usuario": usuario,
            "nome": nome or usuario,
            "role": role or "vip",
            "texto": texto,
            "ts": agora,
            "hora": datetime.datetime.now().strftime("%H:%M"),
            "data": datetime.date.today().isoformat(),
            "denuncias": [],
            "removida": False,
        }
        estado["mensagens"].append(msg)
        estado["mensagens"] = estado["mensagens"][-MAX_MENSAGENS:]
        estado["prox_id"] = mid + 1
        _salvar(estado)
        _ULTIMO_ENVIO[usuario] = agora
    return _publico(msg)


def recentes(desde_id=0, janela=JANELA_PADRAO):
    """Devolve (mensagens_novas, ocultos_ids, ultimo_id).

    - mensagens_novas: visiveis com id > desde_id (so as ultimas `janela`).
    - ocultos_ids: ids removidos (denunciados) na janela — o front apaga da tela.
    - ultimo_id: maior id existente (o front guarda p/ a proxima consulta).
    """
    try:
        desde_id = int(desde_id)
    except Exception:
        desde_id = 0
    with _LOCK:
        estado = _ler()
    msgs = estado.get("mensagens", [])
    recorte = msgs[-janela:] if janela else msgs
    novas = [_publico(m) for m in recorte
             if m["id"] > desde_id and not m.get("removida")]
    ocultos = [m["id"] for m in recorte if m.get("removida")]
    ultimo = estado.get("prox_id", 1) - 1
    return novas, ocultos, ultimo


def denunciar(mid, usuario):
    """Registra a denuncia de `usuario` na mensagem `mid`.

    Retorna um dicionario com:
      ok, erro?, ja (ja tinha denunciado), removida_agora (passou do limite
      agora), autor (chave do dono da mensagem), total (n de denuncias).
    """
    with _LOCK:
        estado = _ler()
        alvo = None
        for m in estado.get("mensagens", []):
            if m["id"] == mid:
                alvo = m
                break
        if not alvo:
            return {"ok": False, "erro": "Mensagem não encontrada (talvez já tenha sido removida)."}
        if alvo["usuario"] == usuario:
            return {"ok": False, "erro": "Você não pode denunciar a sua própria mensagem."}
        denuncias = alvo.setdefault("denuncias", [])
        if usuario in denuncias:
            return {"ok": True, "ja": True, "removida_agora": False,
                    "autor": alvo["usuario"], "total": len(denuncias)}
        denuncias.append(usuario)
        removida_agora = False
        if not alvo.get("removida") and len(denuncias) >= DENUNCIAS_P_OCULTAR:
            alvo["removida"] = True
            removida_agora = True
        _salvar(estado)
        return {"ok": True, "ja": False, "removida_agora": removida_agora,
                "autor": alvo["usuario"], "total": len(denuncias)}


def remover(mid):
    """Admin oculta uma mensagem manualmente."""
    with _LOCK:
        estado = _ler()
        achou = False
        for m in estado.get("mensagens", []):
            if m["id"] == mid:
                m["removida"] = True
                achou = True
        if achou:
            _salvar(estado)
        return achou


def limpar():
    """Admin apaga todo o historico do chat."""
    with _LOCK:
        _salvar({"prox_id": 1, "mensagens": []})
    return True
