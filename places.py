import json
import math
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
CATEGORY_MAP_BG_TO_EN=dict(zip(
    ['Крепост','Пещера','Парк / Забележителност','Манастир','Връх','Скално образувание','Музей','Ждрело / Екопътека','Остров','Езеро / Язовир','Събитие','Зоопарк','Водопад','АИР','Гробница','Светилище','Кромлех','Обсерватория / Планетариум','Хижа'],
    ['Fortress','Cave','Park / Landmark','Monastery','Peak','Rock Formation','Museum','Gorge / Eco Trail','Island','Lake / Reservoir','Event','Zoo','Waterfall','AIR','Tomb','Sanctuary','Cromlech','Observatory / Planetarium','Hut']))
CATEGORIES=sorted(CATEGORY_MAP_BG_TO_EN.values())

def normalize(value):
    value=''.join(c for c in unicodedata.normalize('NFD',value.lower()) if unicodedata.category(c)!='Mn')
    return re.sub(r'^(?:град\s+|гр\.\s*|село\s+|с\.\s*)','',value.strip()).strip()

@lru_cache(maxsize=1)
def cities():
    return json.loads((Path(__file__).parent/'static/data/cities.json').read_text(encoding='utf-8'))

def find_city(query,city_id=None):
    query=normalize(query)
    if not query:return None,[]
    candidates=[c for c in cities() if query in c['keys']]
    if city_id:
        chosen=next((c for c in candidates if str(c['id'])==str(city_id)),None)
        if chosen:return chosen,[]
    if len(candidates)==1:return candidates[0],[]
    return None,candidates

def distance(lat1,lon1,lat2,lon2):
    p1,p2=map(math.radians,[lat1,lat2]); dp=p2-p1;dl=math.radians(lon2-lon1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 6371.0088*2*math.asin(math.sqrt(min(1,max(0,a))))

def nearby(locations,center,radius):
    out=[]
    for loc in locations:
        d=distance(center['lat'],center['lon'],loc['latitude'],loc['longitude'])
        if d<=radius:out.append(dict(loc,distance_km=round(d,2),_distance=d))
    out.sort(key=lambda x:(x['_distance'],x['name_bg']))
    for item in out:item.pop('_distance')
    return out
