"""Progression and summons. No rendering or third-party dependencies."""
from __future__ import annotations

import copy
import sys
import json
import random
from pathlib import Path

RARITIES = {'R': ('РЕДКИЙ', (88, 179, 255)), 'SR': ('ЭПИЧЕСКИЙ', (180, 116, 255)), 'SSR': ('ЛЕГЕНДАРНЫЙ', (255, 203, 108))}
HEROES = {
    'bugdan': dict(name='Бугданчик', title='Плевака', rarity='SR', image='bugdan.png', color=(139, 240, 164), hp=300, atk=31, speed=250, style='spit', skill='Тройной плевок', ultimate='Ливень возмездия', lore='Один плевок — предупреждение. Три — уже ультиматум.', voice='bugdan', crop=(0.24, 0.06, 0.80, 0.98)),
    'ilya': dict(name='Иллюша', title='Злой', rarity='SSR', image='ilya_new.jpg', color=(225, 103, 151), hp=460, atk=44, speed=280, style='slash', skill='Рассекающий рывок', ultimate='Банкай: 8 секунд', lore='Три удара мечом. Рывок сквозь врагов. Банкай усиливает весь стиль боя.', voice='ilya'),
    'artem': dict(name='Булочник', title='Повелитель булочки', rarity='SR', image='artem.png', color=(255, 180, 102), hp=350, atk=26, speed=235, style='heal', skill='Перекус: лечение отряда', ultimate='Пир на весь район', lore='Пока есть булочка, у отряда есть надежда.', voice='heal'),
    'glasses': dict(name='Очкарик', title='Тактик', rarity='R', image='glasses.png', color=(104, 204, 250), hp=280, atk=36, speed=265, style='shot', skill='Бронебойный луч', ultimate='Орбитальный прицел', lore='Шесть выстрелов. R — перезарядка. Ульта наводится мышью и пробивает линию.', voice='glasses'),
    'scream': dict(name='Крикун', title='На максималках', rarity='SR', image='scream.png', color=(129, 137, 255), hp=280, atk=33, speed=250, style='wave', skill='Звуковая волна', ultimate='МИКРОФОН ВКЛЮЧЁН', lore='Убавить громкость можно. Убавить его характер — нет.', voice='scream'),
    'smirk': dict(name='Улыбаш', title='Хитрый', rarity='R', image='smirk.png', color=(116, 232, 212), hp=300, atk=30, speed=285, style='fan', skill='Тройной бумеранг', ultimate='Орбита лезвий', lore='Бумеранг бьёт на пути туда и обратно. Веди его движением героя.', voice='smirk'),
    'white': dict(name='Белый', title='Сосед', rarity='R', image='white.png', color=(206, 215, 239), hp=460, atk=35, speed=255, style='guard', skill='Контрстойка', ultimate='Крепость подъезда', lore='Бьёт щитом вблизи. Контрстойка отражает удар. Купол защищает резонатор.', voice='glasses'),
    'hood': dict(name='Иллюша', title='Тень подъезда', rarity='SSR', image='hood.png', color=(192, 130, 255), hp=380, atk=48, speed=310, style='shadow', skill='За спиной', ultimate='Шесть теней', lore='Кинжалы вблизи. Телепортация к выбранной цели. Серия казней вместо залпа.', voice='ilya'),
    'smiler': dict(name='Артём', title='Смайлер', rarity='SR', image='artem_new.jpg', color=(255, 216, 103), hp=340, atk=32, speed=280, style='smile', skill='Ослепительная улыбка', ultimate='Паника в районе', lore='Цепная вспышка перескакивает между врагами. Ульта заставляет их бежать.', voice='artem_voice'),
    'egor': dict(name='Егор', title='Жёсткий', rarity='SSR', image='egor.jpg', color=(255, 149, 85), hp=570, atk=48, speed=270, style='brawler', skill='Удар об асфальт', ultimate='БОГАТЫРЬ', lore='Кулаки, апперкот, удар об землю. Ульта превращает Егора в великана.', voice='egor'),
    'igor': dict(name='Игорь', title='Пиксельный', rarity='SR', image='igor.jpg', color=(98, 242, 194), hp=310, atk=32, speed=255, style='engineer', skill='Поставить турель', ultimate='Армия пикселей', lore='Бросает взрывные кубики. Турель держит позицию, дроны сами ищут цель.', voice='igor'),
}

BASICS={'spit':'Плевок с ядом','slash':'Меч: комбо из 3 ударов','heal':'Булочка-бомба','shot':'Винтовка: 6 патронов','wave':'Звуковой конус','fan':'Возвратный бумеранг','guard':'Удар щитом','shadow':'Парные кинжалы','smile':'Цепная вспышка','brawler':'Кулаки и апперкот','engineer':'Взрывной кубик'}
ROLE={'spit':'ЯД / ДАЛЬНИЙ БОЙ','slash':'МЕЧ / БЛИЖНИЙ БОЙ','heal':'ПОДДЕРЖКА / ВЗРЫВЫ','shot':'СНАЙПЕР / ПЕРЕЗАРЯДКА','wave':'КОНТРОЛЬ / КОНУС','fan':'МАНЁВР / БУМЕРАНГ','guard':'ТАНК / КОНТРАТАКА','shadow':'УБИЙЦА / ТЕЛЕПОРТ','smile':'ЦЕПЬ / СТРАХ','brawler':'КУЛАКИ / ТАНК','engineer':'ТУРЕЛИ / ВЗРЫВЧАТКА'}
RELICS={'brick':('Кирпич','+15% урона',300),'thermos':('Термос','+12 HP за убийство',350),'watch':('Часы','Атаки и Q на 20% быстрее',450)}
STAGES = [
    ('Первый разлом', 'Знакомый двор больше не кажется знакомым.', 'yard'),
    ('После заката', 'Защити резонатор от монстров.', 'night'),
    ('Пустой подъезд', 'Уничтожь якоря, питающие разлом.', 'block'),
    ('Тихий час', 'Соседи просили потише. Монстры не услышали.', 'yard'),
    ('Ночная смена', 'Защити последний резонатор района.', 'night'),
    ('Хозяин района', 'Разрушь якоря и останови Пожирателя.', 'block'),
]

CONTRACTS = {
    'hunts': dict(name='Зачистка района', desc='Победи 50 монстров', stat='kills', target=50, crystals=320, gold=450),
    'wins': dict(name='Свой человек', desc='Закрой 3 разлома', stat='wins', target=3, crystals=480, gold=600),
    'skills': dict(name='Покажи характер', desc='Примени Q 25 раз', stat='skills', target=25, crystals=240, gold=350),
    'dodges': dict(name='Не сегодня', desc='Сделай 10 идеальных уклонений', stat='dodges', target=10, crystals=400, gold=500),
}

def fresh_save():
    return dict(version=4, crystals=3200, gold=1600, essence=35, pity=0, epic_pity=0,
                total_pulls=0, cleared=0, team=['bugdan', 'glasses', 'white'],
                heroes={h: dict(level=1, xp=0, shards=0, stars=0) for h in ['bugdan', 'glasses', 'white']},
                sound=True, music=True, voices=True, fullscreen=True, history=[], gift_v2=False,gift_v3=False,
                voice_bindings={},v3_wins=0,last_edit_at=0,edit_seen=0,relics=[],equipped_relic=None,activity_wins={},activity_best={},boss_wins={},
                progress={'kills':0,'wins':0,'skills':0,'dodges':0}, claimed=[], best_endless=0, stage_stars={})

class Profile:
    def __init__(self, path: Path | None = None, rng=None):
        self.path = path
        self.rng = rng or random.Random()
        self.data = fresh_save()
        self.warning = ''
        if sys.platform=='emscripten' and path:
            import platform
            stored=platform.window.rdLoad()
            if stored:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(str(stored),encoding='utf-8')
        if path and path.exists():
            try:
                raw = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(raw, dict) or raw.get('version') not in (1,2,3,4):
                    raise ValueError('Unsupported save format')
                data = fresh_save()
                for k in ('crystals','gold','essence','pity','epic_pity','total_pulls','cleared'):
                    value=raw.get(k,data[k])
                    if type(value) is not int or value<0: raise ValueError(k)
                    data[k]=value
                data['pity']=min(59,data['pity']); data['epic_pity']=min(9,data['epic_pity'])
                data['cleared']=min(len(STAGES),data['cleared'])
                owned={}
                for h,stats in raw['heroes'].items():
                    if h not in HEROES: continue
                    if not isinstance(stats,dict): raise ValueError('hero stats')
                    owned[h]={k:max(0,int(stats.get(k,0))) for k in ('level','xp','shards','stars')}
                    owned[h]['level']=max(1,min(20,owned[h]['level']))
                    owned[h]['stars']=min(5,owned[h]['stars'])
                if not owned: raise ValueError('Empty roster')
                data['heroes']=owned
                data['team']=list(dict.fromkeys(h for h in raw['team'] if h in owned))[:3]
                if not data['team']: data['team']=[next(iter(owned))]
                for k in ('sound','music','voices','fullscreen'): data[k]=bool(raw.get(k,data[k]))
                data['history']=[h for h in raw.get('history',[]) if h in HEROES][-30:]
                data['gift_v2']=bool(raw.get('gift_v2',False))
                data['gift_v3']=bool(raw.get('gift_v3',False))
                data['voice_bindings']={str(k):str(v) for k,v in raw.get('voice_bindings',{}).items()}
                for k in ('v3_wins','edit_seen'):data[k]=max(0,int(raw.get(k,0)))
                data['last_edit_at']=max(0,float(raw.get('last_edit_at',0)))
                data['relics']=[r for r in raw.get('relics',[]) if r in RELICS]
                data['equipped_relic']=raw.get('equipped_relic') if raw.get('equipped_relic') in data['relics'] else None
                for key in ('activity_wins','boss_wins'):
                    data[key]={str(k):max(0,int(v)) for k,v in raw.get(key,{}).items()}
                data['activity_best']={str(k):max(0,float(v)) for k,v in raw.get('activity_best',{}).items()}
                for key in data['progress']:data['progress'][key]=max(0,int(raw.get('progress',{}).get(key,0)))
                data['claimed']=[k for k in raw.get('claimed',[]) if k in CONTRACTS]
                data['best_endless']=max(0,int(raw.get('best_endless',0)))
                data['stage_stars']={str(k):max(0,min(3,int(v))) for k,v in raw.get('stage_stars',{}).items() if str(k) in [str(i) for i in range(1,7)]}
                self.data=data
            except (ValueError,KeyError,TypeError,OSError,AttributeError):
                backup=path.with_suffix('.damaged.json')
                i=1
                while backup.exists():
                    backup=path.with_suffix(f'.damaged-{i}.json'); i+=1
                try: backup.write_bytes(path.read_bytes())
                except OSError: pass
                self.warning='Повреждённое сохранение скопировано. Начат новый профиль.'
        if not self.data['gift_v2']:
            self.data['heroes'].setdefault('smiler',dict(level=3,xp=0,shards=0,stars=0))
            self.data['crystals']+=1600
            self.data['gift_v2']=True
            self.save()
        if not self.data['gift_v3']:
            for hero in ('egor','igor'):self.data['heroes'].setdefault(hero,dict(level=4,xp=0,shards=0,stars=0))
            self.data['gift_v3']=True;self.data['voices']=True;self.data['fullscreen']=True;self.save()

    def save(self):
        if sys.platform=='emscripten':
            import platform
            platform.window.rdSave(json.dumps(self.data,ensure_ascii=False));return
        if not self.path: return
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temp=self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),encoding='utf-8')
            temp.replace(self.path)
        except OSError:
            self.warning='Не удалось сохранить прогресс. Проверь доступ к папке saves.'

    def stats(self,h):
        base=HEROES[h]; own=self.data['heroes'].get(h,dict(level=3,stars=0))
        factor=(1+0.105*(own['level']-1))*(1+0.12*own['stars'])
        return dict(hp=round(base['hp']*factor),atk=round(base['atk']*factor),speed=base['speed'])

    def summon(self,count):
        if count not in (1,10) or self.data['crystals']<160*count: return []
        d=self.data; d['crystals']-=160*count; result=[]
        for _ in range(count):
            d['pity']+=1; d['epic_pity']+=1; d['total_pulls']+=1
            roll=self.rng.random()
            rarity='SSR' if d['pity']>=60 or roll<0.03 else 'SR' if d['epic_pity']>=10 or roll<0.20 else 'R'
            if rarity=='SSR': d['pity']=0
            if rarity!='R': d['epic_pity']=0
            h=self.rng.choice([h for h,v in HEROES.items() if v['rarity']==rarity])
            new=h not in d['heroes']; shards=0
            if new: d['heroes'][h]=dict(level=1,xp=0,shards=0,stars=0)
            else:
                shards={'R':10,'SR':20,'SSR':40}[rarity]
                d['heroes'][h]['shards']+=shards; d['essence']+=2
            result.append(dict(id=h,new=new,shards=shards))
            d['history'].append(h)
        d['history']=d['history'][-30:]; self.save(); return result

    def upgrade(self,h):
        if h not in self.data['heroes']: return False
        own=self.data['heroes'][h]; cost=own['level']*90
        if own['level']>=20 or self.data['gold']<cost or self.data['essence']<3: return False
        self.data['gold']-=cost; self.data['essence']-=3; own['level']+=1; own['xp']=0; self.save(); return True

    def awaken(self,h):
        if h not in self.data['heroes']: return False
        own=self.data['heroes'][h]; cost=(own['stars']+1)*20
        if own['stars']>=5 or own['shards']<cost: return False
        own['shards']-=cost; own['stars']+=1; self.save(); return True

    def set_slot(self,h,slot):
        if h not in self.data['heroes'] or not 0<=slot<3: return False
        team=self.data['team']
        if h in team:
            old=team.index(h)
            if slot<len(team): team[old],team[slot]=team[slot],team[old]
            else: return False
        elif slot<len(team): team[slot]=h
        else: team.append(h)
        self.save(); return True

    def reward(self,stage,won,kills,team,*,endless=False,waves=0,stars=0,skills=0,dodges=0):
        stage=max(1,min(len(STAGES),stage)); d=self.data
        first=won and stage>d['cleared']
        crystals=(900 if first else 120) if won else 0
        gold=(300+stage*80) if won else min(150,kills*12)
        essence=(10+stage*2) if won else min(4,kills//3)
        xp=100+stage*30 if won else kills*6
        if endless:
            first=False;crystals=waves*45;gold=waves*100+min(200,kills*4);essence=waves*3;xp=waves*50
            d['best_endless']=max(d['best_endless'],waves)
        d['crystals']+=crystals; d['gold']+=gold; d['essence']+=essence
        if won and not endless:
            d['cleared']=max(d['cleared'],stage)
            d['stage_stars'][str(stage)]=max(stars,d['stage_stars'].get(str(stage),0))
            d['v3_wins']+=1
        d['progress']['kills']+=kills;d['progress']['skills']+=skills;d['progress']['dodges']+=dodges
        if won and not endless:d['progress']['wins']+=1
        levels=[]
        for h in set(team):
            own=d['heroes'][h]; own['xp']+=xp
            while own['level']<20 and own['xp']>=own['level']*100:
                own['xp']-=own['level']*100; own['level']+=1; levels.append(h)
            if own['level']==20: own['xp']=0
        self.save()
        return dict(crystals=crystals,gold=gold,essence=essence,xp=xp,first=first,levels=levels)

    def claim_contract(self,key):
        if key not in CONTRACTS or key in self.data['claimed']:return False
        c=CONTRACTS[key]
        if self.data['progress'][c['stat']]<c['target']:return False
        self.data['crystals']+=c['crystals'];self.data['gold']+=c['gold'];self.data['claimed'].append(key)
        self.save();return True

    def buy_relic(self,key):
        if key not in RELICS:return False
        if key not in self.data['relics']:
            cost=RELICS[key][2]
            if self.data['gold']<cost:return False
            self.data['gold']-=cost;self.data['relics'].append(key)
        self.data['equipped_relic']=key;self.save();return True

    def reward_activity(self,mode,won,kills,team,difficulty,elapsed,boss,bonus=0,skills=0,dodges=0):
        d=self.data;key=mode+':'+str(difficulty);first=won and not d['activity_wins'].get(key)
        crystals=(600 if first else 160+40*difficulty) if won else 0
        gold=round((340+120*difficulty)*(1+bonus)) if won else min(160,kills*8)
        essence=12+difficulty*4 if won else min(4,kills//3);xp=180+difficulty*40 if won else min(90,kills*6)
        if won:
            d['activity_wins'][key]=d['activity_wins'].get(key,0)+1
            d['activity_best'][key]=min(elapsed,d['activity_best'].get(key,float('inf')))
            if mode in ('duel','expedition'):d['boss_wins'][boss]=d['boss_wins'].get(boss,0)+1
            d['v3_wins']+=1;d['progress']['wins']+=1
        d['crystals']+=crystals;d['gold']+=gold;d['essence']+=essence
        d['progress']['kills']+=kills;d['progress']['skills']+=skills;d['progress']['dodges']+=dodges
        levels=[]
        for h in set(team):
            own=d['heroes'][h];own['xp']+=xp
            while own['level']<20 and own['xp']>=own['level']*100:
                own['xp']-=own['level']*100;own['level']+=1;levels.append(h)
            if own['level']==20:own['xp']=0
        self.save();return dict(crystals=crystals,gold=gold,essence=essence,xp=xp,first=first,levels=levels)
