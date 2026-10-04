import html,json,os,re,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import db,places,publishing
from app import create_app
from build_static import build
ROOT=Path(__file__).resolve().parents[1]

class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=self.root/'locations.json';self.source.write_text((ROOT/'locations.json').read_text(),encoding='utf-8')
        self.database=str(self.root/'locations.db')
        self.app=create_app(dict(TESTING=True,SECRET_KEY='tests',DATABASE=self.database,LOCATIONS_JSON=str(self.source),AUTO_EXPORT=False))
        self.client=self.app.test_client()
    def tearDown(self):self.tmp.cleanup()
    def token(self):
        self.client.get('/add')
        with self.client.session_transaction() as s:return s['csrf_token']
    def test_all_pages(self):
        for path in ['/','/city_search','/add','/hall_of_fame']:
            r=self.client.get(path);self.assertEqual(r.status_code,200,path);self.assertIn(b'TRAIL ATLAS',r.data)
        self.assertEqual(self.client.get('/missing').status_code,404)
    def test_city_regression_real_pins(self):
        center,_=places.find_city('град Плевен');self.assertIsNotNone(center)
        expected=places.nearby(db.all_locations(self.database),center,30)
        self.assertGreater(len(expected),0)
        response=self.client.post('/city_search',data={'city':'град Плевен','km':'30'})
        text=html.unescape(response.get_data(as_text=True))
        for item in expected:self.assertIn(item['name_bg'],text);self.assertIn(item['category'],text)
        self.assertNotIn('Regular',text)
        if any(i['sto_nto'] for i in expected):self.assertIn('100 НТО',text)
        self.assertEqual([x['distance_km'] for x in expected],sorted(x['distance_km'] for x in expected))
    def test_city_aliases_and_initial_state(self):
        a,_=places.find_city('гр. Плевен');b,_=places.find_city('Pleven');self.assertEqual(a['id'],b['id'])
        self.assertNotIn('No saved places within this radius.',self.client.get('/city_search').get_data(as_text=True))
    def test_city_validation(self):
        for km in ['-1','0','501','nan','inf','nope']:
            r=self.client.post('/city_search',data={'city':'Плевен','km':km})
            self.assertIn('city-error',r.get_data(as_text=True));self.assertNotIn('places near Pleven',r.get_data(as_text=True))
        self.assertIn('City not found',self.client.post('/city_search',data={'city':'not-a-real-city','km':'30'}).get_data(as_text=True))
    def test_duplicates_require_choice(self):
        sample=[dict(id=1,name='Same',keys=['same']),dict(id=2,name='Same',keys=['same'])]
        with patch('places.cities',return_value=sample):
            center,choices=places.find_city('Same');self.assertIsNone(center);self.assertEqual(len(choices),2)
            center,_=places.find_city('Same','2');self.assertEqual(center['id'],2)
    def test_empty_and_radius_boundary(self):
        self.assertEqual(places.nearby([],{'lat':0,'lon':0},30),[])
        item=dict(id=1,name_bg='At centre',latitude=43,longitude=24,category='Museum',sto_nto=1)
        self.assertEqual(places.nearby([item],{'lat':43,'lon':24},1)[0]['distance_km'],0)
    def test_add_and_json_persist(self):
        initial=len(db.all_locations(self.database));token=self.token()
        r=self.client.post('/add',data={'csrf_token':token,'name_bg':'Тестов връх','coordinates':'42.1, 24.2','category_bg':'Връх','sto_nto':'on'})
        self.assertEqual(r.status_code,302)
        rows=json.loads(self.source.read_text());self.assertEqual(len(rows),initial+1);self.assertEqual(rows[-1]['category'],'Peak');self.assertEqual(rows[-1]['sto_nto'],1)
    def test_add_validation_and_csrf(self):
        initial=len(db.all_locations(self.database));token=self.token()
        for coord in ['nan,0','91,0','0,181','wrong']:
            r=self.client.post('/add',data={'csrf_token':token,'name_bg':'Test','coordinates':coord,'category_bg':'Връх'});self.assertEqual(r.status_code,400)
        self.assertEqual(self.client.post('/add',data={'name_bg':'Test'}).status_code,400)
        self.assertEqual(len(db.all_locations(self.database)),initial)
    def test_failed_sync_does_not_lose_pin(self):
        self.app.config['AUTO_EXPORT']=True;initial=len(db.all_locations(self.database))
        with patch('publishing.refresh_and_publish',side_effect=RuntimeError('test')), self.assertLogs(self.app.logger, level='ERROR'):
            r=self.client.post('/add',data={'csrf_token':self.token(),'name_bg':'Retained','coordinates':'42,24','category_bg':'Връх'},follow_redirects=True)
        self.assertEqual(len(db.all_locations(self.database)),initial+1);self.assertIn(b'Pin saved locally',r.data)
    def test_static_build_paths_data_and_forms(self):
        output=build(self.source,self.root/'site')
        for page in ['index.html','city_search/index.html','add/index.html','hall_of_fame/index.html','404.html']:
            text=(output/page).read_text();self.assertNotIn('{{',text);self.assertNotIn('href="/static/',text)
        self.assertIn('../static/app.js',(output/'city_search/index.html').read_text())
        self.assertNotIn('method="post"',(output/'add/index.html').read_text())
        self.assertTrue((output/'static/data/hikes.geojson').exists())
    def test_personal_routes_only(self):
        features=json.loads((ROOT/'static/data/hikes.geojson').read_text())['features']
        self.assertEqual([f['properties']['source_points'] for f in features],[168891,83360,84597])
        self.assertEqual([f['properties']['code'] for f in features],['E3','E4','E8'])
        self.assertTrue(all(f['geometry']['type']=='MultiLineString' for f in features))

class PublishingTests(unittest.TestCase):
    def test_only_data_commit_and_retry_push(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo';root.mkdir();remote=Path(tmp)/'remote.git'
            def git(*args):return subprocess.run(['git',*args],cwd=root,check=True,capture_output=True,text=True).stdout
            subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True)
            git('init','-b','main');git('config','user.email','test@example.invalid');git('config','user.name','Test')
            (root/'locations.json').write_text('[]');(root/'unrelated.txt').write_text('original')
            git('add','.');git('commit','-m','Initial');git('remote','add','origin',str(remote));git('push','-u','origin','main')
            (root/'unrelated.txt').write_text('unrelated staged change');git('add','unrelated.txt');(root/'locations.json').write_text('[1]')
            with patch.object(publishing,'ROOT',root),patch('build_static.build'),patch.dict(os.environ,{'PAGES_AUTO_PUSH':'1','PAGES_BRANCH':'main','PAGES_REMOTE':'origin'}):
                message=publishing.refresh_and_publish(root/'locations.json');self.assertIn('queued',message)
                self.assertEqual(git('show','--format=','--name-only','HEAD').strip(),'locations.json')
                self.assertIn('unrelated.txt',git('diff','--cached','--name-only'))
                self.assertEqual(git('rev-parse','HEAD').strip(),git('rev-parse','origin/main').strip())
                publishing.refresh_and_publish(root/'locations.json')
    def test_auto_push_off_builds_without_git(self):
        with patch('build_static.build') as b,patch.object(publishing,'git') as g,patch.dict(os.environ,{'PAGES_AUTO_PUSH':'0'}):
            self.assertIn('off',publishing.refresh_and_publish(ROOT/'locations.json'));b.assert_called_once();g.assert_not_called()
if __name__=='__main__':unittest.main()
