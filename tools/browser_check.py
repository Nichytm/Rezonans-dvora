"""Optional end-to-end check: pip install playwright; playwright install chromium.
Run a static server, then python tools/browser_check.py http://localhost:8000.
"""
import json,os,sys
from playwright.sync_api import sync_playwright
url=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8000'
with sync_playwright() as p:
    options={'headless':True}
    if os.getenv('HTTPS_PROXY'):options['proxy']={'server':os.environ['HTTPS_PROXY'],'bypass':'localhost,127.0.0.1'}
    browser=p.chromium.launch(**options)
    ctx=browser.new_context(viewport={'width':932,'height':430},is_mobile=True,has_touch=True)
    page=ctx.new_page();errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url);page.tap('#start')
    page.wait_for_function("document.body.classList.contains('ready')",timeout=180000)
    def py(code):
        page.evaluate('window.qaSuccess=false')
        page.evaluate('(code)=>python.PyRun_SimpleString(code)',code+'\nimport platform\nplatform.window.qaSuccess=True')
        page.wait_for_function('qaSuccess',timeout=20000)
        page.wait_for_timeout(120)
    def get(expression):
        py('import json,platform;platform.window.qaResult=json.dumps('+expression+')')
        return json.loads(page.evaluate('qaResult'))
    def tap(x,y):
        r=page.locator('#canvas').bounding_box()
        page.touchscreen.tap(r['x']+x/1280*r['width'],r['y']+y/720*r['height'])
        page.wait_for_timeout(250)
    assert get('game.sound.ready')
    assert json.loads(page.evaluate('rdLoad()'))['gold']==1600
    tap(985,685)  # Touch the original training button.
    assert get('game.battle.training')
    page.wait_for_function("document.body.classList.contains('playing')")
    initial=get('game.battle.pos.x')
    cdp=ctx.new_cdp_session(page)
    def point(selector,id,offset):
        r=page.locator(selector).bounding_box()
        return dict(x=r['x']+r['width']/2+offset,y=r['y']+r['height']/2,id=id)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[point('#move-stick',1,24),point('#aim-stick',2,20)]})
    page.wait_for_timeout(600)
    assert get('game.web_firing')
    assert get('game.battle.pos.x')>initial+20
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    page.wait_for_timeout(200)
    assert not get('game.web_firing')
    page.tap('[data-command=skill]');page.wait_for_timeout(100)
    assert get('game.battle.skill_count')>0
    page.tap('#training-next');page.wait_for_timeout(150)
    assert get('game.battle.hero')!='bugdan'
    py("game.start_activity('duel')")
    page.tap('[data-command="2"]');page.wait_for_timeout(150)
    assert get('game.battle.hero')=='glasses'
    page.tap('#pause');page.wait_for_timeout(100);assert get('game.paused')
    page.tap('#pause');page.wait_for_timeout(100);assert not get('game.paused')
    py("from worlds import MODES,MAPS\nfor mode in MODES:\n for map_key in MAPS:\n  game.start_activity(mode,map_key=map_key);game.step(.016);game.draw()")
    py("game.profile.data['gold']=2345;game.profile.save()")
    page.reload();page.tap('#start')
    page.wait_for_function("document.body.classList.contains('ready')",timeout=180000)
    assert get("game.profile.data['gold']")==2345
    py('game.cinema.open()')
    page.wait_for_function('rdVideoActive && document.getElementById("video").readyState>=2',timeout=10000)
    page.tap('#video-close');assert not page.evaluate('rdVideoActive')
    page.set_viewport_size({'width':430,'height':932});page.wait_for_timeout(200)
    r=page.locator('#canvas').bounding_box();assert 0<=r['x'] and r['x']+r['width']<=431
    assert not errors,errors
    print('PASS: touch menus, multitouch movement/fire/release, skill, training cycle, hero switch, pause, 36 mode/map combinations, persistent save, HTML5 video, portrait layout.')
    browser.close()
