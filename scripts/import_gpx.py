"""Import personal E3/E4/E8 recordings. Usage: python scripts/import_gpx.py path/to/gpx_folder"""
import argparse, gzip, json, math
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]

def simplify(points,tolerance=12):
    if len(points)<3:return points
    scale=111195; cos=math.cos(math.radians(sum(p[1] for p in points)/len(points)))
    xy=[(p[0]*scale*cos,p[1]*scale) for p in points];keep={0,len(points)-1};stack=[(0,len(points)-1)]
    while stack:
        a,b=stack.pop();ax,ay=xy[a];bx,by=xy[b];dx=bx-ax;dy=by-ay;den=dx*dx+dy*dy;best=tolerance*tolerance;idx=None
        for i in range(a+1,b):
            x,y=xy[i];t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/den)) if den else 0
            d=(x-ax-t*dx)**2+(y-ay-t*dy)**2
            if d>best:best=d;idx=i
        if idx is not None:keep.add(idx);stack.extend([(a,idx),(idx,b)])
    return [points[i] for i in sorted(keep)]

def convert(path,code):
    segments=[];cur=[];days=set();prev=None;count=0
    opener=gzip.open if path.suffix=='.gz' else open
    with opener(path,'rb') as stream:
        for event,e in ET.iterparse(stream,events=('start','end')):
            tag=e.tag.rsplit('}',1)[-1]
            if event=='start' and tag=='trkseg':
                if cur:segments.append(cur);cur=[]
                prev=None
            if event!='end' or tag!='trkpt':continue
            t=next((x.text for x in e if x.tag.rsplit('}',1)[-1]=='time'),None)
            time=datetime.fromisoformat(t.replace('Z','+00:00')) if t else None
            if time:days.add(time.astimezone(ZoneInfo('Europe/Sofia')).date().isoformat())
            if time and prev and ((time-prev).total_seconds()>1800 or time<=prev):
                if cur:segments.append(cur);cur=[]
            cur.append([round(float(e.attrib['lon']),6),round(float(e.attrib['lat']),6)]);prev=time;count+=1;e.clear()
    if cur:segments.append(cur)
    lines=[simplify(s) for s in segments if len(s)>=2]
    labels={'E3':('E3 · Kom–Emine','#c93636'),'E4':('E4 · Five Mountains','#c93636'),'E8':('E8 · Rila–Rhodope','#c93636')}
    name,color=labels[code];dates=sorted(days)
    note='Your personal recorded track. Long recording gaps are kept separate.'
    if code=='E8':note+=' Recorded dates include a six-day gap and two continuous midnight crossings; they may not match original hiking stages.'
    return dict(type='Feature',properties=dict(code=code,name=name,color=color,source_file=path.name,source_points=count,recorded_days=len(days),dates=dates[0]+' → '+dates[-1],description=note),geometry=dict(type='MultiLineString',coordinates=lines))

def main():
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();features=[]
    for code in ['E3','E4','E8']:
        files=list(a.folder.glob(code+'*.gpx'))+list(a.folder.glob(code+'*.gpx.gz'))
        if len(files)!=1:raise SystemExit(f'Expected exactly one {code} GPX; found {len(files)}')
        features.append(convert(files[0],code));print(code,features[-1]['properties']['source_points'],'source points')
    target=ROOT/'static/data/hikes.geojson';target.parent.mkdir(exist_ok=True,parents=True)
    target.write_text(json.dumps(dict(type='FeatureCollection',features=features),ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print('Wrote',target)
if __name__=='__main__':main()
