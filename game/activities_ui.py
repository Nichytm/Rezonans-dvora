"""Mode selection, route decisions and objective artwork."""
import math
import pygame as pg
from worlds import MAPS,MODES,BOSSES
from battle import PERKS,V
from modes import Battle
WHITE=(235,239,250);MUTED=(139,154,184);CYAN=(115,232,228);GOLD=(255,205,120);RED=(245,110,140);LINE=(44,54,77);PANEL=(19,26,43)

class Activities:
    def activities(self):
        u=self.ui;u.text('ДВОР СТАЛ БОЛЬШЕ',36,107,32,WHITE,True)
        u.text('Шесть режимов · шесть карт · пять поганцев. Всё открыто для игры.',38,153,16,MUTED)
        for i,(key,data) in enumerate(MODES.items()):
            x=36+i%3*411;y=192+i//3*224;c=data['color']
            u.panel((x,y,388,205),PANEL,c);u.tag(data['tag'],x+17,y+15,c)
            u.text(data['name'],x+17,y+51,24,WHITE,True,maxwidth=354)
            u.paragraph(data['desc'],x+17,y+91,350,15,MUTED,22)
            wins=sum(v for k,v in self.profile.data['activity_wins'].items() if k.startswith(key+':'))
            u.button((x+17,y+153,354,37),f'ИГРАТЬ  →    ПОБЕД: {wins}',lambda k=key:self.configure_activity(k),small=True)
        u.button((36,658,386,44),'СЮЖЕТНЫЕ РАЗЛОМЫ',lambda:self.navigate('missions'),small=True)
        u.button((447,658,386,44),'ИСПЫТАТЬ ГЕРОЕВ',self.training,small=True)
        u.button((858,658,386,44),'МОЙ ОТРЯД',lambda:self.navigate('roster'),small=True)

    def configure_activity(self,mode):
        self.activity_mode=mode;self.modal='activity_setup'

    def cycle_map(self,delta):self.activity_map=(self.activity_map+delta)%len(MAPS)
    def cycle_boss(self,delta):self.activity_boss=(self.activity_boss+delta)%len(BOSSES)
    def cycle_difficulty(self):self.activity_difficulty=self.activity_difficulty%3+1

    def start_activity(self,mode=None,map_key=None,boss_id=None,difficulty=None):
        mode=mode or self.activity_mode;map_key=map_key or list(MAPS)[self.activity_map];boss_id=boss_id or list(BOSSES)[self.activity_boss]
        difficulty=difficulty or self.activity_difficulty
        self.battle=Battle(self.profile,1,self.sound.play,mode=mode,map_key=map_key,boss_id=boss_id,difficulty=difficulty)
        self.page='battle';self.modal=None;self.paused=False;self.edit_checked=False;self.pressed.clear();self.sound.music('battle')

    def activity_setup(self):
        self.overlay();u=self.ui;mode=self.activity_mode;key=list(MAPS)[self.activity_map];m=MAPS[key];boss=list(BOSSES)[self.activity_boss]
        u.panel((104,66,1072,602));u.text(MODES[mode]['name'],140,91,31,WHITE,True)
        u.text('Выбери место, сложность и соперника',141,138,16,MUTED)
        u.map_preview(key,(141,181,529,205));u.tag(m['tag'],158,195,m['accent'])
        u.text(m['name'],141,406,26,WHITE,True);u.paragraph(m['desc'],141,447,530,16,MUTED,23)
        u.button((141,524,253,38),'← КАРТА',lambda:self.cycle_map(-1),small=True)
        u.button((412,524,258,38),'КАРТА →',lambda:self.cycle_map(1),small=True)
        if mode in ('duel','expedition'):
            u.img('hero_'+boss,(738,181,120,145));u.text('ТВОЙ СОПЕРНИК',882,191,12,GOLD,True)
            u.paragraph(BOSSES[boss]['name'],882,224,226,22,WHITE,27)
            u.paragraph(BOSSES[boss]['title'],722,344,412,16,CYAN,23)
            u.button((722,414,189,38),'← ПОГАНЕЦ',lambda:self.cycle_boss(-1),small=True)
            u.button((929,414,207,38),'ПОГАНЕЦ →',lambda:self.cycle_boss(1),small=True)
        else:
            u.text('ТВОЯ ЗАДАЧА',722,187,14,CYAN,True);u.paragraph(MODES[mode]['desc'],722,222,412,22,WHITE,31)
            u.text('Бой идёт до выполнения задачи',722,383,16,MUTED)
            u.text('или до истечения времени.',722,408,16,MUTED)
        names={1:'ОБЫЧНАЯ',2:'СЛОЖНАЯ',3:'КОШМАР'}
        u.button((722,474,414,42),'СЛОЖНОСТЬ: '+names[self.activity_difficulty]+'  →',self.cycle_difficulty,small=True)
        u.text('Первый успех: 600 кристаллов за каждую сложность.',722,530,13,GOLD,maxwidth=414)
        u.button((141,596,253,44),'НАЗАД',lambda:setattr(self,'modal',None))
        u.button((412,596,724,44),'НАЧАТЬ  →',self.start_activity,True)

    def route_overlay(self):
        b=self.battle;self.overlay();u=self.ui
        u.text(f'КОМНАТА {b.room} ПРОЙДЕНА',640,74,32,CYAN,True,'center')
        u.text('Выбери маршрут. Здоровье, энергия и усиления сохраняются.',640,122,17,WHITE,False,'center')
        for i,choice in enumerate(b.route_choices):
            x=124+i*531;m=MAPS[choice['map']];perk=PERKS[choice['perk']];c=CYAN if i==0 else GOLD
            u.panel((x,182,501,428),PANEL,c);u.map_preview(choice['map'],(x+1,183,499,145))
            u.tag('ПРИВАЛ' if i==0 else 'РИСК + НАГРАДА',x+22,201,c)
            u.text(m['name'],x+22,351,25,WHITE,True)
            u.paragraph('+30% здоровья живым героям и обычные враги.' if i==0 else 'Больше бронированных врагов. +35% монет за итоговую победу.',x+22,394,458,17,MUTED,25)
            u.text('УСИЛЕНИЕ: '+perk[0],x+22,468,17,c,True)
            u.text(perk[1],x+22,499,14,MUTED,maxwidth=457)
            u.button((x+22,548,457,42),'ПОЙТИ ЭТИМ ПУТЁМ',lambda index=i:b.choose_route(index),True,small=True)

class ObjectiveArt:
    def map_preview(self,key,rect):
        name='map_'+key
        if name not in self.images:self.images[name]=self.world_background(key).subsurface((48,180,1184,416)).copy()
        self.img(name,rect,'cover')

    def draw_mode_world(self,b,t):
        mode=getattr(b,'mode',None)
        if mode=='escort':
            p=b.core_pos
            pg.draw.line(self.s,(193,170,110),(220,400),(1080,400),3)
            pg.draw.circle(self.s,(121,224,195),p,130,1)
            for dx in (-25,25):pg.draw.circle(self.s,(27,31,47),p+V(dx,18),12)
            pg.draw.rect(self.s,(191,132,73),(p.x-43,p.y-31,86,48),border_radius=7)
            pg.draw.rect(self.s,(251,200,128),(p.x-43,p.y-31,86,48),3,border_radius=7)
            self.world_sprite('crate',(p.x-25,p.y-58,50,45))
            self.bar((p.x-46,p.y-74,92,7),b.core_hp,b.core_max,(119,235,190))
            self.text('ПОСЫЛКА',1080,427,12,(243,219,165),True,'center')
        elif mode=='heist':
            for p,label,color in [(V(140,400),'ТАЙНИК',(96,238,207)),(V(1130,490),'ВЫХОД',(250,210,127))]:
                pg.draw.circle(self.s,color,p,66,3);self.text(label,p.x,p.y+83,13,color,True,'center')
            self.bar((92,477,96,5),b.deposit_timer,1.2,(96,238,207))
            if b.deposited>=9:self.bar((1082,577,96,5),b.escape_timer,4,(250,210,127))
            for loot in b.loot:
                p=loot['pos']+V(0,math.sin(t*4+loot['pos'].x)*5)
                pg.draw.polygon(self.s,(121,237,234),[p+V(0,-15),p+V(10,0),p+V(0,15),p+V(-10,0)])
                pg.draw.line(self.s,WHITE,p-V(0,11),p+V(0,10),2)
            if b.carry:self.text('◆'*b.carry,b.pos.x,b.pos.y-118,18,GOLD,True,'center')
        elif mode=='capture':
            for i,z in enumerate(b.beacons):
                p=z['pos'];c=CYAN if z['owned'] else (153,163,201)
                pg.draw.circle(self.s,c,p,72,3)
                pg.draw.arc(self.s,GOLD,(p.x-67,p.y-67,134,134),-math.pi/2,-math.pi/2+math.tau*z['value']/100,7)
                self.text('ЗАХВАЧЕН' if z['owned'] else f'{i+1} · {int(z["value"])}%',p.x,p.y,18,c,True,'center')
        elif mode=='survival':
            layer=pg.Surface((1280,613),pg.SRCALPHA);pg.draw.rect(layer,(89,39,100,90),(48,180,1184,416))
            pg.draw.circle(layer,(0,0,0,0),b.safe_center,int(b.safe_radius));self.s.blit(layer,(0,0))
            pg.draw.circle(self.s,(174,242,144),b.safe_center,int(b.safe_radius),3)
        if getattr(b,'map_key',None)=='depot' and b.map_clock>=9 and 2<b.map_clock%9<3.2:
            x=-520+(b.map_clock%9-2)*1600
            for off in (0,183,366):
                pg.draw.rect(self.s,(105,142,170),(x+off,280,175,58),border_radius=10)
                pg.draw.rect(self.s,(211,185,121),(x+off,325,175,7))
                for window in (15,58,101):pg.draw.rect(self.s,(23,47,70),(x+off+window,289,32,20),border_radius=3)

    def draw_mode_hud(self,b):
        mode=getattr(b,'mode',None)
        if not mode:return
        self.panel((24,20,342,70),(16,22,38),LINE,12)
        self.text(MODES[mode]['tag'],42,33,11,MODES[mode]['color'],True)
        self.text(MODES[mode]['name'],42,54,21,WHITE,True,maxwidth=310)
        self.panel((24,95,1030,44),(16,22,38),LINE,8)
        self.text(b.objective_text(),41,116,15,CYAN,True,'midleft',maxwidth=993)
        if b.mode!='expedition':self.text(f'ЛИМИТ {int(b.mode_limit)}с',1238,88,11,MUTED,False,'topright')
