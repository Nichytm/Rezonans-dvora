"""Two human-controlled heroes share one world; its simulation ticks exactly once."""
from contextlib import contextmanager
import copy
from pygame import Vector2 as V
from modes import Battle
from arena_base import Battle as Arena
from model import HEROES

LOCAL=('pos','aim','move','mouse','attack_cd','dash_cd','dash_time','invulnerable','shield','switch_cd',
       'anim','anim_kind','anim_dir','anim_phase','parry','feedback','feedback_time','execution','execute_cd','reticle','reticle_time','ice_velocity')

class CoopBattle(Battle):
    def __init__(self,profile,heroes,sound=lambda *a:None):
        heroes=list(heroes)
        if len(heroes)!=2 or len(set(heroes))!=2 or any(h not in HEROES for h in heroes):
            raise ValueError('Choose two different heroes')
        super().__init__(profile,1,sound)
        self.coop=True;self.team=heroes;self.active=0
        self.hp={h:float(profile.stats(h)['hp']) for h in heroes}
        self.energy={h:70. for h in heroes};self.skills={h:0. for h in heroes}
        self.players=[{name:copy.deepcopy(getattr(self,name)) for name in LOCAL} for _ in heroes]
        self.players[0]['pos']=V(430,400);self.players[1]['pos']=V(820,400)
        self.moves=[(0,0),(0,0)];self._load(0)
        self.banner='ВДВОЁМ · 3 ВОЛНЫ И БОСС';self.banner_time=3

    def _store(self,index):
        for name in LOCAL:self.players[index][name]=getattr(self,name)

    def _load(self,index):
        self.active=index
        for name in LOCAL:setattr(self,name,self.players[index][name])

    @contextmanager
    def player(self,index):
        previous=self.active;self._store(previous);self._load(index)
        try:yield
        finally:self._store(index);self._load(previous)

    def player_position(self,index):
        return V(self.pos if index==self.active else self.players[index]['pos'])

    def alive(self):return [i for i,h in enumerate(self.team) if self.hp[h]>0]

    def nearest(self,origin):
        return min(self.alive(),key=lambda i:self.player_position(i).distance_squared_to(origin),default=0)

    def heal_area(self,pos,radius,fraction):
        healed=False
        for i in self.alive():
            h=self.team[i]
            if self.player_position(i).distance_to(pos)<radius:
                self.hp[h]=min(self.profile.stats(h)['hp'],self.hp[h]+self.profile.stats(h)['hp']*fraction);healed=True
        return healed

    def update_map(self,dt):
        from worlds import MAPS
        dead=self.hp[self.team[0]]<=0
        super().update_map(dt)
        if dead:self.hp[self.team[0]]=0
        h=self.team[1]
        if self.hp[h]>0 and self.map_key and MAPS[self.map_key]['hazard']=='fountain' and self.player_position(1).distance_to(V(640,265))<58:
            self.hp[h]=min(self.profile.stats(h)['hp'],self.hp[h]+dt*9)

    def target_position(self,origin):return self.player_position(self.nearest(origin))

    def owner_position(self,owner):
        return self.player_position(self.team.index(owner)) if owner in self.team else V(self.pos)

    def hurt_where(self,predicate,damage):
        hit=False
        for i in self.alive():
            with self.player(i):
                if predicate(self.pos):self.hurt(damage);hit=True
        return hit

    def update_boss(self,e,dt):
        with self.player(self.nearest(e['pos'])):super().update_boss(e,dt)

    def update_orb(self,orb,dt):
        with self.player(self.nearest(orb['pos'])):super().update_orb(orb,dt)

    def auto_aim(self):
        targets=[e for e in self.enemies if e['hp']>0]
        if targets:
            self.mouse=V(min(targets,key=lambda e:e['pos'].distance_squared_to(self.pos))['pos'])
            delta=self.mouse-self.pos
            if delta.length_squared()>1:self.aim=delta.normalize()
        else:self.mouse=self.pos+self.aim*400
        return bool(targets)

    def advance_actor(self,dt,move,mouse,firing):
        for i in self.alive():
            with self.player(i):
                if i:
                    self.anim=max(0,self.anim-dt);self.parry=max(0,self.parry-dt);self.feedback_time=max(0,self.feedback_time-dt)
                firing=self.auto_aim()
                Arena.advance_actor(self,dt,self.moves[i],self.mouse,firing)

    def command(self,index,command):
        if self.done or self.intermission or self.hp[self.team[index]]<=0:return
        with self.player(index):
            self.auto_aim()
            if command in ('dash','skill','ultimate','reload'):getattr(self,command)()

    def switch(self,index):return False  # Each human keeps their own hero.

    def update(self,dt,move=(0,0),mouse=(900,400),firing=False):
        super().update(dt,move,mouse,firing)
        if self.done or self.intermission:return
        if self.hp[self.team[1]]>0:
            with self.player(1):self.update_actor_effects(dt)
        self._store(self.active)

    def finish(self,won):
        if self.done:return
        self.done=True;self.won=won;self.stars=3 if won and all(hp>0 for hp in self.hp.values()) else int(won)
        # This cooperative challenge is independent from solo progression.
        self.result=dict(crystals=0,gold=0,essence=0,xp=0,first=False,levels=[])
        self.sound('win' if won else 'lose')


def start_coop(game,heroes):
    game.battle=CoopBattle(game.profile,heroes,game.sound.play)
    game.page='battle';game.modal=None;game.paused=False;game.edit_checked=True
    game.pressed.clear();game.sound.music('battle')
