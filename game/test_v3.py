import os
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame as pg
from model import Profile,HEROES
from battle import Battle,V
from cinema import edit_due,Cinema
from audio import Sound,DEFAULT_VOICES

def arena(hero):
    b=Battle(Profile(),1,training=True);b.set_training_hero(hero)
    b.enemies=[];b.pos=V(440,400);b.aim=V(1,0);b.mouse=V(540,400)
    return b

def target(b,pos):
    b.spawn(kind='slime',pos=pos);e=b.enemies[-1];e['pos']=V(pos);e['hp']=e['maxhp']=10000;e['dummy']=True
    return e

class Mechanics(unittest.TestCase):
    def test_sword_is_directional_melee_not_a_projectile(self):
        b=arena('ilya');front=target(b,(540,400));back=target(b,(340,400));far=target(b,(900,400))
        b.attack((900,400))
        self.assertLess(front['hp'],10000);self.assertEqual(back['hp'],10000);self.assertEqual(far['hp'],10000);self.assertFalse(b.bullets)

    def test_gun_nearest_target_and_reload(self):
        b=arena('glasses');front=target(b,(600,400));back=target(b,(800,400))
        for _ in range(6):b.attack_cd=0;b.attack((900,400))
        hp=front['hp'];self.assertLess(hp,10000);self.assertEqual(back['hp'],10000)
        self.assertEqual(b.ammo['glasses'],0);b.attack_cd=0;b.attack((900,400));self.assertEqual(front['hp'],hp)
        for _ in range(90):b.update(1/60)
        self.assertEqual(b.ammo['glasses'],6);b.skill();self.assertLess(back['hp'],10000)

    def test_bomb_has_fuse_and_area_damage(self):
        b=arena('igor');near=target(b,(630,400));far=target(b,(950,400));b.attack((630,400))
        self.assertEqual(near['hp'],10000);self.assertFalse(b.bullets)
        for _ in range(50):b.update(1/60)
        self.assertLess(near['hp'],10000);self.assertEqual(far['hp'],10000)

    def test_boomerang_hits_outbound_and_return(self):
        b=arena('smirk');e=target(b,(600,400));b.attack((900,400))
        for _ in range(28):b.update(1/60)
        outbound=e['hp'];self.assertLess(outbound,10000)
        for _ in range(65):b.update(1/60)
        self.assertLess(e['hp'],outbound);self.assertFalse(b.objects)

    def test_turret_persists_when_switching(self):
        p=Profile();p.data['team']=['igor','bugdan'];b=Battle(p,1);b.next_wave=999
        e=target(b,(800,400));b.mouse=V(700,400);b.skill();b.switch(1)
        hp=e['hp']
        for _ in range(100):b.update(1/60)
        self.assertLess(e['hp'],hp);self.assertTrue(any(o['kind']=='turret' for o in b.objects))

    def test_ultimate_effects_and_stance_expire(self):
        b=arena('ilya');target(b,(540,400));b.ultimate();self.assertEqual(b.stances['ilya'],8)
        for _ in range(510):b.update(1/60)
        self.assertEqual(b.stances['ilya'],0)
        b=arena('smiler');e=target(b,(580,400));e['dummy']=False;b.ultimate();d=e['pos'].distance_to(b.pos)
        b.update(.04);self.assertGreater(e['pos'].distance_to(b.pos),d);self.assertGreater(e['weak'],0)

    def test_poison_and_healing_are_different(self):
        b=arena('bugdan');e=target(b,(570,400));b.attack((570,400))
        for _ in range(18):b.update(1/60)
        hp=e['hp'];self.assertIn('poison',e)
        for _ in range(36):b.update(1/60)
        self.assertLess(e['hp'],hp)
        b=arena('artem');b.hp['artem']=40;b.skill()
        for _ in range(60):b.update(1/60)
        self.assertGreater(b.hp['artem'],40)

    def test_trials_do_not_change_profile(self):
        p=Profile();before=copy.deepcopy(p.data);b=Battle(p,1,training=True)
        for h in HEROES:
            b.set_training_hero(h);b.attack((700,305));b.skill();b.ultimate()
            for _ in range(180):b.update(1/60,(0,0),(700,305),True)
        b.finish(True);self.assertEqual(p.data,before)

    def test_relic_buy_and_equip_once(self):
        p=Profile();gold=p.data['gold'];self.assertTrue(p.buy_relic('brick'));self.assertTrue(p.buy_relic('brick'))
        self.assertEqual(p.data['gold'],gold-300);self.assertEqual(Battle(p,1).power,1.15)
        p.buy_relic('watch');self.assertEqual(Battle(p,1).power,1);self.assertEqual(Battle(p,1).haste,1.2)

class Media(unittest.TestCase):
    def test_edit_frequency(self):
        d=Profile().data;self.assertFalse(edit_due(d,5000,0))
        d['v3_wins']=3;self.assertTrue(edit_due(d,5000,1))
        d['edit_seen']=1;d['last_edit_at']=5000
        self.assertFalse(edit_due(d,5100,0));self.assertFalse(edit_due(d,7000,.5));self.assertTrue(edit_due(d,7000,.01))

    def test_voice_assignments_and_summon_does_not_play_voice(self):
        from main import ASSETS
        pg.mixer.init();sound=Sound(Profile(),ASSETS)
        self.assertTrue(sound.ready);self.assertNotIn('buy_package',DEFAULT_VOICES.values())
        self.assertEqual(sound.binding('ilya:ultimate'),'');self.assertEqual(sound.binding('bugdan:skill'),'bugdanchik_attack')
        with patch.object(sound,'voice') as voice:
            sound.play('summon');voice.assert_not_called()
            sound.play('merchant');voice.assert_called_once_with('buy_package')
        pg.mixer.quit()

    def test_movie_streams_to_end_and_skips(self):
        from main import ASSETS
        pg.init();pg.display.set_mode((1,1));sound=Sound(Profile(),ASSETS);movie=Cinema(ASSETS,sound)
        self.assertTrue(movie.open());self.assertTrue(24<movie.duration<26)
        for _ in range(50):movie.update(.04)
        self.assertIsNotNone(movie.frame);at=movie.elapsed;movie.pause();movie.update(1);self.assertEqual(at,movie.elapsed)
        movie.pause()
        for _ in range(640):movie.update(.04)
        self.assertFalse(movie.active);self.assertTrue(movie.open());movie.close();self.assertFalse(movie.active)
        pg.quit()

if __name__=='__main__':unittest.main()
