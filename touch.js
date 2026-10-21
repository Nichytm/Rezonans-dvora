'use strict';
const $=id=>document.getElementById(id);
let lastBattle=null,lastTraining=null,lastPaused=null,lastCoop=null;
let pendingCoop=false;
let mode=matchMedia('(pointer: coarse)').matches?'touch':'keyboard';
try{const saved=localStorage.getItem('rezonans-controls');if(['board','touch','keyboard'].includes(saved))mode=saved;}catch{}
const requestedMode=new URLSearchParams(location.search).get('mode');
if(['board','touch','keyboard'].includes(requestedMode))mode=requestedMode;
let touch=mode!=='keyboard',board=mode==='board',active=false,commands=[];
const state={move:[0,0],move1:[0,0],move2:[0,0],aim:[0,0],fire:false,hidden:false};
let firing=new Set();
window.rdRead=()=>{const value=JSON.stringify({...state,touch,board,commands,coopHeroes:[$('coop-hero-1').value,$('coop-hero-2').value]});commands=[];return value;};
window.rdLoad=()=>{try{return localStorage.getItem('rezonans-dvora-v4')||'';}catch{return '';}};
window.rdSave=value=>{try{localStorage.setItem('rezonans-dvora-v4',value);}catch{$('storage-warning').hidden=false;}};
window.rdState=(value,battle,training,paused=false,coop=false)=>{
  const changed=active!==value||lastBattle!==battle||lastTraining!==training||lastPaused!==paused||lastCoop!==coop;
  if(!changed)return;
  lastBattle=battle;lastTraining=training;lastPaused=paused;lastCoop=coop;
  if(active!==value){active=value;reset();}
  document.body.classList.toggle('in-battle',Boolean(battle));
  document.body.classList.toggle('playing',Boolean(value));
  document.body.classList.toggle('coop-mode',Boolean(coop));
  $('touch-toggle').disabled=Boolean(coop&&battle);$('board-toggle').disabled=Boolean(coop&&battle);
  $('training-next').hidden=!training;
  $('board-pause').textContent=paused?'Продолжить':'Пауза';
  $('coop-pause').textContent=paused?'Продолжить':'Пауза';
  for(const button of document.querySelectorAll('[data-command]'))button.disabled=!value&&button.dataset.command!=='pause';
  $('touch-controls').inert=!value&&!(board&&battle);
  $('coop-controls').inert=!value&&!(coop&&battle);
  layout();
};
window.rdReady=()=>{document.body.classList.add('ready');$('loading').hidden=true;$('canvas').focus();layout();if(pendingCoop)openCoop();};
function setMode(value){mode=value;touch=mode!=='keyboard';board=mode==='board';reset();document.body.classList.toggle('touch-mode',touch);document.body.classList.toggle('board-mode',board);$('touch-toggle').setAttribute('aria-pressed',String(touch));$('board-toggle').setAttribute('aria-pressed',String(board));$('board-toggle').textContent=board?'Доска ✓':'Доска';try{localStorage.setItem('rezonans-controls',mode);}catch{}$('touch-controls').inert=!active&&!(board&&lastBattle);layout();}
function reset(){state.move=[0,0];state.move1=[0,0];state.move2=[0,0];state.aim=[0,0];state.fire=false;firing.clear();document.querySelectorAll('.knob').forEach(el=>el.style.transform='translate(0,0)');}
function layout(){const bar=$('toolbar').getBoundingClientRect().height;const dock=touch&&(active||(board&&lastBattle))?$(lastCoop?'coop-controls':'touch-controls').getBoundingClientRect().height:0;const width=document.documentElement.clientWidth;const height=Math.max(50,document.documentElement.clientHeight-bar-dock);const w=Math.min(width,height*16/9);const h=w*9/16;Object.assign($('canvas').style,{width:w+'px',height:h+'px',left:((width-w)/2)+'px',top:(bar+(height-h)/2)+'px'});}
window.addEventListener('resize',layout);
window.visualViewport?.addEventListener('resize',layout);
window.addEventListener('blur',()=>{reset();state.hidden=true;});
document.addEventListener('visibilitychange',()=>{state.hidden=document.hidden;reset();});
window.addEventListener('focus',()=>state.hidden=false);
$('touch-toggle').onclick=()=>setMode(touch?'keyboard':'touch');
$('board-toggle').onclick=()=>setMode(board?'touch':'board');
$('pause').onclick=()=>{commands.push('pause');$('canvas').focus();};
$('sound').onclick=()=>{commands.push('sound');$('canvas').focus();};
window.rdFullscreen=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{}layout();};
$('fullscreen').onclick=window.rdFullscreen;
$('help-open').onclick=()=>{$('help').showModal();if(active)commands.push('pause');};
$('board-help').onclick=()=> $('help-open').click();
$('board-fullscreen').onclick=window.rdFullscreen;
$('help-close').onclick=()=>{$('help').close();$('canvas').focus();};
$('start').onclick=()=>{$('start').textContent='Загрузка игры…';$('canvas').focus();};
$('start-board').onclick=()=>{setMode('board');$('start').click();};
for(const el of document.querySelectorAll('[data-command]')){
 el.addEventListener('pointerdown',e=>{e.preventDefault();if(!active&&el.dataset.command!=='pause')return;el.setPointerCapture(e.pointerId);commands.push(el.dataset.command);el.classList.add('pressed');});
 for(const type of ['pointerup','pointercancel','lostpointercapture'])el.addEventListener(type,()=>el.classList.remove('pressed'));
}
for(const [id,key] of [['move-stick','move'],['aim-stick','aim'],['p1-stick','move1'],['p2-stick','move2']]){
 const el=$(id),knob=el.querySelector('.knob');let pointer=null;
 function update(e){const r=el.getBoundingClientRect(),radius=r.width*.32;let x=(e.clientX-r.left-r.width/2)/radius,y=(e.clientY-r.top-r.height/2)/radius;const length=Math.hypot(x,y);if(length>1){x/=length;y/=length;}state[key]=[x,y];knob.style.transform=`translate(${x*radius}px,${y*radius}px)`;}
 el.addEventListener('pointerdown',e=>{e.preventDefault();if(!active||pointer!==null)return;pointer=e.pointerId;el.setPointerCapture(pointer);update(e);if(key==='aim'){firing.add(pointer);state.fire=true;}});
 el.addEventListener('pointermove',e=>{if(e.pointerId===pointer)update(e);});
 function end(e){if(e.pointerId!==pointer)return;firing.delete(pointer);pointer=null;state[key]=[0,0];state.fire=firing.size>0;knob.style.transform='translate(0,0)';}
 for(const type of ['pointerup','pointercancel','lostpointercapture'])el.addEventListener(type,end);
}
window.rdVideoActive=false;
window.rdVideoOpen=()=>{window.rdVideoActive=true;$('cinema').hidden=false;const v=$('video');v.currentTime=0;v.play().catch(()=>{$('video-play').hidden=false;});};
window.rdVideoClose=()=>{window.rdVideoActive=false;$('cinema').hidden=true;$('video').pause();$('canvas').focus();};
window.rdVideoPause=()=>{const v=$('video');if(v.paused)v.play().catch(()=>{});else v.pause();};
$('video-close').onclick=window.rdVideoClose;
$('video-play').onclick=()=>{$('video').play().catch(()=>{});$('video-play').hidden=true;};
$('video').addEventListener('ended',window.rdVideoClose);
$('video').addEventListener('error',()=>{$('video-error').hidden=false;});
$('export-save').onclick=()=>{const save=window.rdLoad();if(!save)return;const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([save],{type:'application/json'}));a.download='rezonans-dvora-save.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
const heroes=[['bugdan','Бугданчик · плевки'],['ilya','Иллюша · меч'],['artem','Булочник · лечение'],['glasses','Очкарик · винтовка'],['scream','Крикун · звук'],['smirk','Улыбаш · бумеранг'],['white','Белый · щит'],['hood','Иллюша · тень'],['smiler','Артём · Смайлер'],['egor','Егор · кулаки'],['igor','Игорь · турели']];
for(const id of ['coop-hero-1','coop-hero-2'])for(const [key,name] of heroes){const option=document.createElement('option');option.value=key;option.textContent=name;$(id).appendChild(option);}
$('coop-hero-2').value='glasses';
function openCoop(){pendingCoop=false;setMode('board');if(active)commands.push('pause');$('coop-error').hidden=true;if(!$('coop-lobby').open)$('coop-lobby').showModal();}
$('coop-open').onclick=openCoop;
$('board-coop').onclick=openCoop;
$('coop-change').onclick=openCoop;
$('start-coop').onclick=()=>{setMode('board');pendingCoop=true;$('start').click();if(document.body.classList.contains('ready'))openCoop();};
$('coop-go').onclick=()=>{if($('coop-hero-1').value===$('coop-hero-2').value){$('coop-error').hidden=false;return;}commands.push('coop_start');$('coop-lobby').close();$('canvas').focus();};
$('coop-cancel').onclick=()=>{$('coop-lobby').close();$('canvas').focus();};
$('coop-exit').onclick=()=>{commands.push('coop_exit');reset();$('canvas').focus();};
$('coop-fullscreen').onclick=window.rdFullscreen;
window.rdCoopHUD=value=>{const players=JSON.parse(value);players.forEach((player,index)=>{const panel=document.querySelector('.player-'+(index+1));$('p'+(index+1)+'-status').textContent=`${index+1} · ${player.name} · ${player.hp>0?player.hp+'% HP · '+player.energy+'% ульта':'ВЫБЫЛ'}`;panel.classList.toggle('down',player.hp<=0);for(const button of panel.querySelectorAll('[data-command]'))button.disabled=!active||player.hp<=0;});};
setMode(mode);
setTimeout(()=>{if(!document.body.classList.contains('ready'))$('slow-loading').hidden=false;},45000);
