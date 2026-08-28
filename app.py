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
        environment=os.getenv("APP_ENV", "production"),
    )

app = Flask(__name__, template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=1_048_576,
)

DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
LOGIN_LIMIT = 5
LOGIN_WINDOW = 300
_attempts = defaultdict(list)


def db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL não configurada")
    return psycopg.connect(
        DATABASE_URL,
        row_factory=psycopg.rows.dict_row,
        connect_timeout=5,
    )


def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS media_items (
            id BIGSERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            source_name TEXT NOT NULL,
            youtube_video_id TEXT NOT NULL UNIQUE,
            youtube_channel_id TEXT,
            media_type TEXT NOT NULL CHECK (media_type IN ('Filme','Serie','Audiolivro','TV')),
            category TEXT NOT NULL DEFAULT 'Geral',
            country TEXT NOT NULL DEFAULT 'Global',
            language TEXT NOT NULL DEFAULT 'Português',
            duration TEXT NOT NULL DEFAULT 'Completo',
            thumbnail_url TEXT,
            source_url TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS media_items_type_idx ON media_items(media_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS media_items_country_idx ON media_items(country)")
        conn.execute("CREATE INDEX IF NOT EXISTS media_items_language_idx ON media_items(language)")
        conn.execute("CREATE INDEX IF NOT EXISTS media_items_active_idx ON media_items(is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS media_items_title_idx ON media_items(title)")
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


def client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.remote_addr) or "unknown"


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
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; frame-src https://www.youtube.com https://www.youtube-nocookie.com; "
        "img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; base-uri 'self'; form-action 'self'"
    )
    return response


@app.get("/")
def index():
    try:
        tipo = request.args.get("tipo", "TODOS")
        pais = request.args.get("pais", "TODOS")
        idioma = request.args.get("idioma", "TODOS")
        with db() as conn:
            query = "SELECT * FROM media_items WHERE is_active"
            params = []
            if tipo != "TODOS":
                query += " AND media_type=%s"
                params.append(tipo)
            if pais != "TODOS":
                query += " AND country=%s"
                params.append(pais)
            if idioma != "TODOS":
                query += " AND language=%s"
                params.append(idioma)
            query += " ORDER BY id DESC LIMIT 500"
            media = conn.execute(query, params).fetchall()
            countries = [r["country"] for r in conn.execute("SELECT DISTINCT country FROM media_items WHERE is_active ORDER BY country").fetchall()]
            languages = [r["language"] for r in conn.execute("SELECT DISTINCT language FROM media_items WHERE is_active ORDER BY language").fetchall()]
            categories = [r["category"] for r in conn.execute("SELECT DISTINCT category FROM media_items WHERE is_active ORDER BY category").fetchall()]
    except Exception as exc:
        if sentry_sdk:
            sentry_sdk.capture_exception(exc)
        media, countries, languages, categories = [], [], [], []
        tipo, pais, idioma = "TODOS", "TODOS", "TODOS"
    return render_template("index.html", media=media, countries=countries, languages=languages, categories=categories, type_active=tipo, country_active=pais, language_active=idioma)


@app.get("/api/media")
def media_api():
    tipo = request.args.get("tipo", "TODOS")
    pais = request.args.get("pais", "TODOS")
    idioma = request.args.get("idioma", "TODOS")
    busca = request.args.get("q", "").strip()
    try:
        with db() as conn:
            query = "SELECT id,title,source_name,youtube_video_id,media_type,category,country,language,duration,thumbnail_url,source_url FROM media_items WHERE is_active"
            params = []
            if tipo != "TODOS":
                query += " AND media_type=%s"
                params.append(tipo)
            if pais != "TODOS":
                query += " AND country=%s"
                params.append(pais)
            if idioma != "TODOS":
                query += " AND language=%s"
                params.append(idioma)
            if busca:
                query += " AND (title ILIKE %s OR source_name ILIKE %s OR country ILIKE %s OR category ILIKE %s)"
                term = f"%{busca}%"
                params.extend([term, term, term, term])
            query += " ORDER BY id DESC LIMIT 200"
            return jsonify(conn.execute(query, params).fetchall())
    except Exception as exc:
        if sentry_sdk:
            sentry_sdk.capture_exception(exc)
        return jsonify(ok=False, error="Falha ao consultar catálogo"), 503


@app.get("/api/channels")
def channels_api():
    with db() as conn:
        return jsonify(conn.execute("SELECT id,name,youtube_channel_id,country,category FROM tv_channels WHERE is_active ORDER BY country,name").fetchall())


@app.get("/api/health")
@app.get("/api/status")
def health():
    try:
        with db() as conn:
            conn.execute("SELECT 1")
            media_count = conn.execute("SELECT count(*) AS n FROM media_items WHERE is_active").fetchone()["n"]
            channel_count = conn.execute("SELECT count(*) AS n FROM tv_channels WHERE is_active").fetchone()["n"]
        return jsonify(ok=True, service="BETARUBI 2.0", database="ok", media_count=media_count, channel_count=channel_count)
    except Exception as exc:
        if sentry_sdk:
            sentry_sdk.capture_exception(exc)
        return jsonify(ok=False, service="BETARUBI 2.0", database="error"), 503


@app.route("/admin", methods=["GET", "POST"])
def admin():
    ip = client_ip()
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
        media = conn.execute("SELECT * FROM media_items ORDER BY id DESC LIMIT 500").fetchall()
        channels = conn.execute("SELECT * FROM tv_channels ORDER BY id DESC LIMIT 500").fetchall()
    return render_template("admin.html", login=False, media=media, channels=channels)


@app.post("/admin/media")
def add_media():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    data = {k: request.form.get(k, "").strip() for k in ("title", "source_name", "youtube_video_id", "youtube_channel_id", "media_type", "category", "country", "language", "duration")}
    if not data["title"] or not data["source_name"] or not data["youtube_video_id"] or data["media_type"] not in {"Filme", "Serie", "Audiolivro", "TV"}:
        return "Dados inválidos.", 400
    source_url = f"https://www.youtube.com/watch?v={data['youtube_video_id']}"
    thumbnail = f"https://i.ytimg.com/vi/{data['youtube_video_id']}/hqdefault.jpg"
    with db() as conn:
        conn.execute("""INSERT INTO media_items(title,source_name,youtube_video_id,youtube_channel_id,media_type,category,country,language,duration,thumbnail_url,source_url)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (youtube_video_id) DO UPDATE SET updated_at=now(), is_active=TRUE""",
                     (data["title"], data["source_name"], data["youtube_video_id"], data["youtube_channel_id"] or None, data["media_type"], data["category"] or "Geral", data["country"] or "Global", data["language"] or "Português", data["duration"] or "Completo", thumbnail, source_url))
    return redirect(url_for("admin"))


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


@app.post("/admin/media/<int:media_id>/delete")
def delete_media(media_id):
    if not session.get("admin"):
        return redirect(url_for("admin"))
    with db() as conn:
        conn.execute("DELETE FROM media_items WHERE id=%s", (media_id,))
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
    if DATABASE_URL:
        init_db()
except Exception as exc:
    if sentry_sdk:
        sentry_sdk.capture_exception(exc)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
