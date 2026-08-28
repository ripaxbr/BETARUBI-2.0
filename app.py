import os
import secrets
import time
from collections import defaultdict

import psycopg
from flask import Flask, jsonify, render_template, request, session, redirect, url_for

try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
except ImportError:
    sentry_sdk = None

if sentry_sdk and os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        integrations=[FlaskIntegration()],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")),
        send_default_pii=False,
    )

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
LOGIN_LIMIT = 5
LOGIN_WINDOW = 300
_attempts = defaultdict(list)


def db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não configurada")
    return psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row, connect_timeout=5)


def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS tv_channels (
            id BIGSERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            youtube_channel_id TEXT NOT NULL UNIQUE,
            country TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Mundial',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS tv_channels_country_idx ON tv_channels(country)")
        conn.execute("CREATE INDEX IF NOT EXISTS tv_channels_active_idx ON tv_channels(is_active)")


def rate_limited(ip):
    now = time.time()
    values = [t for t in _attempts[ip] if now - t < LOGIN_WINDOW]
    _attempts[ip] = values
    return len(values) >= LOGIN_LIMIT


def record_failure(ip):
    _attempts[ip].append(time.time())


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "microphone=(self)"
    return response


@app.get("/")
def index():
    try:
        with db() as conn:
            channels = conn.execute("SELECT id,name,youtube_channel_id,country,category FROM tv_channels WHERE is_active ORDER BY country,name").fetchall()
        countries = sorted({x["country"] for x in channels})
    except Exception as exc:
        if sentry_sdk:
            sentry_sdk.capture_exception(exc)
        channels, countries = [], []
    return render_template("index.html", channels=channels, countries=countries)


@app.get("/api/channels")
def channels():
    with db() as conn:
        return jsonify(conn.execute("SELECT id,name,youtube_channel_id,country,category FROM tv_channels WHERE is_active ORDER BY country,name").fetchall())


@app.get("/api/health")
@app.get("/api/status")
def health():
    try:
        with db() as conn:
            conn.execute("SELECT 1")
        return jsonify(ok=True, service="BETARUBI 2.0", database="ok")
    except Exception as exc:
        if sentry_sdk:
            sentry_sdk.capture_exception(exc)
        return jsonify(ok=False, service="BETARUBI 2.0", database="error"), 503


@app.route("/admin", methods=["GET", "POST"])
def admin():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if not ADMIN_PASSWORD:
        return "Administração não configurada: defina ADMIN_PASSWORD no ambiente.", 503
    if request.method == "POST":
        if rate_limited(ip):
            return "Muitas tentativas. Tente novamente em alguns minutos.", 429
        if not secrets.compare_digest(request.form.get("password", ""), ADMIN_PASSWORD):
            record_failure(ip)
            return render_template("admin.html", login=True, error="Senha incorreta."), 401
        session["admin"] = True
        _attempts.pop(ip, None)
        return redirect(url_for("admin"))
    if not session.get("admin"):
        return render_template("admin.html", login=True)
    with db() as conn:
        channels = conn.execute("SELECT * FROM tv_channels ORDER BY id DESC").fetchall()
    return render_template("admin.html", login=False, channels=channels)


@app.post("/admin/channels")
def add_channel():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    name = request.form.get("name", "").strip()
    cid = request.form.get("youtube_channel_id", "").strip()
    country = request.form.get("country", "").strip()
    if not name or not country or not cid.startswith("UC"):
        return "Dados inválidos.", 400
    with db() as conn:
        conn.execute("INSERT INTO tv_channels(name,youtube_channel_id,country) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING", (name, cid, country))
    return redirect(url_for("admin"))


@app.post("/admin/channels/<int:channel_id>/delete")
def delete_channel(channel_id):
    if not session.get("admin"):
        return redirect(url_for("admin"))
    with db() as conn:
        conn.execute("DELETE FROM tv_channels WHERE id=%s", (channel_id,))
    return redirect(url_for("admin"))


@app.post("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("admin"))


try:
    init_db()
except Exception:
    pass
