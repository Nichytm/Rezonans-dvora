"""Build an optimized static bundle; leave the original desktop assets intact."""
from pathlib import Path
import subprocess,sys,shutil,tempfile,hashlib
ROOT=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(ROOT/'tools/build_legacy.py')],check=True)
with tempfile.TemporaryDirectory(prefix='rezonans-build-') as temp:
    stage=Path(temp)/'game'
    shutil.copytree(ROOT/'game',stage,ignore=shutil.ignore_patterns('build','saves','__pycache__','test_*.py','*.log','sounds','video'))
    # The browser plays the film from media/ through native HTML5 video.
    # Vorbis shrinks the PCM music without changing the desktop source assets.
    for folder in ('audio_v2','voices'):
        for audio in (stage/'assets'/folder).iterdir():
            if audio.suffix not in ('.wav','.mp3'):continue
            subprocess.run(['ffmpeg','-nostdin','-y','-loglevel','error','-i',str(audio),'-c:a','libvorbis','-q:a','4',str(audio.with_suffix('.ogg'))],check=True)
            audio.unlink()
    audio=stage/'audio.py';audio.write_text(audio.read_text().replace("f'{name}.wav'","f'{name}.ogg'"))
    subprocess.run([sys.executable,'-m','pygbag','--build','--no_opt','--title','Резонанс Двора','--template',str(ROOT/'web/index.tmpl'),str(stage)],check=True)
    for name in ['index.html','game.tar.gz','favicon.png']:shutil.copy2(stage/'build/web'/name,ROOT/name)
for name in ['touch.js','touch.css','compat.js']:shutil.copy2(ROOT/'web'/name,ROOT/name)
(ROOT/'media').mkdir(exist_ok=True)
shutil.copy2(ROOT/'game/assets/video/edit3000.mp4',ROOT/'media/edit3000.mp4')
# Changing bundle URLs prevents an older cached runtime or input script from mixing with new HTML.
index=ROOT/'index.html';html=index.read_text()
for name in ['game.tar.gz','touch.js','touch.css','compat.js']:
    digest=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()[:12]
    html=html.replace(name+'"',name+'?v='+digest+'"')
index.write_text(html)
(ROOT/'.nojekyll').touch()
print('Static site ready at',ROOT)
