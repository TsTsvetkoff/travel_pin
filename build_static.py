"""Render the same templates for a root or /repository/ GitHub Pages site."""
import argparse
import json
import shutil
from pathlib import Path
from jinja2 import Environment,FileSystemLoader,select_autoescape
from places import CATEGORIES,CATEGORY_MAP_BG_TO_EN
ROOT=Path(__file__).resolve().parent

def build(source=ROOT/'locations.json',output=ROOT/'_site'):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=select_autoescape(['html']))
    data=json.loads(Path(source).read_text(encoding='utf-8'))
    titles={'10pp.png':'Ten mountain firsts','100Nto.png':'100 National Tourist Sites','5planini.png':'E4 · Five Mountains','kom_emine.png':'E3 · Kom–Emine','Rila_Rodopi.png':'E8 · Rila–Rhodope'}
    diplomas=[dict(file=p.name,title=titles.get(p.name,p.stem)) for p in sorted((ROOT/'static/diplomas').glob('*')) if p.suffix.lower() in {'.png','.jpg','.jpeg','.gif'}]
    for name,folder,page in [('index.html','','index'),('city_search.html','city_search','city'),('add.html','add','add'),('hall_of_fame.html','hall_of_fame','hall'),('error.html','','error')]:
        prefix='../' if folder else './'
        target=output/folder;target.mkdir(exist_ok=True)
        context=dict(static_mode=True,page=page,asset_base=prefix+'static/',
            nav=dict(index=prefix,city=prefix+'city_search/',add=prefix+'add/',hall=prefix+'hall_of_fame/'),
            locations=data,categories=CATEGORIES,bg_categories=CATEGORY_MAP_BG_TO_EN,diplomas=diplomas,
            results=None,city='',km=30,center=None,error=None,choices=[],code=404,message='This trail leads somewhere else. Return to the map.',csrf_token='')
        (target/('404.html' if name=='error.html' else 'index.html')).write_text(env.get_template(name).render(**context),encoding='utf-8')
    shutil.copytree(ROOT/'static',output/'static',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.DS_Store'))
    (output/'.nojekyll').touch()
    print(f'Built {len(data)} pins → {output}')
    return output

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'_site');p.add_argument('--source',type=Path,default=ROOT/'locations.json');a=p.parse_args();build(a.source,a.output)
