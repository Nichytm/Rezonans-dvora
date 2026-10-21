"""Hero trials, voice assignment and the courtyard merchant."""
from model import HEROES,RELICS,BASICS,ROLE
from audio import VOICE_LABELS
from ui import WHITE,MUTED,CYAN,GOLD,PURPLE

class Extras:
    def training(self,hero=None):
        self.start_battle(1,training=True)
        if hero:self.battle.set_training_hero(hero)

    def roster_page_by(self,delta):self.roster_page=(self.roster_page+delta)%2

    def kit_overlay(self):
        self.overlay();u=self.ui;h=HEROES[self.selected]
        u.panel((245,114,790,507));u.tag(ROLE[h['style']],277,140,h['color'])
        u.text(h['name']+' · '+h['title'],277,188,28,WHITE,True,maxwidth=716)
        u.text('ЛКМ  '+BASICS[h['style']],277,245,22,CYAN,True)
        u.paragraph(h['lore'],277,291,710,20,WHITE,31)
        u.text('Q  '+h['skill'],277,423,20,CYAN,True)
        u.text('E  '+h['ultimate'],277,459,20,GOLD,True)
        u.button((277,538,347,49),'ИСПЫТАТЬ НА ПОЛИГОНЕ',lambda:self.training(self.selected),True,small=True)
        u.button((641,538,360,49),'НАЗАД',lambda:setattr(self,'modal',None))

    def settings_overlay(self):
        self.overlay();u=self.ui;u.panel((330,83,620,563));u.text('Настройки',365,108,30,WHITE,True)
        for i,(key,label) in enumerate([('sound','Звуковые эффекты'),('music','Фоновая музыка'),('voices','Реплики друзей')]):
            u.button((365,166+i*58,550,45),label+'  /  '+('ВКЛ' if self.profile.data[key] else 'ВЫКЛ'),lambda k=key:self.toggle(k))
        u.button((365,343,550,45),'ЭКРАН: '+('ПОЛНЫЙ' if self.fullscreen else 'ОКНО')+'  /  F11',self.fullscreen_toggle)
        u.button((365,401,550,45),'ПРОСЛУШАТЬ И НАЗНАЧИТЬ РЕПЛИКИ',lambda:setattr(self,'modal','voices'),small=True)
        u.button((365,459,550,45),'КИНОЗАЛ: ЕДИТ3000',self.play_edit,small=True)
        u.text('Сам по себе едит появляется редко, после победы.',365,520,14,MUTED)
        u.button((365,565,550,45),'ГОТОВО',lambda:setattr(self,'modal',None),True)

    def voice_hero_by(self,delta):self.voice_hero=(self.voice_hero+delta)%len(HEROES)

    def bind_next(self,event):
        options=list(VOICE_LABELS);old=self.sound.binding(event)
        new=options[((options.index(old) if old in options else 0)+1)%len(options)]
        self.profile.data['voice_bindings'][event]=new;self.profile.save()

    def voices_overlay(self):
        self.overlay();u=self.ui;h=list(HEROES)[self.voice_hero];hero=HEROES[h]
        u.panel((180,74,920,576));u.text('Голоса района',215,98,30,WHITE,True)
        u.paragraph('Именованные записи Бугданчика возвращены. Остальные спорные голоса можно прослушать и назначить здесь. «Купи кирпич» звучит только у торговца.',215,146,850,16,MUTED,25)
        u.img('hero_'+h,(227,211,116,111));u.text(hero['name'],385,216,30,WHITE,True)
        u.button((385,273,218,42),'← ПЕРСОНАЖ',lambda:self.voice_hero_by(-1),small=True)
        u.button((619,273,218,42),'ПЕРСОНАЖ →',lambda:self.voice_hero_by(1),small=True)
        for i,(slot,label) in enumerate([('attack','ЛКМ · ОБЫЧНАЯ АТАКА'),('skill','Q · СПОСОБНОСТЬ'),('ultimate','E · УЛЬТИМЕЙТ')]):
            event=h+':'+slot;clip=self.sound.binding(event);y=335+i*73
            u.text(label,218,y,12,CYAN,True)
            u.button((218,y+22,619,42),VOICE_LABELS.get(clip,clip)+'  →',lambda e=event:self.bind_next(e),small=True)
            u.button((854,y+22,206,42),'ПРОСЛУШАТЬ',lambda c=clip:self.sound.voice(c,True),enabled=bool(clip),small=True)
        u.button((218,577,842,43),'ГОТОВО',lambda:setattr(self,'modal','settings'),True)

    def open_shop(self):
        self.modal='shop';self.sound.play('merchant')

    def buy_relic(self,key):
        if self.profile.buy_relic(key):self.sound.play('coin');self.message('Реликвия экипирована. Усиление действует со следующего боя.')
        else:self.message('Не хватает монет. Заработай их в разломах.')

    def shop_overlay(self):
        self.overlay();u=self.ui;u.panel((105,96,1070,543))
        u.text('Лавка у подъезда',143,123,32,WHITE,True)
        u.text('Одна реликвия на весь отряд. Покупается навсегда за игровые монеты.',143,174,17,MUTED)
        for i,(key,(name,desc,cost)) in enumerate(RELICS.items()):
            x=143+i*337;u.panel((x,233,315,281));u.tag('РЕЛИКВИЯ',x+20,253,GOLD)
            u.text(name,x+20,302,29,WHITE,True);u.paragraph(desc,x+20,350,273,17,CYAN)
            owned=key in self.profile.data['relics'];equipped=key==self.profile.data['equipped_relic']
            u.button((x+20,435,275,49),'ЭКИПИРОВАНО' if equipped else 'НАДЕТЬ' if owned else f'КУПИТЬ · {cost}',lambda k=key:self.buy_relic(k),True,not equipped and (owned or self.profile.data['gold']>=cost),True)
        u.button((143,556,985,46),'ВЕРНУТЬСЯ В ШТАБ',lambda:setattr(self,'modal',None),True)

    def play_edit(self):
        if not self.cinema.open():self.message('Не удалось открыть едит3000. Проверь папку assets/video.')
