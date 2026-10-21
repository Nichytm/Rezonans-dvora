"""Two human-controlled heroes share one world; its simulation ticks exactly once."""
from contextlib import contextmanager
import copy
import math
from pygame import Vector2 as V
from modes import Battle
from battle import Battle as Combat
from arena_base import Battle as Arena
from model import HEROES
from worlds import MAPS, resolve_circle
from coop_content import COOP_STAGES

LOCAL=('pos','aim','move','mouse','attack_cd','dash_cd','dash_time','invulnerable','shield','switch_cd',
       'anim','anim_kind','anim_dir','anim_phase','parry','feedback','feedback_time','execution','execute_cd','reticle','reticle_time','ice_velocity')

class CoopBattle(Battle):
    def __init__(self,profile,heroes,sound=lambda *a:None,tour='campaign'):
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
        self.tour='endless' if tour=='endless' else 'campaign'
        self.tour_completed=0;self.tour_bosses=0;self.tour_revives=0;self.tour_finished=False
        self.next_leg()

    def next_leg(self):
        self.leg=COOP_STAGES[self.tour_completed%len(COOP_STAGES)]
        self.stage=1+self.tour_completed%18//3;self.mode=None if self.leg['mode']=='arena' else self.leg['mode']
        self.map_key=self.leg['map'];self.objective='defend' if self.mode=='escort' else 'clear'
        self.allow_waves=False;self.wave=1;self.next_wave=99999;self.spawn_queue=0;self.spawn_cd=.5
        self.mode_time=0.;self.map_clock=0.;self.hazard_cycle=-1;self.last_mode_spawn=2.
        self.mode_limit={'escort':180,'heist':180,'capture':150,'survival':90,'duel':240}.get(self.mode,99999)
        for name in ('enemies','warnings','zones','bullets','objects','fields','orbs','particles','fx','effects','texts'):
            getattr(self,name).clear()
        self.stances.clear();self.cutin=0.;self.core_pos=V(220,400);self.core_max=self.core_hp=1200;self.core_cooldown=0
        self.cart_progress=0.;self.cart_blocked=False;self.carry=self.deposited=0;self.deposit_timer=self.escape_timer=0.;self.loot=[]
        self.beacons=[dict(pos=V(p),value=0.,owned=False) for p in [(250,475),(640,260),(1050,475)]]
        self.safe_center=V(640,395);self.safe_radius=260.
        self._store(self.active)
        for index,state in enumerate(self.players):
            state.update(pos=V(185+index*160,390+index*100),invulnerable=2.,dash_time=0.,ice_velocity=V(),execution=[],reticle=None,reticle_time=0.)
            self.ammo[self.team[index]]=6;self.reloads[self.team[index]]=0
        self._load(0)
        if self.mode=='duel':
            for index,boss in enumerate(self.leg['bosses']):
                self.spawn_photo_boss(boss);self.enemies[-1]['pos']=resolve_circle(V(940+index*180,330+index*170),40,MAPS[self.map_key]['obstacles'])
        elif self.mode=='heist':self.refill_loot()
        elif not self.mode:
            self.spawn_queue=8+(self.stage-1)*2+(self.tour_completed//18)*2
            if self.leg.get('anchors'):self.spawn(kind='anchor',pos=(640,300))
        self.banner=f'ЭТАП {self.tour_completed+1}'+(' / 18' if self.tour=='campaign' else '')+' · '+self.leg['name'];self.banner_time=4

    def spawn(self,boss=False,kind=None,pos=None,photo=None):
        super().spawn(boss,kind,pos,photo)
        if not hasattr(self,'tour_completed'):return
        e=self.enemies[-1];district=self.tour_completed%18//3;lap=self.tour_completed//18
        if boss:
            average=sum(self.profile.stats(h)['atk'] for h in self.team)/2
            e['hp']=e['maxhp']=(2200+average*35)*(1+.25*district+.4*lap)
        else:
            e['hp']*=1.3+.2*district+.25*lap;e['maxhp']=e['hp']

    def choose_perk(self,key):
        if not super().choose_perk(key):return False
        self.next_leg();return True

    def complete_leg(self):
        if self.done or self.intermission:return
        self.tour_completed+=1;self.completed_waves=self.tour_completed
        self.tour_bosses+=len(self.leg.get('bosses',[]))
        if self.tour=='campaign' and self.tour_completed>=len(COOP_STAGES):
            self.tour_finished=True;self.finish(True);return
        for h in self.team:
            maximum=self.profile.stats(h)['hp']
            if self.hp[h]<=0:self.hp[h]=maximum*.45;self.tour_revives+=1
            else:self.hp[h]=min(maximum,self.hp[h]+maximum*(.50 if self.mode=='duel' else .25))
            self.energy[h]=max(65.,self.energy[h]);self.skills[h]=min(1.,self.skills[h])
        self.offer_perks();self.enemies.clear();self.warnings.clear();self.objects.clear();self.fields.clear()

    def end_tour(self):
        self.tour_finished=True;self.finish(True)

    def objective_text(self):
        prefix=f'Этап {self.tour_completed+1}'+(' / 18' if self.tour=='campaign' else '')+' · '
        return prefix+(super().objective_text() if self.mode else 'Зачисти район'+(' и уничтожь якорь' if self.leg.get('anchors') else ''))

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
                motion=self.moves[i]
                if self.map_key=='frost':
                    desired=V(motion)
                    if desired.length_squared()>0:
                        self.move=desired.normalize();desired.scale_to_length(self.profile.stats(self.hero)['speed']*self.speed)
                    self.ice_velocity=self.ice_velocity.lerp(desired,min(1.,dt*3.2))
                    if self.dash_time<=0:self.pos+=self.ice_velocity*dt
                    motion=(0,0)
                Arena.advance_actor(self,dt,motion,self.mouse,firing)

    def command(self,index,command):
        if self.done or self.intermission or self.hp[self.team[index]]<=0:return
        with self.player(index):
            self.auto_aim()
            if command in ('dash','skill','ultimate','reload'):getattr(self,command)()

    def switch(self,index):return False  # Each human keeps their own hero.

    def update(self,dt,move=(0,0),mouse=(900,400),firing=False):
        Combat.update(self,dt,move,mouse,firing)
        if self.done or self.intermission:return
        if self.hp[self.team[1]]>0:
            with self.player(1):self.update_actor_effects(dt)
        self._store(self.active)
        for e in self.enemies:e['pos']=resolve_circle(e['pos'],e['r'],MAPS[self.map_key]['obstacles'])
        self.update_map(dt);self.resolve_warnings(dt)
        if self.done:return
        self.mode_time+=dt;self.last_mode_spawn-=dt
        self.update_objective(dt)

    def update_objective(self,dt):
        near=lambda pos,r:any(self.player_position(i).distance_to(pos)<r for i in self.alive())
        if not self.mode or self.mode=='duel':
            if not self.enemies and not self.spawn_queue:self.complete_leg()
            elif self.mode_time>=self.mode_limit:self.finish(False)
            return
        if self.last_mode_spawn<=0:
            self.last_mode_spawn=max(1.8,3.8-self.mode_time/100)
            if len(self.enemies)<17:self.spawn()
        if self.mode=='escort':
            self.cart_blocked=any(e['pos'].distance_to(self.core_pos)<95 for e in self.enemies)
            if near(self.core_pos,140) and not self.cart_blocked:self.cart_progress=min(1.,self.cart_progress+dt/48)
            self.core_pos=V(220+860*self.cart_progress,400)
            if self.cart_progress>=1:self.complete_leg()
        elif self.mode=='capture':
            for z in self.beacons:
                if z['owned']:continue
                contested=any(e['pos'].distance_to(z['pos'])<85 for e in self.enemies)
                if near(z['pos'],80) and not contested:z['value']=min(100.,z['value']+dt*12.5)
                elif contested:z['value']=max(0.,z['value']-dt*4)
                if z['value']>=100:z['owned']=True
            if all(z['owned'] for z in self.beacons):self.complete_leg()
        elif self.mode=='heist':
            for loot in self.loot[:]:
                loot['cooldown']=max(0.,loot['cooldown']-dt)
                if self.carry<3 and not loot['cooldown'] and near(loot['pos'],34):self.carry+=1;self.loot.remove(loot)
            if self.carry and near(V(140,400),70):
                self.deposit_timer+=dt
                if self.deposit_timer>=1.2:
                    self.deposited+=self.carry;self.carry=0;self.deposit_timer=0.
                    if self.deposited<9 and len(self.loot)<3:self.refill_loot()
            else:self.deposit_timer=0.
            if self.deposited>=9:
                self.escape_timer=self.escape_timer+dt if near(V(1130,490),75) else 0.
                if self.escape_timer>=4:self.complete_leg()
        elif self.mode=='survival':
            self.safe_center=V(640+math.sin(self.mode_time*.032)*230,395+math.sin(self.mode_time*.061)*52)
            self.safe_radius=max(105.,260-self.mode_time*1.72)
            self.hurt_where(lambda pos:pos.distance_to(self.safe_center)>self.safe_radius,17)
            if not self.done and self.mode_time>=90:self.complete_leg()
        if not self.done and not self.intermission and self.mode_time>=self.mode_limit:self.finish(False)

    def finish(self,won):
        if self.done:return
        if won and not self.tour_finished:
            self.complete_leg();return
        self.done=True;self.won=won;self.stars=3 if won and all(hp>0 for hp in self.hp.values()) else int(won)
        # This cooperative challenge is independent from solo progression.
        self.result=dict(crystals=0,gold=0,essence=0,xp=0,first=False,levels=[])
        self.sound('win' if won else 'lose')


def start_coop(game,heroes,tour='campaign'):
    game.battle=CoopBattle(game.profile,heroes,game.sound.play,tour)
    game.page='battle';game.modal=None;game.paused=False;game.edit_checked=True
    game.pressed.clear();game.sound.music('battle')
