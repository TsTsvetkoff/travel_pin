// Offline DOM tests. These do not start a browser or request external resources.
const {JSDOM}=require('jsdom');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve(__dirname,'..');const script=fs.readFileSync(path.join(root,'static/app.js'),'utf8');
const data=JSON.parse(fs.readFileSync(path.join(root,'locations.json'),'utf8'));
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function page(route){
 const file=path.join(root,'_site',route,'index.html');
 const dom=new JSDOM(fs.readFileSync(file,'utf8'),{runScripts:'outside-only',url:'https://example.invalid/my-repository/'+(route?route+'/':''),pretendToBeVisual:true});
 const w=dom.window;w.fetch=async url=>{const u=new URL(url,w.location);assert(u.pathname.startsWith('/my-repository/static/'),'Asset escaped repository subpath');return {ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,u.pathname.replace('/my-repository/','')),'utf8'))};};
 w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
 w.eval(script);await tick();return dom;
}
(async()=>{
 let dom=await page(''),w=dom.window,d=w.document;
 assert.equal(d.querySelectorAll('#trail-options input').length,3);
 assert.equal(d.querySelectorAll('#locations-list .place-card').length,30);
 d.querySelector('#load-more').click();assert.equal(d.querySelectorAll('#locations-list .place-card').length,60);
 d.querySelector('#category').value='Museum';d.querySelector('#category').dispatchEvent(new w.Event('change'));
 d.querySelector('#search').value='Плевен';d.querySelector('#search').dispatchEvent(new w.Event('input'));
 const filtered=data.filter(l=>l.category==='Museum'&&l.name_bg.toLowerCase().includes('плевен'));
 assert.equal(d.querySelectorAll('#locations-list .place-card').length,filtered.length);
 d.querySelector('#trails-only').checked=true;d.querySelector('#trails-only').dispatchEvent(new w.Event('change'));assert.equal(d.querySelector('#map-count').textContent,'Personal hikes');dom.window.close();
 dom=await page('city_search');w=dom.window;d=w.document;
 const form=d.querySelector('#city-form');assert.equal(form.querySelector('button').disabled,false);
 d.querySelector('#city').value='град Плевен';d.querySelector('#km').value='30';form.dispatchEvent(new w.Event('submit',{cancelable:true}));
 assert.equal(d.querySelectorAll('#nearby-results .place-card').length,15);
 assert(d.querySelector('#nearby-title').textContent.includes('Pleven'));assert(d.querySelectorAll('#nearby-results .badge').length>0);
 const labels=[...d.querySelectorAll('#nearby-results h3')].map(x=>x.textContent);assert(labels.every(x=>x.trim()));
 assert(labels.some(x=>x.includes('Панорама')));assert.equal(d.querySelector('#city-error').hidden,true);
 d.querySelector('#city').value='unknown-city';d.querySelector('#city-id').value='';form.dispatchEvent(new w.Event('submit',{cancelable:true}));assert.equal(d.querySelector('#city-error').hidden,false);assert.equal(d.querySelector('#nearby-section').hidden,true);dom.window.close();
 dom=await page('hall_of_fame');d=dom.window.document;assert.equal(d.querySelectorAll('.diploma').length,5);d.querySelector('.diploma').click();assert(d.querySelector('dialog').hasAttribute('open'));d.querySelector('#close-dialog').click();assert(!d.querySelector('dialog').hasAttribute('open'));dom.window.close();
 dom=await page('add');d=dom.window.document;assert.equal(d.querySelectorAll('form[method=post]').length,0);assert.equal(d.querySelector('.form-panel .button').href,'http://127.0.0.1:5000/add');dom.window.close();
 console.log('Offline frontend checks passed: three routes, pagination, combined filters, repository-relative assets, Pleven search (15 named results), error state, diploma dialog, static editor handoff.');
})().catch(e=>{console.error(e);process.exit(1)});
