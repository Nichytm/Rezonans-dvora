"""Export original content and UI artwork for the compatible Canvas client."""
from pathlib import Path
import runpy,json,sys,hashlib,re,subprocess
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'game'))
model=runpy.run_path(str(ROOT/'game/model.py'));worlds=runpy.run_path(str(ROOT/'game/worlds.py'))
audio=runpy.run_path(str(ROOT/'game/audio.py'));arena=runpy.run_path(str(ROOT/'game/arena_base.py'))
coop=runpy.run_path(str(ROOT/'game/coop_content.py'))
heroes=model['HEROES'];assets=ROOT/'legacy/assets';assets.mkdir(exist_ok=True)
for key,hero in heroes.items():
    image=Image.open(ROOT/'game/assets/images'/hero['image']).convert('RGBA')
    if 'crop' in hero:
        a,b,c,d=hero['crop'];image=image.crop((int(a*image.width),int(b*image.height),int(c*image.width),int(d*image.height)))
    else:
        box=image.getbbox()
        if box:image=image.crop(box)
    large=image.copy();large.thumbnail((512,640),Image.Resampling.LANCZOS);large.save(assets/f'ui_{key}.png',optimize=True)
    image.thumbnail((160,180),Image.Resampling.LANCZOS);image.save(assets/f'{key}.png',optimize=True)
for name in ('night','yard','block'):
    image=Image.open(ROOT/'game/assets/images'/f'{name}.png').convert('RGB')
    image.thumbnail((1280,850),Image.Resampling.LANCZOS);image.save(assets/f'{name}.jpg',quality=86,optimize=True)
for name in ('bugdan_hearts','ilya_beach','egor_beach'):
    source=next((ROOT/'game/assets/images').glob(name+'.*'))
    image=Image.open(source).convert('RGB');image.thumbnail((640,720),Image.Resampling.LANCZOS)
    image.save(assets/f'{name}.jpg',quality=86,optimize=True)
for name in ('menu','battle'):
    subprocess.run(['ffmpeg','-nostdin','-y','-loglevel','error','-i',str(ROOT/'game/assets/audio_v2'/f'{name}.wav'),
                    '-c:a','libmp3lame','-b:a','128k',str(assets/f'{name}.mp3')],check=True)
voices={p.stem:p.name for p in (ROOT/'game/assets/voices').iterdir() if p.suffix in ('.wav','.mp3','.ogg')}
effects={p.stem:folder+'/'+p.name for folder in ('audio_v2','sfx') for p in (ROOT/'game/assets'/folder).iterdir()
         if p.suffix in ('.wav','.ogg') and p.stem not in ('menu','battle')}
data=dict(heroes=heroes,maps=worlds['MAPS'],modes=worlds['MODES'],bosses=worlds['BOSSES'],
    rarities=model['RARITIES'],basics=model['BASICS'],roles=model['ROLE'],relics=model['RELICS'],stages=model['STAGES'],
    contracts=model['CONTRACTS'],defaults=model['Profile']().data,perks=arena['PERKS'],
    voiceLabels=audio['VOICE_LABELS'],defaultVoices=audio['DEFAULT_VOICES'],voiceFiles=voices,fxFiles=effects,
    coopStages=coop['COOP_STAGES'])
(ROOT/'legacy/data.js').write_text('var RD_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n')
# Each release must replace old cached scripts on the board as one coherent set.
index=ROOT/'legacy/index.html';html=index.read_text()
for name in ('legacy.css','data.js','profile.js','legacy.js','shell.js'):
    digest=hashlib.sha256((ROOT/'legacy'/name).read_bytes()).hexdigest()[:12]
    html=re.sub(re.escape(name)+r'(?:\?v=[^"\s]+)?"',name+'?v='+digest+'"',html)
index.write_text(html)
print('Original game content, profile defaults and UI artwork exported')
