"""Board and two-player end-to-end checks. Run against a built, served site."""
import os,json,sys
from playwright.sync_api import sync_playwright
url=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8000'
with sync_playwright() as p:
    opts={'headless':True}
    if os.getenv('HTTPS_PROXY'):opts['proxy']={'server':os.environ['HTTPS_PROXY'],'bypass':'localhost,127.0.0.1'}
    browser=p.chromium.launch(**opts)
    ctx=browser.new_context(viewport={'width':1920,'height':1080},has_touch=True)
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url+'?mode=board');page.tap('#start-board')
    page.wait_for_function("document.body.classList.contains('ready')",timeout=180000)
    def py(code):
        page.evaluate('window.qaSuccess=false')
        page.evaluate('(code)=>python.PyRun_SimpleString(code)',code+'\nimport platform\nplatform.window.qaSuccess=True')
        page.wait_for_function('qaSuccess',timeout=20000);page.wait_for_timeout(100)
    def get(expression):
        py('import json,platform;platform.window.qaResult=json.dumps('+expression+')')
        return json.loads(page.evaluate('qaResult'))
    def tap(x,y):
        r=page.locator('#canvas').bounding_box()
        page.touchscreen.tap(r['x']+x/1280*r['width'],r['y']+y/720*r['height']);page.wait_for_timeout(200)
    tap(985,685)
    page.wait_for_function("document.body.classList.contains('playing')")
    assert page.locator('#aim-stick').is_hidden()
    assert get('game.web_firing')  # No second stick or attack button is required.
    for width,height in [(1920,1080),(3840,2160)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(200)
        panel=page.locator('#touch-controls').bounding_box()
        assert panel['x']>=0 and panel['x']+panel['width']<=width+1
        assert page.locator('#touch-controls [data-command=skill]').bounding_box()['height']>=58
    page.set_viewport_size({'width':1920,'height':1080});page.wait_for_timeout(200)
    page.tap('#board-pause');page.wait_for_timeout(200)
    assert get('game.paused');assert page.locator('#board-pause').is_visible()
    page.tap('#board-pause');page.wait_for_timeout(150);assert not get('game.paused')
    print('PASS: one-player board, auto attack, Full HD/4K sizing, reachable pause/resume.',flush=True)
    page.tap('#board-coop')
    page.select_option('#coop-hero-1','bugdan');page.select_option('#coop-hero-2','bugdan');page.tap('#coop-go')
    assert page.locator('#coop-error').is_visible()
    page.select_option('#coop-hero-2','glasses');page.tap('#coop-go')
    page.wait_for_function("document.body.classList.contains('coop-mode')")
    assert get('game.battle.coop')
    py("game.battle.next_wave=99999;game.battle.spawn_queue=0;game.battle.enemies=[];game.battle.spawn(kind='slime',pos=(640,260));game.battle.enemies[-1].update(hp=100000,maxhp=100000,stun=100)")
    initial=get('[list(game.battle.player_position(i)) for i in range(2)]')
    cdp=ctx.new_cdp_session(page)
    def point(selector,id,dx):
        r=page.locator(selector).bounding_box()
        return dict(x=r['x']+r['width']/2+dx,y=r['y']+r['height']/2,id=id)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[point('#p1-stick',11,35),point('#p2-stick',22,-35)]})
    page.wait_for_timeout(650)
    moved=get('[list(game.battle.player_position(i)) for i in range(2)]')
    assert moved[0][0]>initial[0][0]+10,(initial,moved)
    assert moved[1][0]<initial[1][0]-10,(initial,moved)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});page.wait_for_timeout(250)
    assert get('game.battle.moves')==[[0,0],[0,0]]
    page.tap('[data-command="p2:skill"]');page.wait_for_timeout(100)
    assert get("game.battle.skills['glasses']")>0
    assert get("game.battle.skills['bugdan']")==0
    page.tap('#coop-pause');page.wait_for_timeout(100);assert get('game.paused')
    stopped=get('[list(game.battle.player_position(i)) for i in range(2)]');page.wait_for_timeout(300)
    assert get('[list(game.battle.player_position(i)) for i in range(2)]')==stopped
    page.tap('#coop-pause');page.wait_for_timeout(100);assert not get('game.paused')
    assert 'Очкарик' in page.locator('#p2-status').inner_text()
    if os.getenv('BOARD_SCREENSHOT'):page.screenshot(path=os.environ['BOARD_SCREENSHOT'])
    for width,height in [(1920,1080),(3840,2160)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(200)
        panel=page.locator('#coop-controls').bounding_box()
        assert panel['x']>=0 and panel['x']+panel['width']<=width+1
        for selector in ['#p1-stick','#p2-stick','[data-command="p1:skill"]','[data-command="p2:skill"]']:
            assert page.locator(selector).is_visible()
    page.set_viewport_size({'width':1920,'height':1080});page.wait_for_timeout(150)
    original=get('game.profile.data')
    assert get('game.battle.tour')=='campaign'
    for stage in range(18):
        assert get('game.battle.tour_completed')==stage
        if stage==17:assert get("len([e for e in game.battle.enemies if e.get('boss_id')])")==2
        py('''b=game.battle
b.enemies=[];b.spawn_queue=0;b.last_mode_spawn=9999
if b.mode=='capture':
    for z in b.beacons:z.update(value=100.,owned=True)
elif b.mode=='escort':b.cart_progress=1.
elif b.mode=='heist':b.deposited=9;b.escape_timer=4.;b.players[1]['pos']=__import__('pygame').Vector2(1130,490)
elif b.mode=='survival':b.mode_time=90.
b.update_objective(.01)''')
        if stage<17:
            assert get('game.battle.intermission')
            tap(280,483)
            assert not get('game.battle.intermission')
    assert get('game.battle.won');assert get('game.battle.tour_bosses')==7
    assert get('game.profile.data')==original
    page.tap('#coop-change');page.select_option('#coop-tour','endless');page.tap('#coop-go')
    page.wait_for_timeout(200);assert get('game.battle.tour')=='endless'
    py("game.battle.tour_completed=17;game.battle.next_leg();game.battle.finish(True)")
    assert not get('game.battle.done');assert get('game.battle.tour_completed')==18
    tap(280,483);assert get('game.battle.map_key')=='park'
    py('game.battle.finish(True)');tap(640,664)
    assert get('game.battle.done');assert get('game.battle.won')
    print('PASS: 18-stage campaign through real upgrade taps, final double boss, unchanged solo save, endless selector / second lap / finish.',flush=True)
    page.tap('#coop-exit');page.wait_for_timeout(200)
    assert get('game.page')=='home';assert page.locator('#coop-controls').is_hidden()
    assert not errors,errors
    print('PASS: distinct heroes, two simultaneous sticks, independent skills, shared pause, player HUD, 4K layout, exit to solo.',flush=True)
    browser.close()
