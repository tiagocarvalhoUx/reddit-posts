"""
server.py
Servidor Flask que serve o app Vue e expõe API para atualizar os posts do Reddit.

Uso: python execution/server.py
Acesse: http://localhost:8080
"""

import json
import os
import subprocess
import sys
from flask import Flask, jsonify, send_from_directory, Response

# Carrega variáveis do .env manualmente
_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_VERCEL  = bool(os.environ.get("VERCEL"))
TMP_DIR    = "/tmp" if IS_VERCEL else os.path.join(BASE_DIR, ".tmp")
DATA_FILE  = os.path.join(TMP_DIR, "reddit_top_posts.json")

_INDEX_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
try:
    with open(_INDEX_HTML_PATH, encoding="utf-8") as _f:
        _INDEX_HTML = _f.read()
except FileNotFoundError:
    _INDEX_HTML = "<h1>Reddit Pulse</h1><p>Clique em Refresh para carregar os dados.</p>"
FETCH_SCRIPT    = os.path.join(BASE_DIR, "execution", "fetch_reddit_posts.py")
GENERATE_SCRIPT = os.path.join(BASE_DIR, "execution", "generate_app.py")
EMAIL_SCRIPT    = os.path.join(BASE_DIR, "execution", "send_email.py")

app = Flask(__name__, static_folder=TMP_DIR)


@app.route("/")
def index():
    app_html = os.path.join(TMP_DIR, "app.html")
    if os.path.exists(app_html):
        with open(app_html, encoding="utf-8") as f:
            return f.read(), 200, {"Content-Type": "text/html; charset=utf-8"}
    return _INDEX_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/api/data")
def get_data():
    """Retorna os dados atuais do JSON."""
    if not os.path.exists(DATA_FILE):
        return jsonify({})
    with open(DATA_FILE, encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/api/update", methods=["GET", "POST"])
def update():
    """Executa o fetch e retorna os novos dados via streaming de progresso."""

    def run():
        yield "data: " + json.dumps({"status": "running", "msg": "Buscando posts no Reddit..."}) + "\n\n"

        _env = {**os.environ, "TMP_DIR": TMP_DIR}

        result = subprocess.run(
            [sys.executable, FETCH_SCRIPT],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_env,
        )

        if result.returncode != 0:
            yield "data: " + json.dumps({"status": "error", "msg": result.stderr or result.stdout}) + "\n\n"
            return

        yield "data: " + json.dumps({"status": "running", "msg": "Gerando app..."}) + "\n\n"

        subprocess.run(
            [sys.executable, GENERATE_SCRIPT],
            cwd=BASE_DIR,
            capture_output=True,
            env=_env,
        )

        with open(DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)

        yield "data: " + json.dumps({"status": "done", "data": data}) + "\n\n"

    return Response(run(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/send-email", methods=["POST"])
def send_email():
    """Gera e envia o e-mail HTML com os top posts."""
    result = subprocess.run(
        [sys.executable, EMAIL_SCRIPT],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "TMP_DIR": TMP_DIR},
    )
    if result.returncode != 0:
        return jsonify({"status": "error", "msg": result.stderr or result.stdout}), 500
    return jsonify({"status": "ok", "msg": "E-mail enviado com sucesso!"})


if __name__ == "__main__":
    os.makedirs(TMP_DIR, exist_ok=True)
    print(f"\n  Reddit Pulse rodando em: http://localhost:8080\n")
    app.run(host="0.0.0.0", port=8080, debug=False, threaded=True)
