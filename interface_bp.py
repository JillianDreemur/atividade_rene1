from flask import Blueprint, jsonify, request
import services
import agentes
from config import estado_quarto, placas_registradas, aprendizado, salvar_estado

inter_bp = Blueprint("interf", __name__)


@inter_bp.route("/dormir", methods=["POST", "GET"])
def alternar_modo_dormir():
    return services.alternar_dormir()


@inter_bp.route("/ajustar_limite", methods=["GET", "POST"])
def ajustar_temp_limit():
    temp = request.args.get("temp") or (request.json or {}).get("temp")
    return services.ajustar_temp_limite(temp)


@inter_bp.route("/preferencias", methods=["GET", "POST"])
def preferencias():
    if request.method == "GET":
        return jsonify(services.estado_publico())
    dados = request.get_json(silent=True) or request.args.to_dict()
    return services.ajustar_preferencias(dados)


@inter_bp.route("/abrir")
def abrir_janela_endpoint():
    agentes.feedback_override("abrir_janela")
    return services.abrir_janela()


@inter_bp.route("/fechar")
def fechar_janela_endpoint():
    agentes.feedback_override("fechar_janela")
    return services.fechar_janela()


@inter_bp.route("/ligarar")
def ligarar_endpoint():
    agentes.feedback_override("ligar_ar")
    return services.ligar_ar()


@inter_bp.route("/desligarar")
def desligarar_endpoint():
    agentes.feedback_override("desligar_ar")
    return services.desligar_ar()


@inter_bp.route("/ligarventilador")
def ligarventila():
    agentes.feedback_override("ligar_ventilador")
    return services.ligar_ventilador()


@inter_bp.route("/desligarventilador")
def desligarventila():
    agentes.feedback_override("desligar_ventilador")
    return services.desligar_ventilador()


@inter_bp.route("/ligarumidificador")
def ligarumidificador():
    agentes.feedback_override("ligar_umidificador")
    return services.ligar_umidificador()


@inter_bp.route("/desligarumidificador")
def desligarumidificador():
    agentes.feedback_override("desligar_umidificador")
    return services.desligar_umidificador()


@inter_bp.route("/ligarluz")
def ligarluz():
    agentes.feedback_override("ligar_luz")
    return services.ligar_luz()


@inter_bp.route("/desligarluz")
def desligarluz():
    agentes.feedback_override("desligar_luz")
    return services.desligar_luz()


@inter_bp.route("/status_geral", methods=["GET"])
def status_geral():
    return jsonify(services.estado_publico())


@inter_bp.route("/decidir", methods=["GET", "POST"])
def decidir_agora():
    plano = agentes.decidir(origem="manual")
    executar = request.args.get("executar", "1") != "0"
    execucao = services.aplicar_acao(plano["acao"]) if executar else None
    return jsonify({"plano": plano, "execucao": execucao})


@inter_bp.route("/feedback", methods=["GET", "POST"])
def feedback():
    dados = request.get_json(silent=True) or {}
    acao = dados.get("acao") or request.args.get("acao")
    valor = dados.get("valor", request.args.get("valor", -1))
    comentario = dados.get("comentario") or request.args.get("comentario", "")
    if not acao:
        return jsonify({"erro": "Informe a ação (ex: abrir_janela)"}), 400
    resultado = agentes.registrar_feedback(acao, valor, comentario)
    return jsonify({"status": "ok", "aprendizado": resultado, "historico": aprendizado.get("historico_feedback", [])[-10:]})


@inter_bp.route("/aprendizado")
def ver_aprendizado():
    return jsonify(aprendizado)


@inter_bp.route("/simulacao", methods=["GET", "POST"])
def alternar_simulacao():
    estado_quarto["modo_simulacao"] = 0 if estado_quarto.get("modo_simulacao") else 1
    salvar_estado()
    ligado = bool(estado_quarto["modo_simulacao"])
    return jsonify({
        "status": "ok",
        "modo_simulacao": ligado,
        "mensagem": "Simulação ligada: comandos não falam com as ESPs." if ligado else "Simulação desligada: comandos vão para os IPs reais.",
    })


@inter_bp.route("/modo/<nome>", methods=["GET", "POST"])
def trocar_modo(nome):
    if nome not in ("reativo", "cognitivo", "adaptativo"):
        return jsonify({"erro": "Use reativo, cognitivo ou adaptativo"}), 400
    estado_quarto["modo_agente"] = nome
    salvar_estado()
    return jsonify({"status": "ok", "modo_agente": nome})


@inter_bp.route("/placas", methods=["POST"])
def atualizar_placa():
    dados = request.get_json(silent=True) or {}
    nome = dados.get("placa") or request.args.get("placa")
    ip = dados.get("ip") or request.args.get("ip")
    if not nome or not ip:
        return jsonify({"erro": "placa e ip são obrigatórios"}), 400
    placas_registradas[nome] = ip
    return jsonify({"status": "ok", "placas": placas_registradas})
