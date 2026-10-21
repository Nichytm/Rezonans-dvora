/* Shared v4 save schema and original progression rules, compatible with ES5. */
(function(root){
'use strict';
var D=RD_DATA,KEY='rezonans-dvora-v4';
function copy(value){return JSON.parse(JSON.stringify(value));}
function pyRound(n){var f=Math.floor(n),d=n-f;return d===.5?(f%2===0?f:f+1):Math.round(n);}
function integer(n,fallback){return typeof n==='number'&&isFinite(n)&&n>=0?Math.floor(n):fallback;}
function unique(list){var out=[],i;for(i=0;i<list.length;i++)if(out.indexOf(list[i])<0)out.push(list[i]);return out;}
function own(hero){return {level:hero==='smiler'?3:(hero==='egor'||hero==='igor'?4:1),xp:0,shards:0,stars:0};}
function normalize(raw){
    if(!raw||[1,2,3,4].indexOf(raw.version)<0||!raw.heroes||!Array.isArray(raw.team))throw new Error('Неподдерживаемое сохранение');
    var d=copy(D.defaults),keys=['crystals','gold','essence','pity','epic_pity','total_pulls','cleared'],i,k,h,s;
    for(i=0;i<keys.length;i++){k=keys[i];if(typeof raw[k]!=='number'||!isFinite(raw[k])||raw[k]<0)throw new Error('Повреждено поле '+k);d[k]=Math.floor(raw[k]);}
    d.pity=Math.min(59,d.pity);d.epic_pity=Math.min(9,d.epic_pity);d.cleared=Math.min(D.stages.length,d.cleared);d.heroes={};
    for(h in raw.heroes)if(D.heroes[h]){s=raw.heroes[h];d.heroes[h]={level:Math.max(1,Math.min(20,integer(s.level,1))),xp:integer(s.xp,0),shards:integer(s.shards,0),stars:Math.min(5,integer(s.stars,0))};}
    if(!Object.keys(d.heroes).length)throw new Error('Пустая коллекция');
    d.team=unique(raw.team.filter(function(id){return !!d.heroes[id];})).slice(0,3);if(!d.team.length)d.team=[Object.keys(d.heroes)[0]];
    ['sound','music','voices','fullscreen'].forEach(function(key){if(typeof raw[key]!=='undefined')d[key]=!!raw[key];});
    d.history=(Array.isArray(raw.history)?raw.history:[]).filter(function(id){return !!D.heroes[id];}).slice(-30);
    d.voice_bindings={};if(raw.voice_bindings)for(k in raw.voice_bindings)if(Object.prototype.hasOwnProperty.call(raw.voice_bindings,k))d.voice_bindings[k]=String(raw.voice_bindings[k]);
    ['v3_wins','edit_seen','best_endless'].forEach(function(key){d[key]=integer(raw[key],0);});d.last_edit_at=Math.max(0,Number(raw.last_edit_at)||0);
    d.relics=(Array.isArray(raw.relics)?raw.relics:[]).filter(function(id){return !!D.relics[id];});d.equipped_relic=d.relics.indexOf(raw.equipped_relic)>=0?raw.equipped_relic:null;
    ['activity_wins','boss_wins'].forEach(function(key){d[key]={};if(raw[key])for(var name in raw[key])if(Object.prototype.hasOwnProperty.call(raw[key],name))d[key][name]=integer(raw[key][name],0);});
    d.activity_best={};if(raw.activity_best)for(k in raw.activity_best)if(Object.prototype.hasOwnProperty.call(raw.activity_best,k)&&isFinite(raw.activity_best[k]))d.activity_best[k]=Math.max(0,Number(raw.activity_best[k]));
    for(k in d.progress)d.progress[k]=integer(raw.progress&&raw.progress[k],0);
    d.claimed=(Array.isArray(raw.claimed)?raw.claimed:[]).filter(function(id){return !!D.contracts[id];});d.stage_stars={};
    if(raw.stage_stars)for(k in raw.stage_stars)if(Number(k)>=1&&Number(k)<=6)d.stage_stars[k]=Math.min(3,integer(raw.stage_stars[k],0));
    if(!raw.gift_v2){if(!d.heroes.smiler)d.heroes.smiler=own('smiler');d.crystals+=1600;}
    if(!raw.gift_v3){if(!d.heroes.egor)d.heroes.egor=own('egor');if(!d.heroes.igor)d.heroes.igor=own('igor');d.voices=true;d.fullscreen=true;}
    d.gift_v2=true;d.gift_v3=true;d.version=4;return d;
}
function Profile(storage,rng){
    this.storage=storage||null;this.random=rng||Math.random;this.data=copy(D.defaults);this.warning='';var text=null;
    if(this.storage)try{text=this.storage.getItem(KEY);if(text)this.data=normalize(JSON.parse(text));}catch(error){
        this.warning='Сохранение повреждено. Его копия сохранена отдельно.';
        try{if(text)this.storage.setItem(KEY+'-damaged-'+Date.now(),text);}catch(ignore){}
    }
    this.save();
}
Profile.prototype.save=function(){if(!this.storage)return true;try{this.storage.setItem(KEY,JSON.stringify(this.data));return true;}catch(error){this.warning='Браузер запретил сохранение. Скачайте копию в настройках.';return false;}};
Profile.prototype.importSave=function(raw){this.data=normalize(raw);this.save();};
Profile.prototype.stats=function(h){var base=D.heroes[h],v=this.data.heroes[h]||{level:3,stars:0},factor=(1+.105*(v.level-1))*(1+.12*v.stars);return {hp:pyRound(base.hp*factor),atk:pyRound(base.atk*factor),speed:base.speed};};
Profile.prototype.summon=function(count){
    var d=this.data,result=[],i,r,rarity,pool,id,isNew,shards;if([1,10].indexOf(count)<0||d.crystals<160*count)return result;
    d.crystals-=160*count;
    for(i=0;i<count;i++){d.pity++;d.epic_pity++;d.total_pulls++;r=this.random();rarity=d.pity>=60||r<.03?'SSR':(d.epic_pity>=10||r<.20?'SR':'R');
        if(rarity==='SSR')d.pity=0;if(rarity!=='R')d.epic_pity=0;
        pool=Object.keys(D.heroes).filter(function(h){return D.heroes[h].rarity===rarity;});id=pool[Math.floor(this.random()*pool.length)%pool.length];isNew=!d.heroes[id];shards=0;
        if(isNew)d.heroes[id]={level:1,xp:0,shards:0,stars:0};else{shards={R:10,SR:20,SSR:40}[rarity];d.heroes[id].shards+=shards;d.essence+=2;}
        result.push({id:id,'new':isNew,shards:shards});d.history.push(id);
    }
    d.history=d.history.slice(-30);this.save();return result;
};
Profile.prototype.upgrade=function(h){var d=this.data,v=d.heroes[h];if(!v||v.level>=20||d.gold<v.level*90||d.essence<3)return false;d.gold-=v.level*90;d.essence-=3;v.level++;v.xp=0;this.save();return true;};
Profile.prototype.awaken=function(h){var v=this.data.heroes[h];if(!v||v.stars>=5||v.shards<(v.stars+1)*20)return false;v.shards-=(v.stars+1)*20;v.stars++;this.save();return true;};
Profile.prototype.setSlot=function(h,slot){var d=this.data,t=d.team,old=t.indexOf(h),other;if(!d.heroes[h]||slot<0||slot>=3)return false;if(old>=0){if(slot>=t.length)return false;other=t[slot];t[slot]=h;t[old]=other;}else if(slot<t.length)t[slot]=h;else t.push(h);this.save();return true;};
Profile.prototype.claim=function(key){var c=D.contracts[key],d=this.data;if(!c||d.claimed.indexOf(key)>=0||d.progress[c.stat]<c.target)return false;d.crystals+=c.crystals;d.gold+=c.gold;d.claimed.push(key);this.save();return true;};
Profile.prototype.buyRelic=function(key){var d=this.data,r=D.relics[key];if(!r)return false;if(d.relics.indexOf(key)<0){if(d.gold<r[2])return false;d.gold-=r[2];d.relics.push(key);}d.equipped_relic=key;this.save();return true;};
Profile.prototype.experience=function(team,xp){var d=this.data,levels=[];unique(team).forEach(function(h){var own=d.heroes[h];if(!own)return;own.xp+=xp;while(own.level<20&&own.xp>=own.level*100){own.xp-=own.level*100;own.level++;levels.push(h);}if(own.level===20)own.xp=0;});return levels;};
Profile.prototype.rewardStory=function(stage,won,kills,team,options){
    var d=this.data,o=options||{},first,crystals,gold,essence,xp,levels;stage=Math.max(1,Math.min(D.stages.length,stage));first=!!(won&&stage>d.cleared);
    crystals=won?(first?900:120):0;gold=won?300+stage*80:Math.min(150,kills*12);essence=won?10+stage*2:Math.min(4,Math.floor(kills/3));xp=won?100+stage*30:kills*6;
    if(o.endless){first=false;crystals=(o.waves||0)*45;gold=(o.waves||0)*100+Math.min(200,kills*4);essence=(o.waves||0)*3;xp=(o.waves||0)*50;d.best_endless=Math.max(d.best_endless,o.waves||0);}
    d.crystals+=crystals;d.gold+=gold;d.essence+=essence;
    if(won&&!o.endless){d.cleared=Math.max(d.cleared,stage);d.stage_stars[String(stage)]=Math.max(o.stars||0,d.stage_stars[String(stage)]||0);d.v3_wins++;d.progress.wins++;}
    d.progress.kills+=kills;d.progress.skills+=o.skills||0;d.progress.dodges+=o.dodges||0;levels=this.experience(team,xp);this.save();return {crystals:crystals,gold:gold,essence:essence,xp:xp,first:first,levels:levels};
};
Profile.prototype.rewardActivity=function(mode,won,kills,team,difficulty,elapsed,boss,options){
    var d=this.data,o=options||{},key=mode+':'+difficulty,first=!!(won&&!d.activity_wins[key]),crystals=won?(first?600:160+40*difficulty):0,gold=won?pyRound((340+120*difficulty)*(1+(o.bonus||0))):Math.min(160,kills*8),essence=won?12+difficulty*4:Math.min(4,Math.floor(kills/3)),xp=won?180+difficulty*40:Math.min(90,kills*6),levels;
    if(won){d.activity_wins[key]=(d.activity_wins[key]||0)+1;d.activity_best[key]=Math.min(elapsed,typeof d.activity_best[key]==='number'?d.activity_best[key]:Infinity);if(mode==='duel'||mode==='expedition')d.boss_wins[boss]=(d.boss_wins[boss]||0)+1;d.v3_wins++;d.progress.wins++;}
    d.crystals+=crystals;d.gold+=gold;d.essence+=essence;d.progress.kills+=kills;d.progress.skills+=o.skills||0;d.progress.dodges+=o.dodges||0;levels=this.experience(team,xp);this.save();return {crystals:crystals,gold:gold,essence:essence,xp:xp,first:first,levels:levels};
};
Profile.prototype.editDue=function(now,roll){var d=this.data;now=typeof now==='number'?now:Date.now()/1000;roll=typeof roll==='number'?roll:this.random();return d.v3_wins>=3&&(d.edit_seen===0||(now-d.last_edit_at>=1800&&roll<.08));};
root.RDProfile=Profile;root.RDProfileNormalize=normalize;root.RDPyRound=pyRound;
}(typeof window!=='undefined'?window:this));
