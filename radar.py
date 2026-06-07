# -*- coding: utf-8 -*-
"""
Radar de Oportunidades — transforma a análise estruturada (dados do agentes.py)
em uma lista de OPORTUNIDADES por mercado, com valueScore, risco e ranking.

NÃO chama IA nem API: só LÊ análises já salvas (custo zero). É a curadoria que
o front mostra no lugar da antiga lista de jogos.

Linguagem SEMPRE de análise/probabilidade — nunca promessa de ganho.
"""

RISCOS = ("Baixo", "Médio", "Alto")


def _i(x, d=0):
    try:
        return max(0, min(100, int(round(float(x)))))
    except Exception:
        return d


def _risco_por_prob(prob, base_alto=False):
    """Risco aproximado a partir da probabilidade (mercados de resultado/gols)."""
    if base_alto:
        return "Alto"
    if prob >= 65:
        return "Baixo"
    if prob >= 50:
        return "Médio"
    return "Alto"


def _risco_geral(dados):
    rz = (dados.get("indicadores") or {}).get("risco_zebra", "")
    rz = (rz or "").strip().lower()
    if rz.startswith("baix"):
        return "Baixo"
    if rz.startswith("alt"):
        return "Alto"
    return "Médio"


def value_score(op):
    """Pontuação que ordena as oportunidades (fórmula definida pelo dono)."""
    score = op["prob"] * 0.45 + op["confianca"] * 0.35
    r = op["risco"]
    score += 15 if r == "Baixo" else (7 if r == "Médio" else -10)
    if op["mercado"] == "PLACAR_EXATO":
        score -= 15
    if op["mercado"] == "PROXIMO_MARCADOR" and not op.get("jogador_status"):
        score -= 10
    return max(0, min(100, round(score)))


def _op(mercado, titulo, selecao, prob, confianca, risco, badge, **extra):
    o = {"mercado": mercado, "titulo": titulo, "selecao": selecao,
         "prob": _i(prob), "confianca": _i(confianca), "risco": risco, "badge": badge}
    o.update(extra)
    o["value"] = value_score(o)
    return o


def derivar(dados, home, away):
    """Recebe o 'dados' (JSON estruturado da análise) e devolve as oportunidades."""
    if not isinstance(dados, dict):
        return []
    conf = _i(dados.get("confianca_score"), 70) or 70
    rgeral = _risco_geral(dados)
    ops = []

    # 1) RESULTADO FINAL (1X2) — da maior probabilidade
    pc, pe, pf = _i(dados.get("prob_casa")), _i(dados.get("prob_empate")), _i(dados.get("prob_fora"))
    if pc or pe or pf:
        melhor = max([("casa", pc), ("empate", pe), ("fora", pf)], key=lambda t: t[1])
        sel = ("Vitória " + (home or "Mandante")) if melhor[0] == "casa" else \
              ("Vitória " + (away or "Visitante")) if melhor[0] == "fora" else "Empate"
        ops.append(_op("RESULTADO_FINAL", "Resultado Final", sel, melhor[1], conf,
                       _risco_por_prob(melhor[1]), "⚽",
                       prob_casa=pc, prob_empate=pe, prob_fora=pf))

    merc = dados.get("mercados") if isinstance(dados.get("mercados"), dict) else {}

    # 2) MAIS/MENOS GOLS — melhor linha
    gols = [g for g in (merc.get("gols") or []) if isinstance(g, dict) and g.get("linha")]
    if gols:
        g = max(gols, key=lambda x: _i(x.get("prob")))
        linha = str(g.get("linha"))
        badge = "📈" if "mais" in linha.lower() else "📉"
        ops.append(_op("MAIS_MENOS_GOLS", "Gols", linha + " gols", _i(g.get("prob")), conf,
                       _risco_por_prob(_i(g.get("prob"))), badge,
                       linhas=[{"linha": str(x.get("linha")), "prob": _i(x.get("prob"))} for x in gols]))

    # 3) AMBAS MARCAM
    btts = _i(merc.get("ambas_marcam_sim")) or _i((dados.get("indicadores") or {}).get("ambas_marcam"))
    if btts:
        if btts >= 55:
            ops.append(_op("AMBAS_MARCAM", "Ambas Marcam", "Ambas marcam: Sim", btts, conf,
                           _risco_por_prob(btts), "🤝"))
        elif btts <= 45:
            nao = 100 - btts
            ops.append(_op("AMBAS_MARCAM", "Ambas Marcam", "Ambas marcam: Não", nao, conf,
                           _risco_por_prob(nao), "🤝"))

    # 4) ESCANTEIOS
    esc = merc.get("escanteios") if isinstance(merc.get("escanteios"), dict) else {}
    if _i(esc.get("prob")) and (esc.get("linha") or esc.get("faixa")):
        sel = str(esc.get("linha") or "")
        if esc.get("faixa"):
            sel = (sel + " (" + str(esc.get("faixa")) + ")").strip()
        ops.append(_op("ESCANTEIOS", "Escanteios", sel or ("Faixa " + str(esc.get("faixa"))),
                       _i(esc.get("prob")), conf, _risco_por_prob(_i(esc.get("prob"))), "🚩",
                       faixa=esc.get("faixa", "")))

    # 5) VENCE SEM SOFRER GOLS
    vss = merc.get("vence_sem_sofrer") if isinstance(merc.get("vence_sem_sofrer"), dict) else {}
    if _i(vss.get("prob")) and vss.get("time"):
        ops.append(_op("VENCE_SEM_SOFRER", "Vence sem sofrer", str(vss.get("time")) + " vence sem sofrer gols",
                       _i(vss.get("prob")), conf, _risco_por_prob(_i(vss.get("prob")), base_alto=_i(vss.get("prob")) < 50),
                       "🧤"))

    # 6) PRÓXIMO MARCADOR (artilheiros)
    for a in (dados.get("artilheiros") or []):
        if not isinstance(a, dict) or not a.get("nome"):
            continue
        ops.append(_op("PROXIMO_MARCADOR", "Jogador para marcar", str(a.get("nome")) + " para marcar",
                       _i(a.get("prob_gol")), conf, "Alto", "🎯",
                       jogador=a.get("nome"), jogador_time=a.get("time", ""),
                       jogador_status=a.get("status", "")))

    # 7) PLACAR EXATO (sempre risco Alto)
    placares = [p for p in (merc.get("placares") or []) if isinstance(p, dict) and p.get("placar")]
    if not placares and dados.get("placar_principal"):
        placares = [{"placar": dados.get("placar_principal"), "prob": 0}]
    for p in placares[:3]:
        ops.append(_op("PLACAR_EXATO", "Placar exato", str(p.get("placar")), _i(p.get("prob")), conf,
                       "Alto", "🔢",
                       aviso="Mercado de alta dificuldade. Use apenas como leitura estatística."))

    return ops


# Limiares para uma oportunidade ser considerada "forte"/destaque
def eh_forte(op):
    m = op["mercado"]
    if m == "PROXIMO_MARCADOR":
        return op["prob"] >= 22 and op["confianca"] >= 50 and op["value"] >= 55
    if m == "PLACAR_EXATO":
        return op["prob"] >= 15 and op["confianca"] >= 55 and op["value"] >= 50
    return op["prob"] >= 55 and op["confianca"] >= 55 and op["value"] >= 60


def melhor_oportunidade(ops):
    """A 'melhor leitura' do jogo: maior value, evitando placar exato como principal
    (a menos que seja a única opção)."""
    if not ops:
        return None
    nao_exato = [o for o in ops if o["mercado"] != "PLACAR_EXATO"]
    pool = nao_exato or ops
    return max(pool, key=lambda o: o["value"])


def montar(itens):
    """itens = lista de {'jogo': <dict do jogo>, 'dados': <análise.dados ou None>}.
    Devolve a estrutura pronta para o Radar."""
    jogos_out = []
    todas_ops = []
    n_analisados = 0
    for it in itens:
        jogo = it.get("jogo") or {}
        dados = it.get("dados")
        home, away = jogo.get("home", ""), jogo.get("away", "")
        base = {
            "chave": it.get("chave", ""),
            "home": home, "away": away,
            "league": jogo.get("league", ""), "country_pt": jogo.get("country_pt", jogo.get("country", "")),
            "data": jogo.get("data", ""), "time": jogo.get("time", ""),
            "status": jogo.get("status", ""),
            "analisado": False, "estado": "aguardando",
        }
        if isinstance(dados, dict) and dados:
            ops = derivar(dados, home, away)
            for o in ops:
                o["chave"] = base["chave"]
                o["home"] = home
                o["away"] = away
                o["league"] = jogo.get("league", "")
                o["time"] = jogo.get("time", "")
            ops.sort(key=lambda o: o["value"], reverse=True)
            best = melhor_oportunidade(ops)
            forte = any(eh_forte(o) for o in ops)
            base["analisado"] = True
            base["estado"] = "forte" if forte else "fraca"
            base["confianca"] = _i(dados.get("confianca_score"), 70)
            base["risco"] = _risco_geral(dados)
            base["resumo"] = (dados.get("confianca_motivos") or [""])[0] if dados.get("confianca_motivos") else ""
            base["melhor"] = best
            base["mercados"] = ops
            todas_ops.extend(ops)
            n_analisados += 1
        jogos_out.append(base)

    # ranking geral das melhores oportunidades fortes
    fortes = [o for o in todas_ops if eh_forte(o)]
    fortes.sort(key=lambda o: o["value"], reverse=True)
    # destaques: melhores oportunidades de jogos distintos
    destaques, vistos = [], set()
    for o in fortes:
        if o["chave"] in vistos:
            continue
        vistos.add(o["chave"])
        destaques.append(o)
        if len(destaques) >= 6:
            break

    # ordena jogos: fortes primeiro (por value do melhor), depois analisados fracos, depois aguardando
    def ordem(j):
        if j["estado"] == "forte":
            return (0, -(j.get("melhor") or {}).get("value", 0))
        if j["estado"] == "fraca":
            return (1, -(j.get("melhor") or {}).get("value", 0))
        return (2, 0)
    jogos_out.sort(key=ordem)

    return {
        "destaques": destaques,
        "ranking": fortes[:10],
        "jogos": jogos_out,
        "total": len(itens),
        "analisados": n_analisados,
        "fortes": len({o["chave"] for o in fortes}),
    }
