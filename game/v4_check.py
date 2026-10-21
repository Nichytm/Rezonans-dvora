"""Smoke checks shipped in the executable for new modes, maps and bosses."""
import pygame as pg
from worlds import MAPS,MODES,BOSSES

def render_check(game,out):
    def save(name):
        game.draw();pg.image.save(game.canvas,str(out/(name+'.png')))
    game.navigate('activities');save('v4_modes')
    for i,key in enumerate(MAPS):
        game.navigate('activities');game.activity_map=i;game.configure_activity('duel');game.draw();save('setup_'+key)
        game.start_activity('capture',key);game.battle.banner_time=0;save('map_'+key)
    for hero in BOSSES:
        game.start_activity('duel','depot',hero);b=game.battle;b.pos=pg.Vector2(620,400);e=b.enemies[0];e['pos']=pg.Vector2(875,345)
        e['hp']=e['maxhp']*.49;e['cooldown']=0;b.update_boss(e,.01);e['cooldown']=0;b.update_boss(e,.01);b.banner_time=0
        save('boss_'+hero)
    for key in MODES:
        game.start_activity(key,'beach');b=game.battle
        for _ in range(160):b.update(1/60,(0,0),(900,400),True)
        b.banner_time=0;save('mode_'+key)
    game.start_activity('expedition');b=game.battle;b.offer_routes();save('v4_routes')
    b.choose_route(1);b.finish(True);save('v4_result');game.cinema.close(False)
