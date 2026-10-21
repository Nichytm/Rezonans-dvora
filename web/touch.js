'use strict';
const $=id=>document.getElementById(id);
let lastBattle=null,lastTraining=null;
let touch=matchMedia('(pointer: coarse)').matches, active=false, commands=[];
const state={move:[0,0],aim:[0,0],fire:false,hidden:false};
let firing=new Set();
window.rdRead=()=>{const value=JSON.stringify({...state,touch,commands});commands=[];return value;};
window.rdLoad=()=>{try{return localStorage.getItem('rezonans-dvora-v4')||'';}catch{return '';}};
window.rdSave=value=>{try{localStorage.setItem('rezonans-dvora-v4',value);}catch{$('storage-warning').hidden=false;}};
window.rdState=(value,battle,training)=>{
  const changed=active!==value||lastBattle!==battle||lastTraining!==training;
  if(!changed)return;
  lastBattle=battle;lastTraining=training;
  if(active!==value){active=value;reset();}
  document.body.classList.toggle('in-battle',Boolean(battle));
  document.body.classList.toggle('playing',Boolean(value));
  $('training-next').hidden=!training;
  $('touch-controls').inert=!value;
  layout();
};
window.rdReady=()=>{document.body.classList.add('ready');$('loading').hidden=true;$('canvas').focus();layout();};
function setTouch(value){touch=value;reset();document.body.classList.toggle('touch-mode',touch);$('touch-toggle').setAttribute('aria-pressed',String(touch));layout();}
function reset(){state.move=[0,0];state.aim=[0,0];state.fire=false;firing.clear();document.querySelectorAll('.knob').forEach(el=>el.style.transform='translate(0,0)');}
function layout(){const bar=$('toolbar').getBoundingClientRect().height;const dock=touch&&active?$('touch-controls').getBoundingClientRect().height:0;const width=document.documentElement.clientWidth;const height=Math.max(50,document.documentElement.clientHeight-bar-dock);const w=Math.min(width,height*16/9);const h=w*9/16;Object.assign($('canvas').style,{width:w+'px',height:h+'px',left:((width-w)/2)+'px',top:(bar+(height-h)/2)+'px'});}
window.addEventListener('resize',layout);
window.visualViewport?.addEventListener('resize',layout);
window.addEventListener('blur',()=>{reset();state.hidden=true;});
document.addEventListener('visibilitychange',()=>{state.hidden=document.hidden;reset();});
window.addEventListener('focus',()=>state.hidden=false);
$('touch-toggle').onclick=()=>setTouch(!touch);
$('pause').onclick=()=>{commands.push('pause');$('canvas').focus();};
$('sound').onclick=()=>{commands.push('sound');$('canvas').focus();};
window.rdFullscreen=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{}layout();};
$('fullscreen').onclick=window.rdFullscreen;
$('help-open').onclick=()=>{$('help').showModal();commands.push('pause');};
$('help-close').onclick=()=>{$('help').close();$('canvas').focus();};
$('start').onclick=()=>{$('start').textContent='Загрузка игры…';$('canvas').focus();};
for(const el of document.querySelectorAll('[data-command]')){
 el.addEventListener('pointerdown',e=>{e.preventDefault();if(!active)return;el.setPointerCapture(e.pointerId);commands.push(el.dataset.command);el.classList.add('pressed');});
 for(const type of ['pointerup','pointercancel','lostpointercapture'])el.addEventListener(type,()=>el.classList.remove('pressed'));
}
for(const [id,key] of [['move-stick','move'],['aim-stick','aim']]){
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
setTouch(touch);
setTimeout(()=>{if(!document.body.classList.contains('ready'))$('slow-loading').hidden=false;},45000);
