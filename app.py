import os, secrets, time
from collections import defaultdict
import psycopg
from flask import Flask, jsonify, render_template, request, session, redirect, url_for
try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
except ImportError:
    sentry_sdk=None
if sentry_sdk and os.getenv('SENTRY_DSN'):
    sentry_sdk.init(dsn=os.environ['SENTRY_DSN'],integrations=[FlaskIntegration()],traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE','0.05')),send_default_pii=False,environment=os.getenv('APP_ENV','production'))
app=Flask(__name__,template_folder='templates');app.secret_key=os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_SECURE=os.getenv('SESSION_COOKIE_SECURE','true').lower()=='true',SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',MAX_CONTENT_LENGTH=1048576)
DATABASE_URL=os.getenv('DATABASE_URL');ADMIN_PASSWORD=os.getenv('ADMIN_PASSWORD');_attempts=defaultdict(list)
def db():
    if not DATABASE_URL: raise RuntimeError('DATABASE_URL não configurada')
    return psycopg.connect(DATABASE_URL,row_factory=psycopg.rows.dict_row,connect_timeout=5)
def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS media_items(id BIGSERIAL PRIMARY KEY,title TEXT NOT NULL,source_name TEXT NOT NULL,youtube_video_id TEXT NOT NULL UNIQUE,youtube_channel_id TEXT,media_type TEXT NOT NULL CHECK(media_type IN ('Filme','Serie','Audiolivro','TV')),category TEXT NOT NULL DEFAULT 'Geral',country TEXT NOT NULL DEFAULT 'Global',language TEXT NOT NULL DEFAULT 'Português',duration TEXT NOT NULL DEFAULT 'Completo',thumbnail_url TEXT,source_url TEXT NOT NULL,is_active BOOLEAN NOT NULL DEFAULT TRUE,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        for n,col in [('type','media_type'),('country','country'),('language','language'),('active','is_active'),('title','title')]: c.execute(f'CREATE INDEX IF NOT EXISTS media_items_{n}_idx ON media_items({col})')
        c.execute("""CREATE TABLE IF NOT EXISTS tv_channels(id BIGSERIAL PRIMARY KEY,name TEXT NOT NULL,youtube_channel_id TEXT NOT NULL UNIQUE,country TEXT NOT NULL,category TEXT NOT NULL DEFAULT 'Mundial',is_active BOOLEAN NOT NULL DEFAULT TRUE,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        c.execute("""CREATE TABLE IF NOT EXISTS vertical_series(id BIGSERIAL PRIMARY KEY,title TEXT NOT NULL,book_title TEXT,author TEXT,description TEXT,price_total NUMERIC(10,2) NOT NULL DEFAULT 19.90,is_active BOOLEAN NOT NULL DEFAULT TRUE,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        c.execute("""CREATE TABLE IF NOT EXISTS vertical_episodes(id BIGSERIAL PRIMARY KEY,series_id BIGINT NOT NULL REFERENCES vertical_series(id) ON DELETE CASCADE,episode_number INTEGER NOT NULL,title TEXT NOT NULL,youtube_video_id TEXT NOT NULL UNIQUE,release_at TIMESTAMPTZ,free_at TIMESTAMPTZ,access_mode TEXT NOT NULL DEFAULT 'premium' CHECK(access_mode IN ('free','premium')),price NUMERIC(10,2) NOT NULL DEFAULT 2.99,is_active BOOLEAN NOT NULL DEFAULT TRUE,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(series_id,episode_number))")
        c.execute("""CREATE TABLE IF NOT EXISTS orders(id BIGSERIAL PRIMARY KEY,provider TEXT NOT NULL,provider_payment_id TEXT UNIQUE,status TEXT NOT NULL,amount NUMERIC(10,2) NOT NULL,currency TEXT NOT NULL DEFAULT 'BRL',user_ref TEXT,series_id BIGINT REFERENCES vertical_series(id) ON DELETE SET NULL,episode_id BIGINT REFERENCES vertical_episodes(id) ON DELETE SET NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        c.execute("""CREATE TABLE IF NOT EXISTS episode_access(id BIGSERIAL PRIMARY KEY,user_ref TEXT NOT NULL,episode_id BIGINT NOT NULL REFERENCES vertical_episodes(id) ON DELETE CASCADE,order_id BIGINT REFERENCES orders(id) ON DELETE SET NULL,granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(user_ref,episode_id))")
        c.execute("""CREATE TABLE IF NOT EXISTS newsletter_subscribers(id BIGSERIAL PRIMARY KEY,email TEXT NOT NULL UNIQUE,subscribed_at TIMESTAMPTZ NOT NULL DEFAULT now(),active BOOLEAN NOT NULL DEFAULT TRUE)""")
def ip(): x=request.headers.get('X-Forwarded-For','');return (x.split(',')[0].strip() if x else request.remote_addr) or 'unknown'
def limited(x):
    now=time.time();_attempts[x]=[t for t in _attempts[x] if now-t<300];return len(_attempts[x])>=5
@app.after_request
def headers(r):
    r.headers['X-Content-Type-Options']='nosniff';r.headers['X-Frame-Options']='SAMEORIGIN';r.headers['Referrer-Policy']='strict-origin-when-cross-origin';return r
@app.get('/')
def index():
    tipo=request.args.get('tipo','TODOS');pais=request.args.get('pais','TODOS');idioma=request.args.get('idioma','TODOS')
    try:
        with db() as c:
            q='SELECT * FROM media_items WHERE is_active';p=[]
            for v,col in [(tipo,'media_type'),(pais,'country'),(idioma,'language')]:
                if v!='TODOS':q+=f' AND {col}=%s';p.append(v)
            q+=' ORDER BY id DESC LIMIT 500';media=c.execute(q,p).fetchall();countries=[x['country'] for x in c.execute('SELECT DISTINCT country FROM media_items WHERE is_active ORDER BY country').fetchall()]
    except Exception as e:
        if sentry_sdk:sentry_sdk.capture_exception(e)
        media=[];countries=[]
    return render_template('index.html',media=media,countries=countries,languages=[],categories=[],type_active=tipo,country_active=pais,language_active=idioma)
@app.get('/originais')
def originals():
    with db() as c:
        series=c.execute('SELECT * FROM vertical_series WHERE is_active ORDER BY id DESC').fetchall();data=[]
        for s in series:
            eps=c.execute('SELECT * FROM vertical_episodes WHERE series_id=%s AND is_active ORDER BY episode_number',(s['id'],)).fetchall();data.append({'id':s['id'],'title':s['title'],'book_title':s['book_title'],'author':s['author'],'description':s['description'],'price_total':s['price_total'],'episodes':eps})
    return render_template('originais.html',series=data)
@app.get('/api/media')
def media_api():
    qv=request.args.get('q','').strip();tipo=request.args.get('tipo','TODOS');pais=request.args.get('pais','TODOS');idioma=request.args.get('idioma','TODOS')
    try:
        with db() as c:
            q='SELECT id,title,source_name,youtube_video_id,media_type,category,country,language,duration,thumbnail_url,source_url FROM media_items WHERE is_active';p=[]
            for v,col in [(tipo,'media_type'),(pais,'country'),(idioma,'language')]:
                if v!='TODOS':q+=f' AND {col}=%s';p.append(v)
            if qv:q+=' AND (title ILIKE %s OR source_name ILIKE %s OR country ILIKE %s OR category ILIKE %s)';t=f'%{qv}%';p += [t]*4
            q+=' ORDER BY id DESC LIMIT 200';return jsonify(c.execute(q,p).fetchall())
    except Exception as e:
        if sentry_sdk:sentry_sdk.capture_exception(e)
        return jsonify(ok=False,error='Falha ao consultar catálogo'),503
@app.get('/api/channels')
def channels():
    with db() as c:return jsonify(c.execute('SELECT id,name,youtube_channel_id,country,category FROM tv_channels WHERE is_active ORDER BY country,name').fetchall())
@app.get('/api/vertical-series')
def vertical_series():
    with db() as c:return jsonify(c.execute('SELECT id,title,book_title,author,description,price_total FROM vertical_series WHERE is_active ORDER BY id DESC').fetchall())
@app.get('/api/vertical-series/<int:series_id>/episodes')
def episodes(series_id):
    with db() as c:return jsonify(c.execute('SELECT id,episode_number,title,youtube_video_id,release_at,free_at,access_mode,price FROM vertical_episodes WHERE series_id=%s AND is_active ORDER BY episode_number',(series_id,)).fetchall())
@app.post('/api/newsletter/subscribe')
def newsletter_subscribe():
    email=request.form.get('email','').strip().lower() if request.form else ''
    if not email and request.is_json: email=str((request.json or {}).get('email','')).strip().lower()
    if '@' not in email or len(email)>254:return jsonify(ok=False,error='E-mail inválido'),400
    with db() as c:c.execute('INSERT INTO newsletter_subscribers(email) VALUES(%s) ON CONFLICT(email) DO UPDATE SET active=TRUE',(email,))
    return jsonify(ok=True,message='Inscrição ativada')
@app.get('/api/health')
@app.get('/api/status')
def health():
    try:
        with db() as c:c.execute('SELECT 1');m=c.execute('SELECT count(*) n FROM media_items WHERE is_active').fetchone()['n'];s=c.execute('SELECT count(*) n FROM vertical_series WHERE is_active').fetchone()['n'];e=c.execute('SELECT count(*) n FROM vertical_episodes WHERE is_active').fetchone()['n'];ch=c.execute('SELECT count(*) n FROM tv_channels WHERE is_active').fetchone()['n'];n=c.execute('SELECT count(*) n FROM newsletter_subscribers WHERE active').fetchone()['n']
        return jsonify(ok=True,service='WEBPLAY',database='ok',media_count=m,series_count=s,episode_count=e,channel_count=ch,newsletter_subscribers=n)
    except Exception as e:
        if sentry_sdk:sentry_sdk.capture_exception(e)
        return jsonify(ok=False,service='WEBPLAY',database='error'),503
@app.route('/admin',methods=['GET','POST'])
def admin():
    x=ip()
    if not ADMIN_PASSWORD:return 'Administração não configurada.',503
    if request.method=='POST':
        if limited(x):return 'Muitas tentativas.',429
        if not secrets.compare_digest(request.form.get('password',''),ADMIN_PASSWORD):_attempts[x].append(time.time());return render_template('admin.html',login=True,error='Senha incorreta.'),401
        session['admin']=True;_attempts.pop(x,None);return redirect(url_for('admin'))
    if not session.get('admin'):return render_template('admin.html',login=True)
    with db() as c:media=c.execute('SELECT * FROM media_items ORDER BY id DESC LIMIT 500').fetchall();channels=c.execute('SELECT * FROM tv_channels ORDER BY id DESC LIMIT 500').fetchall();series=c.execute('SELECT * FROM vertical_series ORDER BY id DESC LIMIT 100').fetchall()
    return render_template('admin.html',login=False,media=media,channels=channels,series=series)
@app.post('/admin/media')
def add_media():
    if not session.get('admin'):return redirect(url_for('admin'))
    d={k:request.form.get(k,'').strip() for k in ('title','source_name','youtube_video_id','youtube_channel_id','media_type','category','country','language','duration')}
    if not d['title'] or not d['source_name'] or not d['youtube_video_id'] or d['media_type'] not in {'Filme','Serie','Audiolivro','TV'}:return 'Dados inválidos.',400
    with db() as c:c.execute("INSERT INTO media_items(title,source_name,youtube_video_id,youtube_channel_id,media_type,category,country,language,duration,thumbnail_url,source_url) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(youtube_video_id) DO UPDATE SET updated_at=now(),is_active=TRUE",(d['title'],d['source_name'],d['youtube_video_id'],d['youtube_channel_id'] or None,d['media_type'],d['category'] or 'Geral',d['country'] or 'Global',d['language'] or 'Português',d['duration'] or 'Completo',f"https://i.ytimg.com/vi/{d['youtube_video_id']}/hqdefault.jpg",f"https://www.youtube.com/watch?v={d['youtube_video_id']}"))
    return redirect(url_for('admin'))
@app.post('/admin/channels')
def add_channel():
    if not session.get('admin'):return redirect(url_for('admin'))
    n=request.form.get('name','').strip();cid=request.form.get('youtube_channel_id','').strip();p=request.form.get('country','').strip()
    if not n or not p or not cid.startswith('UC'):return 'Dados inválidos.',400
    with db() as c:c.execute('INSERT INTO tv_channels(name,youtube_channel_id,country) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',(n,cid,p))
    return redirect(url_for('admin'))
@app.post('/admin/series')
def add_series():
    if not session.get('admin'):return redirect(url_for('admin'))
    with db() as c:c.execute('INSERT INTO vertical_series(title,book_title,author,description,price_total) VALUES(%s,%s,%s,%s,%s)',(request.form.get('title','').strip(),request.form.get('book_title','').strip() or None,request.form.get('author','').strip() or None,request.form.get('description','').strip() or None,request.form.get('price_total') or 19.90))
    return redirect(url_for('admin'))
@app.post('/admin/episodes')
def add_episode():
    if not session.get('admin'):return redirect(url_for('admin'))
    with db() as c:c.execute('INSERT INTO vertical_episodes(series_id,episode_number,title,youtube_video_id,access_mode,price) VALUES(%s,%s,%s,%s,%s,%s)',(request.form.get('series_id'),request.form.get('episode_number'),request.form.get('title','').strip(),request.form.get('youtube_video_id','').strip(),request.form.get('access_mode','premium'),request.form.get('price') or 2.99))
    return redirect(url_for('admin'))
@app.post('/admin/logout')
def logout():session.clear();return redirect(url_for('admin'))
try:
    if DATABASE_URL:init_db()
except Exception as e:
    if sentry_sdk:sentry_sdk.capture_exception(e)
if __name__=='__main__':app.run(host='127.0.0.1',port=int(os.getenv('PORT','5000')),debug=False)
