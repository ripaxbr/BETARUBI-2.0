"""WEBPLAY — motor diário de descoberta, canais e newsletter.

Princípios:
- Descoberta por APIs oficiais quando disponíveis.
- Nunca trata um vídeo encontrado como livre de direitos automaticamente.
- Só publica/ingere mídia marcada como autorizada, oficial ou domínio público verificado.
- Mantém até 50 canais por país, ranqueados por métricas públicas de audiência.
- Newsletter somente para assinantes ativos e com opt-in registrado.
"""
import html
import json
import os
import smtplib
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import psycopg

DB=os.environ["DATABASE_URL"]
YT_KEY=os.getenv("YOUTUBE_API_KEY","")
SMTP_HOST=os.getenv("SMTP_HOST","");SMTP_PORT=int(os.getenv("SMTP_PORT","587"));SMTP_USER=os.getenv("SMTP_USER","");SMTP_PASS=os.getenv("SMTP_PASS","");SMTP_FROM=os.getenv("SMTP_FROM",SMTP_USER);WEBPLAY_URL=os.getenv("WEBPLAY_URL","")
PAISES={"Brasil":("BR","pt"),"Estados Unidos":("US","en"),"México":("MX","es"),"Reino Unido":("GB","en"),"Argentina":("AR","es"),"Portugal":("PT","pt"),"Japão":("JP","ja"),"Coreia do Sul":("KR","ko"),"Canadá":("CA","en"),"França":("FR","fr"),"Alemanha":("DE","de"),"Espanha":("ES","es"),"Itália":("IT","it"),"Austrália":("AU","en"),"Índia":("IN","en"),"Chile":("CL","es"),"Colômbia":("CO","es"),"Uruguai":("UY","es"),"Peru":("PE","es"),"África do Sul":("ZA","en")}
SEARCH_TERMS=[("TV","live news official"),("Filme","public domain film official"),("Serie","official series episode"),("Audiolivro","public domain audiobook official")]

def get_json(url):
    req=Request(url,headers={"User-Agent":"WEBPLAY-Discovery/1.0"})
    with urlopen(req,timeout=20) as r:return json.loads(r.read().decode("utf-8"))

def youtube_search_channels(code,lang):
    if not YT_KEY:return []
    p=urlencode({"part":"snippet","type":"channel","maxResults":50,"order":"relevance","regionCode":code,"relevanceLanguage":lang,"key":YT_KEY,"q":"official television news culture entertainment"})
    return get_json("https://www.googleapis.com/youtube/v3/search?"+p).get("items",[])

def rank_channels(items):
    ids=[x.get("id",{}).get("channelId") for x in items if x.get("id",{}).get("channelId")]
    if not ids:return items[:50]
    ranked=[]
    for start in range(0,len(ids),50):
        p=urlencode({"part":"snippet,statistics","id":",".join(ids[start:start+50]),"key":YT_KEY})
        for item in get_json("https://www.googleapis.com/youtube/v3/channels?"+p).get("items",[]):
            st=item.get("statistics",{});item["_audience"]=(int(st.get("subscriberCount",0) or 0),int(st.get("viewCount",0) or 0));ranked.append(item)
    ranked.sort(key=lambda x:x.get("_audience",(0,0)),reverse=True)
    return ranked[:50]

def youtube_search_videos(code,lang,term):
    if not YT_KEY:return []
    p=urlencode({"part":"snippet","type":"video","maxResults":50,"order":"viewCount","regionCode":code,"relevanceLanguage":lang,"key":YT_KEY,"q":term})
    return get_json("https://www.googleapis.com/youtube/v3/search?"+p).get("items",[])

def ensure_schema(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS discovery_runs(id BIGSERIAL PRIMARY KEY,run_at TIMESTAMPTZ NOT NULL DEFAULT now(),country TEXT,channels_found INTEGER NOT NULL DEFAULT 0,media_found INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS content_rights(id BIGSERIAL PRIMARY KEY,youtube_video_id TEXT UNIQUE NOT NULL,rights_status TEXT NOT NULL DEFAULT 'unknown',evidence_url TEXT,reviewed_at TIMESTAMPTZ,reviewer TEXT)")

def save_channels(country,items):
    count=0
    with psycopg.connect(DB) as conn:
        for item in items[:50]:
            cid=item.get("id",{}).get("channelId");sn=item.get("snippet",{});name=sn.get("channelTitle") or sn.get("title")
            if not cid or not name:continue
            conn.execute("INSERT INTO tv_channels(name,youtube_channel_id,country,category) VALUES(%s,%s,%s,%s) ON CONFLICT(youtube_channel_id) DO UPDATE SET name=EXCLUDED.name,country=EXCLUDED.country,updated_at=now(),is_active=TRUE",(name,cid,country,"Top audiência WEBPLAY"));count+=1
    return count

def save_videos(country,language,items,media_type,category):
    count=0
    with psycopg.connect(DB) as conn:
        for item in items:
            vid=item.get("id",{}).get("videoId");sn=item.get("snippet",{});title=(sn.get("title") or "").strip();cid=sn.get("channelId");channel=sn.get("channelTitle") or "YouTube"
            if not vid or not title:continue
            conn.execute("INSERT INTO media_items(title,source_name,youtube_video_id,youtube_channel_id,media_type,category,country,language,duration,thumbnail_url,source_url,is_active) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'Completo',%s,%s,FALSE) ON CONFLICT(youtube_video_id) DO UPDATE SET title=EXCLUDED.title,source_name=EXCLUDED.source_name,youtube_channel_id=EXCLUDED.youtube_channel_id,updated_at=now()",(title,channel,vid,cid,media_type,category,country,language,f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",f"https://www.youtube.com/watch?v={vid}"));conn.execute("INSERT INTO content_rights(youtube_video_id,rights_status,evidence_url) VALUES(%s,'unknown',%s) ON CONFLICT(youtube_video_id) DO NOTHING",(vid,f"https://www.youtube.com/watch?v={vid}"));count+=1
    return count

def discover_country(country,code_lang):
    code,lang=code_lang;ch=save_channels(country,rank_channels(youtube_search_channels(code,lang)));med=0
    for media_type,term in SEARCH_TERMS:med+=save_videos(country,lang,youtube_search_videos(code,lang,term),media_type,"Descoberta")
    return country,ch,med

def newsletter():
    if not WEBPLAY_URL or not all((SMTP_HOST,SMTP_USER,SMTP_PASS)):return 0
    with psycopg.connect(DB) as conn:
        users=conn.execute("SELECT email FROM newsletter_subscribers WHERE active=TRUE ORDER BY id").fetchall();items=conn.execute("SELECT title,media_type,country,source_url FROM media_items WHERE is_active=TRUE AND updated_at>=now()-interval '1 day' ORDER BY updated_at DESC LIMIT 15").fetchall()
    if not users or not items:return 0
    rows="".join(f"<li><b>{html.escape(x['title'])}</b> — {html.escape(x['media_type'])} · {html.escape(x['country'])}</li>" for x in items)
    body=f"<div style='font-family:Arial;background:#040407;color:#fff;padding:24px'><h1 style='color:#00ff87'>WEBPLAY — Novidades</h1><p>Atualização diária do catálogo.</p><ul>{rows}</ul><p><a href='{html.escape(WEBPLAY_URL,quote=True)}' style='color:#00ff87'>Abrir WEBPLAY</a></p></div>"
    sent=0
    with smtplib.SMTP(SMTP_HOST,SMTP_PORT,timeout=20) as server:
        server.starttls();server.login(SMTP_USER,SMTP_PASS)
        for row in users:
            msg=MIMEMultipart("alternative");msg["Subject"]="WEBPLAY — novidades de hoje";msg["From"]=SMTP_FROM;msg["To"]=row["email"];msg.attach(MIMEText(body,"html","utf-8"));server.sendmail(SMTP_FROM,row["email"],msg.as_string());sent+=1
    return sent

def run():
    if not YT_KEY:raise RuntimeError("YOUTUBE_API_KEY não configurada; descoberta automática desativada por segurança.")
    with psycopg.connect(DB) as conn:ensure_schema(conn)
    total_channels=total_media=0
    with ThreadPoolExecutor(max_workers=min(8,len(PAISES))) as pool:
        futures=[pool.submit(discover_country,c,v) for c,v in PAISES.items()]
        for future in as_completed(futures):
            country,ch,med=future.result();total_channels+=ch;total_media+=med
            with psycopg.connect(DB) as conn:conn.execute("INSERT INTO discovery_runs(country,channels_found,media_found,status) VALUES(%s,%s,%s,'ok')",(country,ch,med))
    sent=newsletter();print(f"WEBPLAY: {total_channels} canais atualizados, {total_media} mídias descobertas (inativas até revisão), {sent} newsletters enviadas.")

if __name__=="__main__":run()
