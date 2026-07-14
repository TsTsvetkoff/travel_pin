from flask import Flask, render_template, request, redirect, url_for
import requests
from math import radians, cos, sin, asin, sqrt
import os

import db

app = Flask(__name__)

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


@app.route('/', methods=['GET'])
def index():
    sto_nto = request.args.get('sto_nto')
    category = request.args.getlist('category')
    search = request.args.get('search', '').strip()

    locations = db.all_locations()

    # Apply filters in Python — keeps the SQL trivial and the search case-insensitive
    # across all scripts.
    if sto_nto in ('yes', 'no'):
        wanted = 1 if sto_nto == 'yes' else 0
        locations = [loc for loc in locations if loc['sto_nto'] == wanted]
    if category:
        locations = [loc for loc in locations if loc['category'] in category]
    if search:
        locations = [loc for loc in locations if search.lower() in loc['name_bg'].lower()]

    # Category counters (only the categories represented in the current filter).
    category_counts = {cat: 0 for cat in CATEGORIES}
    for loc in locations:
        if loc['category'] in category_counts:
            category_counts[loc['category']] += 1

    # Sort categories: Peak first, then the rest in their canonical order.
    sorted_categories = ['Peak'] + [cat for cat in CATEGORIES if cat != 'Peak']

    # The template still indexes locations by numeric position, so ship it as a
    # list of tuples to keep template changes minimal.
    locations_as_tuples = [
        (loc['id'], loc['name_bg'], loc['latitude'], loc['longitude'],
         loc['category'], loc['sto_nto'])
        for loc in locations
    ]
    locations_js = [
        {
            'id': loc['id'],
            'name_bg': loc['name_bg'],
            'latitude': loc['latitude'],
            'longitude': loc['longitude'],
            'category': loc['category'],
            'sto_nto': loc['sto_nto'],
        }
        for loc in locations
    ]

    return render_template(
        'index.html',
        locations=locations_as_tuples,
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

        db.insert_location(name_bg, latitude, longitude, category_en, sto_nto)
        # Keep locations.json in sync so a subsequent `git add locations.json`
        # followed by `git push` ships the new pin to the GitHub Pages site
        # without any extra steps.
        db.export_locations()
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
                # Geocode city using Nominatim. countrycodes=bg keeps the match
                # inside Bulgaria — without it, "Варна" matches a town in
                # Chelyabinsk Oblast, Russia, and similar collisions happen
                # for other Bulgarian city names.
                resp = requests.get('https://nominatim.openstreetmap.org/search', params={
                    'q': city,
                    'format': 'json',
                    'limit': 1,
                    'countrycodes': 'bg',
                }, headers={'User-Agent': 'my_places_app'})
                data = resp.json()
                if not data:
                    error = f'City "{city}" not found.'
                else:
                    city_lat = float(data[0]['lat'])
                    city_lon = float(data[0]['lon'])
                    all_locations = db.all_locations()
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
                        dist = haversine(city_lat, city_lon, loc['latitude'], loc['longitude'])
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
    db.init_db()
    app.run(debug=True)
