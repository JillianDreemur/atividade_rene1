import math
import os
import random
import threading
import time
from datetime import datetime

import agentes
import daofile
import services
from config import estado_quarto, salvar_estado

INTERVALO_S = 5


def _clamp(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


def _sanear():
    if float(estado_quarto.get("temperatura_atual", 99)) >= 50:
        estado_quarto["temperatura_atual"] = 24.8
    if float(estado_quarto.get("umidade_atual", 99)) >= 90:
        estado_quarto["umidade_atual"] = 56.0
    if float(estado_quarto.get("luminosidade_atual", 0)) <= 0:
        hora = datetime.now().hour
        estado_quarto["luminosidade_atual"] = 420.0 if 7 <= hora <= 18 else 18.0
    salvar_estado()


def _passo_ambiente():
    hora = datetime.now().hour
    temp = float(estado_quarto.get("temperatura_atual", 24.8))
    umid = float(estado_quarto.get("umidade_atual", 56))
    chuva = float(estado_quarto.get("chuva_atual", 8))

    externo = 23.5 + 5.5 * math.sin((hora - 9) / 12 * math.pi)
    if estado_quarto.get("ar_ligado"):
        temp += (22.8 - temp) * 0.18 + random.uniform(-0.15, 0.08)
    elif estado_quarto.get("janela_aberta"):
        temp += (externo - temp) * 0.12 + random.uniform(-0.2, 0.25)
    else:
        temp += 0.12 + random.uniform(-0.15, 0.2)

    if random.random() < 0.12:
        chuva = _clamp(chuva + random.uniform(18, 45), 0, 95)
    else:
        chuva = _clamp(chuva * 0.82 + random.uniform(-4, 3), 0, 95)

    if chuva > 40:
        umid += random.uniform(1.5, 4.0)
        temp -= 0.15
    elif estado_quarto.get("umidificador", 0):
        umid += 1.2
    else:
        umid += random.uniform(-1.4, 1.1)

    luz = 30 + 700 * max(0, math.sin((hora - 6) / 14 * math.pi))
    luz = _clamp(luz + random.uniform(-25, 25), 5, 900)
    if hora < 6 or hora > 20:
        luz = random.uniform(4, 28)

    estado_quarto["temperatura_atual"] = round(_clamp(temp, 18, 34), 1)
    estado_quarto["umidade_atual"] = round(_clamp(umid, 30, 90), 1)
    estado_quarto["chuva_atual"] = round(chuva, 1)
    estado_quarto["luminosidade_atual"] = round(luz, 0)
    estado_quarto["presenca_interna"] = 1 if 7 <= hora <= 23 and random.random() > 0.15 else 0
    salvar_estado()

    daofile.inserir(
        estado_quarto["luminosidade_atual"],
        estado_quarto["umidade_atual"],
        estado_quarto["temperatura_atual"],
        "aberta" if estado_quarto.get("janela_aberta") else "fechada",
        estado_quarto["chuva_atual"],
    )
    daofile.inserir_th(estado_quarto["umidade_atual"], estado_quarto["temperatura_atual"])


def _loop(app):
    while True:
        try:
            if int(estado_quarto.get("modo_simulacao", 0) or 0) == 1:
                with app.app_context():
                    _passo_ambiente()
                    plano = agentes.decidir(origem="ciclo")
                    services.aplicar_acao(plano["acao"], origem="ciclo")
        except Exception:
            pass
        time.sleep(INTERVALO_S)


def iniciar(app):
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    with app.app_context():
        _sanear()
    t = threading.Thread(target=_loop, args=(app,), daemon=True, name="ciclo-ambiente")
    t.start()
