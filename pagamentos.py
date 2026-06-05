# -*- coding: utf-8 -*-
"""
Pagamentos e Assinatura VIP via Mercado Pago (sem dependencias: so urllib).

- Pix: cria um pagamento Pix na API do MP e devolve QR Code + copia-e-cola
  para mostrar DENTRO do nosso site.
- Cartao: cria uma "preference" (Checkout Pro) e devolve a URL segura do MP
  para o cliente pagar la (nao guardamos dados de cartao).
- Webhook + consulta: a liberacao do VIP SO acontece quando consultamos a API
  do MP e ela diz "approved" (nunca confiamos no clique do cliente).

Credenciais: SOMENTE no backend, via variavel de ambiente MP_ACCESS_TOKEN.
Token de TESTE comeca com "TEST-" (sandbox). Producao comeca com "APP_USR-".
"""
import os
import json
import time
import uuid
import datetime
import threading
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", "").strip() or BASE_DIR
DIR = os.path.join(DATA_DIR, "pagamentos")
ARQ = os.path.join(DIR, "pagamentos.json")
_LOCK = threading.Lock()

MP_API = "https://api.mercadopago.com"
FUSO_BR = datetime.timezone(datetime.timedelta(hours=-3))

# ---- Plano VIP (promo dos 1000 primeiros): de R$ 99,90 por R$ 49,90 ----
def plano():
    preco = os.environ.get("VIP_PRECO", "").strip()
    try:
        preco = float(preco.replace(",", ".")) if preco else 49.90
    except Exception:
        preco = 49.90
    try:
        dias = max(1, int(os.environ.get("VIP_DIAS", "30")))
    except Exception:
        dias = 30
    return {
        "nome": "Plano VIP",
        "preco": round(preco, 2),
        "preco_de": 99.90,           # valor "cheio" (promocao)
        "duracao_dias": dias,
        "promo": "Você é um dos 1000 primeiros clientes!",
        "beneficios": [
            "Rodadas (análises) ILIMITADAS",
            "Acesso liberado na hora após o pagamento",
            "Chat ao vivo exclusivo VIP",
            "Pagamento seguro via Mercado Pago",
            "Pix, QR Code ou cartão de crédito",
            "Liberação automática",
        ],
    }


# ---------------------------------------------------------------------------
# Armazenamento (arquivo JSON; mesma ideia dos outros modulos)
# ---------------------------------------------------------------------------
def _garante():
    if not os.path.exists(DIR):
        os.makedirs(DIR, exist_ok=True)


def _ler():
    if not os.path.exists(ARQ):
        return {}
    try:
        with open(ARQ, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _salvar(d):
    _garante()
    tmp = ARQ + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ARQ)


def _agora():
    return datetime.datetime.now(FUSO_BR).strftime("%d/%m/%Y %H:%M")


# ---------------------------------------------------------------------------
# Cliente HTTP do Mercado Pago (urllib)
# ---------------------------------------------------------------------------
def mp_token():
    return (os.environ.get("MP_ACCESS_TOKEN") or "").strip()


def mp_configurado():
    return bool(mp_token())


def _sandbox():
    return mp_token().startswith("TEST-")


def _app_url():
    return (os.environ.get("APP_URL") or "https://scopemind-ai.com.br").strip().rstrip("/")


def _mp(method, path, body=None):
    """Chamada a API do MP. Levanta RuntimeError com a mensagem do MP em erro."""
    token = mp_token()
    if not token:
        raise RuntimeError("Mercado Pago nao configurado (falta MP_ACCESS_TOKEN).")
    url = MP_API + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    if method == "POST":
        req.add_header("X-Idempotency-Key", uuid.uuid4().hex)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf-8"))
            msg = err.get("message") or err.get("error") or str(err)
        except Exception:
            msg = "HTTP %s" % e.code
        raise RuntimeError("Mercado Pago: %s" % msg)
    except Exception as e:
        raise RuntimeError("Falha de rede com o Mercado Pago: %s" % e)


# ---------------------------------------------------------------------------
# Criar pagamentos
# ---------------------------------------------------------------------------
def _novo_id():
    return "pg-" + uuid.uuid4().hex[:16]


def _registrar(reg):
    with _LOCK:
        d = _ler()
        d[reg["id"]] = reg
        _salvar(d)
    return reg


def _criar_checkout(usuario_key, email, nome, foco):
    """Cria uma preference (Checkout Pro) e devolve o registro com checkout_url.
    foco='pix' mostra so Pix; foco='cartao' mostra so cartao. (Funciona em teste e
    em producao sem precisar de homologacao do Pagamentos API.)"""
    p = plano()
    nosso_id = _novo_id()
    base = _app_url()
    if foco == "pix":
        excluded = [{"id": "credit_card"}, {"id": "debit_card"}, {"id": "ticket"}, {"id": "atm"}]
    else:
        excluded = [{"id": "ticket"}, {"id": "bank_transfer"}, {"id": "atm"}]
    body = {
        "items": [{
            "title": "Plano VIP ScopeMind AI",
            "quantity": 1, "unit_price": p["preco"], "currency_id": "BRL",
        }],
        "payer": {"email": email or "", "name": (nome or "")[:40]},
        "external_reference": usuario_key,
        "notification_url": base + "/api/mp/webhook",
        "metadata": {"nosso_id": nosso_id, "usuario": usuario_key},
        "back_urls": {
            "success": base + "/?vip=ok",
            "pending": base + "/?vip=pendente",
            "failure": base + "/?vip=falhou",
        },
        "auto_return": "approved",
        "payment_methods": {"excluded_payment_types": excluded},
    }
    resp = _mp("POST", "/checkout/preferences", body)
    url = resp.get("init_point") or resp.get("sandbox_init_point")
    reg = {
        "id": nosso_id, "usuario": usuario_key, "provider": "mercadopago",
        "provider_payment_id": "", "preference_id": str(resp.get("id") or ""),
        "amount": p["preco"], "status": "pending", "payment_method": foco,
        "qr_code": "", "qr_code_base64": "", "pix_copy_paste": "", "ticket_url": "",
        "checkout_url": url or "", "vip_liberado": False, "paid_at": "",
        "created_at": _agora(), "updated_at": _agora(),
    }
    return _registrar(reg)


def criar_pix(usuario_key, email, nome):
    return _criar_checkout(usuario_key, email, nome, "pix")


def criar_cartao(usuario_key, email, nome):
    return _criar_checkout(usuario_key, email, nome, "cartao")


# ---------------------------------------------------------------------------
# Consultar / confirmar pagamento (a verdade vem SEMPRE da API do MP)
# ---------------------------------------------------------------------------
def obter(nosso_id):
    return _ler().get(nosso_id)


def _atualizar(nosso_id, campos):
    with _LOCK:
        d = _ler()
        reg = d.get(nosso_id)
        if not reg:
            return None
        reg.update(campos)
        reg["updated_at"] = _agora()
        d[nosso_id] = reg
        _salvar(d)
        return reg


def consultar_mp_por_provider_id(mp_payment_id):
    """GET /v1/payments/{id} - status real do pagamento no MP."""
    return _mp("GET", "/v1/payments/%s" % mp_payment_id)


def sincronizar(nosso_id):
    """Consulta o MP e atualiza nosso registro. Devolve (registro, aprovado_agora).
    'aprovado_agora' = True so na PRIMEIRA vez que vira approved (para liberar VIP 1x)."""
    reg = obter(nosso_id)
    if not reg:
        return None, False
    pid = reg.get("provider_payment_id")
    if not pid:
        # cartao (Checkout Pro): tentamos achar pelo external_reference
        achado = _buscar_provider_por_referencia(reg["usuario"])
        if achado:
            pid = str(achado.get("id"))
            reg = _atualizar(nosso_id, {"provider_payment_id": pid,
                                        "payment_method": achado.get("payment_type_id") or reg.get("payment_method")})
    if not pid:
        return reg, False
    try:
        mp = consultar_mp_por_provider_id(pid)
    except Exception:
        return reg, False
    return _aplicar_status_mp(nosso_id, mp)


def _aplicar_status_mp(nosso_id, mp):
    reg = obter(nosso_id)
    if not reg:
        return None, False
    status = mp.get("status") or "pending"   # approved/pending/rejected/cancelled/refunded
    ja_liberado = bool(reg.get("vip_liberado"))
    campos = {"status": status,
              "provider_payment_id": str(mp.get("id") or reg.get("provider_payment_id") or ""),
              "amount_pago": mp.get("transaction_amount"),
              "payment_method": mp.get("payment_type_id") or reg.get("payment_method")}
    aprovado_agora = False
    if status == "approved":
        campos["paid_at"] = reg.get("paid_at") or _agora()
        # confere o valor (anti-fraude): pago >= preco do plano
        try:
            valor_ok = float(mp.get("transaction_amount") or 0) + 0.001 >= float(reg.get("amount") or 0)
        except Exception:
            valor_ok = True
        if valor_ok and not ja_liberado:
            campos["vip_liberado"] = True
            aprovado_agora = True
    reg = _atualizar(nosso_id, campos)
    return reg, aprovado_agora


def _buscar_provider_por_referencia(usuario_key):
    """Procura no MP um pagamento approved deste usuario (para o fluxo de cartao)."""
    try:
        resp = _mp("GET", "/v1/payments/search?sort=date_created&criteria=desc&external_reference=%s"
                   % urllib_quote(usuario_key))
        for r in (resp.get("results") or []):
            if r.get("status") == "approved":
                return r
        results = resp.get("results") or []
        return results[0] if results else None
    except Exception:
        return None


def processar_webhook_payment(mp_payment_id):
    """Recebe o id do pagamento (do webhook), consulta o MP e atualiza o nosso
    registro. Devolve (registro, aprovado_agora). Liga pelo metadata/external_reference."""
    try:
        mp = consultar_mp_por_provider_id(mp_payment_id)
    except Exception:
        return None, False
    nosso_id = ((mp.get("metadata") or {}).get("nosso_id")) or ""
    if not nosso_id:
        # acha pelo provider_payment_id ja salvo, ou cria/atualiza pelo external_reference
        d = _ler()
        for k, reg in d.items():
            if str(reg.get("provider_payment_id")) == str(mp_payment_id):
                nosso_id = k
                break
        if not nosso_id:
            ref = mp.get("external_reference") or ""
            nosso_id = _novo_id()
            _registrar({
                "id": nosso_id, "usuario": ref, "provider": "mercadopago",
                "provider_payment_id": str(mp_payment_id), "amount": mp.get("transaction_amount"),
                "status": "pending", "payment_method": mp.get("payment_type_id") or "cartao",
                "qr_code": "", "qr_code_base64": "", "pix_copy_paste": "", "ticket_url": "",
                "checkout_url": "", "vip_liberado": False, "paid_at": "",
                "created_at": _agora(), "updated_at": _agora(),
            })
    return _aplicar_status_mp(nosso_id, mp)


def urllib_quote(s):
    import urllib.parse
    return urllib.parse.quote(str(s), safe="")


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
def listar_admin():
    d = _ler()
    itens = list(d.values())
    itens.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    # nao expoe campos enormes do QR na listagem
    out = []
    for r in itens:
        out.append({k: r.get(k) for k in (
            "id", "usuario", "amount", "amount_pago", "status", "payment_method",
            "provider_payment_id", "paid_at", "vip_liberado", "created_at", "updated_at")})
    return out


def status_do_usuario(usuario_key):
    """Ultimo pagamento conhecido deste usuario (para a tela do cliente)."""
    d = _ler()
    meus = [r for r in d.values() if r.get("usuario") == usuario_key]
    meus.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return meus[0] if meus else None
