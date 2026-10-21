import os
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy';os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import json,copy,random,tempfile,unittest
from pathlib import Path
import pygame as pg
from model import Profile
from modes import Battle,V
from worlds import MAPS,MODES,BOSSES,resolve_circle

def make(mode='duel',**kw):return Battle(Profile(),1,mode=mode,**kw)
def tick(b,seconds):
    for _ in range(round(seconds*60)):b.update(1/60)

class ActivitiesTests(unittest.TestCase):
    def test_migration_and_activity_reward_once(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'save.json';p=Profile(path);p.data['version']=3;p.data['pity']=31;p.data['cleared']=5;p.save()
            q=Profile(path);self.assertEqual(q.data['version'],4);self.assertEqual(q.data['pity'],31);self.assertEqual(q.data['cleared'],5)
            b=Battle(q,1,mode='duel');b.finish(True);before=copy.deepcopy(q.data);b.finish(True);self.assertEqual(q.data,before)
            self.assertEqual(b.result['crystals'],600);self.assertEqual(q.data['cleared'],5)
            Battle(q,1,mode='duel').finish(True);self.assertEqual(q.data['crystals'],before['crystals']+200)
            self.assertEqual(Profile(path).data,q.data)

    def test_escort_requires_proximity_and_clear_path(self):
        b=make('escort');b.last_mode_spawn=999;b.pos=V(1000,400);tick(b,1);self.assertEqual(b.cart_progress,0)
        b.pos=V(b.core_pos);b.spawn(kind='slime');b.enemies[-1]['pos']=V(b.core_pos)+V(50,0);b.enemies[-1]['stun']=100
        tick(b,.5);self.assertEqual(b.cart_progress,0);self.assertTrue(b.cart_blocked)
        b.enemies=[];tick(b,1);self.assertGreater(b.cart_progress,0)
        b.cart_progress=.999;b.core_pos=V(220+860*b.cart_progress,400);b.pos=V(b.core_pos);tick(b,.1);self.assertTrue(b.won)

    def test_heist_capacity_drop_deposit_and_escape(self):
        b=make('heist');b.last_mode_spawn=999;b.loot=[dict(pos=V(b.pos),cooldown=0) for _ in range(5)]
        tick(b,.1);self.assertEqual(b.carry,3);self.assertEqual(len(b.loot),2)
        b.invulnerable=0;b.hurt(10);self.assertEqual(b.carry,2)
        b.pos=V(140,400);tick(b,1.3);self.assertEqual(b.deposited,2);self.assertEqual(b.carry,0)
        b.deposited=9;self.assertFalse(b.done);b.pos=V(1130,490);tick(b,4.1);self.assertTrue(b.won)

    def test_beacons_contested_and_free_order(self):
        b=make('capture');b.last_mode_spawn=999;z=b.beacons[2];b.pos=V(z['pos'])
        b.spawn(kind='slime');b.enemies[-1]['pos']=V(b.pos)+V(60,0);b.enemies[-1]['stun']=100
        tick(b,1);self.assertEqual(z['value'],0)
        b.enemies=[]
        for z in reversed(b.beacons):b.pos=V(z['pos']);tick(b,8.1)
        self.assertTrue(b.won)

    def test_survival_win_is_time_not_kills(self):
        b=make('survival');b.mode_time=89.9;b.pos=V(705,355);b.invulnerable=5;b.spawn(kind='slime');tick(b,.2)
        self.assertTrue(b.won);self.assertEqual(b.kills,0);self.assertTrue(b.enemies)

    def test_route_freezes_and_changes_room_and_map(self):
        b=make('expedition');b.enemies=[];tick(b,1);self.assertTrue(b.route_pending)
        elapsed=b.elapsed;pos=V(b.pos);b.update(2,(1,0),firing=True);self.assertEqual(b.elapsed,elapsed);self.assertEqual(b.pos,pos)
        choice=b.route_choices[1];self.assertTrue(b.choose_route(1));self.assertFalse(b.choose_route(1))
        self.assertEqual(b.room,2);self.assertEqual(b.map_key,choice['map']);self.assertIn(choice['perk'],b.perks);self.assertAlmostEqual(b.room_reward,.35)
        for _ in range(4):
            for e in b.enemies[:]:b.hit(e,100000,b.hero)
            tick(b,1)
            if b.route_pending:b.choose_route(0)
        self.assertTrue(b.won)

    def test_warnings_commit_and_can_be_dodged(self):
        b=make();b.enemies=[];b.invulnerable=0;before=b.hp[b.hero];p=V(b.pos)
        b.warn('circle',p,60,1,80);b.resolve_warnings(.5);self.assertEqual(b.hp[b.hero],before)
        b.pos+=V(200,0);b.resolve_warnings(.6);self.assertEqual(b.hp[b.hero],before)
        b.warn('line',b.pos-V(0,100),30,.1,80,end=b.pos+V(0,100));b.resolve_warnings(.2);self.assertLess(b.hp[b.hero],before)

    def test_all_bosses_have_distinct_patterns_and_second_phase(self):
        signatures=[]
        for hero in BOSSES:
            b=make(boss_id=hero);e=b.enemies[0];self.assertEqual(e['boss_id'],hero)
            e['cooldown']=0;b.update_boss(e,.01)
            sig=tuple(sorted(w['shape'] for w in b.warnings))+tuple('turret' for enemy in b.enemies if enemy.get('turret'))
            signatures.append(sig)
            e['hp']=e['maxhp']*.49;e['stun']=0;b.update_boss(e,.01);self.assertTrue(e['enraged'])
            b.hit(e,100000,b.hero);tick(b,.1);self.assertTrue(b.won)
        self.assertGreaterEqual(len(set(signatures)),4)

    def test_map_collisions_and_projectile_cover(self):
        for key,m in MAPS.items():
            b=make(map_key=key);r=pg.Rect(m['obstacles'][0]);b.pos=V(r.center);b.clamp();self.assertFalse(r.inflate(40,40).collidepoint(b.pos))
            self.assertTrue(b.projectile_blocked(dict(pos=V(r.center))))
        b=make('capture',map_key='frost');b.enemies=[];b.update(.1,(1,0));x=b.pos.x;b.update(.1);self.assertGreater(b.pos.x,x)

    def test_timeout_is_loss_and_does_not_clear_story(self):
        b=make('capture');b.mode_time=b.mode_limit-.01;b.update(.02);self.assertTrue(b.done);self.assertFalse(b.won)
        self.assertEqual(b.result['crystals'],0);self.assertEqual(b.profile.data['cleared'],0)

    def test_every_mode_on_every_map_runs(self):
        random.seed(64)
        for mode in MODES:
            for key in MAPS:
                b=make(mode,map_key=key);b.invulnerable=999
                for frame in range(660):
                    aim=b.enemies[0]['pos'] if b.enemies else (800,400)
                    if frame%90==0:b.skill()
                    if b.energy[b.hero]>=100:b.ultimate()
                    b.update(1/60,(1 if frame%120<60 else -1,0),aim,True)
                self.assertGreater(b.elapsed,0)

class RenderTests(unittest.TestCase):
    def test_new_menus_mode_ui_and_routes(self):
        from main import Game
        with tempfile.TemporaryDirectory() as d:
            g=Game(Path(d)/'p.json',True);g.navigate('activities');g.draw();self.assertGreaterEqual(len(g.ui.buttons),13)
            for key in MODES:
                g.configure_activity(key);g.draw();g.start_activity();g.draw()
                if key=='expedition':g.battle.offer_routes();g.draw()
            g.battle.finish(True);g.draw();g.leave_battle();self.assertEqual(g.page,'activities');pg.quit()

if __name__=='__main__':unittest.main()
