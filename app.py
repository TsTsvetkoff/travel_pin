from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import requests
from math import radians, cos, sin, asin, sqrt
import os

app = Flask(__name__)

DB_NAME = 'locations.db'

CATEGORY_MAP_BG_TO_EN = {
    'Крепост': 'Fortress',
    'Пещера': 'Cave',
    'Парк / Забележителност': 'Park / Landmark',
    'Манастир': 'Monastery',
    'Връх': 'Peak',
    'Скално образувание': 'Rock Formation',
    'Музей': 'Museum',
    'Ждрело / Екопътека': 'Gorge / Eco Trail',
    'Остров': 'Island',
    'Езеро / Язовир': 'Lake / Reservoir',
    'Събитие': 'Event',
    'Зоопарк': 'Zoo',
    'Водопад': 'Waterfall',
    'АИР': 'AIR',
    'Гробница': 'Tomb',
    'Светилище': 'Sanctuary',
    'Кромлех': 'Cromlech',
    'Обсерватория / Планетариум': 'Observatory / Planetarium',
    'Хижа': 'Hut'
}

CATEGORIES = [
    'Fortress', 'Cave', 'Park / Landmark', 'Monastery', 'Peak', 'Rock Formation',
    'Museum', 'Gorge / Eco Trail', 'Island', 'Lake / Reservoir', 'Event', 'Zoo',
    'Waterfall', 'AIR', 'Tomb', 'Sanctuary', 'Cromlech', 'Observatory / Planetarium', 'Hut'
]

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_bg TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            category TEXT NOT NULL,
            sto_nto INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/', methods=['GET'])
def index():
    sto_nto = request.args.get('sto_nto')
    category = request.args.getlist('category')
    search = request.args.get('search', '').strip()
    # Remove SQL-side LIKE for search
    # Only filter by sto_nto and category in SQL
    query = "SELECT * FROM locations WHERE 1=1"
    params = []
    if sto_nto in ['yes', 'no']:
        query += " AND sto_nto=?"
        params.append(1 if sto_nto == 'yes' else 0)
    if category:
        query += " AND category IN ({})".format(','.join('?'*len(category)))
        params.extend(category)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(query, params)
    locations = c.fetchall()
    conn.close()
    # Python-side case-insensitive search for all scripts
    if search:
        locations = [loc for loc in locations if search.lower() in loc[1].lower()]
    # Category counters
    category_counts = {cat: 0 for cat in CATEGORIES}
    for loc in locations:
        if loc[4] in category_counts:
            category_counts[loc[4]] += 1
    # Sort categories: Peak first, then others
    sorted_categories = ['Peak'] + [cat for cat in CATEGORIES if cat != 'Peak']
    locations_js = [
        {
            'id': loc[0],
            'name_bg': loc[1],
            'latitude': loc[2],
            'longitude': loc[3],
            'category': loc[4],
            'sto_nto': loc[5]
        }
        for loc in locations
    ]
    return render_template(
        'index.html',
        locations=locations,
        locations_js=locations_js,
        categories=sorted_categories,
        category_counts=category_counts,
        selected_category=category,
        sto_nto=sto_nto
    )

@app.route('/add', methods=['GET', 'POST'])
def add_location():
    if request.method == 'POST':
        name_bg = request.form['name_bg']
        coordinates = request.form['coordinates']
        try:
            latitude_str, longitude_str = coordinates.split(',')
            latitude = float(latitude_str.strip())
            longitude = float(longitude_str.strip())
        except Exception:
            return "Invalid coordinates format. Use: latitude, longitude", 400
        category_bg = request.form['category_bg']
        sto_nto = 1 if request.form.get('sto_nto') == 'on' else 0
        category_en = CATEGORY_MAP_BG_TO_EN.get(category_bg, category_bg)
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''
            INSERT INTO locations (name_bg, latitude, longitude, category, sto_nto)
            VALUES (?, ?, ?, ?, ?)
        ''', (name_bg, latitude, longitude, category_en, sto_nto))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return render_template('add.html', bg_categories=list(CATEGORY_MAP_BG_TO_EN.keys()))

@app.route('/city_search', methods=['GET', 'POST'])
def city_search():
    results = []
    error = None
    city = ''
    km = ''
    if request.method == 'POST':
        city = request.form.get('city', '').strip()
        # Special handling for София - append '-град'
        if city.lower() == 'софия':
            city = 'София-град'
        # Prepend 'град ' for other cities if not already present
        elif not city.lower().startswith('град '):
            city = 'град ' + city
        km = request.form.get('km', '').strip()
        if not city or not km:
            error = 'Please provide both city and range.'
        else:
            try:
                km = float(km)
                # Geocode city using Nominatim
                resp = requests.get('https://nominatim.openstreetmap.org/search', params={
                    'q': city,
                    'format': 'json',
                    'limit': 1
                }, headers={'User-Agent': 'my_places_app'})
                data = resp.json()
                if not data:
                    error = f'City "{city}" not found.'
                else:
                    city_lat = float(data[0]['lat'])
                    city_lon = float(data[0]['lon'])
                    # Fetch all locations
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute('SELECT * FROM locations')
                    all_locations = c.fetchall()
                    conn.close()
                    # Haversine function
                    def haversine(lat1, lon1, lat2, lon2):
                        R = 6371  # Earth radius in km
                        dlat = radians(lat2 - lat1)
                        dlon = radians(lon2 - lon1)
                        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
                        c = 2 * asin(sqrt(a))
                        return R * c
                    # Filter locations within range
                    for loc in all_locations:
                        dist = haversine(city_lat, city_lon, loc[2], loc[3])
                        if dist <= km:
                            results.append((loc, round(dist, 2)))
            except Exception as e:
                error = f'Error: {e}'
    return render_template('city_search.html', results=results, error=error, city=city, km=km)

@app.route('/hall_of_fame')
def hall_of_fame():
    diplomas_dir = os.path.join(app.static_folder, 'diplomas')
    if not os.path.exists(diplomas_dir):
        diplomas = []
    else:
        diplomas = [f for f in os.listdir(diplomas_dir)
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]
        diplomas.sort()
    return render_template('hall_of_fame.html', diplomas=diplomas)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)