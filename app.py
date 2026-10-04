"""Local pin editor and public read views. Run: python app.py"""
import math
import os
import secrets
from pathlib import Path
from threading import Lock
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
import db
from places import CATEGORIES, CATEGORY_MAP_BG_TO_EN, find_city, nearby
ROOT = Path(__file__).resolve().parent
SAVE_LOCK = Lock()

def create_app(config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
        DATABASE=os.environ.get('DATABASE_PATH', str(ROOT/'locations.db')),
        LOCATIONS_JSON=str(ROOT/'locations.json'), AUTO_EXPORT=True,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', MAX_CONTENT_LENGTH=64*1024)
    if config: app.config.update(config)
    db.init_db(app.config['DATABASE'], app.config['LOCATIONS_JSON'])

    @app.context_processor
    def shared():
        session.setdefault('csrf_token', secrets.token_urlsafe(32))
        return dict(static_mode=False, csrf_token=session['csrf_token'],
                    nav=dict(index=url_for('index'), city=url_for('city_search'), add=url_for('add_location'), hall=url_for('hall_of_fame')),
                    asset_base=url_for('static', filename=''), categories=CATEGORIES)

    def locations(): return db.all_locations(app.config['DATABASE'])

    @app.get('/')
    def index():
        return render_template('index.html', page='index', locations=locations())

    @app.route('/city_search', methods=['GET','POST'])
    def city_search():
        data=request.form if request.method=='POST' else request.args
        city=data.get('city','').strip(); km=data.get('km','30'); results=None; center=None; error=None; choices=[]
        if city or request.method=='POST':
            try:
                radius=float(km)
                if not math.isfinite(radius) or not 1<=radius<=500: raise ValueError('Choose a radius from 1 to 500 km.')
                center,choices=find_city(city, data.get('city_id'))
                if not center:
                    if choices: raise ValueError('More than one place has this name. Choose a settlement below.')
                    raise ValueError('City not found. Try its Bulgarian or Latin name, or choose a suggestion.')
                results=nearby(locations(), center, radius)
            except ValueError as exc: error=str(exc)
        return render_template('city_search.html', page='city', locations=locations(), results=results,
            city=city, km=km, center=center, error=error, choices=choices)

    @app.route('/add', methods=['GET','POST'])
    def add_location():
        error=None
        if request.method=='POST':
            if not secrets.compare_digest(request.form.get('csrf_token',''), session.get('csrf_token','!')): abort(400, 'The form expired. Reload and try again.')
            try:
                name=request.form.get('name_bg','').strip()
                if not name or len(name)>200: raise ValueError('Enter a name between 1 and 200 characters.')
                try: lat,lon=map(float,request.form.get('coordinates','').split(','))
                except (ValueError,TypeError): raise ValueError('Use coordinates in this format: 43.41791, 24.61666.')
                if not all(map(math.isfinite,[lat,lon])) or not -90<=lat<=90 or not -180<=lon<=180: raise ValueError('Coordinates are outside the valid latitude / longitude range.')
                cat=CATEGORY_MAP_BG_TO_EN.get(request.form.get('category_bg'))
                if cat not in CATEGORIES: raise ValueError('Choose a valid category.')
            except ValueError as exc: error=str(exc)
            if not error:
                with SAVE_LOCK:
                    db.insert_location(name,lat,lon,cat,int(request.form.get('sto_nto')=='on'),app.config['DATABASE'])
                    try:
                        db.export_locations(app.config['DATABASE'],app.config['LOCATIONS_JSON'])
                        if app.config['AUTO_EXPORT']:
                            from publishing import refresh_and_publish
                            message=refresh_and_publish(app.config['LOCATIONS_JSON'])
                        else: message='Pin saved.'
                        flash(message,'success')
                    except Exception:
                        app.logger.exception('Pin saved but export/publish failed')
                        flash('Pin saved locally. Website sync failed; use “Retry website sync” on the Add page. Do not submit the pin again.','warning')
                return redirect(url_for('index'))
        return render_template('add.html',page='add',bg_categories=CATEGORY_MAP_BG_TO_EN,error=error), (400 if error else 200)

    @app.post('/sync')
    def sync():
        if not secrets.compare_digest(request.form.get('csrf_token',''),session.get('csrf_token','!')): abort(400)
        try:
            with SAVE_LOCK:
                db.export_locations(app.config['DATABASE'],app.config['LOCATIONS_JSON'])
                from publishing import refresh_and_publish
                flash(refresh_and_publish(app.config['LOCATIONS_JSON']),'success')
        except Exception:
            app.logger.exception('Website sync failed');flash('Sync failed. Your local pins are safe. Check Git access and the server log, then retry.','warning')
        return redirect(url_for('add_location'))

    @app.get('/hall_of_fame')
    def hall_of_fame():
        return render_template('hall_of_fame.html',page='hall',diplomas=diploma_files())

    @app.errorhandler(400)
    @app.errorhandler(404)
    def error_page(error):
        return render_template('error.html',page='',code=error.code,message=error.description),error.code
    return app

def diploma_files():
    titles={'10pp.png':'Ten mountain firsts','100Nto.png':'100 National Tourist Sites','5planini.png':'E4 · Five Mountains','kom_emine.png':'E3 · Kom–Emine','Rila_Rodopi.png':'E8 · Rila–Rhodope'}
    return [dict(file=p.name,title=titles.get(p.name,p.stem)) for p in sorted((ROOT/'static/diplomas').glob('*')) if p.suffix.lower() in {'.jpg','.jpeg','.png','.gif'}]

app=create_app()
if __name__=='__main__': app.run(host='127.0.0.1',port=int(os.environ.get('PORT','5000')),debug=False)
