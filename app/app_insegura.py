"""
app_insegura.py — Práctica del Módulo 7 (DevSecOps)

⚠️  ESTE ARCHIVO TIENE FALLAS DE SEGURIDAD A PROPÓSITO.
    Es material de laboratorio: sirve para que los escáneres SAST
    tengan algo real que encontrar. NO lo uses como base de nada.

Cada bloque está marcado con el identificador del hallazgo que
debería reportar Semgrep o Bandit. La versión corregida de cada uno
está en app_segura.py, para que puedas comparar.
"""
import hashlib
import os
import sqlite3
import subprocess

from flask import Flask, Response, request

app = Flask(__name__)

# ── HALLAZGO 1 — Credencial escrita en el código ────────────────
# Regla: generic.secrets.security.detected-generic-api-key
# Por qué está mal: queda en el historial de Git para siempre.
#   Aunque la borres después, sigue estando en los commits viejos.
# Cómo se arregla: leerla de una variable de entorno o de un
#   gestor de secretos (Vault, AWS Secrets Manager, etc.).
DB_PASSWORD = "SuperSecreta123!"
API_KEY = "xxxxx"


def get_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INT, nombre TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'ada'), (2, 'linus')")
    return conn


@app.route("/usuario")
def buscar_usuario():
    """
    ── HALLAZGO 2 — Inyección SQL ──────────────────────────────
    Regla: python.sqlalchemy.security.sqlalchemy-execute-raw-query
    Por qué está mal: el texto que manda el usuario se concatena
      directamente a la consulta, así que puede cambiar su sentido.
    Cómo se arregla: usar consultas parametrizadas (ver app_segura.py).
    """
    user_id = request.args.get("id", "1")
    conn = get_db()

    query = "SELECT * FROM users WHERE id = " + user_id   # ← vulnerable
    resultado = conn.execute(query).fetchall()

    return {"resultado": str(resultado)}


@app.route("/hash")
def hashear():
    """
    ── HALLAZGO 3 — Algoritmo de hash obsoleto ─────────────────
    Regla: python.lang.security.audit.insecure-hash-algorithms-md5
    Por qué está mal: MD5 está roto desde hace años; no sirve para
      contraseñas ni para integridad.
    Cómo se arregla: usar bcrypt o argon2 para contraseñas,
      y SHA-256 o superior para integridad.
    """
    texto = request.args.get("texto", "hola")
    return {"md5": hashlib.md5(texto.encode()).hexdigest()}   # ← vulnerable


@app.route("/ping")
def ping():
    """
    ── HALLAZGO 4 — Inyección de comandos ──────────────────────
    Regla: python.lang.security.audit.subprocess-shell-true
    Por qué está mal: con shell=True, lo que escriba el usuario se
      interpreta como parte del comando del sistema operativo.
    Cómo se arregla: nunca shell=True con entrada del usuario;
      pasar los argumentos como lista y validar lo que entra.
    """
    host = request.args.get("host", "localhost")
    salida = subprocess.check_output(f"ping -c 1 {host}", shell=True)   # ← vulnerable
    return Response(salida, mimetype="text/plain")


@app.route("/debug")
def debug():
    """
    ── HALLAZGO 5 — Exposición de información interna ──────────
    Por qué está mal: devolver variables de entorno expone claves,
      tokens y detalles de la infraestructura a cualquiera.
    Cómo se arregla: no exponer esto nunca; si necesitás un endpoint
      de diagnóstico, que devuelva solo estado y esté autenticado.
    """
    return {"env": dict(os.environ)}   # ← vulnerable


@app.route("/")
def home():
    return {"app": "demo insegura", "modulo": 7}


if __name__ == "__main__":
    # ── HALLAZGO 6 — Debug activado y escuchando en todas las interfaces ──
    # Regla: python.flask.security.audit.debug-enabled
    # Por qué está mal: el modo debug de Flask expone una consola
    #   interactiva que permite ejecutar código en el servidor.
    app.run(host="0.0.0.0", port=8000, debug=True)   # ← vulnerable
