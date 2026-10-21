"""Streaming video playback and the rare post-battle meme event."""
import random
import time
import pygame as pg
import sys
if sys.platform!='emscripten':import av

def edit_due(data,now=None,roll=None):
    now=time.time() if now is None else now
    if data['v3_wins']<3:return False
    if data['edit_seen']==0:return True
    return now-data['last_edit_at']>=1800 and (random.random() if roll is None else roll)<.08

class Cinema:
    def __init__(self,assets,sound):
        self.assets=assets;self.sound=sound;self.active=False;self.container=None;self.frame=None;self.elapsed=0;self.duration=25;self.paused=False;self.pending=None

    def open(self):
        if sys.platform=='emscripten':
            import platform
            pg.mixer.music.pause();self.active=True;self.paused=False
            platform.window.rdVideoOpen();return True
        self.close(False)
        try:
            self.container=av.open(str(self.assets/'video'/'edit3000.mp4'))
            stream=self.container.streams.video[0];self.frames=iter(self.container.decode(stream))
            self.duration=float(stream.duration*stream.time_base) if stream.duration else 25
            self.elapsed=0.;self.active=True;self.paused=False;self.pending=None;self.frame=None
            self._advance()
            if self.sound.ready:
                pg.mixer.stop();pg.mixer.music.stop();self.sound.current=None
                if self.sound.profile.data['sound']:
                    pg.mixer.music.load(str(self.assets/'video'/'edit3000.ogg'));pg.mixer.music.set_volume(.55);pg.mixer.music.play()
            return True
        except (OSError,ValueError,pg.error,av.FFmpegError):
            self.close(False);return False

    def _advance(self):
        # Decode only up to the current playback timestamp.
        for _ in range(20):
            if self.pending is None:
                try:self.pending=next(self.frames)
                except StopIteration:return
            timestamp=float(self.pending.time or 0)
            if timestamp>self.elapsed:return
            array=self.pending.to_ndarray(format='rgb24')
            self.frame=pg.image.frombuffer(array.tobytes(),(array.shape[1],array.shape[0]),'RGB').copy()
            self.pending=None

    def update(self,dt):
        if sys.platform=='emscripten':
            import platform
            if self.active and not platform.window.rdVideoActive:self.close()
            return
        if not self.active or self.paused:return
        self.elapsed+=dt;self._advance()
        if self.elapsed>=self.duration:self.close()

    def pause(self):
        if sys.platform=='emscripten':
            import platform
            platform.window.rdVideoPause();return
        self.paused=not self.paused
        if self.sound.ready:
            if self.paused:pg.mixer.music.pause()
            else:pg.mixer.music.unpause()

    def close(self,restore=True):
        if sys.platform=='emscripten':
            import platform
            platform.window.rdVideoClose()
            if self.active:pg.mixer.music.unpause()
            self.active=False;return
        was_active=self.active
        if self.container:self.container.close()
        self.container=None;self.active=False;self.pending=None
        if was_active and self.sound.ready:
            pg.mixer.music.stop();self.sound.current=None
            if restore:self.sound.music('menu')

    def draw(self,u):
        u.s.fill((7,9,19));u.buttons=[]
        u.glow((640,340),(216,111,181),310,35)
        if self.frame:
            im=pg.transform.smoothscale(self.frame,(538,520));u.s.blit(im,(371,82))
        u.text('ЕДИТ3000',640,27,27,(255,175,214),True,'midtop')
        u.text('Район поймал редкий момент. Награды за бой уже сохранены.',640,620,15,(177,187,207),False,'center')
        u.bar((372,607,537,4),self.elapsed,self.duration,(255,175,214))
        u.button((371,651,254,43),'ПРОДОЛЖИТЬ' if self.paused else 'ПАУЗА · SPACE',self.pause,small=True)
        u.button((645,651,264,43),'ПРОПУСТИТЬ · ESC',self.close,small=True)
