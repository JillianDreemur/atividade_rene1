import requests
from config import placas_registradas

TIMEOUT_PADRAO = 5
TIMEOUT_JANELA = 15


def ip_da(nome):
    return placas_registradas.get(nome)


def comando_placa(nome, caminho, timeout=TIMEOUT_PADRAO):
    ip = ip_da(nome)
    if not ip:
        return None, f"IP da placa '{nome}' não encontrado."
    url = f"http://{ip}{caminho}"
    try:
        resposta = requests.get(url, timeout=timeout)
        return resposta, None
    except requests.exceptions.RequestException as erro:
        return None, f"Falha de comunicação com {nome}: {erro}"


def interpretar_comando(resposta, ok_208=True):
    if resposta is None:
        return False, 503
    if resposta.status_code == 200:
        return True, 200
    if ok_208 and resposta.status_code == 208:
        return True, 208
    return False, resposta.status_code
