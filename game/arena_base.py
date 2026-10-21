"""Real-time arena simulation, kept separate from menus and persistence."""
import math
import random
import pygame as pg
from model import HEROES

V=pg.Vector2
BOUNDS=pg.Rect(55,190,1170,390)

PERKS = {
    'power': ('Горячая голова', '+22% урона всем героям', 'АТАКА'),
    'haste': ('Быстрые руки', 'Атаки и перезарядка Q на 18% быстрее', 'ТЕМП'),
    'vampire': ('Второе дыхание', 'Попадания лечат на 4% урона', 'ЛЕЧЕНИЕ'),
    'frost': ('Холодный взгляд', 'Попадания замедляют врагов', 'КОНТРОЛЬ'),
    'pierce': ('Навылет', 'Снаряды пробивают ещё одну цель', 'ПРОБОЙ'),
    'energy': ('На взводе', '+35% получаемой энергии', 'УЛЬТИМЕЙТ'),
    'speed': ('Кроссы с рынка', '+18% бег; рывок быстрее готов', 'МОБИЛЬНОСТЬ'),
    'recovery': ('Привал у подъезда', 'Лечение 40%; один герой оживает', 'ПОДДЕРЖКА'),
    'armor': ('Крепкий характер', '-20% входящего урона', 'ЗАЩИТА'),
}

class Battle:
    def __init__(self,profile,stage,sound=lambda *a:None,endless=False):
        self.profile=profile; self.stage=stage; self.sound=sound
        self.team=list(profile.data['team']); self.active=0
        self.hp={h:float(profile.stats(h)['hp']) for h in self.team}
        self.energy={h:35.0 for h in self.team}; self.skills={h:0.0 for h in self.team}
        self.pos=V(640,410); self.aim=V(1,0); self.move=V(1,0)
        self.enemies=[]; self.bullets=[]; self.effects=[]; self.particles=[]; self.texts=[]; self.orbs=[]
        self.wave=0; self.next_wave=1.2; self.spawn_queue=0; self.spawn_cd=0
        self.kills=0; self.elapsed=0; self.attack_cd=0; self.dash_cd=0; self.dash_time=0
        self.invulnerable=1.5; self.shield=0; self.switch_cd=0; self.combo=0; self.combo_time=0
        self.banner='РАЗЛОМ ОТКРЫТ'; self.banner_time=2.3; self.cutin=0; self.shake=0
        self.done=False; self.won=False; self.result=None
        self.endless=endless;self.completed_waves=0;self.intermission=False;self.choices=[];self.perks=[]
        self.power=1.0;self.haste=1.0;self.speed=1.0;self.armor=1.0;self.lifesteal=0;self.piercing=0;self.energy_gain=1.0;self.frost=False
        self.attack_chain=0;self.skill_count=0;self.perfect_dodges=0;self.slow_time=0;self.uid=0
        self.zones=[];self.zone_tick=0;self.stars=0;self.max_combo=0
        self.objective='survive' if endless else 'defend' if stage in (2,5) else 'anchors' if stage in (3,6) else 'clear'
        self.core_pos=V(640,385);self.core_max=650+stage*85;self.core_hp=float(self.core_max);self.core_cooldown=0
        self.anchors_destroyed=0;self.boss_name={1:'ГРОМИЛА',2:'НАБЛЮДАТЕЛЬ',0:'ПОЖИРАТЕЛЬ'}[stage%3]

    def choose_perk(self,key):
        if not self.intermission or key not in self.choices:return False
        self.perks.append(key)
        if key=='power':self.power+=.22
        elif key=='haste':self.haste+=.18
        elif key=='vampire':self.lifesteal+=.04
        elif key=='frost':self.frost=True
        elif key=='pierce':self.piercing+=1
        elif key=='energy':self.energy_gain+=.35
        elif key=='speed':self.speed+=.18
        elif key=='armor':self.armor*=.8
        elif key=='recovery':
            revived=False
            for h in self.team:
                if self.hp[h]<=0:
                    if revived:continue
                    revived=True
                self.hp[h]=min(self.profile.stats(h)['hp'],self.hp[h]+self.profile.stats(h)['hp']*.4)
            self.core_hp=min(self.core_max,self.core_hp+self.core_max*.2)
        self.intermission=False;self.choices=[];self.next_wave=.8;self.sound('rare')
        self.invulnerable=max(self.invulnerable,1.2)
        return True

    def offer_perks(self):
        pool=[key for key in PERKS if key!='frost' or not self.frost]
        self.choices=random.sample(pool,3);self.intermission=True
        self.bullets.clear();self.zones.clear();self.orbs.clear()
        for h in self.team:
            if self.hp[h]>0:self.hp[h]=min(self.profile.stats(h)['hp'],self.hp[h]+self.profile.stats(h)['hp']*.12)
        self.sound('rare')

    def add_zone(self,pos,radius,life,damage,color,enemy=False):
        self.zones.append(dict(pos=V(pos),radius=radius,life=life,damage=damage,color=color,enemy=enemy,owner=self.hero))

    def hurt_core(self,damage):
        if self.objective!='defend' or self.core_cooldown>0 or self.done:return
        self.core_hp=max(0,self.core_hp-damage);self.core_cooldown=.4
        self.floating('-'+str(int(damage)),self.core_pos-V(0,65),(255,115,134))
        if self.core_hp<=0:self.finish(False)

    @property
    def hero(self): return self.team[self.active]

    def floating(self,text,pos,color=(255,255,255),big=False):
        self.texts.append(dict(text=str(text),pos=V(pos),life=0.85,color=color,big=big))

    def burst(self,pos,color,n=14):
        for _ in range(n):
            angle=random.random()*math.tau; speed=random.uniform(45,210)
            self.particles.append(dict(pos=V(pos),vel=V(math.cos(angle),math.sin(angle))*speed,life=random.uniform(.2,.6),color=color))

    def ring(self,pos,radius,color):
        self.effects.append(dict(pos=V(pos),radius=radius,color=color,life=.5))

    def switch(self,slot):
        if self.done or self.intermission or self.switch_cd>0 or not 0<=slot<len(self.team) or slot==self.active or self.hp[self.team[slot]]<=0: return
        self.active=slot; self.switch_cd=2.4; self.invulnerable=max(.65,self.invulnerable)
        self.burst(self.pos,HEROES[self.hero]['color'],24); self.sound('switch'); self.floating('СМЕНА · '+HEROES[self.hero]['name'],self.pos-V(0,80))
        self.aoe(self.pos,135,self.profile.stats(self.hero)['atk']*1.6,HEROES[self.hero]['color'])

    def dash(self):
        if self.done or self.intermission or self.dash_cd>0: return
        danger=any(b['enemy'] and b['pos'].distance_to(self.pos)<95 for b in self.bullets) or any(e['telegraph']>0 and e['telegraph']<.45 and e['target'].distance_to(self.pos)<110 for e in self.enemies)
        if danger:
            self.slow_time=.85;self.perfect_dodges+=1;self.energy[self.hero]=min(100,self.energy[self.hero]+18)
            self.floating('ИДЕАЛЬНО!',self.pos-V(0,95),(255,224,130),True);self.sound('dodge')
        self.dash_cd=1.65/self.speed; self.dash_time=.19; self.invulnerable=max(self.invulnerable,.38)
        self.ring(self.pos,65,HEROES[self.hero]['color']); self.sound('dash')

    def shoot(self,pos,direction,damage,speed=580,color=None,enemy=False,size=6,pierce=0):
        direction=V(direction)
        if direction.length_squared()<.01: direction=V(1,0)
        self.bullets.append(dict(pos=V(pos),vel=direction.normalize()*speed,damage=damage,life=1.6 if not enemy else 5,
                                 color=color or HEROES[self.hero]['color'],enemy=enemy,size=size,pierce=pierce+(self.piercing if not enemy else 0),hit=set(),owner=self.hero))

    def attack(self,mouse):
        if self.done or self.intermission or self.attack_cd>0: return
        d=V(mouse)-self.pos
        if d.length_squared()>1: self.aim=d.normalize()
        h=HEROES[self.hero]; stats=self.profile.stats(self.hero)
        self.attack_chain+=1;finisher=self.attack_chain%3==0
        self.attack_cd=(.27 if h['style'] in ('shot','fan') else .36)/self.haste
        damage=stats['atk']*(1.8 if finisher else 1)
        self.sound('slash' if h['style']=='shadow' else h['style'])
        if h['style'] in ('slash','shadow'):
            # Long crescent projectile keeps melee heroes usable against ranged enemies.
            self.shoot(self.pos,self.aim,damage*1.15,640,size=21 if finisher else 17,pierce=1)
            self.ring(self.pos+self.aim*40,60,h['color'])
        else: self.shoot(self.pos,self.aim,damage,700 if h['style']=='shot' else 550,size=12 if finisher else 8)
        if finisher:self.ring(self.pos+self.aim*30,36,h['color'])
        self.burst(self.pos+self.aim*23,h['color'],3)

    def aoe(self,pos,radius,damage,color):
        self.ring(pos,radius,color)
        for e in self.enemies[:]:
            if e['pos'].distance_to(pos)<radius+e['r']: self.hit(e,damage,self.hero)

    def skill(self):
        if self.done or self.intermission or self.skills[self.hero]>0: return
        h=HEROES[self.hero]; atk=self.profile.stats(self.hero)['atk']; style=h['style']; color=h['color']
        self.skills[self.hero]=7.0/self.haste; self.sound(h['style']);self.skill_count+=1
        if style=='heal':
            for hero in self.team:
                if self.hp[hero]>0: self.hp[hero]=min(self.profile.stats(hero)['hp'],self.hp[hero]+self.profile.stats(hero)['hp']*.27)
            self.ring(self.pos,220,color); self.floating('+27% ОТРЯДУ',self.pos-V(0,75),color,True)
            self.aoe(self.pos,210,atk*2,color)
        elif style=='guard':
            self.shield=4; self.aoe(self.pos,200,atk*2.5,color); self.floating('ЩИТ · 4 СЕК',self.pos-V(0,75),color)
        elif style in ('slash','shadow'):
            if style=='shadow':
                self.pos+=self.aim*125; self.clamp(); self.invulnerable=.8
            self.aoe(self.pos,240,atk*3.3,color); self.shake=.2
        elif style=='wave':
            self.aoe(self.pos,280,atk*2.6,color)
            for e in self.enemies: e['stun']=2
        elif style=='smile':
            self.aoe(self.pos,310,atk*2.8,color)
            for e in self.enemies:
                if e['pos'].distance_to(self.pos)<330:e['stun']=2.8
            self.shield=1.5
        else:
            count=7 if style=='fan' else 3
            for j in range(count):
                direction=self.aim.rotate((j-(count-1)/2)*13)
                self.shoot(self.pos,direction,atk*2.2,650,size=14,pierce=2)
        self.energy[self.hero]=min(100,self.energy[self.hero]+8)

    def ultimate(self):
        if self.done or self.intermission or self.energy[self.hero]<100: return
        self.energy[self.hero]=0; self.cutin=1.4; self.invulnerable=1.6; self.shake=.5
        h=HEROES[self.hero]; color=h['color']; atk=self.profile.stats(self.hero)['atk']; self.sound('ultimate')
        style=h['style'];self.aoe(self.pos,1300,atk*(3.0 if style in ('spit','heal') else 5.3),color)
        if style=='spit':
            for pos in [self.pos]+[e['pos'] for e in self.enemies[:6]]:self.add_zone(pos,115,5,atk*.65,color)
        elif style in ('wave','smile'):
            for e in self.enemies:e['stun']=3.5
            if style=='smile':self.sound('artem_voice')
            self.bullets=[b for b in self.bullets if not b['enemy']]
        elif style=='guard':self.shield=9
        elif style=='shadow':self.invulnerable=3.5
        elif style=='shot':
            for e in self.enemies[:]:self.shoot(self.pos,e['pos']-self.pos,atk*3,850,size=10,pierce=4)
        for angle in range(0,360,12 if style=='fan' else 30): self.shoot(self.pos,V(1,0).rotate(angle),atk*1.5,450,size=12,pierce=3)
        if h['style']=='heal':
            for hero in self.team:
                if self.hp[hero]>0:self.hp[hero]=min(self.profile.stats(hero)['hp'],self.hp[hero]+self.profile.stats(hero)['hp']*.4)
        self.burst(self.pos,color,65)

    def hit(self,e,damage,owner):
        if e not in self.enemies: return
        crit=random.random()<.13; damage=round(damage*self.power*(1.65 if crit else 1))
        if e.get('armor',0)>0:
            e['armor']-=damage
            if e['armor']<=0:self.sound('break');e['stun']=1.8;self.floating('БРОНЯ СЛОМАНА',e['pos']-V(0,85),(255,205,110))
            damage=round(damage*.5)
        e['hp']-=damage; e['flash']=.11
        if self.frost:e['slow']=2
        if self.lifesteal and self.hp[owner]>0:self.hp[owner]=min(self.profile.stats(owner)['hp'],self.hp[owner]+damage*self.lifesteal)
        self.energy[owner]=min(100,self.energy[owner]+(2 if e['kind']=='boss' else 3)*self.energy_gain)
        self.sound('crit' if crit else 'impact')
        self.floating(str(damage)+('!' if crit else ''),e['pos']+V(random.randint(-15,15),-e['r']-25),(255,205,110) if crit else (235,242,255),crit)
        self.burst(e['pos'],HEROES[owner]['color'],5)
        if e['hp']<=0:
            self.enemies.remove(e); self.kills+=1; self.combo+=1; self.combo_time=4
            self.max_combo=max(self.max_combo,self.combo)
            if e['kind']=='anchor':self.anchors_destroyed+=1;self.sound('break')
            self.burst(e['pos'],e['color'],20)
            self.energy[owner]=min(100,self.energy[owner]+7)
            if random.random()<.32 or e['kind']=='boss': self.orbs.append(dict(pos=V(e['pos']),life=15))

    def hurt(self,damage):
        if self.invulnerable>0 or self.done:return
        damage*=self.armor
        if self.shield>0: damage*=.25
        self.hp[self.hero]=max(0,self.hp[self.hero]-damage); self.invulnerable=.65; self.shake=.18
        self.floating('-'+str(round(damage)),self.pos-V(0,70),(255,115,134),True); self.sound('hit')
        if self.hp[self.hero]<=0:
            available=[i for i,h in enumerate(self.team) if self.hp[h]>0]
            if available:
                self.active=available[0]; self.invulnerable=1.8
                self.banner='В БОЙ ВСТУПАЕТ '+HEROES[self.hero]['name'].upper(); self.banner_time=1.8
            else: self.finish(False)

    def finish(self,won):
        if self.done:return
        self.done=True; self.won=won
        self.stars=(1+int(self.elapsed<180)+int(all(hp>0 for hp in self.hp.values()))) if won and not self.endless else 0
        self.result=self.profile.reward(self.stage,won,self.kills,self.team,endless=self.endless,waves=self.completed_waves,stars=self.stars,skills=self.skill_count,dodges=self.perfect_dodges)
        self.sound('win' if won else 'lose')

    def spawn(self,boss=False,kind=None,pos=None):
        side=random.randrange(4)
        pos=V(pos) if pos is not None else V(random.randint(70,1210),200 if side==0 else 565) if side<2 else V(65 if side==2 else 1210,random.randint(220,560))
        if pos.distance_to(self.pos)<220: pos=V(1210-self.pos.x+55,220 if self.pos.y>390 else 555)
        pool=['slime','slime','ranged','charger'] if self.wave>1 else ['slime','charger']
        if self.stage>=2 or self.wave>=3:pool+=['armored','summoner']
        kind='boss' if boss else kind or random.choice(pool)
        scale=(1+.30*(self.stage-1))*(1+max(0,self.wave-3)*.18 if self.endless else 1)
        hp={'slime':65,'ranged':55,'charger':90,'boss':850,'armored':140,'summoner':110,'anchor':240}[kind]*scale*(1+.10*min(4,self.wave-1))
        self.uid+=1
        self.enemies.append(dict(pos=pos,kind=kind,hp=hp,maxhp=hp,r=46 if boss else 32 if kind=='anchor' else 22,
                                 speed={'slime':80,'ranged':64,'charger':110,'boss':53,'armored':57,'summoner':42,'anchor':0}[kind]+(self.stage*4 if kind!='anchor' else 0),
                                 cooldown=random.uniform(1,2),telegraph=0,target=V(self.pos),stun=0,flash=0,slow=0,uid=self.uid,
                                 armor=80*scale if kind=='armored' else 0,enraged=False,attack_number=0,
                                 color={'slime':(133,105,230),'ranged':(226,92,149),'charger':(247,156,93),'boss':(240,89,135),'armored':(155,180,214),'summoner':(142,234,174),'anchor':(198,117,255)}[kind]))
        self.ring(pos,80,(126,92,212))
        if boss:self.sound('boss'); self.banner=self.boss_name+' · ХОЗЯИН РАЗЛОМА';self.banner_time=2.5

    def clamp(self):
        self.pos.x=max(BOUNDS.left,min(BOUNDS.right,self.pos.x));self.pos.y=max(BOUNDS.top,min(BOUNDS.bottom,self.pos.y))

    def update(self,dt,move=(0,0),mouse=(900,400),firing=False):
        if self.done or self.intermission:return
        self.elapsed+=dt; self.cutin=max(0,self.cutin-dt)
        if self.cutin>0:dt*=.3
        self.slow_time=max(0,self.slow_time-dt)
        if self.slow_time>0:dt*=.45
        self.core_cooldown=max(0,self.core_cooldown-dt)
        for key in ('attack_cd','dash_cd','invulnerable','shield','switch_cd','combo_time','banner_time','shake'):
            setattr(self,key,max(0,getattr(self,key)-dt))
        if self.combo_time==0:self.combo=0
        for h in self.team:
            self.skills[h]=max(0,self.skills[h]-dt)
            self.energy[h]=min(100,self.energy[h]+dt*.8)
        motion=V(move)
        if motion.length_squared()>0:
            motion=motion.normalize(); self.move=motion
        if self.dash_time>0:
            self.dash_time-=dt;self.pos+=self.move*950*dt;self.burst(self.pos,HEROES[self.hero]['color'],2)
        else:self.pos+=motion*self.profile.stats(self.hero)['speed']*self.speed*dt
        self.clamp()
        direction=V(mouse)-self.pos
        if direction.length_squared()>2:self.aim=direction.normalize()
        if firing:self.attack(mouse)
        if getattr(self,'allow_waves',True) and not self.enemies and self.spawn_queue==0:
            self.next_wave-=dt
            if self.next_wave<=0:
                if self.wave>self.completed_waves:
                    self.completed_waves=self.wave
                    if self.wave==3 and not self.endless:self.finish(True);return
                    self.offer_perks();return
                self.wave+=1;self.spawn_queue=4+min(8,self.wave)*2;self.next_wave=1.5
                self.banner=f'ВОЛНА {self.wave}'+(' / 3' if not self.endless else ' · БЕСКОНЕЧНАЯ АРЕНА');self.banner_time=1.8;self.sound('telegraph')
                if self.wave%3==0:self.spawn(boss=True)
                if self.objective=='anchors':self.spawn(kind='anchor',pos=(320 if self.wave%2 else 960,320))
        if self.spawn_queue:
            self.spawn_cd-=dt
            if self.spawn_cd<=0:self.spawn();self.spawn_queue-=1;self.spawn_cd=.65
        for e in self.enemies[:]:
            if e.get('boss_id') and hasattr(self,'update_boss'):
                self.update_boss(e,dt);continue
            e['flash']=max(0,e['flash']-dt);e['stun']=max(0,e['stun']-dt);e['slow']=max(0,e['slow']-dt)
            if e['stun']>0:continue
            target=self.core_pos if self.objective=='defend' and e['uid']%3==0 else self.pos
            delta=target-e['pos'];dist=delta.length();direction=delta.normalize() if dist>0 else V(1,0)
            speed=e['speed']*(.55 if e['slow']>0 else 1)
            e['cooldown']-=dt
            if e['telegraph']>0:
                e['telegraph']-=dt
                if e['telegraph']<=0:
                    if e['kind']=='boss':
                        self.ring(e['target'],105,e['color'])
                        if self.pos.distance_to(e['target'])<105:self.hurt(42+self.stage*7)
                        if self.core_pos.distance_to(e['target'])<105:self.hurt_core(35+self.stage*5)
                        for angle in range(0,360,24 if e['enraged'] else 40):self.shoot(e['pos'],V(1,0).rotate(angle+e['attack_number']*13),18+self.stage*4,190 if e['enraged'] else 160,e['color'],True,9)
                        if self.stage%3==0:self.add_zone(e['target'],90,4,14+self.stage*2,e['color'],True)
                    else:
                        rush=e['target']-e['pos']
                        if rush.length()>0:e['pos']+=rush.normalize()*min(170,rush.length())
                        self.ring(e['pos'],50,e['color'])
                        if self.pos.distance_to(e['pos'])<65:self.hurt(20+self.stage*4)
                        if self.core_pos.distance_to(e['pos'])<65:self.hurt_core(20+self.stage*4)
                continue
            kind=e['kind']
            if kind=='boss' and e['hp']<e['maxhp']*.5 and not e['enraged']:
                e['enraged']=True;self.banner=self.boss_name+' · ЯРОСТЬ';self.banner_time=2;self.sound('boss')
                self.spawn(kind='ranged');self.spawn(kind='armored')
            if kind in ('anchor','summoner'):
                if e['cooldown']<=0:
                    if kind=='summoner' and len(self.enemies)<20:
                        self.spawn(kind='slime',pos=e['pos']+V(35,20));self.spawn(kind='slime',pos=e['pos']-V(35,20));self.sound('enemy')
                    else:
                        for angle in range(0,360,90):self.shoot(e['pos'],V(1,0).rotate(angle),15,145,e['color'],True,8)
                    e['cooldown']=6 if kind=='summoner' else 3.5
                if kind=='summoner' and dist>300:e['pos']+=direction*speed*dt
                continue
            if kind=='ranged':
                if dist>350:e['pos']+=direction*speed*dt
                elif dist<200:e['pos']-=direction*speed*.5*dt
                if e['cooldown']<=0:
                    self.shoot(e['pos'],direction,15+self.stage*3,220,e['color'],True,8);e['cooldown']=2.2;self.sound('enemy')
            else:
                if dist>e['r']+22:e['pos']+=direction*speed*dt
                if kind in ('boss','charger') and e['cooldown']<=0:
                    e['telegraph']=.85 if kind=='boss' and e['enraged'] else 1.05 if kind=='boss' else .7;e['target']=V(target);e['cooldown']=2.8 if e['enraged'] else 3.8 if kind=='boss' else 3;e['attack_number']+=1
                if self.pos.distance_to(e['pos'])<e['r']+23:self.hurt((20 if kind=='boss' else 10)+self.stage*3)
                if self.core_pos.distance_to(e['pos'])<e['r']+24:self.hurt_core((15 if kind=='boss' else 8)+self.stage*2)
            e['pos'].x=max(45,min(1235,e['pos'].x));e['pos'].y=max(185,min(585,e['pos'].y))
        for bullet in self.bullets[:]:
            bullet['pos']+=bullet['vel']*dt;bullet['life']-=dt
            if hasattr(self,'projectile_blocked') and self.projectile_blocked(bullet):
                self.bullets.remove(bullet);continue
            if bullet['enemy']:
                if bullet['pos'].distance_to(self.pos)<bullet['size']+23:
                    self.hurt(bullet['damage']);bullet['life']=0
                elif self.objective=='defend' and bullet['pos'].distance_to(self.core_pos)<bullet['size']+28:
                    self.hurt_core(bullet['damage']);bullet['life']=0
            else:
                for e in self.enemies[:]:
                    if e['uid'] not in bullet['hit'] and bullet['pos'].distance_to(e['pos'])<e['r']+bullet['size']:
                        bullet['hit'].add(e['uid']);self.hit(e,bullet['damage'],bullet['owner']);bullet['pierce']-=1
                        if bullet['pierce']<0:bullet['life']=0;break
            if bullet['life']<=0:self.bullets.remove(bullet)
        for orb in self.orbs[:]:
            orb['life']-=dt;d=self.pos-orb['pos']
            if 1<d.length()<130:orb['pos']+=d.normalize()*260*dt
            if d.length()<28:
                amount=round(self.profile.stats(self.hero)['hp']*.12)
                self.hp[self.hero]=min(self.profile.stats(self.hero)['hp'],self.hp[self.hero]+amount)
                self.floating('+'+str(amount),self.pos-V(0,65),(137,245,190));orb['life']=0;self.sound('pickup')
            if orb['life']<=0:self.orbs.remove(orb)
        self.zone_tick-=dt;tick=self.zone_tick<=0
        if tick:self.zone_tick=.5
        for zone in self.zones[:]:
            zone['life']-=dt
            if tick:
                if zone['enemy']:
                    if self.pos.distance_to(zone['pos'])<zone['radius']:self.hurt(zone['damage'])
                    if self.core_pos.distance_to(zone['pos'])<zone['radius']:self.hurt_core(zone['damage'])
                else:
                    for e in self.enemies[:]:
                        if e['pos'].distance_to(zone['pos'])<zone['radius']:self.hit(e,zone['damage'],zone['owner'])
            if zone['life']<=0:self.zones.remove(zone)
        for group in (self.particles,self.texts,self.effects):
            for item in group[:]:
                item['life']-=dt
                if 'vel' in item:item['pos']+=item['vel']*dt;item['vel']*=max(0,1-dt*4)
                if 'text' in item:item['pos'].y-=48*dt
                if item['life']<=0:group.remove(item)
