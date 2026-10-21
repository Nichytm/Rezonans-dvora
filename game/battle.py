"""Version 0.3: each hero has its own combat mechanics and animations."""
import math
import random
import pygame as pg
from arena_base import Battle as ArenaBattle,PERKS,BOUNDS,V
from model import HEROES

class Battle(ArenaBattle):
    def __init__(self,profile,stage,sound=lambda *args:None,endless=False,training=False):
        super().__init__(profile,stage,sound,endless)
        self.training=training;self.fx=[];self.objects=[];self.fields=[];self.stances={};self.ammo={h:6 for h in HEROES};self.reloads={h:0 for h in HEROES}
        self.anim=0;self.anim_kind='';self.anim_dir=V(1,0);self.anim_phase=0;self.swing_chain={h:0 for h in HEROES}
        self.mouse=V(900,400);self.execution=[];self.execute_cd=0;self.reticle=None;self.reticle_time=0
        self.dot_tick=False;self.total_damage=0;self.damage_tick=0;self.hits_landed=0;self.parry=0;self.training_index=0
        self.combo_timer=0;self.feedback='';self.feedback_time=0
        relic=profile.data['equipped_relic']
        if relic=='brick':self.power+=.15
        if relic=='watch':self.haste+=.20
        if training:self.set_training_hero('bugdan')

    def set_training_hero(self,h):
        if not self.training:return
        self.team=[h];self.active=0;self.hp={h:float(self.profile.stats(h)['hp'])};self.energy={h:100.};self.skills={h:0.}
        self.training_index=list(HEROES).index(h);self.enemies=[];self.bullets=[];self.objects=[];self.fields=[];self.fx=[];self.stances={};self.execution=[];self.reticle=None
        self.done=False;self.wave=1;self.next_wave=100000;self.spawn_queue=0;self.pos=V(440,405);self.invulnerable=1
        self.attack_cd=0;self.dash_cd=0;self.dash_time=0;self.shield=0;self.parry=0;self.cutin=0;self.ammo[h]=6;self.reloads[h]=0
        self.texts=[];self.effects=[];self.particles=[];self.orbs=[];self.zones=[];self.combo=0;self.combo_time=0;self.hits_landed=0
        self.training_targets();self.total_damage=0;self.elapsed=0

    def training_targets(self):
        for pos in [(700,305),(890,340),(770,485)]:
            self.spawn(kind='slime',pos=pos)
            e=self.enemies[-1];e['pos']=V(pos);e['hp']=e['maxhp']=100000;e['dummy']=True
        self.banner='ТРЕНИРОВКА · ВСЕ ГЕРОИ ДОСТУПНЫ';self.banner_time=2

    def training_cycle(self,delta):self.set_training_hero(list(HEROES)[(self.training_index+delta)%len(HEROES)])

    def finish(self,won):
        if self.training:
            self.done=True;self.won=won;self.result=dict(crystals=0,gold=0,essence=0,xp=0,first=False,levels=[]);return
        super().finish(won)

    def effect(self,kind,pos=None,life=.3,**data):
        self.fx.append(dict(kind=kind,pos=V(self.pos if pos is None else pos),life=life,total=life,color=data.pop('color',HEROES[self.hero]['color']),**data))

    def animate(self,kind,life=.24):
        self.anim=life;self.anim_kind=kind;self.anim_dir=V(self.aim);self.anim_phase=self.swing_chain[self.hero]

    def target_near_mouse(self,radius=650):
        targets=[e for e in self.enemies if e['pos'].distance_to(self.pos)<radius]
        return min(targets,key=lambda e:e['pos'].distance_to(self.mouse)) if targets else None

    def melee(self,reach,angle,damage,kind='slash',push=35,origin=None):
        pos=V(self.pos if origin is None else origin);facing=V(self.aim)
        self.effect(kind,pos,.26,reach=reach,direction=facing,arc=angle,phase=self.anim_phase)
        for e in self.enemies[:]:
            delta=e['pos']-pos;distance=delta.length()
            if distance<reach+e['r'] and (distance<25 or facing.dot(delta.normalize())>=math.cos(math.radians(angle/2))):
                self.hit(e,damage,self.hero)
                if e in self.enemies and not e.get('dummy'):
                    e['pos']+=facing*push;e['stun']=max(e['stun'],.22)
        self.shake=max(self.shake,.055)

    def line_hit(self,start,end,width,damage,pierce=False,kind='beam',owner=None):
        start=V(start);end=V(end);delta=end-start;length=delta.length()
        if length<1:return
        direction=delta/length;targets=[]
        for e in self.enemies:
            projected=(e['pos']-start).dot(direction)
            if 0<=projected<=length and (e['pos']-(start+direction*projected)).length()<width+e['r']:targets.append((projected,e))
        targets.sort(key=lambda item:item[0])
        if not pierce:targets=targets[:1]
        if targets and not pierce:end=V(targets[0][1]['pos'])
        self.effect(kind,start,.22,end=end,width=width)
        for _,e in targets:self.hit(e,damage,owner or self.hero)

    def add_boomerang(self,direction,damage):
        self.objects.append(dict(kind='boomerang',pos=V(self.pos),vel=V(direction)*580,age=0.,life=1.55,damage=damage,owner=self.hero,hit=set(),phase=0))

    def add_bomb(self,target,damage,pixel=False):
        d=V(target)-self.pos
        if d.length()>420:d.scale_to_length(420)
        self.objects.append(dict(kind='cube' if pixel else 'bread',pos=V(self.pos),start=V(self.pos),end=self.pos+d,age=0.,life=.72,damage=damage,owner=self.hero))

    def reload(self):
        h=self.hero
        if HEROES[h]['style']=='shot' and self.reloads[h]<=0 and self.ammo[h]<6:
            self.reloads[h]=1.25;self.sound('reload');self.floating('ПЕРЕЗАРЯДКА',self.pos-V(0,100),HEROES[h]['color'])

    def attack(self,mouse):
        if self.done or self.intermission or self.attack_cd>0:return
        self.mouse=V(mouse);d=self.mouse-self.pos
        if d.length_squared()>1:self.aim=d.normalize()
        h=self.hero;hero=HEROES[h];style=hero['style'];atk=self.profile.stats(h)['atk'];boost=self.stances.get(h,0)>0
        if style=='shot':
            if self.reloads[h]>0:return
            if self.ammo[h]<=0:self.reload();return
        self.swing_chain[h]=(self.swing_chain[h]+1)%3;finisher=self.swing_chain[h]==0
        self.attack_chain+=1;self.animate(style);self.combo_timer=1.5
        self.sound('voice:'+h+':attack')
        cooldown={'spit':.42,'slash':.40,'heal':.82,'shot':.46,'wave':.65,'fan':.72,'guard':.57,'shadow':.27,'smile':.62,'brawler':.52,'engineer':.85}[style]
        self.attack_cd=cooldown/self.haste/(1.45 if boost and style=='slash' else 1)
        damage=atk*(1.65 if finisher else 1)
        if style=='spit':
            self.shoot(self.pos,self.aim,damage,600,size=9 if not finisher else 14)
            self.bullets[-1]['kind']='spit';self.effect('spit_mouth',self.pos,.30,direction=V(self.aim));self.sound('spit')
        elif style=='slash':
            self.pos+=self.aim*(23 if not finisher else 37);self.clamp()
            self.melee(180 if boost else 123,165 if finisher else 115,damage*(2.1 if boost else 1.7),'slash',55)
            self.sound('sword')
        elif style=='shadow':
            self.melee(96,100,damage*1.5,'dagger',18);self.sound('dagger')
        elif style=='brawler':
            self.pos+=self.aim*18;self.clamp();self.melee(195 if boost else 102,130 if finisher else 85,damage*(2.6 if boost else 2),'punch',110 if finisher else 42)
            self.sound('heavy' if finisher else 'punch')
        elif style=='guard':
            self.melee(112,135,damage*1.8,'shield_bash',72);self.shield=max(self.shield,.35);self.sound('metal')
        elif style=='shot':
            self.ammo[h]-=1;self.line_hit(self.pos,self.pos+self.aim*850,7,damage*1.9);self.effect('muzzle',self.pos+self.aim*40,.16,direction=V(self.aim));self.sound('shot')
            if self.ammo[h]==0:self.reload()
        elif style=='heal':self.add_bomb(self.mouse,damage*2.2);self.sound('throw')
        elif style=='engineer':self.add_bomb(self.mouse,damage*2.4,True);self.sound('throw')
        elif style=='fan':self.add_boomerang(self.aim,damage*1.5);self.sound('throw')
        elif style=='wave':
            self.melee(255,85,damage*1.65,'sonic',72);self.sound('wave')
        elif style=='smile':
            targets=sorted((e for e in self.enemies if e['pos'].distance_to(self.pos)<390),key=lambda e:e['pos'].distance_to(self.mouse))
            start=V(self.pos)
            for i,e in enumerate(targets[:3]):
                self.effect('lightning',start,.30,end=V(e['pos']),width=4);self.hit(e,damage*(1.35-.2*i),h);start=V(e['pos'])
            if not targets:self.effect('lightning',self.pos,.20,end=self.pos+self.aim*230,width=3)
            self.sound('smile')

    def skill(self):
        if self.done or self.intermission or self.skills[self.hero]>0:return
        h=self.hero;style=HEROES[h]['style'];atk=self.profile.stats(h)['atk'];col=HEROES[h]['color']
        self.skill_count+=1;self.skills[h]=7/self.haste;self.animate(style,.4);self.sound('voice:'+h+':skill')
        if style=='spit':
            for angle in (-17,0,17):
                self.shoot(self.pos,self.aim.rotate(angle),atk*2.2,590,size=17,pierce=1);self.bullets[-1]['kind']='spit'
            self.effect('spit_mouth',self.pos,.55,direction=V(self.aim));self.sound('spit')
        elif style=='slash':
            start=V(self.pos);self.pos+=self.aim*245;self.clamp();self.line_hit(start,self.pos,55,atk*4,True,'cut');self.invulnerable=.6;self.sound('sword')
        elif style=='shadow':
            target=self.target_near_mouse()
            if target:
                start=V(self.pos);self.pos=target['pos']-self.aim*52;self.clamp();self.effect('shadow_trail',start,.40,end=V(self.pos),width=4);self.hit(target,atk*5,h);target['stun']=1.2
            self.invulnerable=1.0;self.sound('dagger')
        elif style=='brawler':
            self.effect('slam',self.pos,.6,reach=195);self.sound('heavy');self.shake=.3
            for e in self.enemies[:]:
                delta=e['pos']-self.pos
                if delta.length()<210:
                    self.hit(e,atk*3.8,h);e['stun']=1.3
                    if delta.length()>1 and not e.get('dummy'):e['pos']+=delta.normalize()*110
        elif style=='guard':self.parry=2.8;self.shield=2.8;self.effect('shield',self.pos,.5,reach=92);self.sound('metal')
        elif style=='shot':self.line_hit(self.pos,self.pos+self.aim*1200,22,atk*4,True);self.sound('shot')
        elif style=='heal':
            self.fields.append(dict(kind='heal',pos=V(self.pos),radius=165,life=6,tick=0,owner=h));self.sound('heal')
        elif style=='fan':
            for angle in (-30,0,30):self.add_boomerang(self.aim.rotate(angle),atk*2)
            self.sound('throw')
        elif style=='wave':
            self.melee(330,150,atk*3,'sonic',120)
            for e in self.enemies:
                if e['pos'].distance_to(self.pos)<330:e['stun']=2
            self.sound('wave')
        elif style=='smile':
            self.effect('flash',self.pos,.5,reach=330)
            for e in self.enemies:
                if e['pos'].distance_to(self.pos)<330:e['stun']=3;e['weak']=5
            self.energy[h]=min(100,self.energy[h]+15);self.sound('smile')
        elif style=='engineer':
            target=self.mouse-self.pos
            if target.length()>200:target.scale_to_length(200)
            self.objects.append(dict(kind='turret',pos=self.pos+target,age=0.,life=12,damage=atk*1.2,owner=h,tick=.2));self.sound('metal')
        self.energy[h]=min(100,self.energy[h]+8)

    def ultimate(self):
        if self.done or self.intermission or self.energy[self.hero]<100:return
        h=self.hero;style=HEROES[h]['style'];atk=self.profile.stats(h)['atk']
        self.energy[h]=0;self.cutin=.70;self.invulnerable=max(1,self.invulnerable);self.animate(style,.45)
        self.sound('voice:'+h+':ultimate');self.sound('ultimate');self.shake=.16
        if style=='spit':
            self.fields.append(dict(kind='rain',pos=V(self.mouse),radius=255,life=6,tick=0,owner=h));self.effect('heart',self.pos,1.2,reach=180)
        elif style=='slash':self.stances[h]=8;self.skills[h]=0;self.effect('bankai',self.pos,1,reach=200)
        elif style=='shadow':
            self.execution=[e['uid'] for e in sorted(self.enemies,key=lambda e:e['hp'])[:6]];self.execute_cd=0;self.invulnerable=2.8
        elif style=='brawler':self.stances[h]=9;self.hp[h]=min(self.profile.stats(h)['hp'],self.hp[h]+self.profile.stats(h)['hp']*.3);self.shield=9;self.effect('slam',self.pos,.8,reach=230)
        elif style=='shot':
            self.reticle=V(self.mouse);self.reticle_time=1.4;self.feedback='НАВЕДИ ПРИЦЕЛ · ЛУЧ ЧЕРЕЗ 1,4 СЕК';self.feedback_time=1.4
        elif style=='heal':
            revived=False
            for hero in self.team:
                if self.hp[hero]<=0:
                    if revived:continue
                    revived=True
                self.hp[hero]=min(self.profile.stats(hero)['hp'],self.hp[hero]+self.profile.stats(hero)['hp']*.5)
            for dx in (-190,0,190):self.fields.append(dict(kind='heal',pos=self.pos+V(dx,0),radius=120,life=9,tick=0,owner=h))
            self.effect('banquet',self.pos,1,reach=220)
        elif style=='wave':self.stances[h]=7;self.fields.append(dict(kind='concert',pos=V(self.pos),radius=275,life=7,tick=0,owner=h))
        elif style=='fan':self.fields.append(dict(kind='orbit',pos=V(self.pos),radius=160,life=9,tick=0,owner=h))
        elif style=='guard':
            self.fields.append(dict(kind='fortress',pos=V(self.pos),radius=245,life=10,tick=0,owner=h));self.shield=10
        elif style=='smile':
            for e in self.enemies:e['fear']=6;e['weak']=8
            self.effect('fear',self.pos,1.2,reach=650)
        elif style=='engineer':
            for i in range(5):self.objects.append(dict(kind='drone',pos=self.pos+V(1,0).rotate(i*72)*70,age=0.,life=10,damage=atk*4.5,owner=h))

    def hit(self,e,damage,owner):
        if e not in self.enemies:return
        before=e['hp'];damage*=1.25 if e.get('weak',0)>0 else 1
        super().hit(e,damage,owner)
        dealt=max(0,before-max(0,e['hp']));self.total_damage+=dealt;self.hits_landed+=1
        self.effect('impact',e['pos'],.18,reach=38)
        if HEROES[owner]['style']=='spit' and not self.dot_tick and e in self.enemies:e['poison']=3;e['poison_owner']=owner
        if e not in self.enemies and self.profile.data['equipped_relic']=='thermos' and self.hp.get(owner,0)>0:self.hp[owner]=min(self.profile.stats(owner)['hp'],self.hp[owner]+12)

    def hurt(self,damage):
        if self.training:return
        if self.parry>0 and self.invulnerable<=0:
            self.parry=0;self.invulnerable=.6;self.effect('shield',self.pos,.6,reach=210);self.sound('metal');self.floating('КОНТРАТАКА',self.pos-V(0,90),(200,225,255),True)
            for e in self.enemies[:]:
                if e['pos'].distance_to(self.pos)<230:self.hit(e,self.profile.stats(self.hero)['atk']*4,self.hero);e['stun']=1.6
            return
        for field in self.fields:
            if field['kind']=='fortress' and self.pos.distance_to(field['pos'])<field['radius']:damage*=.25;break
        super().hurt(damage)

    def hurt_core(self,damage):
        for field in self.fields:
            if field['kind']=='fortress' and self.core_pos.distance_to(field['pos'])<field['radius']:damage*=.2;break
        super().hurt_core(damage)

    def update(self,dt,move=(0,0),mouse=(900,400),firing=False):
        if self.done or self.intermission:return
        self.mouse=V(mouse);self.anim=max(0,self.anim-dt);self.parry=max(0,self.parry-dt);self.feedback_time=max(0,self.feedback_time-dt)
        for h in self.reloads:
            if self.reloads[h]>0:
                self.reloads[h]=max(0,self.reloads[h]-dt)
                if self.reloads[h]==0:self.ammo[h]=6
        for h in list(self.stances):self.stances[h]=max(0,self.stances[h]-dt)
        for e in self.enemies:
            for tag in ('fear','weak'):e[tag]=max(0,e.get(tag,0)-dt)
            if e.get('dummy'):e['stun']=100
            elif e['fear']>0:
                d=e['pos']-self.pos
                if d.length()>0:e['pos']+=d.normalize()*95*dt;e['stun']=.05
        if self.training:
            self.spawn_queue=0;self.next_wave=100000
            if not self.enemies:self.training_targets()
            for h in self.team:self.energy[h]=min(100,self.energy[h]+dt*22);self.skills[h]=max(0,self.skills[h]-dt*2)
        super().update(dt,move,mouse,firing)
        if self.done or self.intermission:return
        self.damage_tick-=dt
        if self.damage_tick<=0:
            self.damage_tick=.5;self.dot_tick=True
            for e in self.enemies[:]:
                if e.get('poison',0)>0:
                    e['poison']-=.5;owner=e['poison_owner'];self.hit(e,self.profile.stats(owner)['atk']*.25,owner)
            self.dot_tick=False
        self.execute_cd-=dt
        if self.execution and self.execute_cd<=0:
            uid=self.execution.pop(0);self.execute_cd=.23;target=next((e for e in self.enemies if e['uid']==uid),None)
            if target:
                start=V(self.pos);self.pos=target['pos']-V(36,0);self.clamp();self.effect('shadow_trail',start,.3,end=V(self.pos),width=9)
                self.hit(target,self.profile.stats('hood')['atk']*7,'hood');self.effect('dagger',target['pos'],.35,direction=V(1,0),arc=160,reach=140,phase=0);self.sound('dagger')
        if self.reticle is not None:
            self.reticle=V(self.mouse);self.reticle_time-=dt
            if self.reticle_time<=0:
                pos=V(self.reticle);self.reticle=None
                self.line_hit(pos-V(0,650),pos+V(0,650),75,self.profile.stats('glasses')['atk']*14,True,'orbital','glasses');self.shake=.45;self.sound('heavy')
        for obj in self.objects[:]:
            obj['age']+=dt;obj['life']-=dt;kind=obj['kind'];owner=obj['owner']
            if kind=='boomerang':
                if obj['age']>.52:
                    if obj['phase']==0:obj['phase']=1;obj['hit'].clear()
                    delta=self.pos-obj['pos']
                    if delta.length()>1:obj['vel']=delta.normalize()*710
                    if delta.length()<24:obj['life']=0
                obj['pos']+=obj['vel']*dt
                for e in self.enemies[:]:
                    if e['uid'] not in obj['hit'] and e['pos'].distance_to(obj['pos'])<e['r']+22:
                        obj['hit'].add(e['uid']);self.hit(e,obj['damage'],owner)
            elif kind in ('bread','cube'):
                f=min(1,obj['age']/.72);obj['pos']=obj['start'].lerp(obj['end'],f)
                if obj['life']<=0:
                    radius=105 if kind=='bread' else 135
                    self.effect('explosion',obj['end'],.5,reach=radius,pixel=kind=='cube');self.sound('wood' if kind=='bread' else 'heavy');self.shake=.1
                    for e in self.enemies[:]:
                        if e['pos'].distance_to(obj['end'])<radius:self.hit(e,obj['damage'],owner)
                    if kind=='bread' and self.hp.get(owner,0)>0 and self.pos.distance_to(obj['end'])<radius:self.hp[owner]=min(self.profile.stats(owner)['hp'],self.hp[owner]+10)
            elif kind=='turret':
                obj['tick']-=dt
                targets=[e for e in self.enemies if e['pos'].distance_to(obj['pos'])<420]
                if targets and obj['tick']<=0:
                    e=min(targets,key=lambda e:e['pos'].distance_to(obj['pos']));obj['tick']=.42
                    self.effect('beam',obj['pos'],.15,end=V(e['pos']),width=3);self.hit(e,obj['damage'],owner);self.sound('shot')
            elif kind=='drone':
                if self.enemies:
                    target=min(self.enemies,key=lambda e:e['pos'].distance_to(obj['pos']));delta=target['pos']-obj['pos']
                    if delta.length()>1:obj['pos']+=delta.normalize()*380*dt
                    if delta.length()<35:self.hit(target,obj['damage'],owner);self.effect('explosion',obj['pos'],.4,reach=110,pixel=True);obj['life']=0;self.sound('heavy')
            if obj['life']<=0 and obj in self.objects:self.objects.remove(obj)
        for field in self.fields[:]:
            field['life']-=dt;field['tick']-=dt;kind=field['kind'];owner=field['owner'];atk=self.profile.stats(owner)['atk']
            if kind in ('concert','orbit'):field['pos']=V(self.pos)
            if field['tick']<=0:
                field['tick']=.45
                if kind=='heal' and self.pos.distance_to(field['pos'])<field['radius']:
                    for h in self.team:
                        if self.hp[h]>0:self.hp[h]=min(self.profile.stats(h)['hp'],self.hp[h]+self.profile.stats(h)['hp']*.025)
                    self.effect('heal_tick',field['pos'],.45,reach=field['radius'])
                elif kind=='rain':
                    for _ in range(4):self.effect('rain_drop',field['pos']+V(random.uniform(-190,190),random.uniform(-130,130)),.4,reach=30)
                    self.dot_tick=True
                    for e in self.enemies[:]:
                        if e['pos'].distance_to(field['pos'])<field['radius']:self.hit(e,atk*1.05,owner);e['slow']=1
                    self.dot_tick=False
                elif kind=='concert':
                    self.effect('sonic',self.pos,.45,reach=275,direction=V(1,0),arc=360,phase=0);self.sound('wave')
                    for e in self.enemies[:]:
                        if e['pos'].distance_to(self.pos)<275:self.hit(e,atk*.85,owner);e['stun']=.20
                elif kind=='orbit':
                    for e in self.enemies[:]:
                        if 80<e['pos'].distance_to(self.pos)<185:self.hit(e,atk*1.5,owner)
            if field['life']<=0:
                if kind=='fortress':
                    self.effect('slam',field['pos'],.7,reach=245)
                    for e in self.enemies[:]:
                        if e['pos'].distance_to(field['pos'])<245:self.hit(e,atk*5,owner)
                self.fields.remove(field)
        for fx in self.fx[:]:
            fx['life']-=dt
            if fx['life']<=0:self.fx.remove(fx)
        if len(self.fx)>150:self.fx=self.fx[-150:]
