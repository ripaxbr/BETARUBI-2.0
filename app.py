import os
import secrets
import psycopg
from flask import Flask, jsonify, render_template
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
except ImportError:
    sentry_sdk = None

if sentry_sdk and os.getenv('SENTRY_DSN'):
    sentry_sdk.init(dsn=os.environ['SENTRY_DSN'], integrations=[FlaskIntegration()], traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE','0.05')))

app=Flask(__name__,template_folder='templates')
app.secret_key=os.getenv('SECRET_KEY') or secrets.token_hex(32)

def db():
    return psycopg.connect(os.environ['DATABASE_URL'], row_factory=psycopg.rows.dict_row, connect_timeout=5)

def init_db():
    with db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS tv_channels (id BIGSERIAL PRIMARY KEY,name TEXT NOT NULL,youtube_channel_id TEXT NOT NULL UNIQUE,country TEXT NOT NULL,category TEXT NOT NULL DEFAULT 'Mundial',is_active BOOLEAN NOT NULL DEFAULT TRUE,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now())''')
        conn.execute('CREATE INDEX IF NOT EXISTS tv_channels_country_idx ON tv_channels(country)')
        conn.execute('CREATE INDEX IF NOT EXISTS tv_channels_active_idx ON tv_channels(is_active)')

@app.get('/')
def index():
    try:
        with db() as conn:
            channels=conn.execute("SELECT id,name,youtube_channel_id,country,category FROM tv_channels WHERE is_active ORDER BY country,name").fetchall()
        countries=sorted({x['country'] for x in channels})
    except Exception:
        channels=[]; countries=[]
    return render_template('index.html',channels=channels,countries=countries)

@app.get('/api/channels')
def channels():
    with db() as conn:
        return jsonify(conn.execute("SELECT id,name,youtube_channel_id,country,category FROM tv_channels WHERE is_active ORDER BY country,name").fetchall())

@app.get('/api/health')
@app.get('/api/status')
def health():
    try:
        with db() as conn: conn.execute('SELECT 1')
        return jsonify(ok=True,service='BETARUBI 2.0',database='ok')
    except Exception:
        return jsonify(ok=False,service='BETARUBI 2.0',database='error'),503

try: init_db()
except Exception: pass
