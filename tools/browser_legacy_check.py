"""Original-menu / progression regression with Android 6 API restrictions."""
import os,sys,json
from playwright.sync_api import sync_playwright
root=(sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8000').rstrip('/')
OLD_UA='Mozilla/5.0 (Linux; Android 6.0; Promethean) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.105 Safari/537.36'
with sync_playwright() as p:
    opts={'headless':True}
    if os.getenv('HTTPS_PROXY'):opts['proxy']={'server':os.environ['HTTPS_PROXY'],'bypass':'localhost,127.0.0.1'}
    b=p.chromium.launch(**opts)
    ctx=b.new_context(viewport={'width':1920,'height':1080},has_touch=True,user_agent=OLD_UA,accept_downloads=True)
    ctx.add_init_script('window.WebAssembly=undefined;window.fetch=undefined;window.PointerEvent=undefined;window.URLSearchParams=undefined;')
    page=ctx.new_page();errors=[];requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url))
    def route(request):
        if request.request.url.startswith(root):request.continue_()
        else:request.abort()
    page.route('**/*',route)
    page.goto(root+'/?mode=board&compat-test=2')
    page.wait_for_url('**/legacy/index.html?board=1&v=coop-tour',timeout=15000)
    page.wait_for_function('!!window.RDUI')
    assert page.locator('#startup').is_hidden()
    assert not any('.wasm' in u or 'main.data' in u or 'game.tar.gz' in u for u in requests),requests
    ev=page.evaluate
    def tap(label):
        item=ev('''function(label){RDUI.render();return RDUI.buttons.filter(function(v){return v.label===label;})[0];}''',label)
        assert item,(label,ev('RDUI.buttons.map(function(v){return v.label;})'))
        r=page.locator('#interface').bounding_box()
        page.touchscreen.tap(r['x']+(item['x']+item['w']/2)/1280*r['width'],r['y']+(item['y']+item['h']/2)/720*r['height'])
        page.wait_for_timeout(80)
    def show(name):ev('(name)=>{RDUI.show(name);RDUI.render();}',name)
    def opening(name):ev('(name)=>{RDUI.open(name);RDUI.render();}',name)
    def launch(opts):ev('(o)=>RDUI.launch(o)',opts)
    def close_movie():
        if page.locator('#cinema').is_visible():page.click('#video-close')
    print('PASS: Android 6 redirects to restored Canvas menus; no Python/WASM or CDN.',flush=True)
    # Original collection, upgrades, team, gacha guarantees and shop via real touches.
    tap('ГЕРОИ');tap('Бугданчик')
    before=ev('RDSave.data.gold')
    tap('УРОВЕНЬ +1 / 90 МОНЕТ + 3 ЭССЕНЦИИ')
    assert ev('RDSave.data.heroes.bugdan.level')==2
    assert ev('RDSave.data.gold')==before-90
    tap('СЛОТ 2');assert ev('RDSave.data.team')==['glasses','bugdan','white']
    tap('ПРИЗЫВ');tap('ПРИЗВАТЬ ×10 / 1 600');tap('ПРОПУСТИТЬ');tap('ЗАБРАТЬ И ПРОДОЛЖИТЬ')
    assert ev('RDSave.data.total_pulls')==10 and ev('RDSave.data.crystals')==3200
    assert ev('RDSave.data.history.some(function(h){return RD_DATA.heroes[h].rarity!=="R";})')
    tap('ШТАБ');tap('ЛАВКА У ПОДЪЕЗДА');tap('КУПИТЬ · 300')
    assert ev('RDSave.data.equipped_relic')=='brick'
    tap('ВЕРНУТЬСЯ В ШТАБ');tap('НАСТРОЙКИ');tap('ПРОСЛУШАТЬ И НАЗНАЧИТЬ РЕПЛИКИ')
    old=ev('JSON.stringify(RDSave.data.voice_bindings)')
    label=ev('RDUI.buttons.filter(function(v){return / →$/.test(v.label)&&v.y>330;})[0].label')
    tap(label);assert ev('JSON.stringify(RDSave.data.voice_bindings)')!=old
    tap('ГОТОВО')
    with page.expect_download() as info:tap('СКАЧАТЬ СОХРАНЕНИЕ')
    saved=json.loads(open(info.value.path()).read());assert saved==ev('RDSave.data')
    # Import through actual FileReader, preserving original v4 data schema.
    saved['gold']=6789
    page.locator('#import-save').set_input_files({'name':'save.json','mimeType':'application/json','buffer':json.dumps(saved).encode()})
    page.wait_for_function('RDSave.data.gold===6789')
    tap('КИНОЗАЛ: ЕДИТ3000');assert page.locator('#cinema').is_visible();close_movie();tap('ГОТОВО')
    opening('contracts');assert len(ev('RDUI.buttons'))>=1;tap('ГОТОВО')
    print('PASS: original collection, upgrades, team slots, x10 summon, relics, voice editor, JSON export/import and cinema.',flush=True)
    # Poligon supports every hero without changing the player's profile.
    original=ev('JSON.stringify(RDSave.data)')
    ev('RDUI.training()');assert ev('RDLegacy.state().training')
    for i in range(11):
        ev('RDLegacy.command(0,"skill");RDLegacy.command(0,"ult");for(var i=0;i<40;i++)RDLegacy.step(.05);')
        assert not ev('RDLegacy.state().done')
        page.tap('#training-next')
    assert ev('JSON.stringify(RDSave.data)')==original
    ev('RDLegacy.menu()');show('home');tap('ВДВОЁМ');tap('НАЧАТЬ СОВМЕСТНЫЙ БОЙ')
    assert ev('RDLegacy.state().count')==2
    assert ev('RDLegacy.state().coopTour.kind')=='campaign'
    ev('RDLegacy.state().spawnLeft=999;RDLegacy.state().spawnCD=999;')
    before=ev('RDLegacy.state().players.map(function(p){return p.x;})')
    cdp=ctx.new_cdp_session(page)
    def point(selector,id,dx):
        r=page.locator(selector).bounding_box();return dict(x=r['x']+r['width']/2+dx,y=r['y']+r['height']/2,id=id)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[point('#stick1',1,32),point('#stick2',2,-32)]})
    page.wait_for_timeout(500)
    after=ev('RDLegacy.state().players.map(function(p){return p.x;})')
    assert after[0]>before[0]+15 and after[1]<before[1]-15,(before,after)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});page.wait_for_timeout(60)
    assert ev('RDLegacy.inputs.map(function(v){return [v.x,v.y];})')==[[0,0],[0,0]]
    page.tap('#skill2');assert ev('RDLegacy.state().players[1].skill')>0
    assert ev('RDLegacy.state().players[0].skill')==0
    page.tap('#pause');assert ev('RDLegacy.state().paused');tap('Продолжить');assert not ev('RDLegacy.state().paused')
    ev('RDLegacy.finish(true)');assert ev('JSON.stringify(RDSave.data)')==original
    print('PASS: all 11 training styles, two simultaneous TouchEvent sticks, separate skills, pause, no co-op/training progression changes.',flush=True)
    # Original solo party and characteristic abilities / boss hazards / endless routes.
    launch(dict(mode='arena',stage=2,team=['glasses','bugdan','white'],reward='story'))
    assert ev('RDLegacy.state().roster.length')==3
    assert ev('RDLegacy.state().cart.hp')==820
    page.tap('#team1');assert ev('RDLegacy.state().players[0].id')=='bugdan'
    launch(dict(mode='arena',stage=3,team=['bugdan','glasses','white'],reward='story'))
    assert ev('RDLegacy.state().enemies.some(function(e){return e.type==="anchor";})')
    for boss in ['bugdan','ilya','smiler','egor','igor']:
        launch(dict(mode='duel',boss=boss,difficulty=3,team=['bugdan','glasses','white'],reward='activity'))
        ev('var g=RDLegacy.state(),e=g.enemies[0];e.hp=e.maxhp*.49;e.cd=0;g.players[0].inv=100;for(var i=0;i<200;i++)RDLegacy.step(.05);')
        assert ev('RDLegacy.state().enemies[0].enraged')
    launch(dict(mode='expedition',team=['bugdan','glasses','white'],reward='activity'))
    ev('var g=RDLegacy.state();g.enemies=[];g.spawnLeft=0;RDLegacy.step(.01);RDUI.render();')
    assert len(ev('RDLegacy.state().routes'))==2
    # Choose risky path through touch, ensuring map/perk/bounty survive room changes.
    item=ev('RDUI.buttons.filter(function(v){return v.label==="ВЫБРАТЬ МАРШРУТ";})[1]')
    r=page.locator('#interface').bounding_box();page.touchscreen.tap(r['x']+(item['x']+item['w']/2)/1280*r['width'],r['y']+(item['y']+item['h']/2)/720*r['height'])
    assert ev('RDLegacy.state().room')==2 and ev('RDLegacy.state().bonus')==.35
    launch(dict(mode='arena',endless=True,stage=1,team=['bugdan','glasses','white'],reward='story'))
    ev('var g=RDLegacy.state();g.wave=4;g.enemies=[];g.spawnLeft=0;RDLegacy.step(.01);RDUI.render();')
    tap('ЗАВЕРШИТЬ ЗАБЕГ С НАГРАДАМИ')
    assert ev('RDSave.data.best_endless')==4
    assert ev('RDLegacy.state().done')
    print('PASS: party switching, resonator defense, anchors, five enraged bosses, expedition routes, endless cash-out.',flush=True)
    # All 42 map / mode pairs update and all seven objective rules can complete.
    total=ev('''function(){var modes=['arena'].concat(Object.keys(RD_DATA.modes)),maps=Object.keys(RD_DATA.maps),count=0;
      for(var m=0;m<modes.length;m++)for(var k=0;k<maps.length;k++){
       RDUI.launch({mode:modes[m],map:maps[k],team:['bugdan','glasses','white'],reward:'none'});
       var g=RDLegacy.state();g.players[0].inv=100;for(var i=0;i<200;i++)RDLegacy.step(.05);count++;
      }RDLegacy.menu();return count;}''')
    assert total==42
    for mode in ['capture','escort','survival','heist','duel','arena','expedition']:
        launch(dict(mode=mode,team=['bugdan','glasses','white'],reward='activity' if mode!='arena' else 'story'))
        crystals=ev('RDSave.data.crystals')
        ev('''function(mode){var g=RDLegacy.state();g.players[0].inv=100;
          if(mode==='capture')g.beacons.forEach(function(v){v.v=100;});
          if(mode==='escort')g.cart.progress=1;
          if(mode==='survival')g.time=90;
          if(mode==='heist'){g.deposited=9;g.escapeTime=4;g.players[0].x=1130;g.players[0].y=520;}
          if(mode==='duel')g.enemies=[];
          if(mode==='arena'){g.wave=3;g.enemies=[];g.spawnLeft=0;}
          if(mode==='expedition'){g.room=5;g.enemies=[];g.spawnLeft=0;}
          RDLegacy.step(.01);if(!g.won)throw new Error('Objective '+mode);
          RDLegacy.finish(true); // Finish must be idempotent.
        }''',mode)
        assert ev('RDSave.data.crystals')-crystals==(900 if mode=='arena' else 600),(mode,crystals,ev('RDSave.data.crystals'))
        close_movie()
    assert ev('RDSave.data.edit_seen')>=1
    # A complete cooperative itinerary must survive all objective transitions.
    before_tour=ev('JSON.stringify(RDSave.data)')
    launch(dict(mode='arena',team=['bugdan','glasses'],coop=True,coopTour='campaign',reward='none'))
    maps=set();modes=set()
    def finish_leg():
        ev('''function(){var g=RDLegacy.state();g.enemies=[];g.spawnLeft=0;g.modeSpawn=999;g.time=1000;
          g.players.forEach(function(p){p.inv=100;});
          if(g.mode==='capture')g.beacons.forEach(function(z){z.v=100;});
          if(g.mode==='escort')g.cart.progress=1;
          if(g.mode==='heist'){g.deposited=9;g.escapeTime=4;g.players[1].x=1130;g.players[1].y=520;}
          if(g.mode==='survival')g.modeTime=90;
          RDLegacy.step(.01);RDUI.render();}''')
    for index in range(18):
        state=ev('({n:RDLegacy.state().coopTour.completed,map:RDLegacy.state().map,mode:RDLegacy.state().mode})')
        assert state['n']==index;maps.add(state['map']);modes.add(state['mode'])
        assert not ev('RDLegacy.state().done')
        if index==17:assert ev('RDLegacy.state().enemies.filter(function(e){return e.type==="boss";}).length')==2
        if index==0:ev('RDLegacy.state().players[1].hp=0')
        finish_leg()
        assert ev('RDLegacy.state().coopTour.completed')==index+1
        if index<17:
            assert ev('RDLegacy.state().overlay') and not ev('RDLegacy.state().done')
            assert ev('RDLegacy.state().players[1].hp')>0
            # Repeated completion cannot count the same encounter twice.
            ev('RDLegacy.finish(true)');assert ev('RDLegacy.state().coopTour.completed')==index+1
            tap('ВЫБРАТЬ')
            assert ev('RDLegacy.state().modeTime')<.3
    assert ev('RDLegacy.state().won')
    assert ev('RDLegacy.state().coopTour.bosses')==7
    assert ev('RDLegacy.state().coopTour.revives')==1
    assert len(maps)==6 and len(modes)==6
    assert ev('JSON.stringify(RDSave.data)')==before_tour
    # Endless tour repeats with stronger bosses rather than stopping at 18.
    launch(dict(mode='arena',team=['bugdan','glasses'],coop=True,coopTour='endless',reward='none'))
    first_boss=None
    for index in range(22):
        if index==2:first_boss=ev('RDLegacy.state().enemies[0].maxhp')
        if index==20:assert ev('RDLegacy.state().enemies[0].maxhp')>first_boss
        finish_leg();assert not ev('RDLegacy.state().done');tap('ВЫБРАТЬ')
    finish_leg();tap('ЗАВЕРШИТЬ ПОХОД')
    assert ev('RDLegacy.state().won') and ev('RDLegacy.state().coopTour.completed')==23
    assert ev('JSON.stringify(RDSave.data)')==before_tour
    print('PASS: 18 cooperative stages, six maps and task types, seven bosses, partner revival, persistent perks, independent scene timers, endless scaling and voluntary finish.',flush=True)
    opening('contracts');ev('RDSave.data.progress.kills=50;RDUI.render()');before=ev('RDSave.data.crystals');tap('ЗАБРАТЬ 320 КРИСТ.');assert ev('RDSave.data.crystals')==before+320
    ev('RDLegacy.menu()');show('home')
    saved=ev('RDSave.data');page.reload();page.wait_for_function('!!window.RDUI');assert ev('RDSave.data')==saved
    for width,height in [(1280,720),(3840,2160),(430,932)]:
        page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(150)
        r=page.locator('#interface').bounding_box();assert r['x']>=-1 and r['y']>=-1 and r['x']+r['width']<=width+1 and r['y']+r['height']<=height+1
        launch(dict(mode='arena',team=['bugdan','glasses'],coop=True,reward='none'))
        for selector in ['#stick1','#stick2','#skill1','#skill2']:
            r=page.locator(selector).bounding_box();assert r['y']>=0 and r['y']+r['height']<=height+1,(selector,r)
        ev('RDLegacy.menu()')
    assert not errors,errors
    if os.getenv('LEGACY_SCREENSHOT'):
        page.set_viewport_size({'width':1920,'height':1080});show('home');page.wait_for_timeout(300);page.screenshot(path=os.environ['LEGACY_SCREENSHOT'])
    print('PASS: 42 map/mode pairs, seven victory conditions, real original rewards, rare cinema event, contracts, persisted v4 save, 720p / 4K / portrait.',flush=True)
    b.close()
