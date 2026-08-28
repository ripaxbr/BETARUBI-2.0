import os,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.parse import quote
from urllib.request import Request,urlopen
import psycopg
TERMS={'Brasil':['TV ao vivo','Web TV ao vivo','TV regional ao vivo','Jornalismo ao vivo','TV Assembleia'],'Argentina':['TN en vivo','C5N en vivo'],'México':['N Mas en vivo','Milenio en vivo'],'Colômbia':['Noticias Caracol en vivo','Canal RCN en vivo'],'Chile':['T13 en vivo','Meganoticias en vivo'],'Peru':['RPP en vivo','TV Peru en vivo'],'Estados Unidos':['ABC News Live','NBC News NOW'],'Canadá':['CBC News live','CTV News live'],'Reino Unido':['Sky News Live','BBC News Live'],'França':['France 24 en direct'],'Espanha':['RTVE en directo'],'Portugal':['RTP ao vivo'],'Itália':['TGCOM24 in diretta'],'Alemanha':['Tagesschau live'],'Japão':['ANN News live'],'Coreia do Sul':['YTN live'],'Índia':['Aaj Tak Live'],'Austrália':['ABC News Australia live'],'África do Sul':['SABC News live']}
def search(t):
 try:
  with urlopen(Request('https://www.youtube.com/results?search_query='+quote(t),headers={'User-Agent':'Mozilla/5.0 BETARUBI-2.0'}),timeout=12) as r:return r.read().decode('utf-8','ignore')
 except Exception:return ''
def ids(html):return set(re.findall(r'"channelId":"(UC[a-zA-Z0-9_-]{20,})"',html))
def run_one(country,term):
 found=0
 for cid in ids(search(term)):
  with psycopg.connect(os.environ['DATABASE_URL']) as c:
   cur=c.execute("INSERT INTO tv_channels(name,youtube_channel_id,country) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING RETURNING id",(f'Canal {cid[-8:]}',cid,country));found+=bool(cur.fetchone())
 return found
def run():
 with ThreadPoolExecutor(max_workers=6) as ex: total=sum(f.result() for f in as_completed([ex.submit(run_one,p,t) for p,ts in TERMS.items() for t in ts]))
 print(f'BETARUBI 2.0: {total} novos canais')
if __name__=='__main__':run()
