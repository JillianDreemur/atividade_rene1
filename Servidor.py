from flask import Flask, jsonify, render_template, request
import daofile
import services
import agentes
from interface_bp import inter_bp
from config import placas_registradas, estado_quarto, salvar_estado

app = Flask(__name__)
app.register_blueprint(inter_bp, url_prefix="/interf")

ip_local = "0.0.0.0"
porta_local = 5050


@app.route("/placas", methods=["GET"])
def ver_status():
    if not placas_registradas:
        return jsonify({"mensagem": "Nenhuma placa registrada ainda."}), 200
    return jsonify(placas_registradas), 200


@app.route("/")
def home():
    return render_template("homeinfo.html", estado=services.estado_publico())


@app.route("/meuip", methods=["GET"])
def registrar_ip():
    nome_placa = request.args.get("placa")
    ip_placa = request.args.get("ip")
    if not nome_placa or not ip_placa:
        return jsonify({"erro": "Parâmetros 'placa' e 'ip' são obrigatórios"}), 400
    placas_registradas[nome_placa] = ip_placa
    return jsonify({"status": "sucesso", "mensagem": "IP registrado corretamente", "placas": placas_registradas}), 200


@app.route("/ajustar", methods=["GET"])
def receber_dados():
    return services.ajustar(
        request.args.get("temperatura"),
        request.args.get("umidade"),
        request.args.get("dormir"),
        request.args.get("aberta"),
        request.args.get("chuva"),
        request.args.get("luminosidade"),
        request.args.get("presenca"),
        request.args.get("presenca_externa"),
    )


@app.route("/listar")
def listar():
    dados = daofile.listar()
    return render_template("index.html", dados_sensor=dados)


@app.route("/status")
def get_status():
    return services.pegar_status()


@app.route("/historico.json")
def historico_json():
    return jsonify({"monitoramento": daofile.listar(120), "th": daofile.ultimas_th(80)})


@app.route("/graficos")
def graficos():
    return render_template("graficos.html")


@app.route("/monitoramento", methods=["POST"])
def recebe_dados():
    data = request.get_json(silent=True) or {}
    try:
        temp = float(data["temperatura"])
        umidade = float(data["umidade"])
        lumin = float(data.get("luminosidade", 0))
        status_janela = "aberta" if int(data.get("statusjanela", 0)) == 1 else "fechada"
        chuva_bruta = float(data.get("chuva", 0))
        chuva = round(100 - (chuva_bruta / 4095) * 100, 1) if chuva_bruta > 100 else round(chuva_bruta, 1)
        presenca = int(data.get("presenca", data.get("pir", 0)) or 0)
        presenca_ext = int(data.get("presenca_externa", 0) or 0)
    except (KeyError, TypeError, ValueError):
        return jsonify({"erro": "JSON incompleto ou inválido"}), 400

    daofile.inserir(lumin, umidade, temp, status_janela, chuva)
    estado_quarto["temperatura_atual"] = temp
    estado_quarto["umidade_atual"] = umidade
    estado_quarto["luminosidade_atual"] = lumin
    estado_quarto["chuva_atual"] = chuva
    estado_quarto["janela_aberta"] = 1 if status_janela == "aberta" else 0
    estado_quarto["presenca_interna"] = presenca
    estado_quarto["presenca_externa"] = presenca_ext
    salvar_estado()
    plano = agentes.decidir(origem="monitoramento")
    execucao = services.aplicar_acao(plano["acao"], origem="monitoramento")
    return jsonify({"message": "Dados salvos com sucesso", "plano": plano, "execucao": execucao}), 200


if __name__ == "__main__":
    print(f"Servidor do quarto em http://127.0.0.1:{porta_local}")
    app.run(host=ip_local, port=porta_local, debug=True)
