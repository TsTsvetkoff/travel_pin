"""Refresh the local GeoNames Bulgaria settlement index (no runtime geocoder)."""
import json,re,urllib.request,zipfile,io,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from places import normalize
ROOT=Path(__file__).resolve().parents[1]

def fetch(url):
    with urllib.request.urlopen(url,timeout=30) as r:return r.read()
def main():
    source=Path(sys.argv[1]).read_bytes() if len(sys.argv)>1 else fetch('https://download.geonames.org/export/dump/BG.zip')
    admin={r[0]:r[1] for line in fetch('https://download.geonames.org/export/dump/admin1CodesASCII.txt').decode().splitlines() if (r:=line.split('\t')) and r[0].startswith('BG.')}
    rows=zipfile.ZipFile(io.BytesIO(source)).read('BG.txt').decode().splitlines();out=[]
    for line in rows:
        r=line.split('\t')
        if r[6]!='P' or r[7] not in {'PPL','PPLA','PPLA2','PPLA3','PPLA4','PPLC'}:continue
        names=[r[1],r[2]]+r[3].split(',')
        out.append(dict(id=int(r[0]),name=r[1],keys=sorted({normalize(s) for s in names if s}),lat=float(r[4]),lon=float(r[5]),region=admin.get('BG.'+r[10],r[10] or 'Bulgaria'),population=int(r[14] or 0)))
    out.sort(key=lambda c:(-c['population'],c['name']))
    (ROOT/'static/data/cities.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print('Saved',len(out),'settlements')
if __name__=='__main__':main()
