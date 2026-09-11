import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_ESTADO = os.path.join(BASE_DIR, "estado_quarto.json")
ARQUIVO_APRENDIZADO = os.path.join(BASE_DIR, "aprendizado.json")

placas_registradas = {
    "janela": "192.168.0.117",
    "esp8266tu": "192.168.0.93",
    "esp8266ar": "192.168.0.172",
    "esp01luzesc": "192.168.0.195",
    "esp32c3vent": "192.168.0.65",
}

estado_quarto_padrao = {
    "dormir": 0,
    "ar_ligado": 0,
    "janela_aberta": 1,
    "ventilador": 0,
    "umidificador": 0,
    "luz_ligada": 0,
    "temperatura_atual": 24.8,
    "umidade_atual": 56.0,
    "luminosidade_atual": 320.0,
    "chuva_atual": 12.0,
    "presenca_interna": 0,
    "presenca_externa": 0,
    "temperatura_limite": 28.5,
    "temperatura_alvo": 24.0,
    "umidade_alvo": 50.0,
    "umidade_minima": 40.0,
    "umidade_maxima": 65.0,
    "limiar_chuva": 40.0,
    "hora_abrir_manha": 7,
    "hora_fechar_noite": 22,
    "modo_agente": "cognitivo",
    "modo_simulacao": 1,
    "ultima_acao_agente": None,
    "ultima_razao_agente": "Ainda sem decisão.",
}

def _carregar_json(caminho, padrao):
    if not os.path.exists(caminho):
        return dict(padrao)
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(padrao, dict):
            mesclado = dict(padrao)
            mesclado.update(dados)
            return mesclado
        return dados
    except (OSError, json.JSONDecodeError):
        return dict(padrao)


def salvar_estado():
    with open(ARQUIVO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado_quarto, f, indent=2, ensure_ascii=False)


def salvar_aprendizado():
    with open(ARQUIVO_APRENDIZADO, "w", encoding="utf-8") as f:
        json.dump(aprendizado, f, indent=2, ensure_ascii=False)


estado_quarto = _carregar_json(ARQUIVO_ESTADO, estado_quarto_padrao)

aprendizado_padrao = {
    "pesos": {
        "abrir_janela": 0.0,
        "fechar_janela": 0.0,
        "ligar_ar": 0.0,
        "desligar_ar": 0.0,
        "ligar_ventilador": 0.0,
        "desligar_ventilador": 0.0,
        "ligar_umidificador": 0.0,
        "desligar_umidificador": 0.0,
        "ligar_luz": 0.0,
        "desligar_luz": 0.0,
        "abrir_janela_manha": 0.0,
    },
    "hora_abrir_manha": 7,
    "historico_feedback": [],
}

aprendizado = _carregar_json(ARQUIVO_APRENDIZADO, aprendizado_padrao)
if "pesos" not in aprendizado:
    aprendizado = dict(aprendizado_padrao)
