import json,sys,os,subprocess,numpy as np,soundfile as sf
from kokoro import KPipeline
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','public','voice'); os.makedirs(OUT,exist_ok=True)
CAST={ # voice, speed, ffmpeg post filters
 'kotetsu':('jm_kumo',0.95,''),
 'geruna':('jm_kumo',0.9,'rubberband=pitch=0.84,'),
 'mimi':('jf_alpha',1.05,''),
 'chip':('jf_tebukuro',1.08,''),
 'hayate':('jm_kumo',1.05,'rubberband=pitch=1.12,'),
}
SAY={ # pronunciation fixes: text shown on screen -> text spoken
 'ハヤテェーッ！':'ハヤテーーっ！',
 '後ろだ、ハヤテ！':'うしろだ！ ハヤテ！',
 'ニャ……ニャルガ帝国、ばんざぁぁい……！':'ニャ、ニャルガ帝国、ばんざーーい！',
 'ニャ、ニャんだとぉぉ……！ 覚えておれ！':'ニャ、ニャんだとー！ 覚えておれ！',
 'Qキーでローリングだ！ 敵の弾をはじけるぞ！':'キューキーでローリングだ！ 敵の弾をはじけるぞ！',
}
def fnv(t):
    h=0x811c9dc5
    for ch in t: h^=ord(ch); h=(h*0x01000193)&0xffffffff
    return '%08x'%h
TMP=os.path.join(os.path.dirname(os.path.abspath(__file__)),'tmp.wav')
lines=json.load(open(sys.argv[1])); only=set(sys.argv[2:])
p=KPipeline(lang_code='j'); idx={}
if os.path.exists(OUT+'/index.json'): idx=json.load(open(OUT+'/index.json'))
for d in lines:
    who,text=d['who'],d['text']; vid=f'{who}-{fnv(text)}'
    if only and vid not in only and who not in only and os.path.exists(f'{OUT}/{vid}.mp3'): continue
    v,sp,post=CAST[who]
    a=np.concatenate([au for _,_,au in p(SAY.get(text,text),voice=v,speed=sp)])
    sf.write(TMP,a,24000)
    af=(f"{post}highpass=f=90,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,"
        "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,"
        "acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-17:TP=-1.5:LRA=7")
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',TMP,'-af',af,'-ar','24000','-ac','1','-b:a','48k',f'{OUT}/{vid}.mp3'],check=True)
    dur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f'{OUT}/{vid}.mp3'],capture_output=True,text=True).stdout)
    idx[vid]=round(dur,2); print(vid,round(dur,2),text,flush=True)
json.dump(dict(sorted(idx.items())),open(OUT+'/index.json','w'),separators=(',',':'))
