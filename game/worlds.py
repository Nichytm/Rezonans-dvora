"""Six authored arenas: geometry, hazards and downloaded tile art."""
import pygame as pg
V=pg.Vector2
MAPS={
 'park':dict(name='Заросший парк',tag='ФОНТАН ЛЕЧИТ',floor='grass',accent=(112,225,153),tile=(70,116,88),obstacles=[(360,235,110,64),(810,475,110,65)],props=['tree','tree'],hazard='fountain',desc='Деревья мешают пройти. У фонтана можно восстановить здоровье.'),
 'depot':dict(name='Грузовой вокзал',tag='ОСТОРОЖНО: ПОЕЗД',floor='concrete',accent=(244,182,96),tile=(82,87,101),obstacles=[(290,220,125,65),(850,490,140,65)],props=['crate','crate'],hazard='train',desc='Подсветка предупреждает о поезде. Уходи с путей в центр или к краю.'),
 'lab':dict(name='Нулевой реактор',tag='ЭЛЕКТРИЧЕСКИЕ ПЛИТЫ',floor='lab',accent=(96,224,249),tile=(59,101,113),obstacles=[(420,215,85,65),(785,490,85,65)],props=['console','console'],hazard='electric',desc='Плиты загораются до разряда. Меняй позицию и не стой на красном.'),
 'beach':dict(name='Берег поганцев',tag='ПРИЛИВ',floor='sand',accent=(251,211,137),tile=(182,159,113),obstacles=[(290,270,75,60),(920,440,85,60)],props=['rock','rock'],hazard='tide',desc='Волна накрывает нижнюю часть берега. Камни закрывают путь и снаряды.'),
 'frost':dict(name='Ледяной квартал',tag='СКОЛЬЗКИЙ ЛЁД',floor='ice',accent=(163,209,252),tile=(114,149,172),obstacles=[(365,230,110,65),(815,480,110,65)],props=['iceblock','iceblock'],hazard='ice',desc='Герой скользит по льду. Снежные обвалы отмечаются заранее.'),
 'market':dict(name='Ночной рынок',tag='ГОРЯЩИЕ БОЧКИ',floor='wood',accent=(233,145,190),tile=(106,79,77),obstacles=[(300,240,150,65),(830,475,150,65)],props=['stall','stall'],hazard='fire',desc='Узкие проходы между прилавками. Вспышки огня чередуются по краям.'),
}
MODES={
 'expedition':dict(name='Экспедиция',tag='ВЫБОР МАРШРУТА',desc='Пять комнат. Выбирай рискованный путь или привал, собирай усиления. В финале — поганец.',color=(173,145,255)),
 'duel':dict(name='Поганец против тебя',tag='БОСС С ДВУМЯ ФАЗАМИ',desc='Выбери соперника на фото. Изучи его приёмы: у каждого свой ритм и слабые места.',color=(255,142,158)),
 'escort':dict(name='Довези посылку',tag='СОПРОВОЖДЕНИЕ',desc='Держись рядом с тележкой и отгоняй врагов. Она едет только под твоей защитой.',color=(251,193,113)),
 'heist':dict(name='Набег за кристаллами',tag='СОБРАТЬ И ВЫНЕСТИ',desc='Собирай по три кристалла, сдавай в тайник. Добычу можно выронить от удара. Затем — эвакуация.',color=(105,230,214)),
 'capture':dict(name='Захват района',tag='КОНТРОЛЬ ТРЁХ ТОЧЕК',desc='Захвати три маяка в любом порядке. Враги мешают захвату. Зачищать всех не обязательно.',color=(120,190,255)),
 'survival':dict(name='Последний круг',tag='90 СЕКУНД ВЫЖИВАНИЯ',desc='Безопасная зона сужается и смещается. Переживи натиск и не задерживайся снаружи.',color=(206,238,121)),
}
BOSSES={
 'bugdan':dict(name='Бугданчик · Хозяин болота',title='Ядовитые плевки и кислотный дождь',hint='Обходи лужи. После веерного залпа есть время для атаки.',color=(132,237,160)),
 'ilya':dict(name='Иллюша · Разрез района',title='Меч, рывки и банкай во второй фазе',hint='Уходи поперёк отмеченной линии. После рывка бей со спины.',color=(241,122,172)),
 'smiler':dict(name='Артём · Король смайлеров',title='Волны, приманки и безопасный круг',hint='Во время большой вспышки займи подсвеченный безопасный круг.',color=(250,218,115)),
 'egor':dict(name='Егор · Последний богатырь',title='Прыжки, ударные волны и тройной обвал',hint='Выходи из кругов приземления. В рывке можно пройти сквозь удар.',color=(255,167,100)),
 'igor':dict(name='Игорь · Сборщик хаоса',title='Турели, мины и орбитальный прицел',hint='Уничтожай турели, пока Игорь готовит следующий обстрел.',color=(107,239,217)),
}

def resolve_circle(pos,radius,rects):
    """Push a circle out of solid props, including teleports into their center."""
    pos=V(pos)
    for rect in rects:
        box=pg.Rect(rect).inflate(radius*2,radius*2)
        if not box.collidepoint(pos):continue
        distances=[(abs(pos.x-box.left),'x',box.left-1),(abs(pos.x-box.right),'x',box.right+1),(abs(pos.y-box.top),'y',box.top-1),(abs(pos.y-box.bottom),'y',box.bottom+1)]
        valid=[item for item in distances if (60<=item[2]<=1220 if item[1]=='x' else 195<=item[2]<=575)]
        _,axis,value=min(valid or distances);setattr(pos,axis,value)
    pos.x=max(60,min(1220,pos.x));pos.y=max(195,min(575,pos.y))
    return pos

class WorldArt:
    def load_worlds(self):
        self.world_images={};self.world_cache={}
        for p in (self.assets/'world').glob('*.png'):self.world_images[p.stem]=pg.image.load(str(p)).convert_alpha()

    def world_sprite(self,name,rect,surface=None):
        if name not in self.world_images:return
        s=surface or self.s;r=pg.Rect(rect);key=(name,r.w,r.h)
        if key not in self.world_cache:self.world_cache[key]=pg.transform.smoothscale(self.world_images[name],r.size)
        s.blit(self.world_cache[key],r)

    def world_background(self,key):
        cache=('map',key)
        if cache in self.world_cache:return self.world_cache[cache]
        m=MAPS[key];s=pg.Surface((1280,613));s.fill((15,23,36))
        for x in range(0,1280,64):
            for y in range(165,614,64):self.world_sprite(m['floor'],(x,y,64,64),s)
        tint=pg.Surface(s.get_size(),pg.SRCALPHA);tint.fill((10,17,34,125));s.blit(tint,(0,0))
        if key=='park':
            pg.draw.rect(s,(99,91,69),(48,353,1184,72))
            for x in range(48,1232,54):pg.draw.line(s,(111,103,81),(x,355),(x,423),1)
            pg.draw.circle(s,(28,89,108),(640,265),48);pg.draw.circle(s,(144,189,191),(640,265),53,6)
            for x in (125,1045):self.world_sprite('tree',(x,110,125,110),s)
        elif key=='depot':
            for y in (294,326):pg.draw.line(s,(143,157,169),(0,y),(1280,y),5)
            for x in range(0,1280,38):pg.draw.line(s,(111,83,68),(x,284),(x,337),6)
            for x in range(70,1280,96):pg.draw.rect(s,(219,184,89),(x,460,45,4))
        elif key=='lab':
            for x in range(80,1250,95):pg.draw.line(s,(40,136,162),(x,190),(x,605),1)
            for y in range(205,600,78):pg.draw.line(s,(40,136,162),(50,y),(1230,y),1)
            for x in (115,1100):
                pg.draw.rect(s,(24,57,75),(x,170,70,58),border_radius=8)
                pg.draw.rect(s,(81,223,237),(x+10,180,50,32),2,border_radius=5)
        elif key=='beach':
            pg.draw.rect(s,(25,95,126),(0,532,1280,81))
            for y in range(537,614,18):pg.draw.line(s,(107,177,189),(0,y),(1280,y),2)
        elif key=='frost':
            for i in range(45):
                x=(i*177+70)%1280;y=190+(i*61)%410
                pg.draw.lines(s,(153,195,214),False,[(x,y),(x+25,y+13),(x+13,y+29)],1)
        elif key=='market':
            for x in range(55,1280,175):
                pg.draw.line(s,(42,38,51),(x,180),(x+60,222),2)
                pg.draw.circle(s,(246,175,142),(x+60,220),6)
            pg.draw.rect(s,(94,65,93),(500,188,280,40),border_radius=12)
        # Solid props have a visible base/shadow and match their collision rectangle.
        for rect,prop in zip(m['obstacles'],m['props']):
            r=pg.Rect(rect);pg.draw.rect(s,(15,24,32),r.move(9,9),border_radius=6)
            if prop=='console':
                pg.draw.rect(s,(30,56,75),r,border_radius=10)
                pg.draw.circle(s,(70,134,155),r.center,24)
                pg.draw.circle(s,(103,245,235),r.center,18,4)
                for off in (-30,30):pg.draw.line(s,(104,186,205),(r.centerx+off,r.top+10),(r.centerx+off,r.bottom-10),3)
            elif prop=='iceblock':
                pg.draw.polygon(s,(55,103,139),[(r.left,r.bottom),(r.left+10,r.top+12),(r.centerx,r.top),(r.right-10,r.top+8),(r.right,r.bottom)])
                pg.draw.lines(s,(155,219,239),False,[(r.left+12,r.bottom-9),(r.centerx,r.top+8),(r.right-14,r.bottom-8)],3)
            else:self.world_sprite(prop,rect,s)
            pg.draw.rect(s,tuple(int(c*.65) for c in m['accent']),r,2,border_radius=5)
        pg.draw.rect(s,m['accent'],(48,180,1184,416),2,border_radius=12)
        self.world_cache[cache]=s;return s

    def draw_world(self,b,t):
        key=getattr(b,'map_key',None)
        if not key:return False
        self.s.blit(self.world_background(key),(0,0));m=MAPS[key]
        self.text(m['name'].upper(),640,158,13,m['accent'],True,'center')
        if m['hazard']=='ice':
            for i in range(35):
                x=(i*113+t*33)%1280;y=180+(i*83+t*37)%420
                pg.draw.circle(self.s,(210,233,246),(int(x),int(y)),2)
        return True

    def draw_photo_boss(self,b,e,t):
        p=e['pos'];hero=e['boss_id'];c=e['color'];enraged=e['enraged']
        self.glow((p.x,p.y-24),c,95,48 if enraged else 27)
        pg.draw.ellipse(self.s,c,(p.x-49,p.y-8,98,35),3)
        size=123 if enraged else 102
        self.img('hero_'+hero,(p.x-size/2,p.y-size+9+__import__('math').sin(t*4)*3,size,size))
        pg.draw.polygon(self.s,(255,212,120),[(p.x-20,p.y-size-15),(p.x-17,p.y-size-31),(p.x-4,p.y-size-20),(p.x+8,p.y-size-36),(p.x+19,p.y-size-16)])
        if e.get('recover',0)>0 and e.get('casting',0)<=0:self.text('ОКНО ДЛЯ АТАКИ',p.x,p.y+36,10,(145,247,199),True,'center')
        elif enraged:self.text('ФАЗА II',p.x,p.y+35,11,c,True,'center')
