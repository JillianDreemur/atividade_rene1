from datetime import datetime
from config import estado_quarto, aprendizado, salvar_aprendizado, salvar_estado

ACOES = (
    "manter",
    "abrir_janela",
    "fechar_janela",
    "ligar_ar",
    "desligar_ar",
    "ligar_ventilador",
    "desligar_ventilador",
    "ligar_umidificador",
    "desligar_umidificador",
    "ligar_luz",
    "desligar_luz",
)


def _hora():
    return datetime.now().hour


def _bool(chave):
    return int(estado_quarto.get(chave, 0) or 0) == 1


def _nivel(chave):
    return int(estado_quarto.get(chave, 0) or 0)


def decidir(origem="ciclo"):
    modo = estado_quarto.get("modo_agente", "cognitivo")
    if modo == "reativo":
        plano = _reativo()
    elif modo == "adaptativo":
        plano = _adaptativo()
    else:
        plano = _cognitivo()

    plano["modo"] = modo
    plano["origem"] = origem
    plano["hora"] = _hora()
    estado_quarto["ultima_acao_agente"] = plano["acao"]
    estado_quarto["ultima_razao_agente"] = plano["razao"]
    salvar_estado()
    return plano


def _reativo():
    temp = float(estado_quarto.get("temperatura_atual", 99))
    umid = float(estado_quarto.get("umidade_atual", 99))
    chuva = float(estado_quarto.get("chuva_atual", 0))
    limite = float(estado_quarto.get("temperatura_limite", 28.5))
    limiar_chuva = float(estado_quarto.get("limiar_chuva", 40))
    umidade_min = float(estado_quarto.get("umidade_minima", 40))
    umidade_max = float(estado_quarto.get("umidade_maxima", 65))

    if chuva >= limiar_chuva and _bool("janela_aberta"):
        return {"acao": "fechar_janela", "razao": f"Chuva em {chuva:.0f}%: fecha a janela (segurança)."}

    if estado_quarto.get("presenca_externa") and _bool("janela_aberta"):
        return {"acao": "fechar_janela", "razao": "Presença externa detectada: fecha a janela."}

    if not estado_quarto.get("dormir"):
        if umid < umidade_min and _nivel("umidificador") == 0:
            return {"acao": "ligar_umidificador", "razao": f"Umidade baixa ({umid:.0f}%): liga umidificador."}
        if umid > umidade_max and _nivel("umidificador") > 0:
            return {"acao": "desligar_umidificador", "razao": f"Umidade alta ({umid:.0f}%): desliga umidificador."}
        return {"acao": "manter", "razao": "Modo acordado: só reage a chuva, presença e umidade extrema."}

    if temp > limite and not _bool("ar_ligado"):
        return {"acao": "ligar_ar", "razao": f"Calor ({temp:.1f}°C > {limite}°C): liga o ar."}
    if temp > limite and _bool("janela_aberta"):
        return {"acao": "fechar_janela", "razao": f"Calor ({temp:.1f}°C): fecha a janela para o ar render."}
    if temp < 26 and _bool("ar_ligado"):
        return {"acao": "desligar_ar", "razao": f"Já esfriou ({temp:.1f}°C): desliga o ar."}
    if temp < 26 and not _bool("janela_aberta") and chuva < limiar_chuva:
        return {"acao": "abrir_janela", "razao": f"Noite amena ({temp:.1f}°C): abre a janela."}

    return {"acao": "manter", "razao": f"Reativo: {temp:.1f}°C está dentro da faixa."}


def _pontuar(acao):
    temp = float(estado_quarto.get("temperatura_atual", 99))
    umid = float(estado_quarto.get("umidade_atual", 99))
    chuva = float(estado_quarto.get("chuva_atual", 0))
    alvo_t = float(estado_quarto.get("temperatura_alvo", 24))
    alvo_u = float(estado_quarto.get("umidade_alvo", 50))
    limiar_chuva = float(estado_quarto.get("limiar_chuva", 40))
    hora = _hora()
    dormir = _bool("dormir")
    janela = _bool("janela_aberta")
    ar = _bool("ar_ligado")
    vent = _nivel("ventilador")
    umidif = _nivel("umidificador")
    luz = _bool("luz_ligada")
    erro_t = abs(temp - alvo_t)
    erro_u = abs(umid - alvo_u)

    score = 0.0

    if acao == "manter":
        score += 1.0 if erro_t < 1.5 else -erro_t

    if chuva >= limiar_chuva or estado_quarto.get("presenca_externa"):
        if acao == "abrir_janela":
            score -= 1000
        if acao == "fechar_janela" and janela:
            score += 80

    if acao == "ligar_ar":
        score -= 8
        if temp > alvo_t + 2:
            score += 12 + (temp - alvo_t)
        if janela:
            score -= 25
        if ar:
            score -= 40

    if acao == "desligar_ar":
        if ar and temp <= alvo_t + 1.5:
            score += 10
        elif ar and 3 <= hora < 6 and temp <= 27:
            score += 14
        elif not ar:
            score -= 40
        else:
            score -= 6

    if acao == "abrir_janela":
        score += 4
        if temp > alvo_t + 1.5 and not ar:
            score += 10
        if ar:
            score -= 20
        if janela:
            score -= 40
        if dormir and hora < int(estado_quarto.get("hora_abrir_manha", 7)):
            score -= 12
        if dormir and hora >= int(estado_quarto.get("hora_fechar_noite", 22)):
            score -= 8

    if acao == "fechar_janela":
        if janela and ar:
            score += 18
        if janela and temp < alvo_t - 1:
            score += 8
        if not janela:
            score -= 40

    if acao == "ligar_ventilador":
        score -= 2
        if temp > alvo_t and janela and not ar:
            score += 11
        if vent >= 3:
            score -= 40

    if acao == "desligar_ventilador":
        if vent > 0 and temp <= alvo_t:
            score += 6
        elif vent == 0:
            score -= 40

    if acao == "ligar_umidificador":
        if umid < alvo_u - 5:
            score += 9 + (alvo_u - umid) / 5
        else:
            score -= 8
        if umidif >= 3:
            score -= 40

    if acao == "desligar_umidificador":
        if umidif > 0 and umid >= alvo_u:
            score += 7
        elif umidif == 0:
            score -= 40

    if acao == "ligar_luz":
        lum = float(estado_quarto.get("luminosidade_atual", 0))
        if lum < 30 and not dormir and not luz:
            score += 5
        else:
            score -= 15

    if acao == "desligar_luz":
        if dormir and luz:
            score += 12
        elif not luz:
            score -= 40

    score -= erro_u * 0.05
    return score


def _cognitivo():
    melhor = "manter"
    melhor_score = -1e9
    detalhes = {}
    for acao in ACOES:
        pontos = _pontuar(acao)
        detalhes[acao] = round(pontos, 2)
        if pontos > melhor_score:
            melhor_score = pontos
            melhor = acao

    razoes = {
        "manter": "Nenhuma ação supera ficar como está (conforto x energia).",
        "abrir_janela": "Resfriar com janela sai mais barato que o ar.",
        "fechar_janela": "Fecha a janela por segurança ou para o ar render.",
        "ligar_ar": "O calor está longe da meta; o ar vale o gasto agora.",
        "desligar_ar": "Já chegou perto da meta (ou madrugada): economiza energia.",
        "ligar_ventilador": "Ventilador + janela aproximam dos 24°C com pouco gasto.",
        "desligar_ventilador": "Temperatura ok: desliga o ventilador.",
        "ligar_umidificador": "Umidade abaixo da meta.",
        "desligar_umidificador": "Umidade já está na faixa.",
        "ligar_luz": "Ambiente escuro e você está acordado.",
        "desligar_luz": "Modo dormir: apaga a luz.",
    }
    return {
        "acao": melhor,
        "razao": razoes.get(melhor, melhor),
        "utilidades": detalhes,
        "meta_temperatura": estado_quarto.get("temperatura_alvo"),
    }


def _adaptativo():
    plano = _cognitivo()
    pesos = aprendizado.get("pesos", {})
    hora_abrir = int(aprendizado.get("hora_abrir_manha", estado_quarto.get("hora_abrir_manha", 7)))
    estado_quarto["hora_abrir_manha"] = hora_abrir

    ajustadas = {}
    melhor = plano["acao"]
    melhor_score = -1e9
    for acao, base in plano.get("utilidades", {}).items():
        extra = float(pesos.get(acao, 0.0))
        if acao == "abrir_janela" and _hora() < hora_abrir:
            extra += float(pesos.get("abrir_janela_manha", 0.0))
            extra -= 6
        total = base + extra
        ajustadas[acao] = round(total, 2)
        if total > melhor_score:
            melhor_score = total
            melhor = acao

    plano["acao"] = melhor
    plano["utilidades"] = ajustadas
    plano["hora_abrir_manha"] = hora_abrir
    plano["razao"] = (
        f"{plano['razao']} Aprendizado: hora preferida de abrir ≈ {hora_abrir}h; "
        f"peso da ação escolhida = {pesos.get(melhor, 0):+.1f}."
    )
    return plano


def registrar_feedback(acao, valor, comentario=""):
    valor = max(-2.0, min(2.0, float(valor)))
    pesos = aprendizado.setdefault("pesos", {})
    pesos[acao] = float(pesos.get(acao, 0.0)) + valor

    if acao == "abrir_janela" and valor < 0:
        aprendizado["hora_abrir_manha"] = min(11, int(aprendizado.get("hora_abrir_manha", 7)) + 1)
        estado_quarto["hora_abrir_manha"] = aprendizado["hora_abrir_manha"]
        pesos["abrir_janela_manha"] = float(pesos.get("abrir_janela_manha", 0.0)) + valor

    if acao == "abrir_janela" and valor > 0:
        aprendizado["hora_abrir_manha"] = max(5, int(aprendizado.get("hora_abrir_manha", 7)) - 0)
        pesos["abrir_janela_manha"] = float(pesos.get("abrir_janela_manha", 0.0)) + valor * 0.3

    historico = aprendizado.setdefault("historico_feedback", [])
    historico.append(
        {
            "acao": acao,
            "valor": valor,
            "comentario": comentario,
            "hora": _hora(),
            "quando": datetime.now().isoformat(timespec="seconds"),
        }
    )
    historico[:] = historico[-80:]
    salvar_aprendizado()
    salvar_estado()
    return {"pesos": pesos, "hora_abrir_manha": aprendizado.get("hora_abrir_manha")}


def feedback_override(acao_usuario):
    ultima = estado_quarto.get("ultima_acao_agente")
    opostos = {
        "abrir_janela": "fechar_janela",
        "fechar_janela": "abrir_janela",
        "ligar_ar": "desligar_ar",
        "desligar_ar": "ligar_ar",
        "ligar_ventilador": "desligar_ventilador",
        "desligar_ventilador": "ligar_ventilador",
        "ligar_umidificador": "desligar_umidificador",
        "desligar_umidificador": "ligar_umidificador",
        "ligar_luz": "desligar_luz",
        "desligar_luz": "ligar_luz",
    }
    if ultima and opostos.get(ultima) == acao_usuario:
        return registrar_feedback(ultima, -1, "override manual")
    if ultima == acao_usuario:
        return registrar_feedback(ultima, 0.4, "confirmacao manual")
    return None
