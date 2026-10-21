"""Резонанс Двора — an offline photo gacha action RPG prototype."""
import argparse
import math
import os
from pathlib import Path
import sys
import time

os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import pygame as pg
from model import Profile,HEROES,RARITIES,STAGES,CONTRACTS
from battle import PERKS
from modes import Battle
from activities_ui import Activities
from worlds import MAPS,MODES,BOSSES
from audio import Sound
from cinema import Cinema,edit_due
from extras import Extras
from ui import UI,W,H,BG,PANEL,LINE,WHITE,MUTED,CYAN,PURPLE,GOLD,RED

ROOT=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
ASSETS=Path(getattr(sys,'_MEIPASS',ROOT))/'assets'

class Game(Activities,Extras):
    def __init__(self,save_path=None,headless=False):
        pg.mixer.pre_init(44100,-16,2,512);pg.init()
        self.profile=Profile(save_path or ROOT/'saves'/'profile.json')
        self.fullscreen=self.profile.data['fullscreen'] and not headless and sys.platform!='emscripten'
        self.screen=pg.display.set_mode((0,0) if self.fullscreen else (1280,720),pg.FULLSCREEN if self.fullscreen else pg.RESIZABLE)
        pg.display.set_caption('РЕЗОНАНС ДВОРА 0.4 — Большой район')
        self.canvas=pg.Surface((W,H));self.ui=UI(self.canvas,ASSETS)
        icon=pg.Surface((48,48),pg.SRCALPHA);pg.draw.polygon(icon,CYAN,[(24,2),(45,24),(24,46),(3,24)],4);pg.draw.line(icon,PURPLE,(24,10),(24,38),4);pg.display.set_icon(icon)
        self.sound=Sound(self.profile,ASSETS);self.cinema=Cinema(ASSETS,self.sound)
        self.activity_mode='expedition';self.activity_map=0;self.activity_boss=0;self.activity_difficulty=1
        self.roster_page=0;self.voice_hero=0;self.edit_checked=False
        self.page='home';self.selected='smiler';self.stage=min(6,self.profile.data['cleared']+1)
        self.t=0;self.running=True;self.window_size=(1280,720)
        self.battle=None;self.paused=False;self.modal=None;self.toast='';self.toast_time=0
        self.results=[];self.reveal=0;self.reveal_sound=False;self.pressed=set();self.scale=1;self.offset=(0,0)
        self.clock=pg.time.Clock();self.headless=headless;self.sound.music('menu')
        self.web_move=None;self.web_aim=None;self.web_firing=False
        if self.profile.warning:self.message(self.profile.warning)

    def message(self,text):self.toast=text;self.toast_time=3.2

    def navigate(self,page):
        self.page=page;self.modal=None;self.sound.music('menu')

    def toggle(self,key):
        self.profile.data[key]=not self.profile.data[key];self.profile.save()
        if key=='sound' and not self.profile.data[key] and self.sound.ready:pg.mixer.stop()
        self.sound.music('battle' if self.page=='battle' else 'menu')

    def summon(self,count):
        result=self.profile.summon(count)
        if not result:self.message('Не хватает кристаллов. Их можно получить в разломах.');return
        self.results=result;self.reveal=0;self.reveal_sound=False;self.modal='summon';self.sound.play('summon')

    def upgrade(self):
        if self.profile.upgrade(self.selected):self.sound.play('rare');self.message('Уровень повышен. Сила атаки и здоровье выросли.')
        else:self.message('Нужно больше монет и эссенции, либо уже достигнут 20 уровень.')

    def awaken(self):
        if self.profile.awaken(self.selected):self.sound.play('rare');self.message('Пробуждение! +12% к базовым характеристикам.')
        else:self.message('Осколки выпадают за повторных персонажей в призыве.')

    def select(self,h):self.selected=h

    def start_battle(self,stage,endless=False,training=False):
        if not endless and stage>min(6,self.profile.data['cleared']+1):return
        self.stage=stage;self.battle=Battle(self.profile,stage,self.sound.play,endless,training);self.edit_checked=False;self.page='battle';self.modal=None
        self.paused=False;self.pressed.clear();self.sound.music('battle')

    def claim(self,key):
        if self.profile.claim_contract(key):self.sound.play('rare');self.message('Контракт выполнен. Награда получена!')

    def choose_perk(self,key):
        if self.battle.choose_perk(key):self.pressed.clear()

    def quit_game(self):
        if sys.platform=='emscripten':self.message('Прогресс сохранён. Вкладку можно закрыть.');self.profile.save()
        else:self.running=False

    def leave_battle(self):
        destination='activities' if getattr(self.battle,'mode',None) else 'missions'
        self.battle=None;self.paused=False;self.pressed.clear();self.navigate(destination)

    def home(self):
        u=self.ui;p=self.profile
        u.img('night',(635,95,615,513),'cover',115)
        u.glow((948,325),PURPLE,265,48)
        pg.draw.circle(self.canvas,(69,65,112),(961,327),186,1)
        pg.draw.circle(self.canvas,(69,65,112),(961,327),210,1)
        for i in range(10):
            a=i*math.tau/10+self.t*.06
            x=961+210*math.cos(a);y=327+210*math.sin(a)
            pg.draw.circle(self.canvas,PURPLE,(int(x),int(y)),3)
        u.img('hero_hood',(682,114,240,437))
        u.img('hero_bugdan',(852,137,309,394))
        u.tag('ВЕРСИЯ 0.4  /  ШЕСТЬ СПОСОБОВ УСТРОИТЬ ХАОС',45,121,CYAN)
        u.text('ТВОЙ ДВОР.',42,170,61,WHITE,True)
        u.text('ТВОИ ЛЕГЕНДЫ.',42,238,61,WHITE,True)
        u.text('Разлом открылся прямо у подъезда.',47,329,20,MUTED)
        u.text('Собери друзей. Разбуди силу. Верни район.',47,360,20,MUTED)
        u.button((47,420,274,58),'ВЫБРАТЬ РЕЖИМ  →',lambda:self.navigate('activities'),True)
        u.button((335,420,212,58),'ПРИЗВАТЬ ГЕРОЕВ',lambda:self.navigate('summon'))
        u.text('6 новых режимов · 6 карт · 5 боссов из твоего отряда',48,496,14,CYAN)
        u.tag('SR  /  БУГДАНЧИК · ПЛЕВАКА',845,550,PURPLE)
        u.text('ТВОЙ ОТРЯД',47,552,12,MUTED,True)
        for i,h in enumerate(p.data['team']):
            x=47+i*196;hero=HEROES[h]
            u.panel((x,579,184,91));u.img('hero_'+h,(x+7,584,59,77))
            u.text(hero['name'],x+76,596,16,WHITE,True)
            u.text(f'{hero["rarity"]}  ·  УР. {p.data["heroes"][h]["level"]}',x+76,625,12,RARITIES[hero['rarity']][1])
            u.buttons.append((pg.Rect(x,579,184,91),lambda hero=h:(self.select(hero),self.navigate('roster'))))
        u.button((669,616,196,43),'КОНТРАКТЫ',lambda:setattr(self,'modal','contracts'),small=True)
        u.button((879,616,166,43),'УПРАВЛЕНИЕ',lambda:setattr(self,'modal','help'),small=True)
        u.button((1059,616,174,43),'НАСТРОЙКИ',lambda:setattr(self,'modal','settings'),small=True)
        u.button((1115,678,120,28),'ВЫХОД',self.quit_game,small=True)
        u.button((669,668,196,34),'ЛАВКА У ПОДЪЕЗДА',self.open_shop,small=True)
        u.button((879,668,210,34),'ПОЛИГОН ГЕРОЕВ',self.training,small=True)

    def roster(self):
        u=self.ui;p=self.profile;h=self.selected;hero=HEROES[h];owned=h in p.data['heroes'];color=RARITIES[hero['rarity']][1]
        u.text('Твои герои',36,104,32,WHITE,True)
        u.text(f'{len(p.data["heroes"])} / {len(HEROES)} в коллекции · Артём = Смайлер',39,148,14,MUTED)
        for i,key in enumerate(list(HEROES)[self.roster_page*9:self.roster_page*9+9]):
            x=36+(i%3)*242;y=184+(i//3)*160
            u.compact_card(key,(x,y,231,150),p,lambda k=key:self.select(k),key==h)
        u.panel((782,108,462,557))
        u.glow((1130,278),hero['color'],150,25);u.img('hero_'+h,(1007,153,211,220))
        u.tag(hero['rarity']+'  /  '+RARITIES[hero['rarity']][0],806,132,color)
        u.text(hero['name'],805,178,36,WHITE,True)
        u.text(hero['title'],807,226,20,color)
        if owned:
            stats=p.stats(h);own=p.data['heroes'][h]
            u.text(f'УРОВЕНЬ {own["level"]} / 20',808,279,14,WHITE,True)
            u.text(f'АТК  {stats["atk"]}    HP  {stats["hp"]}',808,307,16,MUTED)
            u.text('ПРОБУЖДЕНИЕ  '+str(own['stars'])+' / 5',808,337,12,GOLD,True)
            u.bar((808,368,407,5),own['xp'],own['level']*100,PURPLE)
            u.text(f'Опыт: {own["xp"]} / {own["level"]*100}',808,380,12,MUTED)
        else:u.text('Получи героя в призыве',808,312,16,MUTED)
        u.text('Q   '+hero['skill'],808,412,17,CYAN,True,maxwidth=410)
        u.text('E   '+hero['ultimate'],808,443,17,GOLD,True,maxwidth=410)
        if owned:
            cost=own['level']*90;can=own['level']<20 and p.data['gold']>=cost and p.data['essence']>=3
            u.button((807,484,410,44),f'УРОВЕНЬ +1   /   {cost} МОНЕТ + 3 ЭССЕНЦИИ',self.upgrade,True,can,True)
            shards=(own['stars']+1)*20
            u.button((807,538,410,41),f'ПРОБУДИТЬ   /   {own["shards"]} из {shards} осколков',self.awaken,enabled=own['stars']<5 and own['shards']>=shards,small=True)
            u.text('ПОСТАВИТЬ В СЛОТ ОТРЯДА',808,591,11,MUTED,True)
            for slot in range(3):
                u.button((807+slot*140,610,130,36),f'СЛОТ {slot+1}',lambda s=slot:p.set_slot(h,s),small=True)
        else:u.button((807,507,410,48),'ПЕРЕЙТИ К ПРИЗЫВУ',lambda:self.navigate('summon'),True)
        u.button((36,674,196,34),'← СТРАНИЦА',lambda:self.roster_page_by(-1),small=True)
        u.text(f'{self.roster_page+1} / 2',274,690,15,MUTED,True,'center')
        u.button((319,674,196,34),'СТРАНИЦА →',lambda:self.roster_page_by(1),small=True)
        u.button((782,674,462,34),'ПРИЁМЫ И ИСПЫТАНИЕ ГЕРОЯ',lambda:setattr(self,'modal','kit'),small=True)

    def summon_page(self):
        u=self.ui;p=self.profile
        u.panel((35,109,801,453),(19,22,40))
        u.glow((574,324),GOLD,230,38);u.glow((416,320),PURPLE,210,25)
        for r in (130,160,190):pg.draw.circle(self.canvas,(93,78,103),(577,338),r,1)
        u.img('hero_hood',(373,146,233,344));u.img('hero_ilya',(548,153,249,338))
        u.tag('ПОСТОЯННЫЙ ПРИЗЫВ',59,133,GOLD)
        u.text('ЛЕГЕНДЫ',58,191,47,WHITE,True)
        u.text('ПОДЪЕЗДА',58,244,47,WHITE,True)
        u.text('Иллюша. Злой. Легендарка.',62,316,18,GOLD)
        u.text('Одиннадцать героев района.',62,350,16,MUTED)
        u.text('Одна очень странная судьба.',62,378,16,MUTED)
        u.tag('SSR  /  ИЛЛЮША',573,507,GOLD)
        u.panel((859,109,385,453))
        u.text('Как работает призыв',884,135,25,WHITE,True)
        for y,rarity,percent in [(191,'SSR','3%'),(231,'SR','17%'),(271,'R','80%')]:
            u.text(RARITIES[rarity][0],885,y,15,RARITIES[rarity][1],True)
            u.text(percent,1215,y,19,WHITE,True,'topright')
        pg.draw.line(self.canvas,LINE,(885,314),(1215,314))
        u.text('ГАРАНТ ЛЕГЕНДЫ',885,334,12,GOLD,True)
        u.text(f'{p.data["pity"]} / 60',1217,328,23,GOLD,True,'topright')
        u.bar((885,368,332,7),p.data['pity'],60,GOLD)
        u.text('SSR не позднее 60-го призыва.',885,391,15,MUTED)
        u.text('SR или SSR каждые 10 призывов.',885,419,15,MUTED)
        u.text(f'Счётчик SR+: {p.data["epic_pity"]} / 10',885,448,15,PURPLE)
        u.text('Гарант сохраняется между призывами.',885,485,13,MUTED)
        u.text('Дубликат = осколки + 2 эссенции.',885,512,13,MUTED)
        u.button((35,582,389,66),'ПРИЗВАТЬ ×1   /   160',lambda:self.summon(1),enabled=p.data['crystals']>=160)
        u.button((442,582,394,66),'ПРИЗВАТЬ ×10   /   1 600',lambda:self.summon(10),True,p.data['crystals']>=1600)
        u.button((859,582,385,66),'ЗАРАБОТАТЬ В РАЗЛОМАХ  →',lambda:self.navigate('missions'))
        u.text('Только игровая валюта. Все персонажи доступны за прохождение.',37,679,13,MUTED)

    def missions(self):
        u=self.ui;p=self.profile
        u.text('На той стороне двора',36,106,32,WHITE,True)
        u.button((956,108,287,38),'ПОЛИГОН · ВСЕ ГЕРОИ',self.training,small=True)
        u.text('Выбирай усиления между волнами. Защищай резонатор. Разрушай якоря.',38,153,16,MUTED)
        for i,(name,desc,bg) in enumerate(STAGES):
            x=36+(i%3)*411;y=190+(i//3)*201;unlocked=i<=p.data['cleared'];complete=i<p.data['cleared']
            u.panel((x,y,388,193))
            u.img(bg,(x+1,y+1,386,96),'cover',105 if unlocked else 40)
            u.tag(f'{i+1:02}  /  '+('ПРОЙДЕНО' if complete else 'РАЗЛОМ' if unlocked else 'ЗАКРЫТО'),x+15,y+14,CYAN if complete else PURPLE if unlocked else MUTED)
            u.text(name,x+16,y+63,25,WHITE if unlocked else MUTED,True)
            mode='ЗАЩИТА' if i+1 in (2,5) else 'ЯКОРЯ' if i+1 in (3,6) else 'ЗАЧИСТКА'
            stars=p.data['stage_stars'].get(str(i+1),0)
            u.text(f'{mode}  ·  Ур. {1+i*2}  ·  Рейтинг {stars}/3',x+17,y+104,13,MUTED)
            u.button((x+16,y+136,355,42),'ВОЙТИ  →' if unlocked else 'ПРОЙДИ ПРЕДЫДУЩИЙ РАЗЛОМ',lambda n=i+1:self.start_battle(n),accent=unlocked and not complete,enabled=unlocked,small=True)
        u.panel((36,599,1207,105))
        u.text('БЕСКОНЕЧНАЯ АРЕНА',54,617,20,GOLD,True)
        u.text(f'Босс каждые 3 волны. Рекорд: {p.data["best_endless"]}. Награда за каждую пройденную волну.',54,653,14,MUTED)
        u.button((864,621,356,54),'НАЧАТЬ ЗАБЕГ  →',lambda:self.start_battle(1,True),True)

    def overlay(self):
        shade=pg.Surface((W,H),pg.SRCALPHA);shade.fill((4,7,17,225));self.canvas.blit(shade,(0,0));self.ui.buttons=[]

    def summon_overlay(self):
        u=self.ui;self.overlay()
        if self.reveal<1.6:
            best=max((HEROES[r['id']]['rarity'] for r in self.results),key=lambda r:['R','SR','SSR'].index(r));col=RARITIES[best][1]
            u.glow((640,338),col,280,55)
            for i in range(4):
                radius=int(70+i*36+math.sin(self.reveal*5+i)*12)
                pg.draw.circle(self.canvas,col,(640,338),radius,2)
            for i in range(12):
                a=i*math.tau/12+self.reveal*1.8;r=245-self.reveal*64
                pg.draw.line(self.canvas,col,(640+math.cos(a)*r,338+math.sin(a)*r),(640+math.cos(a)*(r+30),338+math.sin(a)*(r+30)),2)
            u.text('КТО ОТВЕТИТ НА ЗОВ?',640,573,22,WHITE,True,'center')
            u.button((1050,650,185,40),'ПРОПУСТИТЬ',lambda:setattr(self,'reveal',1.7),small=True)
            return
        if not self.reveal_sound:self.sound.play('rare');self.reveal_sound=True
        u.text('РАЙОН ОТВЕТИЛ',640,58,33,WHITE,True,'center')
        u.text('Новые герои и осколки уже в коллекции',640,101,16,MUTED,False,'center')
        if len(self.results)==1:
            r=self.results[0];u.card(r['id'],(505,159,270,386),self.profile,selected=True)
            u.text('НОВЫЙ ГЕРОЙ' if r['new'] else f'+{r["shards"]} ОСКОЛКОВ · +2 ЭССЕНЦИИ',640,567,19,CYAN,True,'center')
        else:
            for i,r in enumerate(self.results):
                x=64+(i%5)*234;y=151+(i//5)*225
                u.card(r['id'],(x,y,218,181),self.profile,selected=r['new'])
                u.text('НОВЫЙ!' if r['new'] else f'+{r["shards"]} ОСКОЛКОВ',x+109,y+193,12,CYAN if r['new'] else MUTED,True,'midtop')
        u.button((451,635,378,52),'ЗАБРАТЬ И ПРОДОЛЖИТЬ',lambda:setattr(self,'modal',None),True)

    def help_overlay(self):
        self.overlay();u=self.ui;u.panel((259,118,762,502))
        u.text('Добро пожаловать во двор',296,147,29,WHITE,True)
        rows=[('W A S D / стрелки','Двигаться по арене'),('МЫШЬ + ЛКМ','Целиться и атаковать (можно зажать)'),('SPACE','Рывок с короткой неуязвимостью'),('Q','Особая способность выбранного героя'),('E','Ультимейт, когда энергия достигнет 100%'),('1 / 2 / 3 · R','Сменить героя · перезарядить винтовку'),('ESC / F11 / M','Пауза / полный экран / звук')]
        for i,(key,desc) in enumerate(rows):
            u.text(key,298,207+i*40,16,CYAN,True);u.text(desc,535,207+i*40,16,WHITE)
        u.text('Рывок в последний момент замедляет время. Каждая 3-я атака сильнее.',298,509,14,MUTED)
        u.button((298,552,682,43),'ПОГНАЛИ',lambda:setattr(self,'modal',None),True)

    def contracts_overlay(self):
        self.overlay();u=self.ui;u.panel((220,90,840,559));u.text('Контракты района',252,118,30,WHITE,True)
        u.text('Прогресс учитывается после завершения боя, включая поражения.',252,165,14,MUTED)
        for i,(key,c) in enumerate(CONTRACTS.items()):
            y=206+i*85;progress=self.profile.data['progress'][c['stat']];claimed=key in self.profile.data['claimed']
            u.text(c['name'],252,y,20,WHITE,True);u.text(c['desc']+f'  ·  {min(progress,c["target"])} / {c["target"]}',252,y+29,14,MUTED)
            u.bar((252,y+55,435,4),progress,c['target'],CYAN)
            u.button((728,y+5,294,46),'ПОЛУЧЕНО' if claimed else f'ЗАБРАТЬ {c["crystals"]} КРИСТ.',lambda k=key:self.claim(k),True,not claimed and progress>=c['target'],True)
        u.button((252,570,769,45),'ГОТОВО',lambda:setattr(self,'modal',None),True)

    def perk_overlay(self):
        b=self.battle;self.overlay();u=self.ui
        u.text(f'ВОЛНА {b.completed_waves} ПРОЙДЕНА',640,115,34,CYAN,True,'center')
        u.text('Выбери одно усиление. Оно действует до конца этого забега.',640,166,18,WHITE,False,'center')
        u.text('Живые герои восстановили 12% здоровья. Бой на паузе.',640,199,14,MUTED,False,'center')
        for i,key in enumerate(b.choices):
            name,desc,kind=PERKS[key];x=109+i*360;col=[CYAN,PURPLE,GOLD][i]
            u.panel((x,259,340,281),PANEL,col)
            u.tag(kind,x+23,284,col);u.text(str(i+1),x+292,293,25,col,True,'center')
            u.text(name,x+23,344,24,WHITE,True,maxwidth=300)
            u.paragraph(desc,x+23,387,294,16,MUTED)
            u.button((x+23,457,294,53),'ВЫБРАТЬ',lambda k=key:self.choose_perk(k),True)
        u.text('Усиления можно складывать. Комбинируй их со способностями отряда.',640,594,15,MUTED,False,'center')
        if b.endless:u.button((436,644,407,40),'ЗАВЕРШИТЬ ЗАБЕГ С НАГРАДАМИ',lambda:b.finish(True),small=True)

    def battle_overlay(self):
        b=self.battle;u=self.ui
        if b.done:
            self.overlay();u.panel((350,119,580,501))
            u.text('ЗАДАЧА ВЫПОЛНЕНА' if b.mode and b.won else 'ПОПЫТКА ЗАВЕРШЕНА' if b.mode else 'ЗАБЕГ ЗАВЕРШЁН' if b.endless else 'РАЗЛОМ ЗАКРЫТ' if b.won else 'РАЗЛОМ ПОБЕДИЛ',640,151,34,CYAN if b.won else RED,True,'midtop')
            summary=f'Пройдено волн: {b.completed_waves}' if b.endless else f'Рейтинг: {b.stars} / 3  ·  '+('Отличная работа!' if b.won else 'Усиль отряд и попробуй ещё.')
            if b.mode:summary=MODES[b.mode]['name']+' · '+('Задача выполнена!' if b.won else 'Попробуй другую тактику.')
            u.text(summary,640,207,17,MUTED,False,'midtop')
            u.text(f'{b.kills} монстров  ·  {int(b.elapsed)//60}:{int(b.elapsed)%60:02} в бою',640,247,16,WHITE,False,'midtop')
            result=b.result
            for i,(key,title,col) in enumerate([('crystals','КРИСТАЛЛЫ',CYAN),('gold','МОНЕТЫ',GOLD),('essence','ЭССЕНЦИЯ',PURPLE)]):
                x=386+i*174;u.panel((x,292,160,87));u.text('+'+str(result[key]),x+80,304,29,col,True,'midtop');u.text(title,x+80,351,11,MUTED,True,'midtop')
            u.text(f'+{result["xp"]} опыта каждому герою отряда',640,399,17,WHITE,False,'midtop')
            if result['first']:u.text('БОНУС ПЕРВОГО ПРОХОЖДЕНИЯ ПОЛУЧЕН',640,432,12,GOLD,True,'midtop')
            if result['levels']:u.text('Уровень повышен: '+', '.join(HEROES[h]['name'] for h in result['levels']),640,457,13,CYAN,False,'midtop',maxwidth=490)
            u.button((389,508,501,47),'В ШТАБ РАЗЛОМОВ',self.leave_battle,True)
            u.button((389,566,501,34),'ПОВТОРИТЬ БОЙ',lambda:self.start_activity(b.mode,b.map_key,b.boss_choice,b.difficulty) if b.mode else self.start_battle(b.stage,b.endless),small=True)
        elif self.paused:
            self.overlay();u.panel((427,220,426,278));u.text('ПАУЗА',640,246,35,WHITE,True,'midtop')
            u.button((462,310,356,51),'ПРОДОЛЖИТЬ',lambda:setattr(self,'paused',False),True)
            u.button((462,378,356,44),'ЗАВЕРШИТЬ ЗАБЕГ' if b.endless else 'ПОКИНУТЬ БОЙ',lambda:b.finish(True) if b.endless else self.leave_battle())
            u.text('Награды за пройденные волны сохранятся.' if b.endless else 'При выходе награды за бой не выдаются.',640,448,13,MUTED,False,'midtop')
        elif b.route_pending:self.route_overlay()
        elif b.intermission:self.perk_overlay()

    def draw(self):
        u=self.ui;u.mouse=self.mouse_pos()
        if self.page=='battle':
            u.arena(self.battle,self.t,self.paused);self.battle_overlay()
        else:
            u.base(self.t);u.top(self.profile,self.page,self.navigate)
            {'home':self.home,'roster':self.roster,'summon':self.summon_page,'missions':self.missions,'activities':self.activities}[self.page]()
            if self.modal=='summon':self.summon_overlay()
            elif self.modal=='help':self.help_overlay()
            elif self.modal=='settings':self.settings_overlay()
            elif self.modal=='contracts':self.contracts_overlay()
            elif self.modal=='voices':self.voices_overlay()
            elif self.modal=='shop':self.shop_overlay()
            elif self.modal=='kit':self.kit_overlay()
            elif self.modal=='activity_setup':self.activity_setup()
        if self.cinema.active:self.cinema.draw(u)
        if self.toast_time>0:
            u.panel((200,11,880,54),(37,48,62),CYAN,10);u.text(self.toast,640,38,16,WHITE,False,'center',maxwidth=840)
        sw,sh=self.screen.get_size();self.scale=min(sw/W,sh/H)
        size=(max(1,round(W*self.scale)),max(1,round(H*self.scale)));self.offset=((sw-size[0])//2,(sh-size[1])//2)
        self.screen.fill((4,7,13))
        if size==(W,H):self.screen.blit(self.canvas,self.offset)
        else:self.screen.blit(pg.transform.smoothscale(self.canvas,size),self.offset)
        pg.display.flip()

    def mouse_pos(self):
        x,y=getattr(self,'touch_pos',None) or pg.mouse.get_pos();return ((x-self.offset[0])/self.scale,(y-self.offset[1])/self.scale)

    def fullscreen_toggle(self):
        if sys.platform=='emscripten':
            import platform
            platform.window.rdFullscreen();return
        self.fullscreen=not self.fullscreen
        if self.fullscreen:
            self.window_size=self.screen.get_size();self.screen=pg.display.set_mode((0,0),pg.FULLSCREEN)
        else:self.screen=pg.display.set_mode(self.window_size,pg.RESIZABLE)
        self.profile.data['fullscreen']=self.fullscreen;self.profile.save()

    def events(self):
        for event in pg.event.get():
            if event.type==pg.QUIT:self.running=False
            elif event.type==pg.FINGERDOWN:
                sw,sh=self.screen.get_size();self.touch_pos=(event.x*sw,event.y*sh)
                for rect,callback in reversed(self.ui.buttons):
                    if rect.collidepoint(self.mouse_pos()):self.sound.play('click');callback();break
            elif event.type==pg.MOUSEMOTION and not getattr(event,'touch',False):self.touch_pos=None
            elif self.cinema.active:
                if event.type==pg.KEYDOWN:
                    if event.key==pg.K_ESCAPE:self.cinema.close()
                    elif event.key==pg.K_SPACE:self.cinema.pause()
                    elif event.key==pg.K_F11:self.fullscreen_toggle()
                elif event.type==pg.WINDOWFOCUSLOST and not self.cinema.paused:self.cinema.pause()
                elif event.type==pg.MOUSEBUTTONDOWN and event.button==1 and not getattr(event,'touch',False):
                    for rect,callback in reversed(self.ui.buttons):
                        if rect.collidepoint(self.mouse_pos()):callback();break
                continue
            elif event.type==pg.WINDOWFOCUSLOST:
                self.pressed.clear()
                if self.page=='battle' and not self.battle.done:self.paused=True
            elif event.type==pg.KEYUP:self.pressed.discard(getattr(event,'scancode',0))
            elif event.type==pg.KEYDOWN:
                sc=getattr(event,'scancode',0);self.pressed.add(sc)
                if event.key==pg.K_F11:self.fullscreen_toggle()
                elif event.key==pg.K_m or sc==16:self.toggle('sound')
                elif event.key==pg.K_ESCAPE:
                    if self.modal=='summon':
                        if self.reveal<1.6:self.reveal=1.7
                        else:self.modal=None
                    elif self.modal:self.modal=None
                    elif self.page=='battle' and not self.battle.done:self.paused=not self.paused;self.pressed.clear()
                    elif self.page!='home' and self.page!='battle':self.navigate('home')
                elif self.page=='battle' and not self.paused and not self.battle.done:
                    if self.battle.route_pending:
                        if event.key in (pg.K_1,pg.K_2):self.battle.choose_route(event.key-pg.K_1)
                    elif self.battle.intermission:
                        if event.key in (pg.K_1,pg.K_2,pg.K_3):self.choose_perk(self.battle.choices[event.key-pg.K_1])
                    elif event.key==pg.K_SPACE:self.battle.dash()
                    elif sc==21 or event.key==pg.K_r:self.battle.reload()
                    elif event.key==pg.K_TAB and self.battle.training:self.battle.training_cycle(1)
                    elif sc==20 or event.key==pg.K_q:self.battle.skill()
                    elif sc==8 or event.key==pg.K_e:self.battle.ultimate()
                    elif event.key in (pg.K_1,pg.K_2,pg.K_3):self.battle.switch(event.key-pg.K_1)
            elif event.type==pg.MOUSEBUTTONDOWN and event.button==1 and not getattr(event,'touch',False):
                pos=self.mouse_pos()
                for rect,callback in reversed(self.ui.buttons):
                    if rect.collidepoint(pos):self.sound.play('click');callback();break

    def step(self,dt):
        self.t+=dt;self.toast_time=max(0,self.toast_time-dt)
        if self.cinema.active:self.cinema.update(dt);return
        if self.modal=='summon':self.reveal+=dt
        if self.page=='battle' and not self.paused and not self.battle.done:
            keys=pg.key.get_pressed();move=(int(7 in self.pressed or keys[pg.K_RIGHT])-int(4 in self.pressed or keys[pg.K_LEFT]),int(22 in self.pressed or keys[pg.K_DOWN])-int(26 in self.pressed or keys[pg.K_UP]))
            mouse=self.mouse_pos();firing=pg.mouse.get_pressed()[0] and 175<mouse[1]<607
            if self.web_move is not None:move=self.web_move
            if self.web_aim is not None:mouse=self.web_aim
            firing=firing or self.web_firing
            self.battle.update(dt,move,mouse,firing)
        if self.page=='battle' and self.battle.done and not self.edit_checked:
            self.edit_checked=True
            if self.battle.won and not self.battle.training and edit_due(self.profile.data):
                if self.cinema.open():
                    self.profile.data['edit_seen']+=1;self.profile.data['last_edit_at']=time.time();self.profile.save()

    def run(self):
        self.draw()
        while self.running:
            dt=min(.04,self.clock.tick(60)/1000)
            self.events();self.step(dt);self.draw()
        self.cinema.close(False);self.profile.save();pg.quit()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');parser.add_argument('--screenshots',type=Path);parser.add_argument('--display-check',type=Path)
    args=parser.parse_args()
    if args.display_check:
        import tempfile,json
        os.environ['SDL_AUDIODRIVER']='dummy'
        with tempfile.TemporaryDirectory() as temp:
            game=Game(Path(temp)/'profile.json');game.navigate('roster')
            for _ in range(8):pg.event.pump();game.draw();game.clock.tick(60)
            args.display_check.mkdir(parents=True,exist_ok=True)
            pg.image.save(game.screen,str(args.display_check/'fullscreen.png'))
            (args.display_check/'display.json').write_text(json.dumps(dict(fullscreen=game.fullscreen,screen=game.screen.get_size(),desktop=pg.display.get_desktop_sizes()[0],flags=game.screen.get_flags())),encoding='utf-8')
            pg.quit()
    elif args.smoke:
        os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            game=Game(Path(temp)/'save.json',True)
            out=args.screenshots or ROOT/'work'/'screenshots';out.mkdir(parents=True,exist_ok=True)
            for page in ('home','roster','summon','missions','activities'):
                game.navigate(page);game.draw();pg.image.save(game.canvas,str(out/f'{page}.png'))
            game.summon(10);game.reveal=2;game.draw();pg.image.save(game.canvas,str(out/'summon_results.png'))
            game.start_battle(1)
            for _ in range(180):game.battle.update(1/60,(0,0),(1000,400),True)
            game.draw();pg.image.save(game.canvas,str(out/'battle.png'))
            game.battle.skills[game.battle.hero]=0;game.battle.skill();game.battle.energy[game.battle.hero]=100;game.battle.ultimate();game.draw()
            pg.image.save(game.canvas,str(out/'ultimate.png'))
            game.battle.finish(True);game.draw();pg.image.save(game.canvas,str(out/'victory.png'))
            game.profile.data['cleared']=6
            game.start_battle(2);game.battle.wave=3;game.battle.spawn(True);game.battle.spawn(kind='armored');game.battle.spawn(kind='summoner')
            game.draw();pg.image.save(game.canvas,str(out/'defense.png'))
            game.start_battle(3)
            for _ in range(100):game.battle.update(1/60)
            game.draw();pg.image.save(game.canvas,str(out/'anchors.png'))
            game.battle.completed_waves=1;game.battle.offer_perks();game.draw();pg.image.save(game.canvas,str(out/'perks.png'))
            game.navigate('home');game.modal='contracts';game.draw();pg.image.save(game.canvas,str(out/'contracts.png'))
            game.modal='settings';game.draw();pg.image.save(game.canvas,str(out/'settings.png'))
            game.screen=pg.display.set_mode((1920,1080));game.modal=None;game.navigate('roster');game.draw()
            pg.image.save(game.screen,str(out/'fullhd.png'))
            for modal in ('voices','shop','kit'):
                game.modal=modal;game.draw();pg.image.save(game.canvas,str(out/f'{modal}.png'))
            game.modal=None;game.roster_page=1;game.selected='igor';game.draw();pg.image.save(game.canvas,str(out/'new_heroes.png'))
            for hero in HEROES:
                game.training(hero);b=game.battle;b.pos=pg.Vector2(590,400);b.invulnerable=0;b.banner_time=0
                for i,e in enumerate(b.enemies):e['pos']=pg.Vector2(690+i*75,400+(i%2)*70)
                b.attack((850,400));b.skill();b.energy[hero]=100;b.ultimate();b.cutin=0
                for _ in range(13):b.update(1/60,(0,0),(850,400),True)
                game.draw();pg.image.save(game.canvas,str(out/f'hero_{hero}.png'))
            assert game.sound.ready and 'sword' in game.sound.sounds and 'bugdanchik_attack' in game.sound.voices
            assert game.cinema.open(), 'Bundled video failed to open'
            for _ in range(100):game.cinema.update(.04)
            assert game.cinema.frame is not None
            game.draw();pg.image.save(game.canvas,str(out/'edit3000.png'))
            for _ in range(550):game.cinema.update(.04)
            assert not game.cinema.active, 'Video did not finish'
            from v4_check import render_check
            render_check(game,out)
            pg.quit();print('SMOKE OK: all screens rendered, skills, summons, rewards and save executed.')
    else:Game().run()

if __name__=='__main__':
    try:main()
    except Exception:
        import traceback
        log=traceback.format_exc()
        try:(ROOT/'error.log').write_text(log,encoding='utf-8')
        except OSError:pass
        if not getattr(sys,'frozen',False):raise
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,'Не удалось запустить игру. Подробности записаны в error.log рядом с игрой.','Резонанс Двора',0x10)
        except Exception:pass
        raise SystemExit(1)
