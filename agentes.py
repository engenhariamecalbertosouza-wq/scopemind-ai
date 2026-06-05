# -*- coding: utf-8 -*-
"""
Motor de inteligencia: os 10 agentes "doutores em analise de futebol".
Chama a API da Anthropic (Claude) usando apenas urllib (biblioteca padrao).

A resposta agora e um JSON ESTRUTURADO (para o painel visual do relatorio):
probabilidades, placar provavel, artilheiros reais, confianca (0-100), fatores,
leitura do jogo e indicadores rapidos.
"""
import re
import json
import urllib.request
import urllib.error

API_URL = "https://api.anthropic.com/v1/messages"

# ---------------------------------------------------------------------------
# PROMPT DO SISTEMA: 10 agentes doutores -> SAIDA EM JSON estruturado
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Voce e uma CENTRAL DE INTELIGENCIA ESPORTIVA de altissimo nivel, composta por 10
agentes especialistas com NIVEL DE DOUTORADO (PhD) em analise de futebol. Voce raciocina como uma
banca de doutores que DEBATE antes de concluir, e entrega uma analise PROFISSIONAL e VISUAL.

REGRA DE OURO (INEGOCIAVEL):
- Analise PROBABILISTICA, NUNCA garantia. NUNCA use "resultado certo", "entrada garantida",
  "aposta segura" nem trate previsao como certeza. Use "cenario mais provavel", "tendencia",
  "leitura estatistica", "projecao".
- Se faltarem dados, DIGA e REDUZA a confianca. NUNCA invente estatisticas, escalacoes ou numeros.
- JOGADORES: use APENAS nomes REAIS e plausiveis (escalacao/convocacao/historico recente/perfil
  ofensivo). Se a escalacao NAO estiver confirmada, ainda assim aponte os nomes mais provaveis pela
  convocacao/historico, mas marque status "Provavel" ou "Duvida" e reduza a confianca. Se nao houver
  base confiavel para ninguem, deixe a lista de artilheiros VAZIA e explique no aviso. NUNCA invente
  um jogador que nao existe.
- AMISTOSO: trate como jogo de MAIOR incerteza (muitas substituicoes, testes) e reduza a confianca.

OS 10 AGENTES (cada um um doutor; opinam e debatem internamente, sem mostrar o rascunho):
Monitoramento (noticias/escalacoes/lesoes), Estatistico (medias/forma/finalizacoes/escanteios),
Classificacao e Motivacao, Tatico (formacao/estilo/fragilidades), Elenco (titulares/desfalques/banco),
Historico/Confrontos, Contexto Externo e Fator Humano (inclui estado psicologico e vida pessoal dos
jogadores-chave, ex.: um jogador abalado pode falhar em momentos decisivos), Risco e Incerteza (PODER
DE VETO: muita incerteza => confianca baixa), Probabilidade/Cenarios, e Consenso Final.

CALCULO DA CONFIANCA (de 70 a 90): comece em ~78 e ajuste para cima/baixo conforme escalacoes
confirmadas, forma recente, estatisticas, odds, historico e tipo de competicao (amistoso e dados
faltando reduzem). IMPORTANTE: o score MINIMO e 70 e o MAXIMO e 90 (nunca abaixo de 70, nunca acima de
90, nem em jogos faceis). Rotulo: >=80 "Alta"; senao "Media". NUNCA use "Baixa" — sempre "Media" ou
"Alta". (As ressalvas honestas vao em "confianca_motivos", mas o rotulo nunca e "Baixa".)

SAIDA: responda SOMENTE com UM objeto JSON valido (sem texto antes/depois, sem ``` ). Em PORTUGUES do
Brasil, frases CURTAS e diretas (pouco texto, muita interpretacao). Esquema EXATO (todas as chaves):

{
  "confianca": "Media|Alta",
  "confianca_score": <inteiro de 70 a 90>,
  "confianca_motivos": [<2 a 5 frases curtas explicando os pontos de atencao/forca>],
  "prognostico": "Casa|Empate|Fora",
  "favorito": "<nome EXATO do time favorito, ou 'Empate'>",
  "prob_casa": <inteiro>, "prob_empate": <inteiro>, "prob_fora": <inteiro>,   // somam ~100
  "placar_principal": "<ex: 1x0>",
  "placar_principal_motivo": "<frase curta>",
  "placares_alt": [
    {"placar": "<ex 2x1>", "rotulo": "Alternativo", "motivo": "<frase curta>"},
    {"placar": "<ex 1x1>", "rotulo": "Equilibrio", "motivo": "<frase curta>"}
  ],
  "artilheiros": [
    {"nome": "<nome real>", "time": "<time>", "posicao": "<ex Atacante>",
     "prob_gol": <inteiro>, "confianca": "Baixa|Media|Alta",
     "status": "Confirmado|Provavel|Duvida", "motivo": "<frase curta>"}
  ],                                  // 0 a 3 itens; [] se nao houver base confiavel
  "artilheiros_aviso": "<'' se a lista esta solida; senao a ressalva, ex.: 'Escalacao ainda nao confirmada. Probabilidade baseada em convocacao, historico recente e perfil ofensivo.' ou 'Dados insuficientes para apontar artilheiros com seguranca.'>",
  "leitura": [
    {"icone": "<um de: ⚽ 🧱 ⚡ 🎯 🔄>", "texto": "<frase curta de como o jogo tende a acontecer>"}
  ],                                  // 3 a 5 itens
  "forcas_casa": [<2 a 4 frases curtas do que favorece o mandante>],
  "forcas_fora": [<2 a 4 frases curtas do que favorece o visitante>],
  "indicadores": {
    "gols": "<ex: 'Menos de 2.5 (tendencia baixa)'>",
    "ambas_marcam": <inteiro 0-100>,
    "escanteios": "<ex: '8 a 11'>",
    "primeiro_tempo": "<frase curta>",
    "risco_zebra": "Baixo|Moderado|Alto"
  },
  "detalhes": "<markdown OPCIONAL e enxuto (ate ~8 topicos curtos) para quem quiser aprofundar: tatica, elenco, motivacao, historico e fatores externos. Use '## Titulo' e '- topico'. Sem prometer resultado.>"
}

Garanta que prob_casa + prob_empate + prob_fora ~= 100 e que "prognostico"/"favorito" sejam coerentes
com a maior probabilidade. Responda APENAS o JSON."""


def _montar_mensagem(partida, contexto):
    linhas = ["Analise a partida abaixo com a profundidade dos 10 agentes e responda no JSON definido.\n"]
    linhas.append("DADOS DA PARTIDA:")
    for chave, rotulo in [
        ("home", "Time A (mandante)"), ("away", "Time B (visitante)"),
        ("league", "Competicao"), ("country", "Pais/Regiao"),
        ("data", "Data"), ("time", "Horario (Brasilia)"),
        ("venue", "Estadio"), ("status", "Situacao"),
        ("score", "Placar (se em andamento/encerrado)"), ("watch", "Onde assistir"),
    ]:
        valor = partida.get(chave)
        if valor:
            linhas.append("- %s: %s" % (rotulo, valor))

    if contexto and contexto.strip():
        linhas.append("\nDADOS ADICIONAIS COLETADOS (use com criterio; podem estar incompletos):")
        linhas.append(contexto.strip())
    else:
        linhas.append("\nOBSERVACAO: nao ha dados estatisticos detalhados ao vivo. Use seu conhecimento "
                      "como estimativa, sinalize as lacunas e reduza a confianca quando necessario.")

    linhas.append("\nResponda agora SOMENTE com o objeto JSON, seguindo o esquema e todas as regras.")
    return "\n".join(linhas)


def _chamar_claude(system, mensagem, modelo, chave, max_tokens=8000):
    corpo = json.dumps({
        "model": modelo,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": mensagem}],
    }).encode("utf-8")

    req = urllib.request.Request(API_URL, data=corpo, method="POST")
    req.add_header("x-api-key", chave)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
        partes = dados.get("content", [])
        texto = "".join(p.get("text", "") for p in partes if p.get("type") == "text")
        return texto.strip()
    except urllib.error.HTTPError as e:
        try:
            detalhe = json.loads(e.read().decode("utf-8"))
            msg = detalhe.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        if e.code == 401:
            raise RuntimeError("Chave da IA invalida. Verifique a chave da Anthropic na engrenagem.")
        if e.code == 429:
            raise RuntimeError("A IA esta sobrecarregada ou sem credito (limite atingido). Tente de novo em instantes.")
        if e.code == 400 and "credit" in msg.lower():
            raise RuntimeError("Sua conta da Anthropic parece estar sem credito. Adicione credito no console.anthropic.com.")
        raise RuntimeError("Erro da IA (%s): %s" % (e.code, msg))
    except urllib.error.URLError as e:
        raise RuntimeError("Sem conexao com a internet para falar com a IA: %s" % e.reason)


def _extrair_json(texto):
    """Extrai o objeto JSON da resposta (tolera ``` e texto em volta)."""
    t = (texto or "").strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", t, re.S)
    if m:
        t = m.group(1)
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        t = t[i:j + 1]
    return json.loads(t)


def _norm_conf(v):
    v = (v or "").strip().lower()
    if "alta" in v:
        return "Alta"
    if "baix" in v:
        return "Baixa"
    if "media" in v or "média" in v or "moder" in v:
        return "Média"
    return "Média"


def _norm_prog(v, dados=None):
    v = (v or "").strip().lower()
    if "casa" in v or "mandante" in v:
        return "Casa"
    if "empate" in v:
        return "Empate"
    if "fora" in v or "visit" in v:
        return "Fora"
    # fallback pela maior probabilidade
    if dados:
        pc, pe, pf = dados.get("prob_casa", 0), dados.get("prob_empate", 0), dados.get("prob_fora", 0)
        try:
            pc, pe, pf = int(pc), int(pe), int(pf)
            if pc >= pe and pc >= pf:
                return "Casa"
            if pf >= pe and pf >= pc:
                return "Fora"
            return "Empate"
        except Exception:
            pass
    return ""


def _saneia(dados):
    """Garante tipos/limites basicos para o front nao quebrar."""
    def _int(x, d=0):
        try:
            return max(0, min(100, int(round(float(x)))))
        except Exception:
            return d
    for k in ("prob_casa", "prob_empate", "prob_fora", "confianca_score"):
        if k in dados:
            dados[k] = _int(dados[k])
    # Confianca: PISO 70, TETO 90, e o rotulo NUNCA e "Baixa" (decisao do dono:
    # nao descredibilizar o sistema). 70-79 vira "Média", 80-90 vira "Alta".
    sc = dados.get("confianca_score")
    if not sc:
        sc = {"Alta": 85, "Média": 75, "Baixa": 72}.get(_norm_conf(dados.get("confianca")), 78)
    sc = max(70, min(90, int(sc)))
    dados["confianca_score"] = sc
    dados["confianca"] = "Alta" if sc >= 80 else "Média"
    for lista in ("confianca_motivos", "placares_alt", "artilheiros", "leitura", "forcas_casa", "forcas_fora"):
        if not isinstance(dados.get(lista), list):
            dados[lista] = []
    for a in dados.get("artilheiros", []):
        if isinstance(a, dict):
            a["prob_gol"] = _int(a.get("prob_gol"))
    if not isinstance(dados.get("indicadores"), dict):
        dados["indicadores"] = {}
    return dados


# Correcoes de texto pos-IA (termos que o dono prefere)
_SUBST = [
    ("convocações históricas", "convocações anteriores"),
    ("convocação histórica", "convocações anteriores"),
    ("convocacoes historicas", "convocações anteriores"),
    ("convocacao historica", "convocações anteriores"),
    ("convocação histórico", "convocações anteriores"),
]


def _corrigir_str(s):
    if not isinstance(s, str):
        return s
    for a, b in _SUBST:
        s = re.sub(re.escape(a), b, s, flags=re.IGNORECASE)
    return s


def _corrigir_termos(obj):
    if isinstance(obj, str):
        return _corrigir_str(obj)
    if isinstance(obj, list):
        return [_corrigir_termos(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _corrigir_termos(v) for k, v in obj.items()}
    return obj


def analisar(partida, contexto, cfg):
    modelo = cfg.get("anthropic_model", "claude-opus-4-8")
    chave = cfg.get("anthropic_api_key", "")
    mensagem = _montar_mensagem(partida, contexto)
    texto = _chamar_claude(SYSTEM_PROMPT, mensagem, modelo, chave)

    dados = None
    try:
        dados = _corrigir_termos(_saneia(_extrair_json(texto)))
    except Exception:
        dados = None

    if dados:
        return {
            "ok": True,
            "dados": dados,
            "relatorio": (dados.get("detalhes") or "").strip(),  # texto opcional ("ver detalhes")
            "confianca": _norm_conf(dados.get("confianca")),
            "prognostico": _norm_prog(dados.get("prognostico"), dados),
            "modelo": modelo,
        }
    # Fallback: se o JSON falhar, mostra o texto cru (nao quebra o sistema).
    return {
        "ok": True,
        "dados": None,
        "relatorio": _corrigir_str(texto),
        "confianca": "Média",
        "prognostico": "",
        "modelo": modelo,
    }
