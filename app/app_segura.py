"""
app_segura.py — La versión corregida, para comparar.

Cada hallazgo de app_insegura.py está arreglado acá, con el mismo
número de referencia. Leé los dos archivos en paralelo: la diferencia
suele ser de una o dos líneas, y ese es el punto del ejercicio.
"""
import hashlib
import os
import shlex
import sqlite3
import subprocess

from flask import Flask, Response, request

app = Flask(__name__)

# ── ARREGLO 1 — Credenciales desde el entorno ───────────────────
# Nada sensible queda escrito en el código ni en el historial de Git.
DB_PASSWORD = os.environ.get("DB_PASSWORD")
API_KEY = os.environ.get("API_KEY")


def get_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INT, nombre TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'ada'), (2, 'linus')")
    return conn


@app.route("/usuario")
def buscar_usuario():
    """── ARREGLO 2 — Consulta parametrizada ──
    El valor viaja aparte de la consulta, así que el motor nunca lo
    interpreta como SQL. Además validamos que sea un número.
    """
    user_id = request.args.get("id", "1")
    if not user_id.isdigit():
        return {"error": "el id tiene que ser numerico"}, 400

    conn = get_db()
    resultado = conn.execute(
        "SELECT * FROM users WHERE id = ?", (int(user_id),)
    ).fetchall()
    return {"resultado": str(resultado)}


@app.route("/hash")
def hashear():
    """── ARREGLO 3 — SHA-256 en lugar de MD5 ──
    Para contraseñas no alcanza ni SHA-256: ahí va bcrypt o argon2.
    """
    texto = request.args.get("texto", "hola")
    return {"sha256": hashlib.sha256(texto.encode()).hexdigest()}


@app.route("/ping")
def ping():
    """── ARREGLO 4 — Sin shell, con lista de argumentos y validación ──
    Sin shell=True no hay intérprete de comandos que pueda ser engañado,
    y además restringimos qué hosts se aceptan.
    """
    host = request.args.get("host", "localhost")
    permitidos = {"localhost", "127.0.0.1"}
    if host not in permitidos:
        return {"error": "host no permitido"}, 400

    salida = subprocess.check_output(
        ["ping", "-c", "1", shlex.quote(host)], timeout=5
    )
    return Response(salida, mimetype="text/plain")


@app.route("/salud")
def salud():
    """── ARREGLO 5 — Diagnóstico sin exponer nada ──
    Devuelve estado, no configuración.
    """
    return {"estado": "ok"}


@app.route("/")
def home():
    return {"app": "demo segura", "modulo": 7}


if __name__ == "__main__":
    # ── ARREGLO 6 — Debug apagado ──
    # En producción esto además iría detrás de un servidor WSGI real
    # (gunicorn, uwsgi), no con el servidor de desarrollo de Flask.
    app.run(host="0.0.0.0", port=8000, debug=False)
