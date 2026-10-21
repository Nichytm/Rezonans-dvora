"""Readable, committed attacks for five photo bosses."""
import math,random
import pygame as pg
from worlds import BOSSES,resolve_circle,MAPS
V=pg.Vector2

def segment_distance(p,a,b):
    d=b-a
    if d.length_squared()<1:return p.distance_to(a)
    return p.distance_to(a+d*max(0,min(1,(p-a).dot(d)/d.length_squared())))

class Bosses:
    def spawn_photo_boss(self,hero=None):
        hero=hero or random.choice(list(BOSSES))
        self.spawn(boss=True,photo=hero)

    def warn(self,shape,pos,radius=80,delay=1.1,damage=30,**extra):
        self.warnings.append(dict(shape=shape,pos=V(pos),radius=radius,delay=delay,total=delay,damage=damage,**extra))

    def update_boss(self,e,dt):
        hero=e['boss_id'];e['flash']=max(0,e['flash']-dt);e['slow']=max(0,e['slow']-dt)
        e['stun']=max(0,e['stun']-dt);e['cooldown']-=dt;e['recover']=max(0,e.get('recover',0)-dt)
        if e['hp']<e['maxhp']*.5 and not e['enraged']:
            e['enraged']=True;e['cooldown']=.6;self.banner='ФАЗА II · '+BOSSES[hero]['name'];self.banner_time=2.4;self.sound('phase')
            self.ring(e['pos'],190,e['color'])
        if e['stun']>0:return
        delta=self.pos-e['pos'];dist=delta.length();direction=delta.normalize() if dist>1 else V(1,0)
        if e['recover']<=0 and e.get('casting',0)<=0:
            desired=110 if hero in ('ilya','egor') else 285
            if dist>desired:e['pos']+=direction*(82 if hero=='ilya' else 48)*dt
            elif dist<140 and hero in ('bugdan','igor'):e['pos']-=direction*50*dt
        e['pos']=resolve_circle(e['pos'],32,MAPS[self.map_key]['obstacles'])
        e['casting']=max(0,e.get('casting',0)-dt)
        if e['cooldown']>0 or e['recover']>0:return
        enraged=e['enraged'];n=e['attack_number'];e['attack_number']+=1
        damage=(25+8*self.difficulty)*(1.2 if enraged else 1)
        e['cooldown']=3.0 if enraged else 4.1;e['casting']=1.1
        origin=V(e['pos']);target=V(self.pos);warning_start=len(self.warnings)
        if hero=='bugdan':
            if n%2==0:
                for i in range(4 if enraged else 2):
                    p=target+V((i%2)*150-60,(i//2)*115-40);p.x=max(100,min(1180,p.x));p.y=max(230,min(550,p.y))
                    self.warn('circle',p,65,1.25,damage,poison=True)
                self.sound('voice:bugdan:skill')
            else:
                self.warn('fan',origin,delay=.9,damage=damage,direction=direction,spread=100 if enraged else 70,count=11 if enraged else 7,color=e['color'])
            e['recover']=1.7
        elif hero=='ilya':
            end=resolve_circle(origin+direction*min(600,max(310,dist+100)),30,MAPS[self.map_key]['obstacles'])
            self.warn('line',origin,38 if not enraged else 50,1.0,damage*1.3,end=end,boss_uid=e['uid'],relocate=True)
            if enraged and n%2:
                for side in (-1,1):self.warn('line',origin+V(0,side*100),25,1.45,damage,end=end+V(0,side*100))
            e['recover']=2.25;e['cooldown']=3.4 if enraged else 4.0
        elif hero=='smiler':
            if n%3==2:
                safe=resolve_circle(self.pos+V(random.choice((-260,260)),random.choice((-90,90))),30,MAPS[self.map_key]['obstacles'])
                self.warn('safe',safe,100 if not enraged else 82,2.2,damage*1.5)
                self.feedback='АРТЁМ ГОТОВИТ ВСПЫШКУ · ВСТАНЬ В ЗЕЛЁНЫЙ КРУГ';self.feedback_time=2.2
                self.sound('voice:smiler:ultimate')
            else:
                self.warn('ring',origin,delay=1,damage=damage*.65,count=20 if enraged else 12,color=e['color'],rotation=n*17)
                if enraged and len(self.enemies)<10:
                    self.spawn(kind='charger');self.enemies[-1]['decoy_id']='smiler';self.enemies[-1]['hp']*=.65
            e['recover']=2.0
        elif hero=='egor':
            self.warn('circle',target,110,1.3,damage*1.5,boss_uid=e['uid'],relocate=True)
            if enraged:
                for side in (-1,1):self.warn('circle',target+V(side*180,0),90,1.7,damage)
            e['recover']=2.8;e['cooldown']=3.8 if enraged else 4.6
        elif hero=='igor':
            if n%2==0:
                for i in range(2 if enraged else 1):
                    self.spawn(kind='ranged',pos=origin+V(-100 if i else 100,70));turret=self.enemies[-1]
                    turret['turret']=True;turret['speed']=0;turret['hp']=turret['maxhp']=130*self.difficulty
                self.sound('mechanical')
            else:
                for i in range(3 if enraged else 2):
                    x=max(90,min(1190,target.x+(i-1)*170));self.warn('line',V(x,190),32,1.5,damage*1.25,end=V(x,580))
            e['recover']=1.8
        e['casting']=max((w['delay'] for w in self.warnings[warning_start:]),default=.3)
        e['recover']=max(e['recover'],e['casting']+1.)
        e['cooldown']=max(e['cooldown'],e['recover']+.7)

    def resolve_warnings(self,dt):
        for w in self.warnings[:]:
            w['delay']-=dt
            if w['delay']>0:continue
            self.warnings.remove(w);p=w['pos'];shape=w['shape'];r=w['radius'];damage=w['damage']
            if shape in ('circle','safe','line'):
                def hit(pos):
                    if shape=='circle':return pos.distance_to(p)<r+15
                    if shape=='safe':return pos.distance_to(p)>r-8
                    return segment_distance(pos,p,w['end'])<r+15
                if hit(self.pos):self.hurt(damage)
                if self.objective=='defend' and hit(self.core_pos):self.hurt_core(damage*.7)
                if shape=='line':self.effect('orbital' if not w.get('relocate') else 'cut',p,.4,end=w['end'],width=r*1.2,color=(255,106,132))
                else:self.effect('slam',p,.6,reach=r,color=(255,123,145))
                if w.get('poison'):self.add_zone(p,int(r),5,10,(131,221,124),True)
                if w.get('relocate'):
                    boss=next((e for e in self.enemies if e['uid']==w.get('boss_uid')),None)
                    if boss:boss['pos']=V(w.get('end',p));boss['recover']=1.4
                self.sound('detonate');self.shake=.16
            elif shape in ('fan','ring'):
                count=w['count']
                for i in range(count):
                    d=V(1,0).rotate(i*360/count+w.get('rotation',0)) if shape=='ring' else w['direction'].rotate(-w['spread']/2+w['spread']*i/(count-1))
                    self.shoot(p,d,damage,200 if shape=='ring' else 290,w['color'],True,9)
                self.sound('plasma')

class ThreatArt:
    def draw_threats(self,b,t):
        if not hasattr(b,'warnings'):return
        layer=pg.Surface((1280,613),pg.SRCALPHA)
        for w in b.warnings:
            p=w['pos'];r=w['radius'];k=max(0,1-w['delay']/w['total']);c=(255,104,126);shape=w['shape']
            if shape=='safe':
                pg.draw.rect(layer,(125,35,65,35),(48,180,1184,416))
                pg.draw.circle(layer,(80,235,178,65),p,r);pg.draw.circle(layer,(110,255,196,230),p,r,4)
                self.text('СЮДА',p.x,p.y,17,(144,255,202),True,'center')
            elif shape=='line':
                pg.draw.line(layer,(*c,45),p,w['end'],int(r*2))
                pg.draw.line(layer,(*c,210),p,w['end'],3)
                delta=w['end']-p
                if delta.length()>1:
                    d=delta.normalize().rotate(90)*r
                    pg.draw.line(layer,(*c,150),p+d,w['end']+d,2);pg.draw.line(layer,(*c,150),p-d,w['end']-d,2)
            elif shape=='circle':
                pg.draw.circle(layer,(*c,40),p,r);pg.draw.circle(layer,(*c,220),p,r,3)
                pg.draw.circle(layer,(*c,70),p,max(1,int(r*k)))
            elif shape=='fan':
                d=w['direction'];angle=math.atan2(d.y,d.x);arc=math.radians(w['spread']);reach=210
                points=[p]+[p+V(math.cos(angle-arc/2+arc*i/12),math.sin(angle-arc/2+arc*i/12))*reach for i in range(13)]
                pg.draw.polygon(layer,(*c,45),points);pg.draw.lines(layer,(*c,210),True,points,2)
            else:pg.draw.circle(layer,(*c,170),p,65+int(k*70),3)
        self.s.blit(layer,(0,0))
