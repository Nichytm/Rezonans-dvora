"""Effects and explicitly assigned voices use separate mixer channels."""
import time
import pygame as pg

VOICE_LABELS={
    '':'Без реплики',
    'bugdanchik_attack':'Бугданчик · атака из старой игры',
    'bugdanchik_scratch':'Бугданчик · scratch',
    'bugdanchik_suffocate':'Бугданчик · suffocate',
    'artem_smile':'Смайлер · старая запись',
    'go_gylat':'«Пошли на улицу» · голос не уточнён',
    'die':'Крик 1 · голос не уточнён',
    'die_2':'Крик 2 · голос не уточнён',
    'old_scream':'Старая запись sound1 · голос не уточнён',
    'old_glasses':'Старая запись sound2 · голос не уточнён',
    'old_smirk':'Старая запись sound3 · голос не уточнён',
}
DEFAULT_VOICES={'bugdan:attack':'bugdanchik_attack','bugdan:skill':'bugdanchik_attack','bugdan:ultimate':'bugdanchik_scratch','smiler:ultimate':'artem_smile'}

class Sound:
    def __init__(self,profile,assets):
        self.profile=profile;self.assets=assets;self.sounds={};self.voices={};self.current=None;self.ready=False;self.last={};self.voice_last=-100.
        try:
            if not pg.mixer.get_init():pg.mixer.init(44100,-16,2,512)
            pg.mixer.set_num_channels(32);pg.mixer.set_reserved(3)
            for directory in ('audio_v2','sfx'):
                for p in (assets/directory).glob('*'):
                    if p.suffix not in ('.wav','.ogg') or p.stem in ('menu','battle'):continue
                    sound=pg.mixer.Sound(str(p));sound.set_volume(.38);self.sounds[p.stem]=sound
            for p in (assets/'voices').glob('*'):
                if p.suffix not in ('.wav','.mp3','.ogg'):continue
                sound=pg.mixer.Sound(str(p));sound.set_volume(.38);self.voices[p.stem]=sound
            self.ready=True
        except (pg.error,OSError):pass

    def binding(self,event):return self.profile.data['voice_bindings'].get(event,DEFAULT_VOICES.get(event,''))

    def voice(self,name,preview=False):
        if not self.ready or name not in self.voices:return
        if not preview and (not self.profile.data['voices'] or not self.profile.data['sound']):return
        now=time.monotonic()
        if not preview and (now-self.voice_last<7 or now-self.last.get('voice_'+name,-100)<15):return
        self.voice_last=now;self.last['voice_'+name]=now
        pg.mixer.Channel(0).play(self.voices[name])

    def play(self,name):
        if name.startswith('voice:'):self.voice(self.binding(name[6:]));return
        if name=='merchant':self.voice('buy_package');return
        if not self.ready or not self.profile.data['sound'] or name not in self.sounds:return
        now=time.monotonic()
        if now-self.last.get(name,-100)<(.10 if name in ('impact','crit','enemy','shot') else .06):return
        self.last[name]=now
        channel=pg.mixer.Channel(1 if name in ('ultimate','win','lose') else 2) if name in ('ultimate','win','lose','rare','summon') else pg.mixer.find_channel()
        if channel:channel.play(self.sounds[name])

    def music(self,name):
        if not self.ready:return
        if not self.profile.data['music']:pg.mixer.music.stop();self.current=None;return
        if self.current==name:return
        try:
            pg.mixer.music.load(str(self.assets/'audio_v2'/f'{name}.wav'))
            pg.mixer.music.set_volume(.18 if name=='menu' else .22)
            pg.mixer.music.play(-1,fade_ms=650);self.current=name
        except (pg.error,OSError):pass
