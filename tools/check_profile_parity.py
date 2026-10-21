"""Compare the compatible client's economy with the original Python Profile."""
import copy
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'game'))
from model import Profile, HEROES, CONTRACTS, RELICS

cases = []

def check(method, args, js_method=None, js_args=None, setup=None, result=True):
    p = Profile()
    if setup:
        setup(p.data)
    before = copy.deepcopy(p.data)
    value = getattr(p, method)(*args)
    if isinstance(value, dict) and 'levels' in value:
        value['levels'].sort()
    cases.append(dict(before=before, method=js_method or method, args=js_args if js_args is not None else args,
                      after=p.data, result=value, compare=result))

for h in HEROES:
    for level, stars in [(1, 0), (7, 2), (20, 5)]:
        check('stats', [h], setup=lambda d,h=h,level=level,stars=stars: d['heroes'].update({h:dict(level=level,stars=stars,xp=0,shards=0)}))
for h in ['bugdan', 'ilya']:
    check('upgrade', [h])
    check('awaken', [h])
check('upgrade', ['bugdan'], setup=lambda d: d.update(gold=0))
check('upgrade', ['bugdan'], setup=lambda d: d['heroes']['bugdan'].update(level=20))
check('awaken', ['bugdan'], setup=lambda d: d['heroes']['bugdan'].update(shards=100))
for slot in range(3):
    for h in ['bugdan', 'smiler', 'ilya']:
        check('set_slot', [h, slot], 'setSlot')
for k in CONTRACTS:
    check('claim_contract', [k], 'claim')
    check('claim_contract', [k], 'claim', setup=lambda d,k=k:d['progress'].update({CONTRACTS[k]['stat']:CONTRACTS[k]['target']}))
for k in RELICS:
    check('buy_relic', [k], 'buyRelic')
    check('buy_relic', [k], 'buyRelic', setup=lambda d:d.update(gold=0))
for stage in range(1,7):
    for won in [False,True]:
        p=Profile();before=copy.deepcopy(p.data)
        val=p.reward(stage,won,14,p.data['team'],stars=3,skills=7,dodges=2);val['levels'].sort()
        cases.append(dict(before=before,method='rewardStory',args=[stage,won,14,before['team'],dict(stars=3,skills=7,dodges=2)],after=p.data,result=val,compare=True))
for waves in [0,1,7,20]:
    p=Profile();before=copy.deepcopy(p.data);val=p.reward(1,False,41,p.data['team'],endless=True,waves=waves);val['levels'].sort()
    cases.append(dict(before=before,method='rewardStory',args=[1,False,41,before['team'],dict(endless=True,waves=waves)],after=p.data,result=val,compare=True))
for mode in ['expedition','escort','capture','heist','survival','duel']:
    for difficulty in [1,2,3]:
        for won in [False,True]:
            for repeat in [False,True]:
                p=Profile()
                if repeat:p.data['activity_wins'][mode+':'+str(difficulty)]=1
                before=copy.deepcopy(p.data)
                val=p.reward_activity(mode,won,19,p.data['team'],difficulty,123.5,'igor',bonus=.35,skills=6,dodges=1);val['levels'].sort()
                cases.append(dict(before=before,method='rewardActivity',args=[mode,won,19,before['team'],difficulty,123.5,'igor',dict(bonus=.35,skills=6,dodges=1)],after=p.data,result=val,compare=True))

program = r'''
var fs=require('fs'),vm=require('vm'),env={};vm.createContext(env);
vm.runInContext(fs.readFileSync('legacy/data.js','utf8'),env);
vm.runInContext(fs.readFileSync('legacy/profile.js','utf8'),env);
var cases=JSON.parse(fs.readFileSync(0,'utf8'));
function canonical(o){if(Array.isArray(o))return o.map(canonical);if(o&&typeof o==='object'){var r={};Object.keys(o).sort().forEach(function(k){r[k]=canonical(o[k]);});return r;}return o;}
function equal(a,b){return JSON.stringify(canonical(a))===JSON.stringify(canonical(b));}
cases.forEach(function(c,i){var p=new env.RDProfile();p.data=c.before;
 var result=p[c.method].apply(p,c.args);if(result&&result.levels)result.levels.sort();
 if(!equal(p.data,c.after)||c.compare&&!equal(result,c.result))throw new Error('Mismatch #'+i+' '+c.method+' '+JSON.stringify(c.args)+'\n'+JSON.stringify(result)+'\n'+JSON.stringify(c.result));
});
// Deterministic roll / choice sequence: both guarantees and duplicate shard counts.
var p=new env.RDProfile(null,function(){return .99;});p.data.pity=59;p.data.epic_pity=9;
var pulled=p.summon(1);if(env.RD_DATA.heroes[pulled[0].id].rarity!=='SSR'||p.data.pity!==0||p.data.epic_pity!==0)throw new Error('SSR guarantee');
p.data.pity=0;p.data.epic_pity=9;pulled=p.summon(1);if(env.RD_DATA.heroes[pulled[0].id].rarity!=='SR')throw new Error('SR guarantee');
var before=p.data.crystals;p.data.crystals=0;if(p.summon(10).length)throw new Error('Overspend');
if(!equal(env.RDProfileNormalize(p.data),p.data))throw new Error('Round trip');
console.log('PASS: '+cases.length+' original Python / ES5 economy comparisons, gacha guarantees and save round trip.');
'''
subprocess.run(['node','-e',program],input=json.dumps(cases),text=True,cwd=ROOT,check=True)
