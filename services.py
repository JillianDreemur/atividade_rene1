from flask import jsonify
from datetime import datetime
import daofile
import agentes
import devices
from config import estado_quarto, placas_registradas, salvar_estado


def _float_ok(valor, minimo=-20, maximo=80):
    numero = float(valor)
    if numero < minimo or numero > maximo:
        raise ValueError("fora da faixa")
    return numero


def aplicar_acao(acao, origem="agente"):
    mapa = {
        "abrir_janela": abrir_janela,
        "fechar_janela": fechar_janela,
        "ligar_ar": ligar_ar,
        "desligar_ar": desligar_ar,
        "ligar_ventilador": ligar_ventilador,
        "desligar_ventilador": desligar_ventilador,
        "ligar_umidificador": ligar_umidificador,
        "desligar_umidificador": desligar_umidificador,
        "ligar_luz": ligar_luz,
        "desligar_luz": desligar_luz,
    }
    if acao == "manter" or acao not in mapa:
        return {"status": "ok", "acao": "manter", "origem": origem}
    bruto = mapa[acao]()
    if isinstance(bruto, tuple):
        corpo, codigo = bruto
    else:
        corpo, codigo = bruto, 200
    if hasattr(corpo, "get_json"):
        corpo = corpo.get_json()
    return {"status": "ok", "acao": acao, "origem": origem, "dispositivo": corpo, "http": codigo}


def ajustar(temp_str, umid_str, dormir, aberta, chuva=None, luminosidade=None, presenca_in=None, presenca_out=None):
    if temp_str is None or umid_str is None:
        return jsonify({"erro": "Faltam parâmetros de temperatura ou umidade"}), 400

    try:
        if dormir is not None:
            estado_quarto["dormir"] = int(dormir)
        if aberta is not None:
            estado_quarto["janela_aberta"] = int(aberta)
        if chuva is not None:
            estado_quarto["chuva_atual"] = float(chuva)
        if luminosidade is not None:
            estado_quarto["luminosidade_atual"] = float(luminosidade)
        if presenca_in is not None:
            estado_quarto["presenca_interna"] = int(presenca_in)
        if presenca_out is not None:
            estado_quarto["presenca_externa"] = int(presenca_out)

        temperatura = _float_ok(temp_str, -10, 55)
        umidade = _float_ok(umid_str, 0, 100)
        daofile.inserir_th(umidade, temperatura)
        estado_quarto["temperatura_atual"] = temperatura
        estado_quarto["umidade_atual"] = umidade
        salvar_estado()

        plano = agentes.decidir(origem="sensor")
        execucao = aplicar_acao(plano["acao"], origem="agente")
        return jsonify({
            "status": "sucesso",
            "temperatura": temperatura,
            "umidade": umidade,
            "plano": plano,
            "execucao": execucao,
        }), 200

    except ValueError:
        return jsonify({"erro": "Valores inválidos de temperatura/umidade"}), 400
    except Exception as erro:
        return jsonify({"status": "erro", "mensagem": str(erro)}), 503


def ajustar_temp_limite(tempo):
    try:
        estado_quarto["temperatura_limite"] = float(tempo)
        salvar_estado()
        return jsonify({"status": "ok", "temperatura_limite": estado_quarto["temperatura_limite"]}), 200
    except (TypeError, ValueError):
        return jsonify({"erro": "limite inválido"}), 400


def ajustar_preferencias(dados):
    chaves = (
        "temperatura_alvo",
        "umidade_alvo",
        "umidade_minima",
        "umidade_maxima",
        "limiar_chuva",
        "hora_abrir_manha",
        "hora_fechar_noite",
        "modo_agente",
        "temperatura_limite",
    )
    for chave in chaves:
        if chave in dados and dados[chave] not in (None, ""):
            if chave == "modo_agente":
                if dados[chave] not in ("reativo", "cognitivo", "adaptativo"):
                    return jsonify({"erro": "modo_agente inválido"}), 400
                estado_quarto[chave] = dados[chave]
            elif chave.startswith("hora_"):
                estado_quarto[chave] = int(dados[chave])
            else:
                estado_quarto[chave] = float(dados[chave])
    salvar_estado()
    return jsonify({"status": "ok", "estado": estado_publico()}), 200


def estado_publico():
    return {
        **estado_quarto,
        "placas": placas_registradas,
        "hora_servidor": datetime.now().strftime("%H:%M:%S"),
    }


def pegar_status():
    ip_esp32 = placas_registradas.get("janela")
    extra = ""
    if ip_esp32:
        resposta, erro = devices.comando_placa("janela", "/status", timeout=5)
        extra = erro or (resposta.text if resposta is not None else "")
    return jsonify({"estado": estado_publico(), "placa_janela": extra})


def abrir_janela():
    return _janela("/abrir", 1, "aberta", "Janela aberta")


def fechar_janela():
    resposta = _janela("/fechar", 0, "fechada", "Janela fechada")
    if resposta[1] in (200, 208):
        estado_quarto["dormir"] = 0
        salvar_estado()
    return resposta


def _janela(caminho, flag, texto_estado, mensagem):
    resposta, erro = devices.comando_placa("janela", caminho, timeout=devices.TIMEOUT_JANELA)
    if erro:
        return jsonify({"erro": erro}), 503
    ok, codigo = devices.interpretar_comando(resposta)
    if not ok:
        return jsonify({"erro": f"Placa retornou {codigo}"}), 500
    estado_quarto["janela_aberta"] = flag
    salvar_estado()
    tipo = "aviso" if codigo == 208 else "sucesso"
    return jsonify({"status": tipo, "mensagem": mensagem, "estado_janela": texto_estado}), 200


def ligar_ar():
    return _binario("esp8266ar", "/ligar", "ar_ligado", 1, "Ar ligado")


def desligar_ar():
    return _binario("esp8266ar", "/desligar", "ar_ligado", 0, "Ar desligado")


def ligar_luz():
    return _binario("esp01luzesc", "/ligar", "luz_ligada", 1, "Luz ligada")


def desligar_luz():
    return _binario("esp01luzesc", "/desligar", "luz_ligada", 0, "Luz desligada")


def _binario(placa, caminho, chave, valor, mensagem):
    resposta, erro = devices.comando_placa(placa, caminho)
    if erro:
        return jsonify({"erro": erro}), 503
    ok, codigo = devices.interpretar_comando(resposta)
    if not ok:
        return jsonify({"erro": f"Placa retornou {codigo}"}), 500
    estado_quarto[chave] = valor
    salvar_estado()
    tipo = "aviso" if codigo == 208 else "sucesso"
    return jsonify({"status": tipo, "mensagem": mensagem, chave: valor}), 200


def ligar_ventilador():
    return _ciclo("esp32c3vent", "/ventilador", "ventilador", "Ventilador")


def desligar_ventilador():
    tentativas = 0
    ultimo = None
    while estado_quarto.get("ventilador", 0) > 0 and tentativas < 4:
        ultimo = ligar_ventilador()
        tentativas += 1
    return ultimo or jsonify({"status": "sucesso", "mensagem": "Ventilador já desligado", "ventilador": 0}), 200


def ligar_umidificador():
    return _ciclo("esp32c3vent", "/umidificador", "umidificador", "Umidificador")


def desligar_umidificador():
    tentativas = 0
    ultimo = None
    while estado_quarto.get("umidificador", 0) > 0 and tentativas < 4:
        ultimo = ligar_umidificador()
        tentativas += 1
    return ultimo or jsonify({"status": "sucesso", "mensagem": "Umidificador já desligado", "umidificador": 0}), 200


def _ciclo(placa, caminho, chave, rotulo):
    resposta, erro = devices.comando_placa(placa, caminho)
    if erro:
        return jsonify({"erro": erro}), 503
    if resposta.status_code != 200:
        return jsonify({"erro": f"Placa retornou {resposta.status_code}"}), 500
    atual = int(estado_quarto.get(chave, 0) or 0)
    if atual < 3:
        estado_quarto[chave] = atual + 1
        msg = f"{rotulo} nível {estado_quarto[chave]}"
    else:
        estado_quarto[chave] = 0
        msg = f"{rotulo} desligado"
    salvar_estado()
    return jsonify({"status": "sucesso", "mensagem": msg, chave: estado_quarto[chave]}), 200


def alternar_dormir():
    pretendido = 0 if estado_quarto.get("dormir") else 1
    resposta, erro = devices.comando_placa("janela", "/dormir")
    if erro:
        return jsonify({"erro": erro}), 503
    if resposta.status_code != 200:
        return jsonify({"erro": f"Placa respondeu {resposta.status_code}"}), 500
    estado_quarto["dormir"] = pretendido
    salvar_estado()
    texto = "entrando" if pretendido else "saindo"
    return jsonify({
        "mensagem": f"ESP32 informada: {texto} em modo dormir.",
        "modo_dormir": bool(pretendido),
    }), 200
