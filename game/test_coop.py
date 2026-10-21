"""Cooperative invariants: independent actors, one shared world, shared victory."""
import os
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import copy,unittest
import pygame as pg
from coop import CoopBattle,V
from model import Profile,HEROES

class CoopTests(unittest.TestCase):
    def make(self,heroes=('bugdan','glasses')):
        b=CoopBattle(Profile(),heroes);b.next_wave=9999;return b

    def test_two_independent_sticks_and_single_world_clock(self):
        b=self.make();p1=b.player_position(0);p2=b.player_position(1)
        b.moves=[(1,0),(-1,0)];b.update(.1)
        self.assertGreater(b.player_position(0).x,p1.x);self.assertLess(b.player_position(1).x,p2.x)
        self.assertAlmostEqual(b.elapsed,.1);self.assertEqual(b.active,0)
        b.moves=[(0,0),(0,1)];p1=b.player_position(0);p2=b.player_position(1);b.update(.1)
        self.assertEqual(b.player_position(0),p1);self.assertGreater(b.player_position(1).y,p2.y)

    def test_projectiles_advance_only_once(self):
        b=self.make();b.shoot(V(100,200),V(1,0),10,100)
        before=V(b.bullets[0]['pos']);b.update(.1)
        self.assertAlmostEqual(b.bullets[0]['pos'].x-before.x,10)

    def test_player_two_ability_and_dash_have_independent_cooldowns(self):
        b=self.make();b.command(1,'skill')
        self.assertEqual(b.skills[b.team[0]],0);self.assertGreater(b.skills[b.team[1]],0)
        b.command(1,'dash');self.assertEqual(b.players[0]['dash_cd'],0);self.assertGreater(b.players[1]['dash_cd'],0)
        b.update(.1);self.assertGreater(b.skills[b.team[1]],0);self.assertEqual(b.active,0)

    def test_damage_nearest_actor_and_death_do_not_switch_humans(self):
        b=self.make();b.invulnerable=0;b._store(0);b.players[1]['invulnerable']=0
        p2=b.player_position(1);hp=b.hp[b.team[1]];b.hurt_area(p2,30,20)
        self.assertLess(b.hp[b.team[1]],hp);self.assertEqual(b.hp[b.team[0]],b.profile.stats(b.team[0])['hp'])
        b.players[1]['invulnerable']=0;b.hurt_area(p2,30,10000)
        self.assertEqual(b.active,0);self.assertEqual(b.hp[b.team[1]],0);self.assertFalse(b.done)
        self.assertEqual(b.target_position(p2),b.player_position(0))
        b.invulnerable=0;b.hurt(10000);self.assertTrue(b.done);self.assertFalse(b.won)

    def test_survivor_continues_after_player_one_dies(self):
        b=self.make();b.hp[b.team[0]]=0;p1=b.player_position(0);p2=b.player_position(1)
        b.moves=[(1,0),(-1,0)];b.update(.1)
        self.assertEqual(b.player_position(0),p1);self.assertLess(b.player_position(1).x,p2.x);self.assertFalse(b.done)

    def test_enemy_contact_and_bullet_can_hit_player_two(self):
        b=self.make();b.players[1]['invulnerable']=0;b.spawn(kind='slime',pos=b.player_position(1));e=b.enemies[-1]
        e['pos']=b.player_position(1);e['stun']=0;e['hp']=10000;hp=b.hp[b.team[1]];b.update(.01)
        self.assertLess(b.hp[b.team[1]],hp)
        b.enemies=[];b.players[1]['invulnerable']=0;hp=b.hp[b.team[1]]
        b.shoot(b.player_position(1),V(1,0),20,0,enemy=True);b.update(.01)
        self.assertLess(b.hp[b.team[1]],hp)

    def test_boss_telegraph_targets_nearest_actor_and_warning_hits_both(self):
        b=self.make();b.spawn_photo_boss('egor');e=b.enemies[-1];e['pos']=V(880,400);e['cooldown']=0
        p2=b.player_position(1);b.update_boss(e,.1)
        self.assertLess(b.warnings[0]['pos'].distance_to(p2),1)
        b.invulnerable=0;b._store(0);b.players[1]['invulnerable']=0;before=dict(b.hp)
        b.warnings=[];b.warn('circle',V(640,400),500,0,20);b.resolve_warnings(.1)
        self.assertLess(b.hp[b.team[0]],before[b.team[0]]);self.assertLess(b.hp[b.team[1]],before[b.team[1]])

    def test_orb_can_heal_player_two(self):
        b=self.make();h=b.team[1];b.hp[h]-=50
        b.orbs=[dict(pos=b.player_position(1),life=5)];before=b.hp[h];b.update(.01)
        self.assertGreater(b.hp[h],before);self.assertFalse(b.orbs)

    def test_all_hero_styles_and_player_two_ultimate(self):
        for hero in HEROES:
            b=self.make(('white' if hero!='white' else 'bugdan',hero))
            b.spawn(kind='slime',pos=(840,400));b.enemies[-1]['hp']=b.enemies[-1]['maxhp']=10000
            b.energy[hero]=100;b.command(1,'skill');b.command(1,'ultimate');b.moves=[(0,0),(.2,0)]
            for _ in range(80):b.update(.02)
            self.assertEqual(b.active,0);self.assertEqual(len(b.players),2)

    def test_coop_challenge_does_not_change_solo_progression(self):
        b=self.make();before=copy.deepcopy(b.profile.data)
        b.completed_waves=3;b.finish(True);b.finish(True)
        self.assertTrue(b.won);self.assertEqual(b.profile.data,before)

    def test_healing_field_reaches_player_two_and_keeps_dead_player_down(self):
        b=self.make(('white','artem'));h=b.team[1];b.hp[h]-=100;b.command(1,'skill');before=b.hp[h]
        b.update(.1);self.assertGreater(b.hp[h],before)
        b.hp[b.team[0]]=0;b.players[0]['pos']=V(640,265);b._load(0);b.update(.1)
        self.assertEqual(b.hp[b.team[0]],0)

    def test_shared_three_wave_victory(self):
        b=self.make();b.next_wave=0
        for _ in range(300):
            for e in b.enemies[:]:b.hit(e,1000000,b.team[1])
            if b.intermission:b.choose_perk(b.choices[0])
            b.update(.1)
            if b.done:break
        self.assertTrue(b.won);self.assertEqual(b.completed_waves,3)

    def test_draw_both_heroes_and_repeat_coop(self):
        import tempfile
        from pathlib import Path
        from game import Game
        with tempfile.TemporaryDirectory() as temp:
            game=Game(Path(temp)/'save.json',True);game.start_coop(['white','glasses'])
            game.battle.command(1,'ultimate');game.draw()
            self.assertEqual(game.battle.active,0)
            game.battle.finish(True);game.draw()
            callback=next(callback for rect,callback in game.ui.buttons if rect.collidepoint((600,580)))
            callback();self.assertTrue(game.battle.coop);self.assertEqual(game.battle.team,['white','glasses'])
            pg.quit()

    def test_cannot_choose_same_or_invalid_heroes(self):
        for heroes in [('bugdan','bugdan'),('unknown','white'),('bugdan',)]:
            with self.assertRaises(ValueError):self.make(heroes)

if __name__=='__main__':unittest.main()
