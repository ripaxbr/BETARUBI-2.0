import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
from urllib.request import Request, urlopen

import psycopg

TERMS = {
    "Brasil": ["TV ao vivo", "Web TV ao vivo", "TV regional ao vivo", "Jornalismo ao vivo", "TV Assembleia"],
    "Argentina": ["TN en vivo", "C5N en vivo", "Crónica TV en vivo", "Noticias Argentina"],
    "México": ["N Mas en vivo", "Milenio en vivo", "Foro TV en vivo", "TV Azteca en vivo"],
    "Colômbia": ["Noticias Caracol en vivo", "Canal RCN en vivo"],
    "Chile": ["T13 en vivo", "Meganoticias en vivo"],
    "Peru": ["RPP en vivo", "TV Peru en vivo"],
    "Estados Unidos": ["ABC News Live", "NBC News NOW", "LiveNOW from FOX", "Voice of America"],
    "Canadá": ["CBC News live", "CTV News live"],
    "Reino Unido": ["Sky News Live", "BBC News Live", "GB News Live"],
    "França": ["France 24 en direct", "BFMTV en direct", "CNEWS en direct"],
    "Espanha": ["RTVE en directo", "Antena 3 en directo", "La Sexta en directo"],
    "Portugal": ["RTP ao vivo", "SIC Noticias ao vivo", "CNN Portugal ao vivo"],
    "Itália": ["TGCOM24 in diretta", "Rai News 24 in diretta"],
    "Alemanha": ["Tagesschau live", "WELT Nachrichtensender live", "N-TV live"],
    "Japão": ["ANN News live", "TBS News live", "FNN プライムオンライン"],
    "Coreia do Sul": ["YTN live", "KBS News live"],
    "Índia": ["Aaj Tak Live", "NDTV India Live", "India TV Live"],
    "Austrália": ["ABC News Australia live", "Sky News Australia live"],
    "África do Sul": ["SABC News live", "eNCA live"],
    "Egito": ["Al Jazeera Arabic live", "Al Arabiya live"],
    "República Dominicana": ["Noticias SIN en vivo", "CDN 37 en vivo"],
    "Porto Rico": ["WAPA en vivo", "Telemundo PR en vivo"],
}


def search(term):
    try:
        url = "https://www.youtube.com/results?search_query=" + quote(term)
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 BETARUBI-2.0"})
        with urlopen(req, timeout=12) as response:
            return response.read().decode("utf-8", "ignore")
    except Exception:
        return ""


def extract(html):
    ids = set(re.findall(r'"channelId":"(UC[a-zA-Z0-9_-]{20,})"', html))
    return ids


def run_one(country, term):
    found = 0
    ids = extract(search(term))
    if not ids:
        return 0
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        for channel_id in ids:
            row = conn.execute(
                """INSERT INTO tv_channels(name,youtube_channel_id,country,category,is_active)
                   VALUES(%s,%s,%s,'Mundial',TRUE)
                   ON CONFLICT (youtube_channel_id) DO UPDATE SET updated_at=now(), is_active=TRUE
                   RETURNING id""",
                (f"Canal {channel_id[-8:]}", channel_id, country),
            ).fetchone()
            found += bool(row)
    return found


def cleanup():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("DELETE FROM tv_channels WHERE youtube_channel_id IS NULL OR youtube_channel_id NOT LIKE 'UC%'")


def run():
    print("BETARUBI 2.0 — rastreador multithread iniciado")
    tasks = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for country, terms in TERMS.items():
            for term in terms:
                tasks.append(executor.submit(run_one, country, term))
        total = sum(f.result() for f in as_completed(tasks))
    cleanup()
    print(f"BETARUBI 2.0 — varredura concluída: {total} registros processados")


if __name__ == "__main__":
    run()
