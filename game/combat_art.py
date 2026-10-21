"""Animated weapons, trajectories and persistent ability areas."""
import math
import pygame as pg
from model import HEROES

V=pg.Vector2
WHITE=(241,248,255)

class CombatArt:
    def texture(self,name,pos,size,color,angle=0,alpha=220):
        source=self.vfx.get(name)
        if source is None:return
        # A bounded set of source sizes; rotating frames are never cached.
        key=('vfx',name,int(size),tuple(color))
        if key not in self.scaled:
            im=pg.transform.smoothscale(source,(int(size),int(size))).copy()
            im.fill((*color,255),special_flags=pg.BLEND_RGBA_MULT)
            self.scaled[key]=im
        im=pg.transform.rotate(self.scaled[key],angle);im.set_alpha(alpha)
        self.s.blit(im,im.get_rect(center=pos))

    def draw_hero(self,b,t):
        style=HEROES[b.hero]['style'];col=HEROES[b.hero]['color'];p=V(b.pos)
        boost=b.stances.get(b.hero,0)>0
        pulse=math.sin(min(1,b.anim/.24)*math.pi) if b.anim else 0
        p+=b.anim_dir*pulse*(14 if style in ('brawler','slash','guard','shadow') else -5)
        giant=style=='brawler' and boost
        name='egor_beach' if giant else 'hero_'+b.hero
        if boost:self.texture('magic_01',b.pos,160,col,-t*40,130)
        src=self.images.get(name)
        if src:
            size=(110,138) if giant else (65,90)
            key=('actor',name,size)
            if key not in self.scaled:
                ratio=min(size[0]/src.get_width(),size[1]/src.get_height())
                self.scaled[key]=pg.transform.smoothscale(src,(int(src.get_width()*ratio),int(src.get_height()*ratio)))
            im=pg.transform.rotate(self.scaled[key],pulse*(12 if b.anim_phase%2 else -12))
            self.s.blit(im,im.get_rect(midbottom=(p.x,p.y+12-math.sin(t*8)*1.5)))
        d=V(b.aim);side=d.rotate(90);hand=p+d*22-V(0,20)
        angle=math.degrees(math.atan2(-d.y,d.x))
        if style in ('slash','shadow'):
            tip=hand+d*(80 if style=='slash' else 42)
            pg.draw.line(self.s,(35,38,61),hand-d*8,tip,10)
            pg.draw.line(self.s,WHITE,hand,tip,5)
            pg.draw.line(self.s,col,hand+side*12,hand-side*12,5)
        elif style=='shot':
            pg.draw.line(self.s,(60,79,103),hand-d*12,hand+d*49,13)
            pg.draw.line(self.s,col,hand,hand+d*54,4)
            pg.draw.circle(self.s,col,hand+d*23-side*9,6,2)
        elif style=='guard':
            q=hand+d*13
            pts=[q+side*26-d*10,q+side*24+d*15,q+d*33,q-side*24+d*15,q-side*26-d*10]
            pg.draw.polygon(self.s,(43,62,88),pts);pg.draw.polygon(self.s,col,pts,3)
        elif style=='brawler':
            for sign in (-1,1):
                q=hand+side*sign*27+d*pulse*(27 if sign==1 else -8)
                pg.draw.circle(self.s,(93,49,39),q,20 if giant else 13)
                pg.draw.circle(self.s,col,q,20 if giant else 13,3)
        elif style=='wave':
            pg.draw.line(self.s,(117,127,154),hand,hand+d*28,7);pg.draw.circle(self.s,col,hand+d*30,12)
        elif style=='engineer':
            pg.draw.line(self.s,col,hand-d*9,hand+d*23,8)
            pg.draw.circle(self.s,col,hand+d*25,10,4)
        elif style=='spit' and b.anim:
            pg.draw.ellipse(self.s,(63,20,31),(p.x+d.x*20-9,p.y-56,18+int(pulse*10),12))

    def draw_fields(self,b,t):
        layer=pg.Surface(self.s.get_size(),pg.SRCALPHA)
        for f in b.fields:
            p=f['pos'];r=f['radius'];kind=f['kind'];c=HEROES[f['owner']]['color']
            pg.draw.circle(layer,(*c,19),p,r)
            pg.draw.circle(layer,(*c,120),p,r,2)
            if kind=='heal':
                for i in range(5):
                    q=p+V(1,0).rotate(t*30+i*72)*r*.65
                    pg.draw.line(layer,(*c,170),q-V(8,0),q+V(8,0),3);pg.draw.line(layer,(*c,170),q-V(0,8),q+V(0,8),3)
            elif kind=='fortress':
                pts=[p+V(r,0).rotate(i*60+30) for i in range(6)]
                pg.draw.polygon(layer,(*c,210),pts,4)
                for q in pts:pg.draw.line(layer,(*c,180),q,q-V(0,48),5)
            elif kind=='rain':
                for i in range(18):
                    x=math.sin(i*73.1)*r*.85;y=((t*240+i*39)%(r*1.4))-r*.7
                    q=p+V(x,y);pg.draw.line(layer,(130,244,150,150),q-V(6,18),q,3)
            elif kind=='orbit':
                for i in range(5):
                    q=p+V(r,0).rotate(t*200+i*72);d=(q-p).normalize();side=d.rotate(90)
                    pg.draw.polygon(layer,(*c,230),[q+d*25,q+side*9,q-d*25,q-side*9])
            elif kind=='concert':
                for i in range(3):pg.draw.circle(layer,(*c,90),p,int((t*150+i*90)%r)+1,3)
        self.s.blit(layer,(0,0))
        if b.reticle is not None:
            p=b.reticle;radius=75+int(max(0,b.reticle_time)*55)
            pg.draw.circle(self.s,(255,195,90),p,radius,3)
            pg.draw.circle(self.s,(255,195,90),p,75,1)
            for d in (V(1,0),V(-1,0),V(0,1),V(0,-1)):pg.draw.line(self.s,WHITE,p+d*50,p+d*100,3)

    def draw_objects(self,b,t):
        for o in b.objects:
            p=V(o['pos']);kind=o['kind'];c=HEROES[o['owner']]['color']
            if kind in ('bread','cube'):
                pg.draw.ellipse(self.s,(8,13,24),(p.x-15,p.y-5,30,10))
                p.y-=math.sin(min(1,o['age']/.72)*math.pi)*115
                if kind=='bread':
                    pg.draw.ellipse(self.s,(246,187,97),(p.x-20,p.y-11,40,22))
                    for x in (-9,0,9):pg.draw.line(self.s,(147,82,36),p+V(x,-7),p+V(x-5,5),3)
                else:
                    pts=[p+V(18,18).rotate(o['age']*500+i*90) for i in range(4)]
                    pg.draw.polygon(self.s,(54,73,110),pts);pg.draw.polygon(self.s,c,pts,3)
                    pg.draw.circle(self.s,WHITE,p,4)
            elif kind=='boomerang':
                d=V(24,0).rotate(o['age']*1100)
                pg.draw.lines(self.s,c,False,[p+d,p,p+d.rotate(100)],7)
                pg.draw.lines(self.s,WHITE,False,[p+d*.85,p,p+d.rotate(100)*.85],2)
            elif kind=='turret':
                for d in (V(-24,13),V(24,13),V(0,-24)):pg.draw.line(self.s,(126,142,170),p,p+d,5)
                pg.draw.circle(self.s,(26,46,64),p,20);pg.draw.circle(self.s,c,p,20,3)
                target=min(b.enemies,key=lambda e:e['pos'].distance_to(p))['pos'] if b.enemies else p+V(1,0)
                d=target-p
                if d.length()>1:d=d.normalize()
                pg.draw.line(self.s,c,p,p+d*34,9)
                self.bar((p.x-20,p.y+26,40,3),o['life'],12,c)
            elif kind=='drone':
                pg.draw.rect(self.s,c,(p.x-10,p.y-8,20,16),2)
                for x in (-17,17):
                    pg.draw.line(self.s,WHITE,p+V(x-9,math.sin(t*80)*3),p+V(x+9,-math.sin(t*80)*3),2)
                self.texture('spark_01',p,48,c,t*90,120)

    def draw_fx(self,b,t):
        layer=pg.Surface(self.s.get_size(),pg.SRCALPHA)
        for f in b.fx:
            p=f['pos'];kind=f['kind'];k=1-f['life']/f['total'];c=f['color'];alpha=max(0,int(255*(1-k)))
            r=f.get('reach',65);d=f.get('direction',V(1,0));angle=math.atan2(d.y,d.x)
            if kind in ('slash','dagger','shield_bash','sonic'):
                arc=math.radians(f.get('arc',100));reach=r*(.55+.45*k)
                if kind=='sonic':
                    for off in (0,25,50):
                        rr=max(1,reach-off);pg.draw.arc(layer,(*c,alpha),(p.x-rr,p.y-rr,rr*2,rr*2),-angle-arc/2,-angle+arc/2,4)
                else:
                    pts=[p]+[p+V(math.cos(angle-arc/2+arc*i/18),math.sin(angle-arc/2+arc*i/18))*reach for i in range(19)]
                    pg.draw.polygon(layer,(*c,int(alpha*.22)),pts)
                    pg.draw.lines(layer,(*c,alpha),False,pts[1:],6)
                    self.texture('slash_02' if kind=='dagger' else 'slash_01',p+d*r*.55,128,c,-math.degrees(angle),alpha)
            elif kind=='punch':
                q=p+d*r*(.45+.55*k);pg.draw.line(layer,(*c,alpha),p,q,17)
                pg.draw.circle(layer,(*c,alpha),q,25,5)
                self.texture('spark_02',q,96,c,k*45,alpha)
            elif kind in ('beam','cut','orbital','shadow_trail','lightning'):
                end=f['end'];width=max(1,int(f.get('width',5)*(1-k)))
                if kind=='lightning':
                    delta=end-p;side=delta.normalize().rotate(90) if delta.length()>1 else V(0,1)
                    pts=[p]+[p+delta*i/8+side*math.sin(i*23+t*45)*17 for i in range(1,8)]+[end]
                    pg.draw.lines(layer,(*c,alpha),False,pts,6);pg.draw.lines(layer,(*WHITE,alpha),False,pts,2)
                else:
                    pg.draw.line(layer,(*c,int(alpha*.35)),p,end,max(4,width*2))
                    pg.draw.line(layer,(*WHITE,alpha),p,end,max(2,width//2))
            elif kind in ('explosion','impact','muzzle'):
                self.texture('spark_02' if kind!='explosion' else 'smoke_02',p,128 if kind=='explosion' else 64,c,k*60,alpha)
                if f.get('pixel'):
                    for i in range(12):
                        q=p+V(r*k,0).rotate(i*30);pg.draw.rect(layer,(*c,alpha),(q.x-5,q.y-5,10,10))
            elif kind in ('slam','bankai','shield','flash','fear','banquet','heal_tick'):
                rr=max(1,int(r*k));pg.draw.circle(layer,(*c,alpha),p,rr,5)
                if kind in ('slam','bankai'):
                    for i in range(12):
                        d=V(1,0).rotate(i*30);pg.draw.line(layer,(*c,alpha),p+d*rr*.65,p+d*rr,4)
                if kind=='bankai':self.texture('magic_01',p,256,c,k*80,alpha)
            elif kind=='heart':
                for i in range(7):
                    q=p+V((i-3)*37,-35-k*125+math.sin(i)*20)
                    pg.draw.circle(layer,(255,126,184,alpha),q+V(-5,-3),7);pg.draw.circle(layer,(255,126,184,alpha),q+V(5,-3),7)
                    pg.draw.polygon(layer,(255,126,184,alpha),[q+V(-12,0),q+V(12,0),q+V(0,15)])
            elif kind in ('rain_drop','spit_mouth'):
                q=p+V(0,-80*(1-k)) if kind=='rain_drop' else p+d*50*k-V(0,42)
                for i in range(5):pg.draw.circle(layer,(135,244,144,alpha),q+V(i*4,-i*3),max(2,7-i))
        self.s.blit(layer,(0,0))
