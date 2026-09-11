import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sensores.db")


def _conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init():
    with _conectar() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS monitoramento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                luminosidade REAL,
                umidade REAL,
                temperatura REAL,
                status_janela TEXT,
                chuva REAL,
                criado_em TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS temperatura_umidade (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                umidade REAL,
                temperatura REAL,
                criado_em TEXT
            )
            """
        )


def inserir(luminosidade, umidade, temperatura, status_janela, chuva):
    _init()
    agora = datetime.now().isoformat(timespec="seconds")
    with _conectar() as conn:
        conn.execute(
            """
            INSERT INTO monitoramento
            (luminosidade, umidade, temperatura, status_janela, chuva, criado_em)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (luminosidade, umidade, temperatura, status_janela, chuva, agora),
        )


def inserir_th(umidade, temperatura):
    _init()
    agora = datetime.now().isoformat(timespec="seconds")
    with _conectar() as conn:
        conn.execute(
            """
            INSERT INTO temperatura_umidade (umidade, temperatura, criado_em)
            VALUES (?, ?, ?)
            """,
            (umidade, temperatura, agora),
        )


def listar(limite=200):
    _init()
    with _conectar() as conn:
        linhas = conn.execute(
            """
            SELECT * FROM monitoramento
            ORDER BY id DESC
            LIMIT ?
            """,
            (limite,),
        ).fetchall()
    return [dict(l) for l in linhas]


def ultimas_th(limite=80):
    _init()
    with _conectar() as conn:
        linhas = conn.execute(
            """
            SELECT temperatura, umidade, criado_em
            FROM temperatura_umidade
            ORDER BY id DESC
            LIMIT ?
            """,
            (limite,),
        ).fetchall()
    return [dict(l) for l in reversed(linhas)]
