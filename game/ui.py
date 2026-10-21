"""Drawing helpers. All coordinates use a fixed 1280x720 logical canvas."""
import math
from contextlib import nullcontext
from functools import lru_cache
from pathlib import Path
import pygame as pg
from model import HEROES,RARITIES,BASICS
from combat_art import CombatArt
from worlds import WorldArt
from bosses import ThreatArt
from activities_ui import ObjectiveArt

W,H=1280,720
BG=(10,14,26); PANEL=(19,26,43); LINE=(44,54,77); WHITE=(235,239,250); MUTED=(139,154,184)
CYAN=(115,232,228); PURPLE=(178,135,251); GOLD=(255,205,120); RED=(245,110,140)

class UI(CombatArt,WorldArt,ThreatArt,ObjectiveArt):
    def __init__(self,surface,assets):
        self.s=surface; self.assets=Path(assets); self.buttons=[]; self.mouse=(0,0); self.images={};self.scaled={}
        self.regular=str(self.assets/'fonts'/'regular.ttf')
        self.bold=str(self.assets/'fonts'/'bold.ttf')
        self.fonts={}
        for p in (self.assets/'images').iterdir():
            try:self.images[p.stem]=pg.image.load(str(p)).convert_alpha()
            except pg.error:pass
        self.vfx={p.stem:pg.image.load(str(p)).convert_alpha() for p in (self.assets/'vfx').glob('*.png')}
        for h,hero in HEROES.items():
            im=self.images.get(Path(hero['image']).stem)
            if im is None:continue
            if 'crop' in hero:
                a,b,c,d=hero['crop']; iw,ih=im.get_size();im=im.subsurface(pg.Rect(int(a*iw),int(b*ih),int((c-a)*iw),int((d-b)*ih))).copy()
            else:
                rect=im.get_bounding_rect(min_alpha=12)
                if rect.width and rect.height:im=im.subsurface(rect).copy()
            self.images['hero_'+h]=im
        self.load_worlds()
        self.background=pg.Surface((W,H))
        for y in range(H):pg.draw.line(self.background,(10+int(y/H*6),14+int(y/H*6),26+int(y/H*10)),(0,y),(W,y))

    def text(self,value,x,y,size=20,color=WHITE,bold=False,anchor='topleft',maxwidth=None):
        key=(size,bold)
        if key not in self.fonts:self.fonts[key]=pg.font.Font(self.bold if bold else self.regular,size)
        font=self.fonts[key];value=str(value)
        if maxwidth:
            while value and font.size(value)[0]>maxwidth:value=value[:-2]+'…'
        surf=font.render(value,True,color);rect=surf.get_rect();setattr(rect,anchor,(int(x),int(y)));self.s.blit(surf,rect)
        return rect

    def panel(self,rect,color=PANEL,border=LINE,radius=16):
        r=pg.Rect(rect);pg.draw.rect(self.s,color,r,border_radius=radius)
        if border:pg.draw.rect(self.s,border,r,width=1,border_radius=radius)
        return r

    def paragraph(self,text,x,y,width,size=16,color=MUTED,line_height=24):
        words=text.split();line='';row=0
        font=pg.font.Font(self.regular,size)
        for word in words:
            candidate=(line+' '+word).strip()
            if font.size(candidate)[0]>width and line:
                self.text(line,x,y+row*line_height,size,color);row+=1;line=word
            else:line=candidate
        if line:self.text(line,x,y+row*line_height,size,color)

    def button(self,rect,label,callback,accent=False,enabled=True,small=False):
        r=pg.Rect(rect);hover=r.collidepoint(self.mouse) and enabled
        fill=CYAN if accent and enabled else (43,55,78) if hover else (25,33,52)
        if not enabled:fill=(22,27,40)
        self.panel(r,fill,CYAN if hover or accent and enabled else LINE,10)
        self.text(label,r.centerx,r.centery,16 if small else 18,BG if accent and enabled else WHITE if enabled else (84,97,121),True,'center')
        if enabled:self.buttons.append((r,callback))

    def bar(self,rect,value,maximum,color=CYAN):
        r=pg.Rect(rect);pg.draw.rect(self.s,(36,43,61),r,border_radius=r.height//2)
        ratio=max(0,min(1,value/maximum if maximum else 0))
        if ratio:pg.draw.rect(self.s,color,(r.x,r.y,max(r.height,int(r.w*ratio)),r.h),border_radius=r.height//2)

    def img(self,name,rect,mode='contain',alpha=255):
        if name not in self.images:return
        x,y,w,h=map(int,rect);key=(name,w,h,mode)
        if key not in self.scaled:
            src=self.images[name];sw,sh=src.get_size();ratio=(max if mode=='cover' else min)(w/sw,h/sh)
            im=pg.transform.smoothscale(src,(max(1,round(sw*ratio)),max(1,round(sh*ratio))))
            out=pg.Surface((w,h),pg.SRCALPHA);out.blit(im,((w-im.get_width())//2,(h-im.get_height())//2));self.scaled[key]=out
        im=self.scaled[key]
        if alpha!=255:im=im.copy();im.set_alpha(alpha)
        self.s.blit(im,(x,y))

    def glow(self,pos,color,radius=100,strength=50):
        key=('glow',color,radius,strength)
        if key not in self.scaled:
            im=pg.Surface((radius*2,radius*2))
            im.fill((0,0,0))
            for r in range(radius,0,-6):
                intensity=strength/255*(1-r/radius)**1.5
                pg.draw.circle(im,tuple(int(c*intensity) for c in color),(radius,radius),r)
            self.scaled[key]=im
        self.s.blit(self.scaled[key],(int(pos[0]-radius),int(pos[1]-radius)),special_flags=pg.BLEND_RGB_ADD)

    def base(self,t):
        self.buttons=[];self.s.blit(self.background,(0,0))
        for i in range(36):
            x=(i*173+25)%1280;y=(i*83-t*(5+i%3*4))%720
            pg.draw.circle(self.s,(49,64,92),(int(x),int(y)),1 if i%3 else 2)

    def top(self,profile,page,navigate):
        self.text('РЕЗОНАНС',34,22,25,WHITE,True)
        self.text('Д В О Р А',36,51,12,CYAN,True)
        for i,(key,title) in enumerate([('home','ШТАБ'),('roster','ГЕРОИ'),('summon','ПРИЗЫВ'),('activities','РЕЖИМЫ')]):
            x=268+i*129;r=pg.Rect(x,21,118,43)
            self.button(r,title,lambda k=key:navigate(k),small=True)
            if page==key:pg.draw.line(self.s,CYAN,(x+22,70),(x+96,70),3)
        self.text('КРИСТАЛЛЫ',848,21,10,MUTED,True);self.text(f'{profile.data["crystals"]:,}'.replace(',',' '),848,36,24,CYAN,True)
        self.text('МОНЕТЫ',997,21,10,MUTED,True);self.text(f'{profile.data["gold"]:,}'.replace(',',' '),997,36,24,GOLD,True)
        self.text('ЭССЕНЦИЯ',1135,21,10,MUTED,True);self.text(profile.data['essence'],1135,36,24,PURPLE,True)
        pg.draw.line(self.s,LINE,(32,83),(1248,83))

    def tag(self,text,x,y,color=CYAN):
        r=self.text(text,x+10,y+4,12,color,True)
        pg.draw.rect(self.s,color,(x,y,r.w+20,27),1,border_radius=5)

    def card(self,h,rect,profile,callback=None,selected=False):
        r=pg.Rect(rect);hero=HEROES[h];rarity=hero['rarity'];color=RARITIES[rarity][1];owned=h in profile.data['heroes']
        self.panel(r,(25,30,49),color if selected else LINE,13)
        old=self.s.get_clip();self.s.set_clip(r.inflate(-2,-2))
        self.glow((r.centerx,r.y+r.h*.45),color,min(130,r.w),24)
        self.img('hero_'+h,(r.x+8,r.y+24,r.w-16,r.h-89),alpha=255 if owned else 95)
        self.s.set_clip(old)
        self.text(rarity,r.x+12,r.y+10,13,color,True)
        if owned:self.text('УР. '+str(profile.data['heroes'][h]['level']),r.right-10,r.y+10,12,MUTED,True,'topright')
        self.text(hero['name'],r.x+13,r.bottom-65,20,WHITE,True,maxwidth=r.w-24)
        self.text(hero['title'],r.x+13,r.bottom-38,13,color,maxwidth=r.w-24)
        if h in profile.data['team']:
            pg.draw.circle(self.s,CYAN,(r.right-18,r.bottom-20),10)
            self.text(str(profile.data['team'].index(h)+1),r.right-18,r.bottom-20,12,BG,True,'center')
        if not owned:self.text('НЕ ПОЛУЧЕН',r.centerx,r.y+int(r.h*.48),12,WHITE,True,'center')
        if callback:self.buttons.append((r,callback))

    def compact_card(self,h,rect,profile,callback,selected=False):
        r=pg.Rect(rect);hero=HEROES[h];color=RARITIES[hero['rarity']][1];own=profile.data['heroes'].get(h)
        self.panel(r,(26,34,51) if selected else PANEL,color if selected else LINE,12)
        self.img('hero_'+h,(r.x+6,r.y+28,85,r.h-35),alpha=255 if own else 70)
        self.text(hero['rarity'],r.x+12,r.y+8,12,color,True)
        self.text(hero['name'],r.x+101,r.y+33,18,WHITE,True,maxwidth=r.w-110)
        self.text(hero['title'],r.x+101,r.y+61,12,color,maxwidth=r.w-110)
        self.text('УР. '+str(own['level']) if own else 'НЕ ПОЛУЧЕН',r.x+101,r.y+88,12,MUTED,True)
        if h in profile.data['team']:self.tag('СЛОТ '+str(profile.data['team'].index(h)+1),r.x+101,r.y+111,CYAN)
        self.buttons.append((r,callback))

    def arena(self,b,t,paused=False):
        self.buttons=[];s=self.s;s.fill(BG)
        from model import STAGES
        if not self.draw_world(b,t):
            bg=STAGES[b.stage-1][2]
            self.img(bg,(0,0,1280,340),'cover',alpha=190)
            dark=pg.Surface((1280,615),pg.SRCALPHA);dark.fill((9,14,30,95));s.blit(dark,(0,0))
            # Perspective floor, arena rim, and light columns create depth around photo billboards.
            pg.draw.polygon(s,(18,25,42),[(170,180),(1110,180),(1280,607),(0,607)])
            for x in range(-500,1801,140):pg.draw.line(s,(33,43,65),(640+(x-640)*.58,180),(x,608))
            for i in range(9):
                y=180+(i/8)**1.6*427;pg.draw.line(s,(34,44,65),(0,y),(1280,y))
            # Scuffed paving slabs and benches at the back of the playable yard.
            for x,y in [(211,301),(818,478),(467,527),(1020,356)]:
                pg.draw.lines(s,(43,48,65),False,[(x,y),(x+16,y+8),(x+10,y+18),(x+25,y+26)],1)
            for x in (185,955):
                pg.draw.polygon(s,(37,38,56),[(x,176),(x+134,176),(x+152,194),(x-8,194)])
                pg.draw.line(s,(82,72,79),(x-5,188),(x+145,188),5)
                pg.draw.line(s,(60,62,82),(x+12,195),(x+12,214),4)
                pg.draw.line(s,(60,62,82),(x+124,195),(x+131,214),4)
            pg.draw.line(s,(67,95,117),(55,188),(1225,188),2)
            pg.draw.line(s,(67,95,117),(0,598),(1280,598),2)
            for x in (55,1225):
                self.glow((x,190),PURPLE,110,45)
                pg.draw.line(s,(123,97,173),(x,105),(x,190),3)
                pg.draw.polygon(s,PURPLE,[(x,115),(x+10,133),(x,149),(x-10,133)],2)
        for zone in b.zones:
            radius=zone['radius'];pos=zone['pos'];col=zone['color']
            surf=pg.Surface((radius*2+4,radius*2+4),pg.SRCALPHA)
            pg.draw.circle(surf,(*col,36),(radius+2,radius+2),radius)
            pg.draw.circle(surf,(*col,140),(radius+2,radius+2),radius,2)
            s.blit(surf,(pos.x-radius-2,pos.y-radius-2))
            for i in range(6):
                a=t+i*math.tau/6;pg.draw.circle(s,col,(int(pos.x+math.cos(a)*radius*.6),int(pos.y+math.sin(a)*radius*.45)),3)
        self.draw_fields(b,t)
        self.draw_mode_world(b,t)
        self.draw_threats(b,t)
        if b.objective=='defend' and getattr(b,'mode',None)!='escort':
            x,y=b.core_pos;self.glow((x,y-35),CYAN,90,55)
            pg.draw.ellipse(s,(7,17,26),(x-40,y+6,80,25))
            pg.draw.polygon(s,(27,94,109),[(x,y-74),(x+28,y-34),(x,y+10),(x-28,y-34)])
            pg.draw.polygon(s,CYAN,[(x,y-74),(x+28,y-34),(x,y+10),(x-28,y-34)],3)
            pg.draw.line(s,WHITE,(x,y-65),(x,y-1),2)
            self.bar((x-45,y-90,90,6),b.core_hp,b.core_max,CYAN)
        for e in b.enemies:
            if e['telegraph']>0:
                pos=e['target'];radius=105 if e['kind']=='boss' else 53
                tele=pg.Surface((radius*2+4,radius*2+4),pg.SRCALPHA)
                pg.draw.circle(tele,(255,75,113,48),(radius+2,radius+2),radius)
                pg.draw.circle(tele,(255,115,145,210),(radius+2,radius+2),radius,2)
                s.blit(tele,(pos.x-radius-2,pos.y-radius-2))
                pg.draw.line(s,RED,(pos.x-10,pos.y),(pos.x+10,pos.y),2);pg.draw.line(s,RED,(pos.x,pos.y-10),(pos.x,pos.y+10),2)
        for orb in b.orbs:
            x,y=orb['pos'];self.glow((x,y),CYAN,25,50)
            pg.draw.circle(s,CYAN,(int(x),int(y)),7);pg.draw.line(s,BG,(x-3,y),(x+3,y),2);pg.draw.line(s,BG,(x,y-3),(x,y+3),2)
        players=[(b.player_position(i).y,'hero',i) for i in range(2)] if getattr(b,'coop',False) else [(b.pos.y,'hero',None)]
        entities=[(e['pos'].y,'enemy',e) for e in b.enemies]+players
        for _,kind,e in sorted(entities,key=lambda a:a[0]):
            if kind=='hero':
                with b.player(e) if getattr(b,'coop',False) else nullcontext():
                    x,y=b.pos;col=HEROES[b.hero]['color'];r=26
                    pg.draw.ellipse(s,(8,11,22),(x-34,y+10,68,19));pg.draw.ellipse(s,col,(x-30,y+5,60,20),2)
                    if not(b.invulnerable>0 and int(t*16)%2):self.draw_hero(b,t)
                    if b.shield>0:pg.draw.ellipse(s,CYAN,(x-49,y-95,98,125),3)
                    aim=b.pos+b.aim*57;pg.draw.circle(s,col,(int(aim.x),int(aim.y)),5,1)
                    self.bar((x-28,y-105,56,5),b.hp[b.hero],b.profile.stats(b.hero)['hp'],CYAN)
                    if getattr(b,'coop',False):self.text(f'ИГРОК {e+1}'+(' · ВЫБЫЛ' if b.hp[b.hero]<=0 else ''),x,y-121,13,CYAN if e==0 else GOLD,True,'center')
            else:
                x,y=e['pos'];r=e['r'];col=(255,255,255) if e['flash'] else e['color']
                pg.draw.ellipse(s,(8,11,22),(x-r,y+9,r*2,16))
                bob=math.sin(t*4+x)*3
                if e.get('boss_id'):
                    self.draw_photo_boss(b,e,t)
                elif e.get('decoy_id'):
                    self.img('hero_'+e['decoy_id'],(x-22,y-52,44,60),alpha=155)
                elif e.get('turret'):
                    pg.draw.rect(s,(34,59,71),(x-22,y-27,44,33),border_radius=6)
                    pg.draw.rect(s,col,(x-22,y-27,44,33),3,border_radius=6)
                    pg.draw.line(s,col,(x,y-10),(x+25,y-20),7)
                elif e['kind']=='boss':
                    self.glow((x,y-25),RED,90,65 if e['enraged'] else 35)
                    pts=[(x-47,y-4),(x-46,y-72),(x-24,y-47),(x,y-84),(x+23,y-46),(x+46,y-72),(x+48,y-4),(x+24,y+19),(x-21,y+19)]
                    pg.draw.polygon(s,(56,30,53),pts);pg.draw.polygon(s,col,pts,3)
                    for off in (-18,18):
                        pg.draw.polygon(s,GOLD if e['enraged'] else WHITE,[(x+off-8,y-33),(x+off+8,y-29),(x+off,y-23)])
                    pg.draw.lines(s,col,False,[(x-19,y-5),(x-9,y+4),(x,y-3),(x+8,y+4),(x+20,y-5)],3)
                elif e['kind']=='anchor':
                    self.glow((x,y-20),PURPLE,65,40)
                    pg.draw.circle(s,(47,32,75),(int(x),int(y-20)),30)
                    pg.draw.circle(s,PURPLE,(int(x),int(y-20)),32,3)
                    for i in range(3):
                        a=t+i*math.tau/3;pg.draw.line(s,PURPLE,(x,y-20),(x+math.cos(a)*43,y-20+math.sin(a)*43),3)
                elif e['kind']=='summoner':
                    pg.draw.polygon(s,(32,60,55),[(x,y-52),(x+28,y+7),(x-28,y+7)])
                    pg.draw.polygon(s,col,[(x,y-52),(x+28,y+7),(x-28,y+7)],2)
                    pg.draw.circle(s,WHITE,(int(x),int(y-21)),6)
                    pg.draw.circle(s,col,(int(x),int(y-19)),36,1)
                elif e['kind']=='armored':
                    pg.draw.rect(s,(44,53,76),(x-26,y-44,52,53),border_radius=12)
                    pg.draw.rect(s,col,(x-26,y-44,52,53),2,border_radius=12)
                    pg.draw.line(s,RED,(x-12,y-23),(x+12,y-23),4)
                    if e['armor']>0:pg.draw.arc(s,GOLD,(x-35,y-53,70,70),0,math.tau,4)
                elif e['kind']=='ranged':
                    pts=[(x,y-48+bob),(x+24,y-20+bob),(x,y+6+bob),(x-24,y-20+bob)]
                    pg.draw.polygon(s,(67,37,73),pts);pg.draw.polygon(s,col,pts,2)
                    pg.draw.circle(s,WHITE,(int(x),int(y-19+bob)),6)
                elif e['kind']=='charger':
                    pts=[(x-25,y),(x-23,y-40),(x-8,y-26),(x+10,y-46),(x+27,y-8),(x+14,y+8)]
                    pg.draw.polygon(s,(83,48,49),pts);pg.draw.polygon(s,col,pts,2)
                    pg.draw.line(s,GOLD,(x-10,y-17),(x+9,y-17),4)
                else:
                    pg.draw.ellipse(s,(65,48,96),(x-26,y-41+bob,52,49));pg.draw.ellipse(s,col,(x-26,y-41+bob,52,49),2)
                    for off in (-9,9):pg.draw.circle(s,(210,220,255),(int(x+off),int(y-20+bob)),4)
                if e['kind']!='boss':self.bar((x-23,y-58,46,4),e['hp'],e['maxhp'],col)
                if e.get('dummy'):self.text('МАНЕКЕН',x,y-78,10,MUTED,True,'center')
                elif e.get('fear',0)>0:self.text('СТРАХ',x,y-78,10,GOLD,True,'center')
                elif e['stun']>0:self.text('ОГЛУШЁН',x,y-78,10,CYAN,True,'center')
                if e.get('poison',0)>0:pg.draw.circle(s,(116,240,139),(int(x+28),int(y-48)),5)
        for bullet in b.bullets:
            p=bullet['pos'];tail=p-bullet['vel']*.03;col=bullet['color'];r=bullet['size']
            if bullet.get('kind')=='spit':
                direction=bullet['vel'].normalize();side=direction.rotate(90)
                pg.draw.polygon(s,(83,189,116),[p+direction*r,p-direction*r*2+side*r*.65,p-direction*r*2-side*r*.65])
                pg.draw.circle(s,col,(int(p.x),int(p.y)),r);pg.draw.circle(s,WHITE,(int(p.x-r*.25),int(p.y-r*.25)),max(2,r//3))
            else:
                pg.draw.line(s,col,tail,p,max(2,r));pg.draw.circle(s,col,(int(p.x),int(p.y)),r)
                pg.draw.circle(s,WHITE,(int(p.x),int(p.y)),max(2,r//3))
        self.draw_objects(b,t)
        self.draw_fx(b,t)
        for effect in b.effects:
            p=effect['pos'];radius=max(1,int(effect['radius']*(1-effect['life']/.55)))
            if radius<1800:pg.draw.circle(s,effect['color'],(int(p.x),int(p.y)),radius,max(1,int(effect['life']*8)))
        for particle in b.particles:
            p=particle['pos'];pg.draw.circle(s,particle['color'],(int(p.x),int(p.y)),max(1,int(particle['life']*7)))
        for text in b.texts:self.text(text['text'],text['pos'].x,text['pos'].y,25 if text['big'] else 17,text['color'],True,'center')
        self.panel((24,20,322,71),(16,22,38),LINE,12)
        self.text(('АРЕНА  /  ВОЛНА '+str(max(1,b.wave))) if b.endless else f'РАЗЛОМ {b.stage:02}  /  ВОЛНА {min(3,max(1,b.wave))} ИЗ 3',42,33,12,CYAN,True)
        self.text('Совместная арена' if getattr(b,'coop',False) else 'Испытание героев' if b.training else 'Бесконечная арена' if b.endless else STAGES[b.stage-1][0],42,53,20,WHITE,True)
        task='Защити резонатор: '+str(int(100*b.core_hp/b.core_max))+'%' if b.objective=='defend' else f'Якоря разлома: {b.anchors_destroyed} / 3' if b.objective=='anchors' else 'Зачисти все волны'
        self.text(('Урон: '+str(int(b.total_damage))) if b.training else task,30,101,13,CYAN,True)
        if b.perks:self.text(f'Усилений: {len(b.perks)}  ·  Урон ×{b.power:.2f}',30,124,12,MUTED)
        self.text(f'{int(b.elapsed)//60:02}:{int(b.elapsed)%60:02}',1238,27,24,WHITE,True,'topright')
        self.text('ПАУЗА НА ПАНЕЛИ' if getattr(b,'board_mode',False) else 'ESC · ПАУЗА',1238,63,12,MUTED,False,'topright')
        bosses=[e for e in b.enemies if e['kind']=='boss']
        if bosses:
            boss=bosses[0];self.text(b.boss_name+(' · ЯРОСТЬ' if boss['enraged'] else ''),640,24,14,RED,True,'midtop');self.bar((425,49,430,9),boss['hp'],boss['maxhp'],RED)
        if b.combo>1:self.text(f'{b.combo}  КОМБО',1235,111,25,GOLD,True,'topright')
        if b.banner_time>0:
            banner_y=144 if getattr(b,'mode',None) else 105
            self.panel((300,banner_y,680,40),(17,24,41),LINE,8);self.text(b.banner,640,banner_y+20,18,WHITE,True,'center',maxwidth=650)
        self.panel((0,613,1280,107),(13,19,33),None,0)
        for i,h in enumerate(b.team):
            x=23+i*184;active=h==b.hero;col=HEROES[h]['color']
            self.panel((x,630,174,69),(31,41,59) if active else (19,26,42),col if active else LINE,10)
            self.img('hero_'+h,(x+6,634,48,58));self.text(f'{i+1} · '+HEROES[h]['name'],x+59,638,13,WHITE if b.hp[h]>0 else RED,True)
            self.bar((x+60,663,102,5),b.hp[h],b.profile.stats(h)['hp'],col)
            self.bar((x+60,676,102,4),b.energy[h],100,GOLD)
            if b.hp[h]<=0:self.text('ВЫБЫЛ',x+60,681,10,RED,True)
            self.buttons.append((pg.Rect(x,630,174,69),lambda slot=i:b.switch(slot)))
        if getattr(b,'coop',False):
            for index,h in enumerate(b.team):
                x=640+index*302;col=CYAN if index==0 else GOLD
                self.panel((x,630,284,69),(19,26,42),col,10)
                self.text(f'ИГРОК {index+1} · '+HEROES[h]['name'],x+12,637,14,col,True)
                skill='Приём готов' if b.skills[h]<=0 else f'Приём: {b.skills[h]:.1f}с'
                self.text(skill+f' · Ульта: {round(b.energy[h])}%',x+12,670,13,WHITE)
        else:
            h=HEROES[b.hero]
            self.text('АВТОПРИЦЕЛ И АТАКА' if getattr(b,'board_mode',False) else 'ЛКМ · '+BASICS[h['style']],580,626,11,CYAN,True,maxwidth=203)
            self.text('СТИК · ДВИЖЕНИЕ' if getattr(b,'board_mode',False) else 'WASD · ДВИЖЕНИЕ',600,652,12,MUTED)
            self.text('КНОПКИ НИЖЕ' if getattr(b,'board_mode',False) else 'СМЕНА: '+(f'{b.switch_cd:.1f}с' if b.switch_cd>0 else '1 / 2 / 3'),600,674,12,MUTED)
            if h['style']=='shot':
                self.text(f'R · {b.reloads[b.hero]:.1f}с' if b.reloads[b.hero]>0 else f'ПАТРОНЫ  {b.ammo[b.hero]} / 6 · R',600,692,11,GOLD,True)
            if b.stances.get(b.hero,0)>0:self.text(f'{HEROES[b.hero]["ultimate"]} · {b.stances[b.hero]:.1f}с',640,578,20,GOLD,True,'center')
            if b.feedback_time>0:self.text(b.feedback,640,171,17,GOLD,True,'center')
            if b.training:
                self.button((220,630,150,34),'← ГЕРОЙ',lambda:b.training_cycle(-1),small=True)
                self.button((380,630,150,34),'ГЕРОЙ →',lambda:b.training_cycle(1),small=True)
                self.text('ВСЕ 11 · БЕЗ ЗАТРАТ',228,678,12,MUTED)
            for x,key,label,cooldown,ready,action in [
                (794,'SPACE','Рывок',b.dash_cd,b.dash_cd<=0,b.dash),
                (948,'Q',h['skill'],b.skills[b.hero],b.skills[b.hero]<=0,b.skill),
                (1102,'E','Ультимейт',100-b.energy[b.hero],b.energy[b.hero]>=100,b.ultimate)]:
                self.panel((x,630,138,68),(26,39,52) if ready else (21,26,41),CYAN if ready else LINE,10)
                self.text(key,x+12,637,14,CYAN if ready else MUTED,True)
                status='ГОТОВО' if ready else f'{b.energy[b.hero]:.0f}%' if key=='E' else f'{cooldown:.1f}с'
                self.text(status,x+126,640,12,GOLD if key=='E' else WHITE,True,'topright')
                self.text(label,x+12,671,12,WHITE,maxwidth=115)
                if ready:self.buttons.append((pg.Rect(x,630,138,68),action))
        self.draw_mode_hud(b)
        if b.cutin>0:
            self.panel((0,212,790,137),(26,20,46),PURPLE,0)
            picture={'bugdan':'bugdan_hearts','ilya':'ilya_beach','egor':'egor_beach'}.get(b.hero,'hero_'+b.hero)
            self.img(picture,(20,186,155,181))
            self.text(HEROES[b.hero]['name'].upper(),192,235,18,GOLD,True)
            self.text(HEROES[b.hero]['ultimate'],192,265,36,WHITE,True,maxwidth=565)
        if b.slow_time>0:
            pg.draw.rect(s,CYAN,(3,3,W-6,H-6),4)
