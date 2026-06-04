# -*- coding: utf-8 -*-
"""
Servidor local do "Analise Futebol IA".
Usa SOMENTE a biblioteca padrao do Python (nenhuma instalacao extra).
Sobe um site em http://localhost:8765 com tela de login, jogos de hoje/semana/mes
e analise com os 10 agentes (cerebro: Claude API da Anthropic).
"""
import os
import re
import sys
import json
import hmac
import hashlib
import secrets
import time
import threading
import webbrowser
import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
IMAGENS_DIR = os.path.join(BASE_DIR, "imagens")
# DATA_DIR = onde ficam os DADOS que precisam sobreviver (config.json, cache,
# relatorios, chat, comunidade). LOCAL = a propria pasta do projeto. Na HOSPEDAGEM,
# aponte para o DISCO PERMANENTE da Render pela variavel de ambiente DATA_DIR
# (ex.: /var/data) — assim cadastros, chat e palpites NAO somem a cada atualizacao.
DATA_DIR = os.environ.get("DATA_DIR", "").strip() or BASE_DIR
os.makedirs(DATA_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
PORT = 8765
ULTIMA_ATUALIZACAO = {"quando": "ainda nao"}
_ANALISES_HOJE = {"dia": "", "qtd": 0}  # teto diario de analises (protecao de custo)

# Garante que conseguimos importar os modulos vizinhos
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import agentes          # noqa: E402
import dados_futebol    # noqa: E402
import relatorios       # noqa: E402
import chat             # noqa: E402
import comunidade       # noqa: E402


# ----------------------------------------------------------------------------
# Configuracao (chaves de API, usuarios, etc.)
# ----------------------------------------------------------------------------
def _hash_senha(senha, salt):
    return hashlib.sha256((salt + senha).encode("utf-8")).hexdigest()


def _config_raw():
    if not os.path.exists(CONFIG_PATH):
        criar_config_padrao()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def carregar_config():
    cfg = _config_raw()
    # Na HOSPEDAGEM, variaveis de ambiente sobrescrevem o config.json (mantem chaves fora do codigo).
    if os.environ.get("ANTHROPIC_API_KEY"):
        cfg["anthropic_api_key"] = os.environ["ANTHROPIC_API_KEY"].strip()
    if os.environ.get("FOOTBALL_API_KEY"):
        cfg["football_api_key"] = os.environ["FOOTBALL_API_KEY"].strip()
    if os.environ.get("ANTHROPIC_MODEL"):
        cfg["anthropic_model"] = os.environ["ANTHROPIC_MODEL"].strip()
    if os.environ.get("APP_SECRET"):
        cfg["secret"] = os.environ["APP_SECRET"].strip()
    if os.environ.get("ADMIN_PASSWORD"):
        usuario = (os.environ.get("ADMIN_USER", "admin").strip() or "admin")
        salt = "env-" + cfg.get("secret", "x")[:8]
        cfg.setdefault("usuarios", {})
        cfg["usuarios"][usuario] = {"salt": salt, "hash": _hash_senha(os.environ["ADMIN_PASSWORD"].strip(), salt), "role": "admin"}
    return cfg


def salvar_config(cfg):
    # gravacao atomica (evita config.json corrompido se 2 requisicoes salvarem juntas)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)


def criar_config_padrao():
    salt = secrets.token_hex(8)
    cfg = {
        "anthropic_api_key": "",
        "anthropic_model": "claude-opus-4-8",
        "football_api_key": "",
        "auto_reanalise": False,
        "secret": secrets.token_hex(16),
        "usuarios": {
            "admin": {"salt": salt, "hash": _hash_senha("admin", salt), "role": "admin"}
        }
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print(">> config.json criado (login padrao: admin / admin)")


def gerar_token(cfg, usuario):
    return hmac.new(cfg["secret"].encode(), usuario.encode(), hashlib.sha256).hexdigest()


def token_valido(cfg, token):
    if not token:
        return False
    for usuario in cfg.get("usuarios", {}):
        if hmac.compare_digest(token, gerar_token(cfg, usuario)):
            return True
    return False


def usuario_do_token(cfg, token):
    if not token:
        return None
    for usuario in cfg.get("usuarios", {}):
        if hmac.compare_digest(token, gerar_token(cfg, usuario)):
            return usuario
    return None


def cpf_valido(cpf):
    c = re.sub(r"\D", "", cpf or "")
    if len(c) != 11 or c == c[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(c[j]) * ((i + 1) - j) for j in range(i))
        dig = (soma * 10) % 11
        if dig == 10:
            dig = 0
        if dig != int(c[i]):
            return False
    return True


def _pode_analisar():
    """Teto diario de analises com IA (protege contra gasto excessivo)."""
    import time as _t
    hoje = _t.strftime("%Y-%m-%d")
    if _ANALISES_HOJE["dia"] != hoje:
        _ANALISES_HOJE["dia"] = hoje
        _ANALISES_HOJE["qtd"] = 0
    limite = int(os.environ.get("MAX_ANALISES_DIA", "30"))
    if _ANALISES_HOJE["qtd"] >= limite:
        return False
    _ANALISES_HOJE["qtd"] += 1
    return True


def _eh_admin(u):
    """True se o usuario e administrador (conta legada sem 'role' = admin)."""
    return u.get("role", "admin") == "admin"


def _pode_chat(u):
    """Quem pode acessar o chat: o admin OU um cliente VIP com prazo válido."""
    return _vip_valido(u)


def _limite_gratis(cfg):
    """Quantas analises gratis cada cliente comum tem. O admin define pela
    engrenagem (config.json); se nao definiu, usa a variavel de ambiente; senao, 3."""
    v = cfg.get("limite_analises_gratis")
    if v is None or v == "":
        v = os.environ.get("LIMITE_ANALISES_GRATIS", "3")
    try:
        return max(0, int(v))
    except Exception:
        return 3


VIP_DIAS = int(os.environ.get("VIP_DIAS", "30"))   # duracao do VIP em dias


def _vip_valido(u):
    """VIP ativo: admin sempre; cliente com vip=True e prazo nao vencido
    (vip_ate ausente = VIP sem prazo/vitalicio)."""
    if _eh_admin(u):
        return True
    if not u.get("vip"):
        return False
    ate = u.get("vip_ate")
    if not ate:
        return True
    try:
        return time.time() < float(ate)
    except Exception:
        return True


# ----------------------------------------------------------------------------
# Servidor HTTP
# ----------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # silencio no console (evita poluir a janela)

    # ---- utilidades ----
    def _json(self, obj, status=200):
        corpo = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _corpo_json(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            if n <= 0:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _query(self):
        d = {}
        if "?" in self.path:
            for par in self.path.split("?", 1)[1].split("&"):
                if "=" in par:
                    k, v = par.split("=", 1)
                    d[k] = urllib.parse.unquote(v)
        return d

    def _token(self):
        return self.headers.get("X-Auth-Token", "")

    def _arquivo(self, caminho_rel):
        caminho = os.path.join(WEB_DIR, caminho_rel)
        caminho = os.path.normpath(caminho)
        if not caminho.startswith(WEB_DIR):  # evita acesso fora da pasta web
            self.send_error(403)
            return
        if not os.path.exists(caminho) or os.path.isdir(caminho):
            self.send_error(404)
            return
        tipo = mimetypes.guess_type(caminho)[0] or "application/octet-stream"
        with open(caminho, "rb") as f:
            dados = f.read()
        self.send_response(200)
        self.send_header("Content-Type", tipo + ("; charset=utf-8" if tipo.startswith("text") or "javascript" in tipo else ""))
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "no-cache")  # navegador sempre revalida (pega versao nova)
        self.end_headers()
        self.wfile.write(dados)

    def _arquivo_imagem(self, rel):
        caminho = os.path.normpath(os.path.join(IMAGENS_DIR, rel))
        if not caminho.startswith(IMAGENS_DIR) or not os.path.isfile(caminho):
            self.send_error(404)
            return
        tipo = mimetypes.guess_type(caminho)[0] or "application/octet-stream"
        with open(caminho, "rb") as f:
            dados = f.read()
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("Cache-Control", "max-age=86400")
        self.end_headers()
        self.wfile.write(dados)

    # ---- GET ----
    def do_GET(self):
        try:
            rota = self.path.split("?")[0]
            if rota == "/" or rota == "/index.html":
                self._arquivo("index.html")
            elif rota.startswith("/api/"):
                self._api_get(rota)
            elif rota.startswith("/imagens/"):
                self._arquivo_imagem(rota[len("/imagens/"):])
            else:
                self._arquivo(rota.lstrip("/"))
        except Exception as e:
            self._json({"erro": "Falha interna: %s" % e}, 500)

    def _api_get(self, rota):
        cfg = carregar_config()
        if rota == "/api/status":
            self._json({
                "ao_vivo_dados": bool(cfg.get("football_api_key")),
                "ao_vivo_ia": bool(cfg.get("anthropic_api_key")),
                "modelo": cfg.get("anthropic_model", "claude-opus-4-8"),
                "auto_reanalise": bool(cfg.get("auto_reanalise")),
                "limite_analises_gratis": _limite_gratis(cfg),
                "ultima_atualizacao": ULTIMA_ATUALIZACAO["quando"],
            })
            return
        if rota == "/api/jogos":
            params = {}
            if "?" in self.path:
                for par in self.path.split("?", 1)[1].split("&"):
                    if "=" in par:
                        k, v = par.split("=", 1)
                        params[k] = v
            periodo = params.get("periodo", "hoje")
            try:
                jogos, modo, aviso = dados_futebol.listar_jogos(periodo, cfg)
                self._json({"jogos": jogos, "modo": modo, "aviso": aviso, "periodo": periodo})
            except Exception as e:
                self._json({"erro": "Nao consegui buscar os jogos: %s" % e}, 500)
            return
        if rota == "/api/tabela":
            q = self._query()
            try:
                tab = dados_futebol.tabela(q.get("league", ""), q.get("season", ""), cfg)
                self._json({"tabela": tab})
            except Exception as e:
                self._json({"erro": "Nao consegui a tabela: %s" % e}, 500)
            return
        if rota == "/api/placar":
            self._placar(cfg)
            return
        if rota == "/api/relatorios":
            self._json({"relatorios": relatorios.listar()})
            return
        if rota == "/api/relatorio":
            chave = self._query().get("chave", "")
            r = relatorios.obter(chave)
            if r:
                self._json(r)
            else:
                self._json({"erro": "Relatorio nao encontrado."}, 404)
            return
        if rota == "/api/chat":
            self._chat_poll(cfg)
            return
        if rota == "/api/chat/usuarios":
            self._chat_usuarios(cfg)
            return
        if rota == "/api/comunidade/jogos":
            self._com_jogos(cfg)
            return
        if rota == "/api/comunidade/ranking":
            self._com_ranking(cfg)
            return
        if rota == "/api/comunidade/eu":
            self._com_eu(cfg)
            return
        if rota == "/api/comunidade/admin/usuarios":
            self._com_admin_usuarios(cfg)
            return
        if rota == "/api/comunidade/admin/palpites":
            self._com_admin_palpites(cfg)
            return
        if rota == "/api/comunidade/admin/exportar":
            self._com_admin_exportar(cfg)
            return
        if rota == "/api/conta":
            self._conta(cfg)
            return
        self._json({"erro": "rota nao encontrada"}, 404)

    def _placar(self, cfg):
        if not token_valido(cfg, self._token()):
            self._json({"erro": "Nao autorizado."}, 401)
            return
        regs = relatorios.todos()
        resultados = {}
        for per in ("ontem", "hoje"):
            try:
                jogos, _, _ = dados_futebol.listar_jogos(per, cfg)
                for j in jogos:
                    resultados[relatorios.chave_do_jogo(j)] = j
            except Exception:
                pass
        itens, acertos, erros = [], 0, 0
        for r in regs:
            jogo = resultados.get(r.get("chave"))
            item = {
                "home": r.get("home"), "away": r.get("away"), "data": r.get("data"),
                "league": r.get("league"), "country_pt": r.get("country_pt"),
                "prognostico": r.get("prognostico"), "confianca": r.get("confianca"),
                "chave": r.get("chave"), "situacao": "pendente",
            }
            if jogo and "encerrad" in (jogo.get("status", "") or "").lower() and jogo.get("score"):
                item["placar"] = jogo.get("score")
                try:
                    h, a = [int(x) for x in jogo["score"].split(" - ")]
                    real = "Casa" if h > a else ("Fora" if a > h else "Empate")
                    item["vencedor_real"] = real
                    if r.get("prognostico"):
                        ok = (r["prognostico"] == real)
                        item["situacao"] = "acerto" if ok else "erro"
                        if ok:
                            acertos += 1
                        else:
                            erros += 1
                    else:
                        item["situacao"] = "encerrado"
                except Exception:
                    item["situacao"] = "encerrado"
            itens.append(item)
        total = acertos + erros
        pct = round(100 * acertos / total) if total else None
        self._json({"itens": itens, "acertos": acertos, "erros": erros, "total": total, "pct": pct})

    # ---- POST ----
    def do_POST(self):
        try:
            rota = self.path.split("?")[0]
            if rota == "/api/login":
                self._login()
            elif rota == "/api/cadastrar":
                self._cadastrar()
            elif rota == "/api/configurar":
                self._configurar()
            elif rota == "/api/analisar":
                self._analisar()
            elif rota == "/api/excluir-relatorio":
                self._excluir_relatorio()
            elif rota == "/api/chat/enviar":
                self._chat_enviar()
            elif rota == "/api/chat/denunciar":
                self._chat_denunciar()
            elif rota == "/api/chat/usuario":
                self._chat_set_usuario()
            elif rota == "/api/chat/remover":
                self._chat_remover()
            elif rota == "/api/chat/limpar":
                self._chat_limpar()
            elif rota == "/api/comunidade/palpitar":
                self._com_palpitar()
            elif rota == "/api/comunidade/admin/resultado":
                self._com_admin_resultado()
            elif rota == "/api/comunidade/admin/reprocessar":
                self._com_admin_reprocessar()
            elif rota == "/api/comunidade/admin/ajustar-xp":
                self._com_admin_ajustar()
            elif rota == "/api/comunidade/admin/bloquear":
                self._com_admin_bloquear()
            elif rota == "/api/trocar-senha":
                self._trocar_senha()
            else:
                self._json({"erro": "rota nao encontrada"}, 404)
        except Exception as e:
            self._json({"erro": "Falha interna: %s" % e}, 500)

    def _login(self):
        cfg = carregar_config()
        dados = self._corpo_json()
        entrada = (dados.get("usuario") or "").strip()
        senha = (dados.get("senha") or "").strip()  # ignora espacos acidentais (autofill/copiar-colar)
        usuarios = cfg.get("usuarios", {})
        chave = entrada if entrada in usuarios else entrada.lower()
        u = usuarios.get(chave)
        if u and hmac.compare_digest(u["hash"], _hash_senha(senha, u["salt"])):
            role = u.get("role", "admin")
            resp = {"ok": True, "token": gerar_token(cfg, chave), "usuario": u.get("nome", chave), "role": role,
                    "vip": _vip_valido(u)}
            if role == "cliente" and not _vip_valido(u):
                limite = _limite_gratis(cfg)
                resp["analises_restantes"] = max(0, limite - len(u.get("jogos_abertos", [])))
            self._json(resp)
        else:
            self._json({"ok": False, "erro": "Usuário ou senha incorretos."}, 401)

    def _cadastrar(self):
        dados = self._corpo_json()
        nome = (dados.get("nome") or "").strip()
        email = (dados.get("email") or "").strip().lower()
        cpf = re.sub(r"\D", "", dados.get("cpf") or "")
        senha = (dados.get("senha") or "").strip()  # ignora espacos acidentais
        if len(nome) < 2:
            self._json({"erro": "Informe o seu nome."}, 400)
            return
        if "@" not in email or "." not in email.split("@")[-1]:
            self._json({"erro": "E-mail inválido."}, 400)
            return
        if not cpf_valido(cpf):
            self._json({"erro": "CPF inválido. Confira os números."}, 400)
            return
        if len(senha) < 4:
            self._json({"erro": "A senha precisa ter ao menos 4 caracteres."}, 400)
            return
        raw = _config_raw()
        usuarios = raw.setdefault("usuarios", {})
        if email in usuarios:
            self._json({"erro": "Este e-mail já está cadastrado."}, 409)
            return
        for ex in usuarios.values():
            if ex.get("cpf") == cpf:
                self._json({"erro": "Este CPF já está cadastrado."}, 409)
                return
        salt = secrets.token_hex(8)
        usuarios[email] = {
            "salt": salt, "hash": _hash_senha(senha, salt), "role": "cliente",
            "nome": nome, "email": email, "cpf": cpf, "analises_usadas": 0,
            "criado_em": time.strftime("%d/%m/%Y %H:%M"),
        }
        salvar_config(raw)
        cfg = carregar_config()
        limite = _limite_gratis(cfg)
        self._json({"ok": True, "token": gerar_token(cfg, email), "usuario": nome,
                    "role": "cliente", "vip": False, "analises_restantes": limite})

    def _configurar(self):
        cfg = carregar_config()
        usuario = usuario_do_token(cfg, self._token())
        if not usuario or cfg.get("usuarios", {}).get(usuario, {}).get("role", "admin") != "admin":
            self._json({"erro": "Apenas o administrador pode alterar as configuracoes."}, 403)
            return
        dados = self._corpo_json()
        if "anthropic_api_key" in dados:
            cfg["anthropic_api_key"] = dados["anthropic_api_key"].strip()
        if "football_api_key" in dados:
            cfg["football_api_key"] = dados["football_api_key"].strip()
        if dados.get("anthropic_model"):
            cfg["anthropic_model"] = dados["anthropic_model"].strip()
        if "auto_reanalise" in dados:
            cfg["auto_reanalise"] = bool(dados["auto_reanalise"])
        if "limite_analises_gratis" in dados:
            try:
                cfg["limite_analises_gratis"] = max(0, int(dados["limite_analises_gratis"]))
            except Exception:
                pass
        salvar_config(cfg)
        self._json({"ok": True})

    def _analisar(self):
        cfg = carregar_config()
        usuario = usuario_do_token(cfg, self._token())
        if not usuario:
            self._json({"erro": "Nao autorizado."}, 401)
            return
        u = cfg.get("usuarios", {}).get(usuario, {})
        is_admin = _eh_admin(u)
        is_vip = _vip_valido(u)
        # So o cliente COMUM (nao-VIP) tem limite. VIP e admin = ilimitado.
        cliente_limitado = (u.get("role", "admin") == "cliente") and not is_vip
        limite_gratis = _limite_gratis(cfg)

        partida = self._corpo_json()
        import datetime as _dt
        _data = partida.get("data", "")
        if ("encerrad" in (partida.get("status", "") or "").lower()) or (_data and _data < _dt.date.today().isoformat()):
            self._json({"erro": "Jogo ja encerrado ou passado — analise com IA indisponivel (economia)."}, 400)
            return

        # REAPROVEITAMENTO: se ja existe analise salva deste jogo, mostramos ela
        # (custo ZERO — nao chama a IA). So roda de novo se nao existir nenhuma,
        # ou se o ADMIN pedir "forcar" (botao Refazer).
        chave = relatorios.chave_do_jogo(partida)
        existente = relatorios.obter(chave)
        forcar = bool(partida.get("forcar")) and is_admin
        reaproveitar = (existente is not None) and not forcar

        # Controle de credito do cliente comum: cada JOGO diferente gasta 1 das 3;
        # reabrir o MESMO jogo nao cobra de novo.
        abertos = list(u.get("jogos_abertos", []))
        jogo_novo = chave not in abertos
        if cliente_limitado and jogo_novo and len(abertos) >= limite_gratis:
            self._json({"erro": "Você já usou suas %d análises grátis. Vire membro VIP para liberar análises ilimitadas." % limite_gratis}, 402)
            return

        if reaproveitar:
            resultado = {
                "relatorio": existente.get("relatorio"),
                "dados": existente.get("dados"),
                "confianca": existente.get("confianca"),
                "prognostico": existente.get("prognostico"),
                "modelo": existente.get("modelo"),
                "chave": chave,
                "reaproveitado": True,
            }
        else:
            if not cfg.get("anthropic_api_key"):
                self._json({"erro": "Chave da IA (Anthropic) nao configurada. Clique na engrenagem e cole sua chave."}, 400)
                return
            if not _pode_analisar():
                self._json({"erro": "Limite diario de analises atingido (protecao de custo). Tente novamente amanha."}, 429)
                return
            try:
                contexto = dados_futebol.coletar_contexto(partida, cfg)
                resultado = agentes.analisar(partida, contexto, cfg)
                try:
                    resultado["chave"] = relatorios.salvar(partida, resultado)
                except Exception:
                    resultado["chave"] = chave
            except Exception as e:
                self._json({"erro": "Falha ao analisar: %s" % e}, 500)
                return

        # Cobra 1 credito do cliente comum (so quando e um jogo novo p/ ele).
        if cliente_limitado:
            if jogo_novo:
                raw = _config_raw()
                ru = raw.get("usuarios", {}).get(usuario)
                if ru is not None:
                    ab = list(ru.get("jogos_abertos", []))
                    if chave not in ab:
                        ab.append(chave)
                    ru["jogos_abertos"] = ab
                    ru["analises_usadas"] = len(ab)
                    salvar_config(raw)
                    abertos = ab
                else:
                    abertos = abertos + [chave]
            resultado["analises_restantes"] = max(0, limite_gratis - len(abertos))

        self._json(resultado)

    def _excluir_relatorio(self):
        cfg = carregar_config()
        if not token_valido(cfg, self._token()):
            self._json({"erro": "Nao autorizado."}, 401)
            return
        chave = self._corpo_json().get("chave", "")
        self._json({"ok": relatorios.excluir(chave)})

    # ---- CHAT AO VIVO ----
    def _eu_chat(self, usuario, u):
        """Resumo do usuario logado, p/ o front decidir o que mostrar no chat."""
        admin = _eh_admin(u)
        return {
            "usuario": usuario,
            "nome": u.get("nome", usuario),
            "role": "admin" if admin else ("vip" if _vip_valido(u) else "cliente"),
            "admin": admin,
            "vip": _vip_valido(u),
            "suspenso": bool(u.get("suspenso")),
            "pode_falar": _pode_chat(u) and not u.get("suspenso"),
        }

    def _chat_poll(self, cfg):
        usuario = usuario_do_token(cfg, self._token())
        if not usuario:
            self._json({"erro": "Nao autorizado."}, 401)
            return
        u = cfg.get("usuarios", {}).get(usuario, {})
        eu = self._eu_chat(usuario, u)
        if not _pode_chat(u):
            self._json({"acesso": False, "eu": eu, "mensagens": [], "ocultos": [], "ultimo_id": 0})
            return
        desde = self._query().get("desde", "0")
        novas, ocultos, ultimo = chat.recentes(desde)
        self._json({"acesso": True, "eu": eu, "mensagens": novas,
                    "ocultos": ocultos, "ultimo_id": ultimo})

    def _chat_enviar(self):
        cfg = carregar_config()
        usuario = usuario_do_token(cfg, self._token())
        if not usuario:
            self._json({"erro": "Nao autorizado."}, 401)
            return
        u = cfg.get("usuarios", {}).get(usuario, {})
        if not _pode_chat(u):
            self._json({"erro": "O chat é exclusivo para membros VIP. Fale com o suporte para liberar."}, 403)
            return
        if u.get("suspenso"):
            self._json({"erro": "Sua conta está suspensa no chat por denúncias. Você pode ler, mas não enviar."}, 403)
            return
        role = "admin" if _eh_admin(u) else "vip"
        nome = u.get("nome", usuario)
        texto = self._corpo_json().get("texto", "")
        try:
            msg = chat.enviar(usuario, nome, role, texto)
        except ValueError as e:
            self._json({"erro": str(e)}, 400)
            return
        self._json({"ok": True, "mensagem": msg})

    def _chat_denunciar(self):
        cfg = carregar_config()
        usuario = usuario_do_token(cfg, self._token())
        if not usuario:
            self._json({"erro": "Nao autorizado."}, 401)
            return
        u = cfg.get("usuarios", {}).get(usuario, {})
        if not _pode_chat(u):
            self._json({"erro": "Apenas membros do chat podem denunciar."}, 403)
            return
        try:
            mid = int(self._corpo_json().get("id"))
        except Exception:
            self._json({"erro": "Mensagem inválida."}, 400)
            return
        res = chat.denunciar(mid, usuario)
        if not res.get("ok"):
            self._json({"erro": res.get("erro", "Não foi possível denunciar.")}, 400)
            return
        suspenso_autor = False
        if res.get("removida_agora"):
            autor = res.get("autor")
            raw = _config_raw()
            au = raw.get("usuarios", {}).get(autor)
            if au and not _eh_admin(au):   # o admin nunca e suspenso
                au["strikes"] = au.get("strikes", 0) + 1
                if au["strikes"] >= chat.STRIKES_P_SUSPENDER:
                    au["suspenso"] = True
                    suspenso_autor = True
                salvar_config(raw)
        self._json({"ok": True, "removida": res.get("removida_agora", False),
                    "suspenso_autor": suspenso_autor, "total": res.get("total")})

    def _chat_usuarios(self, cfg):
        """Lista de clientes (so admin) p/ liberar VIP e moderar."""
        usuario = usuario_do_token(cfg, self._token())
        u = cfg.get("usuarios", {}).get(usuario, {})
        if not usuario or not _eh_admin(u):
            self._json({"erro": "Apenas o administrador."}, 403)
            return
        raw = _config_raw()
        out = []
        for chave, info in raw.get("usuarios", {}).items():
            if _eh_admin(info):
                continue
            out.append({
                "email": info.get("email", chave),
                "nome": info.get("nome", chave),
                "vip": bool(info.get("vip")),
                "suspenso": bool(info.get("suspenso")),
                "strikes": info.get("strikes", 0),
                "criado_em": info.get("criado_em", ""),
            })
        out.sort(key=lambda x: (x["nome"] or "").lower())
        self._json({"usuarios": out})

    def _chat_set_usuario(self):
        """Admin marca/desmarca VIP e suspende/reativa um cliente."""
        cfg = carregar_config()
        usuario = usuario_do_token(cfg, self._token())
        u = cfg.get("usuarios", {}).get(usuario, {})
        if not usuario or not _eh_admin(u):
            self._json({"erro": "Apenas o administrador."}, 403)
            return
        dados = self._corpo_json()
        email = (dados.get("email") or "").strip().lower()
        raw = _config_raw()
        alvo = raw.get("usuarios", {}).get(email)
        if not alvo:
            self._json({"erro": "Cliente não encontrado."}, 404)
            return
        if "vip" in dados:
            alvo["vip"] = bool(dados["vip"])
            # Ao tornar VIP, define o prazo de VIP_DIAS dias (renovar = clicar de novo).
            alvo["vip_ate"] = (time.time() + VIP_DIAS * 86400) if dados["vip"] else None
        if "suspenso" in dados:
            alvo["suspenso"] = bool(dados["suspenso"])
            if not dados["suspenso"]:
                alvo["strikes"] = 0   # ao reativar, zera os strikes
        salvar_config(raw)
        self._json({"ok": True})

    def _chat_remover(self):
        """Admin oculta uma mensagem manualmente."""
        cfg = carregar_config()
        usuario = usuario_do_token(cfg, self._token())
        u = cfg.get("usuarios", {}).get(usuario, {})
        if not usuario or not _eh_admin(u):
            self._json({"erro": "Apenas o administrador."}, 403)
            return
        try:
            mid = int(self._corpo_json().get("id"))
        except Exception:
            self._json({"erro": "Mensagem inválida."}, 400)
            return
        self._json({"ok": chat.remover(mid)})

    def _chat_limpar(self):
        """Admin apaga todo o historico do chat."""
        cfg = carregar_config()
        usuario = usuario_do_token(cfg, self._token())
        u = cfg.get("usuarios", {}).get(usuario, {})
        if not usuario or not _eh_admin(u):
            self._json({"erro": "Apenas o administrador."}, 403)
            return
        self._json({"ok": chat.limpar()})

    # ---- PLACAR DA COMUNIDADE ----
    def _com_admin_ok(self, cfg):
        """Retorna o usuario admin logado, ou envia o erro e retorna None."""
        usuario = usuario_do_token(cfg, self._token())
        u = cfg.get("usuarios", {}).get(usuario, {})
        if not usuario or not _eh_admin(u):
            self._json({"erro": "Apenas o administrador."}, 403)
            return None
        return usuario

    def _com_jogos(self, cfg):
        usuario = usuario_do_token(cfg, self._token())
        if not usuario:
            self._json({"erro": "Nao autorizado."}, 401)
            return
        try:
            comunidade.processar_pendentes(cfg)
        except Exception:
            pass
        vistos, jogos = set(), []
        for per in ("ontem", "hoje", "amanha"):
            try:
                js, _, _ = dados_futebol.listar_jogos(per, cfg)
            except Exception:
                js = []
            for j in js:
                ch = comunidade.chave_jogo(j)
                if ch in vistos:
                    continue
                vistos.add(ch)
                j2 = dict(j)
                j2["chave"] = ch
                j2["meu"] = comunidade.meu_palpite(usuario, ch)
                jogos.append(j2)
        self._json({"jogos": jogos})

    def _com_ranking(self, cfg):
        usuario = usuario_do_token(cfg, self._token())
        if not usuario:
            self._json({"erro": "Nao autorizado."}, 401)
            return
        faixa = self._query().get("faixa", "geral")
        self._json({"ranking": comunidade.ranking(faixa), "faixa": faixa, "eu": usuario})

    def _com_eu(self, cfg):
        usuario = usuario_do_token(cfg, self._token())
        if not usuario:
            self._json({"erro": "Nao autorizado."}, 401)
            return
        u = cfg.get("usuarios", {}).get(usuario, {})
        try:
            comunidade.processar_pendentes(cfg)
        except Exception:
            pass
        self._json(comunidade.estatisticas(usuario, u.get("nome", usuario)))

    def _com_palpitar(self):
        cfg = carregar_config()
        usuario = usuario_do_token(cfg, self._token())
        if not usuario:
            self._json({"erro": "Nao autorizado."}, 401)
            return
        u = cfg.get("usuarios", {}).get(usuario, {})
        nome = u.get("nome", usuario)
        d = self._corpo_json()
        jogo = d.get("jogo") or {}
        try:
            p = comunidade.palpitar(usuario, nome, jogo, d.get("ph"), d.get("pa"))
        except ValueError as e:
            self._json({"erro": str(e)}, 400)
            return
        except Exception as e:
            self._json({"erro": "Falha ao salvar palpite: %s" % e}, 500)
            return
        self._json({"ok": True, "palpite": p})

    def _com_admin_usuarios(self, cfg):
        if not self._com_admin_ok(cfg):
            return
        self._json({"usuarios": comunidade.admin_lista_usuarios()})

    def _com_admin_palpites(self, cfg):
        if not self._com_admin_ok(cfg):
            return
        self._json({"palpites": comunidade.admin_listar_palpites(self._query().get("q", ""))})

    def _com_admin_exportar(self, cfg):
        if not self._com_admin_ok(cfg):
            return
        tipo = self._query().get("tipo", "ranking")
        self._json({"tipo": tipo, "csv": comunidade.exportar_csv(tipo)})

    def _com_admin_resultado(self):
        cfg = carregar_config()
        if not self._com_admin_ok(cfg):
            return
        d = self._corpo_json()
        chave = (d.get("chave") or "").strip()
        if not chave:
            self._json({"erro": "Informe o jogo."}, 400)
            return
        try:
            n = comunidade.admin_set_resultado(cfg, chave, d.get("home_score"), d.get("away_score"), d.get("marcar", ""))
        except ValueError as e:
            self._json({"erro": str(e)}, 400)
            return
        self._json({"ok": True, "processados": n})

    def _com_admin_reprocessar(self):
        cfg = carregar_config()
        if not self._com_admin_ok(cfg):
            return
        chave = (self._corpo_json().get("chave") or "").strip() or None
        self._json({"ok": True, "processados": comunidade.reprocessar(cfg, chave)})

    def _com_admin_ajustar(self):
        cfg = carregar_config()
        admin = self._com_admin_ok(cfg)
        if not admin:
            return
        d = self._corpo_json()
        alvo = (d.get("usuario") or "").strip()
        if not alvo:
            self._json({"erro": "Informe o usuário."}, 400)
            return
        try:
            comunidade.admin_ajustar_xp(alvo, d.get("amount"), d.get("motivo", ""), admin)
        except ValueError as e:
            self._json({"erro": str(e)}, 400)
            return
        self._json({"ok": True})

    def _com_admin_bloquear(self):
        cfg = carregar_config()
        if not self._com_admin_ok(cfg):
            return
        d = self._corpo_json()
        alvo = (d.get("usuario") or "").strip()
        if not alvo:
            self._json({"erro": "Informe o usuário."}, 400)
            return
        comunidade.admin_bloquear(alvo, bool(d.get("bloquear", True)))
        self._json({"ok": True})

    # ---- CONTA do usuario ----
    def _conta(self, cfg):
        usuario = usuario_do_token(cfg, self._token())
        if not usuario:
            self._json({"erro": "Nao autorizado."}, 401)
            return
        u = cfg.get("usuarios", {}).get(usuario, {})
        admin = _eh_admin(u)
        vip = _vip_valido(u)
        ate = u.get("vip_ate")
        dias_rest = None
        data_fim = None
        if vip and not admin and ate:
            try:
                ate = float(ate)
                dias_rest = max(0, int((ate - time.time() + 86399) // 86400))
                data_fim = time.strftime("%d/%m/%Y", time.localtime(ate))
            except Exception:
                pass
        resp = {
            "usuario": usuario,
            "nome": ("Administrador" if admin else u.get("nome", usuario)),
            "email": u.get("email", usuario),
            "admin": admin,
            "role": "admin" if admin else ("vip" if vip else "cliente"),
            "vip": vip,
            "vip_dias_total": VIP_DIAS,
            "vip_dias_restantes": dias_rest,
            "vip_ate_data": data_fim,
            "pode_trocar_senha": (not admin),
            "criado_em": u.get("criado_em", ""),
        }
        if (not admin) and (not vip):
            resp["analises_restantes"] = max(0, _limite_gratis(cfg) - len(u.get("jogos_abertos", [])))
        self._json(resp)

    def _trocar_senha(self):
        cfg = carregar_config()
        usuario = usuario_do_token(cfg, self._token())
        if not usuario:
            self._json({"erro": "Nao autorizado."}, 401)
            return
        u = cfg.get("usuarios", {}).get(usuario, {})
        if _eh_admin(u):
            self._json({"erro": "A senha do administrador é definida na hospedagem (Render), não por aqui."}, 403)
            return
        d = self._corpo_json()
        atual = (d.get("senha_atual") or "").strip()
        nova = (d.get("nova_senha") or "").strip()
        if len(nova) < 4:
            self._json({"erro": "A nova senha precisa ter ao menos 4 caracteres."}, 400)
            return
        raw = _config_raw()
        ru = raw.get("usuarios", {}).get(usuario)
        if not ru or not hmac.compare_digest(ru.get("hash", ""), _hash_senha(atual, ru.get("salt", ""))):
            self._json({"erro": "Senha atual incorreta."}, 400)
            return
        salt = secrets.token_hex(8)
        ru["salt"] = salt
        ru["hash"] = _hash_senha(nova, salt)
        salvar_config(raw)
        self._json({"ok": True})


def _ciclo_atualizacao():
    """Roda a cada 6h: atualiza dados (gratis) e, se habilitado, reanalisa
    com IA os jogos salvos que vao acontecer em breve (isso GASTA creditos)."""
    cfg = carregar_config()
    if cfg.get("football_api_key"):
        for per in ("hoje", "amanha"):
            try:
                dados_futebol.listar_jogos(per, cfg)
            except Exception:
                pass
    ULTIMA_ATUALIZACAO["quando"] = time.strftime("%d/%m %H:%M")
    try:
        comunidade.processar_pendentes(cfg, forcar=True)  # resolve palpites de jogos encerrados
    except Exception:
        pass
    if cfg.get("auto_reanalise") and cfg.get("anthropic_api_key"):
        for reg in relatorios.para_reanalisar(2)[:8]:
            try:
                contexto = dados_futebol.coletar_contexto(reg, cfg)
                resultado = agentes.analisar(reg, contexto, cfg)
                relatorios.salvar(reg, resultado)
            except Exception:
                pass


def _agendador():
    while True:
        _ciclo_atualizacao()
        time.sleep(6 * 3600)


def abrir_navegador():
    try:
        webbrowser.open("http://localhost:%d" % PORT)
    except Exception:
        pass


class ServidorScopeMind(ThreadingHTTPServer):
    daemon_threads = True          # cada requisicao em sua thread (nao trava as outras)
    request_queue_size = 128       # aguenta rajadas de conexoes (evita "Failed to fetch")
    allow_reuse_address = True


def main():
    carregar_config()  # garante config.json
    porta = int(os.environ.get("PORT", str(PORT)))
    local = "PORT" not in os.environ  # sem PORT no ambiente = rodando no PC (local)
    host = "127.0.0.1" if local else "0.0.0.0"
    try:
        servidor = ServidorScopeMind((host, porta), Handler)
    except OSError:
        print("\n" + "=" * 60)
        print("  AVISO: a porta %d ja esta em uso." % porta)
        print("  O app provavelmente JA ESTA ABERTO em outra janela.")
        print("  Feche a outra janela preta (e a aba do navegador) e")
        print("  abra o INICIAR.bat de novo.")
        print("=" * 60)
        return
    print("=" * 60)
    print("  ScopeMind AI  -  servidor iniciado (porta %d)" % porta)
    if local:
        print("  Abra no navegador: http://localhost:%d" % porta)
        print("  (NAO feche esta janela enquanto estiver usando o app)")
    print("=" * 60)
    if local:
        threading.Timer(1.5, abrir_navegador).start()
    threading.Thread(target=_agendador, daemon=True).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando...")
        servidor.shutdown()


if __name__ == "__main__":
    main()
