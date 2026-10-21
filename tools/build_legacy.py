"""Export original game data and small portraits for the ES5 / Canvas edition."""
from pathlib import Path
import runpy,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
model=runpy.run_path(str(ROOT/'game/model.py'))
worlds=runpy.run_path(str(ROOT/'game/worlds.py'))
heroes=model['HEROES']
for key,hero in heroes.items():
    image=Image.open(ROOT/'game/assets/images'/hero['image']).convert('RGBA')
    if 'crop' in hero:
        a,b,c,d=hero['crop'];image=image.crop((int(a*image.width),int(b*image.height),int(c*image.width),int(d*image.height)))
    else:
        box=image.getbbox()
        if box:image=image.crop(box)
    image.thumbnail((160,180),Image.Resampling.LANCZOS)
    image.save(ROOT/'legacy/assets'/f'{key}.png',optimize=True)
data=dict(heroes=heroes,maps=worlds['MAPS'],modes=worlds['MODES'],bosses=worlds['BOSSES'])
(ROOT/'legacy/data.js').write_text('var RD_DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n')
print('Legacy data and portraits ready')
