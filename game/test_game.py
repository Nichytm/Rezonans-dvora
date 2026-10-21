"""Run with: python -m unittest -v test_game"""
import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import json
import random
import tempfile
import unittest
from pathlib import Path
import pygame as pg
from model import Profile,HEROES
from battle import Battle

class AlwaysRare:
    def random(self):return .99
    def choice(self,seq):return seq[0]

class EconomyTests(unittest.TestCase):
    def test_guarantees_and_duplicate_rewards(self):
        p=Profile(rng=AlwaysRare());p.data['crystals']=100000
        pulls=[]
        for _ in range(6):pulls+=p.summon(10)
        self.assertEqual(HEROES[pulls[59]['id']]['rarity'],'SSR')
        for i in (9,19,29,39,49):self.assertEqual(HEROES[pulls[i]['id']]['rarity'],'SR')
        self.assertEqual(p.data['pity'],0)
        self.assertEqual(p.data['epic_pity'],0)
        self.assertEqual(p.data['crystals'],100000-60*160)
        self.assertGreater(p.data['heroes']['glasses']['shards'],0)

    def test_insufficient_currency_is_atomic(self):
        p=Profile();p.data['crystals']=159
        before=json.dumps(p.data,sort_keys=True)
        self.assertEqual(p.summon(1),[]);self.assertEqual(p.summon(-1),[])
        self.assertEqual(json.dumps(p.data,sort_keys=True),before)

    def test_upgrade_awakening_and_team(self):
        p=Profile();hp=p.stats('bugdan')['hp']
        self.assertTrue(p.upgrade('bugdan'));self.assertGreater(p.stats('bugdan')['hp'],hp)
        self.assertFalse(p.awaken('bugdan'));p.data['heroes']['bugdan']['shards']=20
        self.assertTrue(p.awaken('bugdan'));self.assertEqual(p.data['heroes']['bugdan']['stars'],1)
        self.assertTrue(p.set_slot('glasses',0));self.assertEqual(len(set(p.data['team'])),3)
        self.assertFalse(p.set_slot('ilya',0))

    def test_save_load_and_corrupt_backup(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'profile.json';p=Profile(path);p.upgrade('bugdan');p.summon(10);p.save()
            self.assertEqual(Profile(path).data,p.data)
            path.write_text('{broken',encoding='utf-8');q=Profile(path)
            self.assertTrue(q.warning);self.assertTrue(path.with_suffix('.damaged.json').exists())
            q.save();self.assertEqual(Profile(path).data,q.data)

    def test_first_clear_and_replay_rewards(self):
        p=Profile();team=p.data['team']
        first=p.reward(1,True,25,team);again=p.reward(1,True,25,team)
        self.assertEqual(first['crystals'],900);self.assertEqual(again['crystals'],120)
        self.assertFalse(again['first']);self.assertEqual(p.data['cleared'],1)
        self.assertEqual(p.reward(2,False,4,team)['crystals'],0)
        self.assertEqual(p.data['cleared'],1)

class BattleTests(unittest.TestCase):
    def test_all_hero_skills_and_ultimates(self):
        p=Profile()
        for h in HEROES:
            p.data['heroes'][h]=dict(level=1,xp=0,shards=0,stars=0)
            p.data['team']=[h];b=Battle(p,1);b.spawn(True);b.spawn()
            b.skill();self.assertGreater(b.skills[h],0)
            b.energy[h]=100;b.ultimate();self.assertLess(b.energy[h],100)
            b.dash();self.assertGreater(b.invulnerable,0)
            for _ in range(120):b.update(1/60,(1,0),(1000,400),True)
            self.assertTrue(55<=b.pos.x<=1225)

    def test_knockout_switch_and_reward_once(self):
        p=Profile();b=Battle(p,1);first=b.hero;b.invulnerable=0;b.hurt(10000)
        self.assertNotEqual(b.hero,first);self.assertEqual(b.hp[first],0)
        b.invulnerable=0;b.hurt(10000);b.invulnerable=0;b.hurt(10000)
        self.assertTrue(b.done);self.assertFalse(b.won)
        before=json.dumps(p.data,sort_keys=True);b.finish(True)
        self.assertEqual(json.dumps(p.data,sort_keys=True),before)

    def test_damage_projectiles_and_full_wave_progression(self):
        p=Profile();b=Battle(p,1)
        for _ in range(2500):
            if b.intermission:b.choose_perk(b.choices[0])
            for e in b.enemies[:]:b.hit(e,10000,b.hero)
            b.update(1/60)
            if b.done:break
        self.assertTrue(b.won);self.assertEqual(b.wave,3);self.assertGreaterEqual(b.kills,25)
        self.assertEqual(p.data['cleared'],1)

    def test_first_stage_playable_with_starter_team(self):
        random.seed(41);p=Profile();b=Battle(p,1)
        # Aim at the nearest monster and run around the arena; no stat or health cheats.
        for frame in range(60*240):
            if b.intermission:b.choose_perk('power' if 'power' in b.choices else b.choices[0])
            angle=frame/60*.50
            target=pg.Vector2(640+440*__import__('math').cos(angle),390+150*__import__('math').sin(angle))
            move=target-b.pos
            aim=min(b.enemies,key=lambda e:e['pos'].distance_to(b.pos))['pos'] if b.enemies else (950,400)
            if b.enemies and b.skills[b.hero]<=0:b.skill()
            if b.energy[b.hero]>=100:b.ultimate()
            if any(e['pos'].distance_to(b.pos)<70 for e in b.enemies):b.dash()
            b.update(1/60,move,aim,True)
            if b.done:break
        self.assertTrue(b.won,f'Starter team failed: wave={b.wave}, kills={b.kills}, hp={b.hp}')

class InterfaceTests(unittest.TestCase):
    def test_click_navigation_summon_pause_and_save(self):
        from main import Game
        with tempfile.TemporaryDirectory() as temp:
            game=Game(Path(temp)/'profile.json',headless=True)
            def click(x,y):
                game.mouse_pos=lambda:(x,y)
                pg.event.post(pg.event.Event(pg.MOUSEBUTTONDOWN,button=1,pos=(x,y)))
                game.events();game.draw()
            game.draw();click(587,40);self.assertEqual(game.page,'summon')
            click(600,613);self.assertEqual(len(game.results),10)
            self.assertEqual(game.profile.data['crystals'],3200)
            game.reveal=2;game.draw();click(640,660);self.assertIsNone(game.modal)
            click(450,40);self.assertEqual(game.page,'roster')
            game.start_battle(1);game.draw()
            pg.event.post(pg.event.Event(pg.KEYDOWN,key=pg.K_ESCAPE,scancode=41));game.events()
            elapsed=game.battle.elapsed;game.step(.5)
            self.assertTrue(game.paused);self.assertEqual(game.battle.elapsed,elapsed)
            game.draw();click(640,331);self.assertFalse(game.paused)
            game.step(.1);self.assertGreater(game.battle.elapsed,elapsed)
            game.leave_battle();game.profile.save()
            self.assertEqual(Profile(Path(temp)/'profile.json').data['crystals'],3200)
            pg.quit()

if __name__=='__main__':unittest.main()
