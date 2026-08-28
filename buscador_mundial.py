import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
from urllib.request import Request, urlopen
import psycopg

MATRIZ_GLOBAL = [
    {"tipo":"Filme","categoria":"Acao","pais":"Brasil","idioma":"Portugues","termo":"filme de acao completo dublado"},
    {"tipo":"Filme","categoria":"Terror","pais":"Brasil","idioma":"Portugues","termo":"filme de terror completo dublado"},
    {"tipo":"Filme","categoria":"Comedia","pais":"EUA","idioma":"Ingles","termo":"full comedy movie public domain"},
    {"tipo":"Filme","categoria":"Sci-Fi","pais":"EUA","idioma":"Ingles","termo":"full sci-fi movie public domain"},
    {"tipo":"Filme","categoria":"Drama","pais":"Mexico","idioma":"Espanhol","termo":"pelicula de drama completa dominio publico"},
    {"tipo":"Filme","categoria":"Anime","pais":"Japao","idioma":"Japones","termo":"公式 アニメ 映画 フル 公開"},
    {"tipo":"Serie","categoria":"Documentario","pais":"Brasil","idioma":"Portugues","termo":"serie documental episodio completo oficial"},
    {"tipo":"Serie","categoria":"Sci-Fi","pais":"EUA","idioma":"Ingles","termo":"web series episode full official"},
    {"tipo":"Audiolivro","categoria":"Filosofia","pais":"Brasil","idioma":"Portugues","termo":"audiolivro dominio publico portugues"},
    {"tipo":"Audiolivro","categoria":"Literatura","pais":"Brasil","idioma":"Portugues","termo":"audiolivro machado de assis dominio publico"},
    {"tipo":"Audiolivro","categoria":"Literatura","pais":"Reino Unido","idioma":"Ingles","termo":"public domain audiobook sherlock holmes"},
]

def search(term):
    try:
        url = "https://www.youtube.com/results?search_query=" + quote(term)
        req = Request(url, headers={"User-Agent":"WEBPLAY-Discovery/1.0"})
        with urlopen(req, timeout=12) as response:
            return response.read().decode("utf-8", "ignore")
    except Exception:
        return ""

def initial_data(html):
    match = re.search(r"ytInitialData\s*=\s*(\{.*?\})\s*;", html, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

def walk(obj):
    if isinstance(obj, dict):
        if "videoRenderer" in obj:
            yield obj["videoRenderer"]
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)

def extract(html, node):
    data = initial_data(html)
    if not data:
        return []
    result=[];seen=set()
    for video in walk(data):
        video_id=video.get("videoId");runs=video.get("title",{}).get("runs",[]);owner=video.get("ownerText",{}).get("runs",[])
        if not video_id or not runs or video_id in seen: continue
        title=runs[0].get("text","").strip();source=owner[0].get("text","YouTube") if owner else "YouTube";lower=title.lower()
        if node["tipo"]=="Filme" and any(x in lower for x in ("trailer","review","reaction","gameplay")): continue
        if node["tipo"]=="Audiolivro" and not any(x in lower for x in ("audio","livro","book","hoerbuch")): continue
        seen.add(video_id);result.append((title,source,video_id,video.get("lengthText",{}).get("simpleText","Completo")))
    return result[:30]

def processar(node):
    items=extract(search(node["termo"]),node)
    if not items:return 0
    count=0
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        for title,source,video_id,duration in items:
            conn.execute("""INSERT INTO media_items(title,source_name,youtube_video_id,media_type,category,country,language,duration,thumbnail_url,source_url,is_active)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE)
            ON CONFLICT(youtube_video_id) DO UPDATE SET title=EXCLUDED.title,source_name=EXCLUDED.source_name,updated_at=now()""",
            (title,source,video_id,node["tipo"],node["categoria"],node["pais"],node["idioma"],duration,f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",f"https://www.youtube.com/watch?v={video_id}"))
            count+=1
    return count

def run():
    print("WEBPLAY — indexador global multithread")
    total=0
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures=[executor.submit(processar,node) for node in MATRIZ_GLOBAL]
        for future in as_completed(futures): total+=future.result()
    print(f"WEBPLAY — concluído: {total} registros descobertos; mídia permanece inativa até validação de direitos.")

if __name__=="__main__": run()
