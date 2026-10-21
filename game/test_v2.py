import os
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import json
import tempfile
import unittest
from pathlib import Path
import pygame as pg
from model import Profile,fresh_save,HEROES,CONTRACTS
from battle import Battle,PERKS

class V2Tests(unittest.TestCase):
    def test_v1_progress_migrates_and_gift_is_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'profile.json';old=fresh_save();old['version']=1
            old['crystals']=40;old['pity']=31;old['cleared']=2;old['heroes']['bugdan']['level']=3
            old['heroes']['artem']=dict(level=2,xp=160,stars=0,shards=40);old['team']=['bugdan','artem','white']
            path.write_text(json.dumps(old),encoding='utf-8');p=Profile(path)
            self.assertEqual(p.data['crystals'],1640);self.assertEqual(p.data['pity'],31)
            self.assertEqual(p.data['cleared'],2);self.assertEqual(p.data['heroes']['artem'],old['heroes']['artem'])
            self.assertEqual(p.data['team'],old['team']);self.assertIn('smiler',p.data['heroes'])
            self.assertEqual(HEROES['smiler']['name'],'Артём');self.assertEqual(HEROES['artem']['name'],'Булочник')
            self.assertEqual(Profile(path).data,p.data)

    def test_intermission_freezes_and_cannot_double_claim(self):
        b=Battle(Profile(),1);b.completed_waves=1;b.offer_perks();before=b.elapsed;pos=b.pos.copy()
        b.update(2,(1,0),firing=True);b.skill();b.dash();b.attack((100,100))
        self.assertEqual(b.elapsed,before);self.assertEqual(b.pos,pos);self.assertEqual(b.skill_count,0)
        key=b.choices[0];self.assertTrue(b.choose_perk(key));self.assertFalse(b.choose_perk(key))
        self.assertEqual(len(b.perks),1)

    def test_all_perks_apply_and_recovery_revives_one(self):
        b=Battle(Profile(),1)
        for key in PERKS:
            if key=='recovery':b.hp[b.team[1]]=0;b.hp[b.team[2]]=0
            b.intermission=True;b.choices=[key];self.assertTrue(b.choose_perk(key))
        self.assertGreater(b.power,1);self.assertGreater(b.haste,1);self.assertGreater(b.speed,1)
        self.assertLess(b.armor,1);self.assertTrue(b.frost);self.assertGreater(b.piercing,0)
        self.assertGreater(b.hp[b.team[1]],0);self.assertEqual(b.hp[b.team[2]],0)

    def test_defense_loss_and_anchors_spawn(self):
        p=Profile();b=Battle(p,2);self.assertEqual(b.objective,'defend');b.hurt_core(100000)
        self.assertTrue(b.done);self.assertFalse(b.won);self.assertEqual(p.data['cleared'],0)
        b=Battle(p,3)
        for _ in range(90):b.update(1/60)
        anchors=[e for e in b.enemies if e['kind']=='anchor'];self.assertEqual(len(anchors),1)
        b.hit(anchors[0],100000,b.hero);self.assertEqual(b.anchors_destroyed,1)

    def test_endless_continues_past_wave_three_and_rewards_once(self):
        p=Profile();b=Battle(p,1,endless=True)
        for _ in range(4000):
            if b.intermission:
                if b.completed_waves>=4:break
                b.choose_perk(b.choices[0])
            for e in b.enemies[:]:b.hit(e,100000,b.hero)
            b.update(1/60)
        self.assertEqual(b.completed_waves,4);self.assertFalse(b.done)
        b.finish(True);self.assertEqual(p.data['best_endless'],4);self.assertEqual(p.data['cleared'],0)
        self.assertEqual(b.result['crystals'],180);before=p.data['crystals'];b.finish(True);self.assertEqual(p.data['crystals'],before)

    def test_perfect_dodge_and_hero_specific_ultimates(self):
        p=Profile();b=Battle(p,1);b.shoot(b.pos+(40,0),(-1,0),10,enemy=True)
        b.dash();self.assertEqual(b.perfect_dodges,1);self.assertGreater(b.slow_time,0)
        b.energy[b.hero]=100;b.ultimate();self.assertTrue(any(f['kind']=='rain' for f in b.fields))
        p.data['team']=['smiler'];b=Battle(p,1);b.spawn();b.energy[b.hero]=100;b.ultimate()
        if b.enemies:self.assertGreater(b.enemies[0]['fear'],0)

    def test_contract_reward_cannot_be_claimed_twice(self):
        p=Profile();self.assertFalse(p.claim_contract('hunts'));p.data['progress']['kills']=50
        before=p.data['crystals'];self.assertTrue(p.claim_contract('hunts'));self.assertFalse(p.claim_contract('hunts'))
        self.assertEqual(p.data['crystals'],before+CONTRACTS['hunts']['crystals'])

    def test_v2_effects_and_music_are_valid_and_peak_limited(self):
        from main import ASSETS,Sound
        pg.mixer.init();p=Profile();audio=Sound(p,ASSETS);self.assertTrue(audio.ready)
        for name in ('sword','punch','heavy','dagger','metal','wood','throw','reload'):self.assertIn(name,audio.sounds)
        for name in ('dash','impact','crit','dodge','break','win','lose'):self.assertIn(name,audio.sounds)
        metadata=json.loads((ASSETS/'audio_v2'/'levels.json').read_text())
        self.assertEqual(len(metadata),28)
        for name,data in metadata.items():
            self.assertLessEqual(data['peak'],.72);self.assertGreater(data['rms'],.005)
            self.assertGreater(pg.mixer.Sound(str(ASSETS/'audio_v2'/f'{name}.wav')).get_length(),0)
        self.assertTrue(p.data['voices']);pg.mixer.quit()

if __name__=='__main__':unittest.main()
