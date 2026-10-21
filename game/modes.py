"""Objectives, room routes, map rules and photo boss integration."""
import math,random
import pygame as pg
from battle import Battle as Combat,PERKS,V,BOUNDS
from bosses import Bosses
from worlds import MAPS,MODES,BOSSES,resolve_circle

class Battle(Bosses,Combat):
    def __init__(self,profile,stage,sound=lambda *a:None,endless=False,training=False,mode=None,map_key=None,boss_id='bugdan',difficulty=1):
        self.mode=mode;self.difficulty=max(1,min(3,int(difficulty)));self.boss_choice=boss_id
        self.map_key=None if training else map_key or list(MAPS)[(stage-1)%len(MAPS)]
        self.allow_waves=not mode;self.warnings=[];self.map_clock=0.;self.hazard_cycle=-1;self.last_mode_spawn=1.
        self.route_pending=False;self.route_choices=[];self.room=0;self.room_wait=.8;self.room_reward=0.;self.room_type=''
        self.mode_time=0.;self.mode_limit={'escort':180,'heist':180,'capture':150,'survival':90,'duel':240,'expedition':600}.get(mode,99999)
        self.ice_velocity=V();self.route_history=[];self.carry=0;self.deposited=0;self.deposit_timer=0.;self.escape_timer=0.;self.loot=[]
        self.beacons=[];self.safe_center=V(640,395);self.safe_radius=260.;self.cart_progress=0.;self.cart_blocked=False
        super().__init__(profile,stage,sound,endless,training)
        self.objective='defend' if mode=='escort' else 'clear' if mode else self.objective
        if mode:
            self.wave=1;self.next_wave=99999;self.spawn_queue=0;self.pos=V(190,400);self.energy={h:70. for h in self.team}
            self.banner=MODES[mode]['name'].upper();self.banner_time=2.5
            if mode=='duel':self.spawn_photo_boss(boss_id)
            elif mode=='escort':self.core_pos=V(220,400);self.core_max=self.core_hp=1050
            elif mode=='heist':self.refill_loot()
            elif mode=='capture':self.beacons=[dict(pos=V(p),value=0.,owned=False) for p in [(250,475),(640,260),(1050,475)]]
            elif mode=='expedition':self.next_room('steady',self.map_key)

    def spawn(self,boss=False,kind=None,pos=None,photo=None):
        super().spawn(boss,kind,pos)
        e=self.enemies[-1]
        if self.map_key:e['pos']=resolve_circle(e['pos'],e['r'],MAPS[self.map_key]['obstacles'])
        if boss and not self.training:
            hero=photo or list(BOSSES)[(self.stage+self.wave//3-1)%len(BOSSES)]
            e['boss_id']=hero;e['color']=BOSSES[hero]['color'];e['cooldown']=2.;e['recover']=0.;e['casting']=0.
            self.boss_name=BOSSES[hero]['name'];self.banner=self.boss_name;self.banner_time=2.5
            if self.mode:
                average=sum(self.profile.stats(h)['atk'] for h in self.team)/len(self.team)
                e['hp']=e['maxhp']=(3100+average*30)*(1+.4*(self.difficulty-1))
            self.feedback=BOSSES[hero]['hint'];self.feedback_time=5.
        elif self.mode and not self.training:
            scale=1.4+.4*(self.difficulty-1);e['hp']*=scale;e['maxhp']*=scale

    def clamp(self):
        super().clamp()
        if self.map_key:self.pos=resolve_circle(self.pos,21,MAPS[self.map_key]['obstacles'])

    def projectile_blocked(self,bullet):
        return bool(self.map_key and any(pg.Rect(r).collidepoint(bullet['pos']) for r in MAPS[self.map_key]['obstacles']))

    def hurt(self,damage):
        hurt_hero=self.hero;before=self.hp[hurt_hero]
        super().hurt(damage)
        if self.mode=='heist' and self.hp.get(hurt_hero,0)<before and self.carry:
            self.carry-=1;self.loot.append(dict(pos=resolve_circle(self.pos+V(70,0),22,MAPS[self.map_key]['obstacles']),cooldown=1.4));self.floating('ВЫРОНИЛ КРИСТАЛЛ',self.pos-V(0,80),(255,172,143))

    def refill_loot(self):
        for p in [(160,260),(510,265),(740,515),(1120,290),(1020,550),(565,540)]:
            self.loot.append(dict(pos=resolve_circle(V(p),22,MAPS[self.map_key]['obstacles']),cooldown=.4))

    def next_room(self,path,map_key):
        self.room+=1;self.room_type=path;self.map_key=map_key;self.map_clock=0;self.hazard_cycle=-1
        self.route_history.append((path,map_key));self.route_pending=False;self.enemies=[];self.warnings=[];self.zones=[];self.bullets=[];self.objects=[];self.fields=[];self.orbs=[]
        self.pos=V(185,400);self.room_wait=.9;self.last_mode_spawn=9999;self.invulnerable=1.5
        self.banner=f'КОМНАТА {self.room} / 5 · '+MAPS[map_key]['name'];self.banner_time=2.4
        if path=='rest':
            for h in self.team:
                if self.hp[h]>0:self.hp[h]=min(self.profile.stats(h)['hp'],self.hp[h]+self.profile.stats(h)['hp']*.30)
        elif path=='elite':self.room_reward+=.35
        if self.room==5:self.spawn_photo_boss(self.boss_choice)
        else:
            count=4+self.room+(2 if path=='elite' else 0)
            for i in range(count):self.spawn(kind=('armored' if i%2==0 else 'ranged') if path=='elite' else random.choice(['slime','charger','ranged']))

    def offer_routes(self):
        self.route_pending=True;self.bullets=[];self.warnings=[];self.zones=[]
        maps=random.sample([k for k in MAPS if k!=self.map_key],2)
        perks=random.sample(list(PERKS),2)
        self.route_choices=[dict(path='rest',map=maps[0],perk=perks[0]),dict(path='elite',map=maps[1],perk=perks[1])]
        self.sound('route')

    def choose_route(self,index):
        if not self.route_pending or index not in (0,1):return False
        choice=self.route_choices[index];self.intermission=True;self.choices=[choice['perk']];self.choose_perk(choice['perk'])
        self.next_room(choice['path'],choice['map']);return True

    def finish(self,won):
        if self.done:return
        if not self.mode:return super().finish(won)
        self.done=True;self.won=won;self.stars=(1+int(self.mode_time<self.mode_limit*.8)+int(all(hp>0 for hp in self.hp.values()))) if won else 0
        self.result=self.profile.reward_activity(self.mode,won,self.kills,self.team,self.difficulty,self.mode_time,self.boss_choice,self.room_reward,self.skill_count,self.perfect_dodges)
        self.sound('win' if won else 'lose')

    def objective_text(self):
        if self.mode=='duel':return 'Победи поганца · '+str(max(0,int(self.mode_limit-self.mode_time)))+'с'
        if self.mode=='escort':return f'Тележка {int(self.cart_progress*100)}% · Прочность {int(self.core_hp/self.core_max*100)}% · '+('ОТОГОНИ ВРАГОВ' if self.cart_blocked else 'Стой рядом, чтобы ехать')
        if self.mode=='heist':return f'В руках {self.carry}/3 · В тайнике {self.deposited}/9 · '+('Иди к выходу справа' if self.deposited>=9 else 'Сдавай добычу слева')
        if self.mode=='capture':return f'Маяки: {sum(z["owned"] for z in self.beacons)} / 3 · Стой в круге, враги мешают захвату'
        if self.mode=='survival':return f'Осталось {max(0,math.ceil(90-self.mode_time))}с · Держись внутри безопасного круга'
        if self.mode=='expedition':return f'Комната {self.room} / 5 · Премия за риск +{int(self.room_reward*100)}%'
        return ''

    def update_map(self,dt):
        if not self.map_key:return
        self.map_clock+=dt;m=MAPS[self.map_key];cycle=int(self.map_clock/9)
        if m['hazard']=='fountain' and self.pos.distance_to(V(640,265))<58:
            self.hp[self.hero]=min(self.profile.stats(self.hero)['hp'],self.hp[self.hero]+dt*9)
        if cycle==self.hazard_cycle:return
        self.hazard_cycle=cycle
        if cycle==0:return
        hazard=m['hazard']
        if hazard=='train':self.warn('line',V(50,310),35,2.0,55,end=V(1230,310),train=True)
        elif hazard=='electric':
            for p in [(540,460),(740,285)] if cycle%2 else [(540,285),(740,460)]:self.warn('circle',p,88,1.6,35)
        elif hazard=='tide':self.warn('line',V(50,540),46,2.0,28,end=V(1230,540))
        elif hazard=='ice':
            for _ in range(2):self.warn('circle',V(random.randint(220,1100),random.randint(240,530)),75,1.8,32)
        elif hazard=='fire':
            x=180 if cycle%2 else 1100;self.warn('line',V(x,200),40,1.6,32,end=V(x,575))

    def update(self,dt,move=(0,0),mouse=(900,400),firing=False):
        if self.done or self.intermission or self.route_pending:return
        was_ice=self.map_key=='frost' and not self.training;input_move=V(move)
        if was_ice:
            desired=input_move.normalize()*self.profile.stats(self.hero)['speed']*self.speed if input_move.length_squared()>0 else V()
            self.ice_velocity=self.ice_velocity.lerp(desired,min(1,dt*3.2))
            if input_move.length_squared()>0:self.move=input_move.normalize()
            if self.dash_time<=0:self.pos+=self.ice_velocity*dt
            move=(0,0)
        super().update(dt,move,mouse,firing)
        if self.done or self.intermission:return
        self.clamp()
        if self.map_key:
            for e in self.enemies:
                old=V(e['pos']);e['pos']=resolve_circle(e['pos'],e['r'],MAPS[self.map_key]['obstacles'])
                if old!=e['pos'] and not e.get('boss_id'):
                    e['pos'].y+=(-1 if self.pos.y<e['pos'].y else 1)*dt*80
        self.update_map(dt);self.resolve_warnings(dt)
        if not self.mode or self.done:return
        self.mode_time+=dt;self.last_mode_spawn-=dt
        if self.mode=='duel':
            if not any(e.get('boss_id') for e in self.enemies):self.finish(True);return
        elif self.mode=='expedition':
            if not self.enemies:
                self.room_wait-=dt
                if self.room_wait<=0:
                    self.completed_waves=self.room
                    if self.room>=5:self.finish(True)
                    else:self.offer_routes()
        else:
            if self.last_mode_spawn<=0:
                self.last_mode_spawn=max(1.6,4.4-self.difficulty*.55-self.mode_time/110)
                if len(self.enemies)<12+self.difficulty*3:
                    self.spawn(kind=random.choice(['slime','charger','ranged','armored'] if self.mode_time>30 else ['slime','charger']))
            if self.mode=='escort':
                self.cart_blocked=any(e['pos'].distance_to(self.core_pos)<95 for e in self.enemies)
                if self.pos.distance_to(self.core_pos)<130 and not self.cart_blocked:self.cart_progress=min(1,self.cart_progress+dt/48)
                self.core_pos=V(220+860*self.cart_progress,400)
                if self.cart_progress>=1:self.finish(True)
            elif self.mode=='heist':
                for loot in self.loot[:]:
                    loot['cooldown']=max(0,loot['cooldown']-dt)
                    if self.carry<3 and loot['cooldown']==0 and loot['pos'].distance_to(self.pos)<34:
                        self.carry+=1;self.loot.remove(loot);self.sound('pickup')
                if self.pos.distance_to(V(140,400))<67 and self.carry:
                    self.deposit_timer+=dt
                    if self.deposit_timer>=1.2:
                        self.deposited+=self.carry;self.carry=0;self.deposit_timer=0;self.sound('deposit')
                        if self.deposited<9 and len(self.loot)<3:self.refill_loot()
                else:self.deposit_timer=0
                if self.deposited>=9:
                    if self.pos.distance_to(V(1130,490))<70:self.escape_timer+=dt
                    else:self.escape_timer=0
                    if self.escape_timer>=4:self.finish(True)
            elif self.mode=='capture':
                for z in self.beacons:
                    if z['owned']:continue
                    contested=any(e['pos'].distance_to(z['pos'])<80 for e in self.enemies)
                    if self.pos.distance_to(z['pos'])<72 and not contested:z['value']=min(100,z['value']+dt*12.5)
                    elif contested:z['value']=max(0,z['value']-dt*4)
                    if z['value']>=100:z['owned']=True;self.sound('capture');self.floating('МАЯК НАШ',z['pos']-V(0,40),(120,245,198),True)
                if all(z['owned'] for z in self.beacons):self.finish(True)
            elif self.mode=='survival':
                self.safe_center=V(640+math.sin(self.mode_time*.032)*230,395+math.sin(self.mode_time*.061)*52)
                self.safe_radius=max(105,260-self.mode_time*1.72)
                if self.pos.distance_to(self.safe_center)>self.safe_radius:self.hurt(13+self.difficulty*4)
                if self.mode_time>=90:self.finish(True)
        if not self.done and self.mode_time>=self.mode_limit:self.finish(False)
