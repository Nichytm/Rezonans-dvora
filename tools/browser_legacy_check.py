"""Check the Canvas edition with old-browser APIs removed and external traffic blocked."""
import os,sys,json
from playwright.sync_api import sync_playwright
root=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8000'
OLD_UA='Mozilla/5.0 (Linux; Android 6.0; Promethean) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.105 Safari/537.36'
with sync_playwright() as p:
    opts={'headless':True}
    if os.getenv('HTTPS_PROXY'):opts['proxy']={'server':os.environ['HTTPS_PROXY'],'bypass':'localhost,127.0.0.1'}
    b=p.chromium.launch(**opts)
    ctx=b.new_context(viewport={'width':1920,'height':1080},has_touch=True,user_agent=OLD_UA)
    ctx.add_init_script('window.WebAssembly=undefined;window.fetch=undefined;window.PointerEvent=undefined;window.URLSearchParams=undefined;')
    page=ctx.new_page();errors=[];requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url))
    def route(request):
        if request.request.url.startswith(root):request.continue_()
        else:request.abort()
    page.route('**/*',route)
    page.goto(root+'/?mode=board&compat-test=1')
    page.wait_for_url('**/legacy/index.html?board=1',timeout=10000)
    page.wait_for_function('!!window.RDLegacy')
    assert page.locator('#startup').is_hidden()
    assert page.locator('#hero1 option').count()==11
    assert page.locator('#map option').count()==6
    assert not any('.wasm' in u or 'main.data' in u or 'game.tar.gz' in u for u in requests),requests
    print('PASS: Android 6 / Chrome 49 user agent redirects to Canvas; no Python/WASM bundle requested.',flush=True)
    page.select_option('#count','2');page.select_option('#hero2','bugdan');page.tap('#play')
    assert 'разных' in page.locator('#menu-error').inner_text()
    page.select_option('#hero2','glasses');page.tap('#play')
    page.wait_for_function('RDLegacy.state() && RDLegacy.state().count===2')
    def ev(code):return page.evaluate(code)
    # Keep the first wave from interrupting the input check with its upgrade menu.
    ev('RDLegacy.state().spawnLeft=999;RDLegacy.state().spawnCD=999;')
    before=ev('RDLegacy.state().players.map(function(p){return p.x;})')
    cdp=ctx.new_cdp_session(page)
    def touch(selector,id,dx):
        r=page.locator(selector).bounding_box();return dict(x=r['x']+r['width']/2+dx,y=r['y']+r['height']/2,id=id)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[touch('#stick1',1,32),touch('#stick2',2,-32)]})
    page.wait_for_timeout(500)
    after=ev('RDLegacy.state().players.map(function(p){return p.x;})')
    assert after[0]>before[0]+15 and after[1]<before[1]-15,(before,after)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});page.wait_for_timeout(100)
    assert ev('RDLegacy.inputs.map(function(v){return [v.x,v.y];})')==[[0,0],[0,0]]
    page.tap('#skill2');assert ev('RDLegacy.state().players[1].skill')>0
    assert ev('RDLegacy.state().players[0].skill')==0
    page.tap('#pause');assert ev('RDLegacy.state().paused')
    page.get_by_role('button',name='Продолжить',exact=True).click();assert not ev('RDLegacy.state().paused')
    print('PASS: two TouchEvent sticks, release, separate abilities, pause/resume.',flush=True)
    if os.getenv('LEGACY_SCREENSHOT'):page.screenshot(path=os.environ['LEGACY_SCREENSHOT'])
    # Exercise every map/mode combination using the actual engine, including boss hazards.
    ev('RDLegacy.menu()')
    result=ev('''function(){var mode=document.getElementById('mode'),map=document.getElementById('map'),count=0;
      for(var m=0;m<mode.options.length;m++)for(var k=0;k<map.options.length;k++){
       mode.selectedIndex=m;map.selectedIndex=k;RDLegacy.start();
       for(var i=0;i<200;i++)RDLegacy.step(.05);
       if(!RDLegacy.state())throw new Error('No state');count++;
      }RDLegacy.menu();return count;}''')
    assert result==42,result
    # All combat styles can use both abilities; energy and player identity stay separate.
    result=ev('''function(){var h=document.getElementById('hero1'),mode=document.getElementById('mode');mode.value='duel';var count=0;
      for(var i=0;i<h.options.length;i++){h.selectedIndex=i;document.getElementById('count').value='1';RDLegacy.start();
       var g=RDLegacy.state();g.players[0].energy=100;RDLegacy.command(0,'skill');RDLegacy.command(0,'ult');
       for(var t=0;t<120;t++)RDLegacy.step(.05);count++;
      }RDLegacy.menu();return count;}''')
    assert result==11
    # The objective rules must lead to victory rather than an endless arena.
    ev('''function(){var mode=document.getElementById('mode');mode.value='capture';RDLegacy.start();var g=RDLegacy.state();
      g.beacons.forEach(function(v){v.v=100;});RDLegacy.step(.01);if(!g.won)throw new Error('capture');
      mode.value='escort';RDLegacy.start();g=RDLegacy.state();g.cart.progress=1;RDLegacy.step(.01);if(!g.won)throw new Error('escort');
      mode.value='survival';RDLegacy.start();g=RDLegacy.state();g.time=90;RDLegacy.step(.01);if(!g.won)throw new Error('survival');
      mode.value='heist';RDLegacy.start();g=RDLegacy.state();g.deposited=9;g.escapeTime=4;g.players[0].x=1130;g.players[0].y=520;RDLegacy.step(.01);if(!g.won)throw new Error('heist');
      mode.value='duel';RDLegacy.start();g=RDLegacy.state();g.enemies=[];RDLegacy.step(.01);if(!g.won)throw new Error('duel');
      mode.value='arena';RDLegacy.start();g=RDLegacy.state();g.wave=3;g.enemies=[];g.spawnLeft=0;RDLegacy.step(.01);if(!g.won)throw new Error('arena');
      mode.value='expedition';RDLegacy.start();g=RDLegacy.state();g.room=5;g.enemies=[];g.spawnLeft=0;RDLegacy.step(.01);if(!g.won)throw new Error('expedition');
      RDLegacy.menu();}''')
    assert not errors,errors
    print('PASS: 42 map/mode combinations, all 11 hero styles, seven victory conditions.',flush=True)
    assert ev("JSON.parse(localStorage.getItem('rezonans-legacy-record')).wins")>=7
    page.reload();page.wait_for_function('!!window.RDLegacy');assert 'Побед в этой версии' in page.locator('#record').inner_text()
    page.select_option('#count','2');page.select_option('#hero2','glasses');page.tap('#play')
    for width,height in [(1280,720),(3840,2160),(430,932)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(150)
        r=page.locator('#game').bounding_box();assert r['x']>=-1 and r['x']+r['width']<=width+1
        for selector in ['#stick1','#stick2','#skill1','#skill2']:
            r=page.locator(selector).bounding_box();assert r['y']>=0 and r['y']+r['height']<=height+1,(selector,r)
    print('PASS: record persistence, 720p / 4K / portrait controls stay inside viewport.',flush=True)
    b.close()
