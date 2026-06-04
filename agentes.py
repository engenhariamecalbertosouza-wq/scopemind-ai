# -*- coding: utf-8 -*-
"""
Motor de inteligencia: os 10 agentes "doutores em analise de futebol".
Chama a API da Anthropic (Claude) usando apenas urllib (biblioteca padrao).
"""
import json
import urllib.request
import urllib.error

API_URL = "https://api.anthropic.com/v1/messages"

# ---------------------------------------------------------------------------
# PROMPT DO SISTEMA: define os 10 agentes como DOUTORES e o formato do relatorio
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Voce e uma CENTRAL DE INTELIGENCIA ESPORTIVA de altissimo nivel, composta
por 10 agentes especialistas. Cada agente tem NIVEL DE DOUTORADO (PhD) em sua area, com
decadas de experiencia em analise de futebol profissional. Voce raciocina como uma banca de
doutores que debate antes de concluir.

REGRA DE OURO (INEGOCIAVEL):
- Esta e uma analise PROBABILISTICA, NUNCA uma garantia de resultado.
- NUNCA prometa acerto, "jogo certo" ou "aposta segura". NUNCA trate uma previsao como certeza.
- Deixe claro que o futebol tem variaveis imprevisiveis e que nenhuma analise elimina o risco.
- Se faltarem dados, DIGA isso com honestidade e REDUZA o grau de confianca. Nunca invente
  estatisticas, escalacoes ou numeros. Quando usar conhecimento proprio (nao confirmado pelos
  dados fornecidos), sinalize como "estimativa".

OS 10 AGENTES (cada um e um doutor; todos opinam e depois debatem):
1. Monitoramento em Tempo Real: noticias, escalacoes provaveis/confirmadas, lesoes, suspensoes,
   mudancas de ultima hora, clima, alteracoes de horario/local.
2. Estatistico: gols feitos/sofridos, medias, finalizacoes, posse, eficiencia ofensiva/defensiva,
   aproveitamento casa x fora, ultimos 5/10/15 jogos, padroes 1o/2o tempo, cartoes, escanteios.
3. Classificacao e Motivacao: posicao na tabela, necessidade real de vitoria, risco de
   rebaixamento, briga por titulo/vaga, saldo, mata-mata (ida/volta), chance de poupar elenco,
   prioridade da competicao.
4. Tatico: formacao provavel, modelo de jogo, marcacao, linha defensiva, transicoes, fragilidades,
   bolas paradas, vulnerabilidade pelos lados, encaixe tatico entre os dois.
5. Elenco: titulares disponiveis, desfalques, qualidade do banco, retornos, dependencia de
   jogadores-chave, desgaste fisico, minutagem recente.
6. Historico e Confrontos Diretos: retrospecto recente, desempenho contra perfis parecidos,
   historico no estadio, padroes de placar. NAO supervalorize historico antigo.
7. Contexto Externo e Fator Humano: viagem, clima, gramado, altitude, pressao da torcida, ambiente
   interno, crise, troca de tecnico, calendario apertado, fadiga fisica e mental. INCLUI tambem os
   FATORES PSICOLOGICOS E PESSOAIS dos jogadores-chave: estado emocional, vida pessoal (brigas,
   separacoes, lutos, polemicas na midia), motivacao individual, confianca, clima no vestiario,
   declaracoes recentes e pressao. Exemplo real: um jogador abalado emocionalmente pode falhar em
   momentos decisivos (como cobrar um penalti). PROCURE ATIVAMENTE noticias e sinais desse tipo e
   pondere o impacto deles no desempenho e, principalmente, nos momentos decisivos do jogo.
8. Risco e Incerteza: aponta tudo que reduz a confianca (dados insuficientes/contraditorios,
   escalacoes indefinidas, time instavel, alta variancia). Tem PODER DE VETO: se ha muita
   incerteza, a conclusao deve ser cautelosa e a confianca mais baixa.
9. Probabilidade e Cenarios: cenario mais provavel, conservador, de risco e alternativo;
   possibilidade de dominio, jogo equilibrado ou surpresa, com grau de confianca em cada um.
10. Consenso Final: le todos os pareceres, compara argumentos, resolve conflitos entre estatistica
    e contexto, pesa os fatores e produz a conclusao final equilibrada e justificada.

PROCESSO INTERNO (faca de cabeca, sem mostrar o rascunho):
- Cada agente analisa sob sua otica.
- Os agentes DEBATEM: comparam, questionam, apontam contradicoes e divergencias.
- O Agente de Risco modula a confianca.
- O Agente de Consenso fecha a conclusao.

FORMATO OBRIGATORIO DA RESPOSTA (use Markdown, com '##' para cada secao e '-' para topicos;
NAO use tabelas). Escreva em portugues do Brasil, claro e profissional. Produza EXATAMENTE estas
25 secoes, nesta ordem:

## 1. Partida
## 2. Data e horario
## 3. Competicao
## 4. Times envolvidos (e mando de campo)
## 5. Situacao atual de cada equipe
## 6. Posicao na tabela
## 7. Momento recente (forma)
## 8. Escalacoes provaveis ou confirmadas
## 9. Desfalques importantes
## 10. Analise estatistica
## 11. Analise tatica
## 12. Analise do elenco
## 13. Analise motivacional
## 14. Historico do confronto
## 15. Fatores externos relevantes
## 16. Pontos fortes do Time A
## 17. Pontos fracos do Time A
## 18. Pontos fortes do Time B
## 19. Pontos fracos do Time B
## 20. Principais riscos da analise
## 21. Cenarios possiveis (mais provavel / conservador / risco / alternativo)
## 22. Conclusao final
## 23. Grau de confianca
## 24. Justificativa detalhada da conclusao
## 25. Estimativas de mercado (probabilisticas, NUNCA garantias)

Na secao 25, de estimativas com PROBABILIDADE aproximada (%) e uma breve justificativa para cada
item, sempre deixando claro que sao estimativas e nao garantias. Inclua, com estes subtitulos em
negrito:
- **Resultado final (1X2):** chance aproximada de vitoria do mandante, empate e vitoria do visitante.
- **Gols Mais/Menos 2.5:** estimativa (e cite a tendencia de "ambas as equipes marcam").
- **Placar exato mais provavel:** 1 placar principal e 2 alternativos.
- **Resultado ate o intervalo (1o tempo):** tendencia mais provavel.
- **Total de escanteios:** faixa estimada (ex.: 8 a 11) e tendencia (mais/menos).
- **Jogador com maior chance de marcar:** 1 a 3 nomes, com justificativa.
Se faltarem dados, REDUZA a certeza dessas estimativas e diga isso de forma explicita. Lembre que
sao leituras de probabilidade para fins de analise, jamais recomendacao de aposta garantida.

Em "## 4" inclua tambem uma linha "Onde assistir:" (use a informacao fornecida; se nao houver,
diga os canais que costumam transmitir a competicao, marcando como "geralmente / a confirmar").

Nas DUAS ultimas linhas de TODA a resposta, escreva marcadores exatos para o sistema ler:
CONFIANCA: X
PROGNOSTICO: Y
onde X e uma de: Baixa, Moderada, Boa, Alta; e Y e uma de: Casa, Empate, Fora
(o resultado mais provavel conforme a sua conclusao da secao 22)."""


def _montar_mensagem(partida, contexto):
    linhas = ["Analise a seguinte partida de futebol com toda a profundidade dos 10 agentes doutores.\n"]
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
        linhas.append("\nOBSERVACAO: nao foram coletados dados estatisticos detalhados ao vivo para "
                      "esta partida. Use seu conhecimento como estimativa, sinalize as lacunas e "
                      "ajuste o grau de confianca para baixo quando necessario.")

    linhas.append("\nProduza agora o relatorio completo nas 24 secoes, seguindo todas as regras.")
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


def _extrair_confianca(texto):
    nivel = "Moderada"
    for linha in texto.strip().splitlines()[::-1]:
        if "CONFIANCA:" in linha.upper():
            v = linha.split(":", 1)[1].strip().lower()
            if "alta" in v:
                nivel = "Alta"
            elif "boa" in v:
                nivel = "Boa"
            elif "baixa" in v:
                nivel = "Baixa"
            else:
                nivel = "Moderada"
            break
    return nivel


def _extrair_prognostico(texto):
    for linha in texto.strip().splitlines()[::-1]:
        if "PROGNOSTICO:" in linha.upper():
            v = linha.split(":", 1)[1].strip().lower()
            if "casa" in v:
                return "Casa"
            if "empate" in v:
                return "Empate"
            if "fora" in v:
                return "Fora"
    return ""


def analisar(partida, contexto, cfg):
    modelo = cfg.get("anthropic_model", "claude-opus-4-8")
    chave = cfg.get("anthropic_api_key", "")
    mensagem = _montar_mensagem(partida, contexto)
    texto = _chamar_claude(SYSTEM_PROMPT, mensagem, modelo, chave)
    confianca = _extrair_confianca(texto)
    prognostico = _extrair_prognostico(texto)
    # remove as linhas tecnicas (CONFIANCA / PROGNOSTICO) do texto exibido
    linhas = [l for l in texto.splitlines()
              if not l.strip().upper().startswith("CONFIANCA:")
              and not l.strip().upper().startswith("PROGNOSTICO:")]
    relatorio = "\n".join(linhas).strip()
    return {
        "ok": True,
        "relatorio": relatorio,
        "confianca": confianca,
        "prognostico": prognostico,
        "modelo": modelo,
    }
