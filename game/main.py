"""Async browser entry point; the complete original game lives in game.py."""
import asyncio
import json
import math
import sys
import pygame as pg
from game import Game, ASSETS, Sound

WEB=sys.platform=='emscripten'
if WEB:import platform

KEYS={'dash':pg.K_SPACE,'skill':pg.K_q,'ultimate':pg.K_e,'reload':pg.K_r,
      '1':pg.K_1,'2':pg.K_2,'3':pg.K_3,'pause':pg.K_ESCAPE,'next':pg.K_TAB,'sound':pg.K_m}

def browser_input(game):
    state=json.loads(str(platform.window.rdRead()))
    for command in state['commands']:
        if command in KEYS:pg.event.post(pg.event.Event(pg.KEYDOWN,key=KEYS[command],scancode=0))
    b=game.battle
    active=game.page=='battle' and b and not game.paused and not b.done and not b.intermission and not b.route_pending and not game.cinema.active
    platform.window.rdState(bool(active), bool(game.page=='battle'), bool(b and b.training))
    game.web_move=None;game.web_aim=None;game.web_firing=False
    if state.get('hidden') and active:game.paused=True;return
    if not active or not state['touch']:return
    game.web_move=state['move']
    ax,ay=state['aim']
    if math.hypot(ax,ay)>.12:
        game.web_aim=(b.pos.x+ax*600,b.pos.y+ay*600)
        game.web_firing=state['fire']
    else:
        targets=[e for e in b.enemies if e.get('hp',0)>0]
        if targets:
            target=min(targets,key=lambda e:(e['pos']-b.pos).length_squared())
            game.web_aim=tuple(target['pos'])
        else:game.web_aim=tuple(b.pos+b.aim*400)
        game.web_firing=state['fire']
    if state.get('hidden') and not game.paused:game.paused=True

async def main():
    global game
    game=Game()
    if WEB:
        game.profile.save()
        platform.window.rdReady()
    previous=pg.time.get_ticks()
    game.draw()
    while game.running:
        now=pg.time.get_ticks();dt=max(.001,min(.04,(now-previous)/1000));previous=now
        if WEB:browser_input(game)
        game.events();game.step(dt);game.draw()
        await asyncio.sleep(0)
    game.profile.save();pg.quit()

if __name__=='__main__':
    asyncio.run(main())
