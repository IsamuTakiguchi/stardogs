# Renders every radio line to public/voice/<who>-<fnv1a(text)>.mp3 with Style-Bert-VITS2 (JVNV models),
# choosing an emotion per line so the cast sounds like they're in the middle of a dogfight.
# usage: python gen_voice.py lines.json [--pick] [id or speaker ...]   (no ids: only lines whose file is missing)
#   --pick renders several takes per line (full, 70% and 45% emotion) and keeps the one Whisper understands best,
#          preferring the more intense take when they're close (needs faster-whisper and pykakasi)
import json, sys, os, re, glob, subprocess, warnings
import numpy as np, soundfile as sf
warnings.filterwarnings('ignore')
from style_bert_vits2.tts_model import TTSModel
from style_bert_vits2.nlp import bert_models
from style_bert_vits2.constants import Languages

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'public', 'voice'); os.makedirs(OUT, exist_ok=True)
MODELS = os.environ.get('SBV_MODELS', os.path.join(HERE, 'models'))  # jvnv-*-jp folders from litagin/style_bert_vits2_jvnv
TMP = os.path.join(HERE, 'tmp.wav')

# speaker model, default emotion and weight, pitch/intonation scaling, speed (length<1 is faster), ffmpeg post filter
CAST = {
  'kotetsu': dict(model='M1', style='Angry', w=3.0, pitch=0.86, inton=1.25, length=0.9, post=''),
  'geruna':  dict(model='M2', style='Angry', w=5.0, pitch=1.0, inton=1.3, length=0.95, post='rubberband=pitch=0.76,'),
  'mimi':    dict(model='F2', style='Angry', w=3.5, pitch=1.0, inton=1.25, length=0.9, post=''),
  'chip':    dict(model='F1', style='Surprise', w=3.5, pitch=1.0, inton=1.3, length=0.88, post=''),
}
# per-line emotion: (regex on the line, style, weight); first match wins, else the character's default
MOOD = {
  'kotetsu': [(r'よくやった|見事だ', 'Happy', 3.0), (r'ハヤテェ|大丈夫か', 'Fear', 3.5), (r'後ろだ', 'Surprise', 4.0)],
  'geruna':  [(r'ニャんだと|ばんざ', 'Surprise', 5.0)],
  'mimi':    [(r'きゃあ', 'Fear', 4.0), (r'ありがと', 'Happy', 2.0), (r'おかげね|燃えてきた', 'Happy', 3.5), (r'後ろにつかれた', 'Fear', 3.0)],
  'chip':    [(r'パワーアップ|レーザー|リング3つ|守られた|撤退|逃げていく|ありがとう|お礼に|こわしておくと楽', 'Happy', 4.0),
              (r'もうダメ|うわーっ|撃たないで', 'Fear', 4.0)],
}
# pronunciation fixes: text shown on screen -> text spoken
SAY = {
  'ハヤテェーッ！': 'ハヤテーーッ！',
  'ニャ……ニャルガ帝国、ばんざぁぁい……！': 'ニャ、ニャルガ帝国、ばんざーーい！',
  'ニャ、ニャんだとぉぉ……！ 覚えておれ！': 'ニャ、ニャんだとー！ 覚えておれ！',
  'Qキーでローリングだ！ 敵の弾をはじけるぞ！': 'キューキーでローリングだ！ 敵の弾をはじけるぞ！',
}

def fnv(t):
    h = 0x811c9dc5
    for ch in t: h ^= ord(ch); h = (h * 0x01000193) & 0xffffffff
    return '%08x' % h

def main():
    args = sys.argv[2:]; pick = '--pick' in args; only = set(a for a in args if a != '--pick')
    lines = json.load(open(sys.argv[1], encoding='utf-8'))
    if pick:
        from faster_whisper import WhisperModel; import difflib, pykakasi
        asr = WhisperModel('small', device='cpu', compute_type='int8'); kk = pykakasi.kakasi()
        kana = lambda s: ''.join(x['hira'] for x in kk.convert(re.sub(r'[\s、。！？!?…・「」ー〜,.]', '', s)))
        score = lambda path, text: difflib.SequenceMatcher(None, kana(text), kana(''.join(x.text for x in asr.transcribe(path, language='ja', beam_size=5)[0]))).ratio()
    bert_models.load_model(Languages.JP, 'ku-nlp/deberta-v2-large-japanese-char-wwm')
    bert_models.load_tokenizer(Languages.JP, 'ku-nlp/deberta-v2-large-japanese-char-wwm')
    models = {}
    idx = json.load(open(OUT + '/index.json')) if os.path.exists(OUT + '/index.json') else {}
    for d in lines:
        who, text = d['who'], d['text']; vid = f'{who}-{fnv(text)}'
        want = (vid in only or who in only) if only else not os.path.exists(f'{OUT}/{vid}.mp3')
        if not want: continue
        c = CAST[who]; style, w = c['style'], c['w']
        for pat, st, ww in MOOD.get(who, []):
            if re.search(pat, text): style, w = st, ww; break
        if c['model'] not in models:
            dd = f"{MODELS}/jvnv-{c['model']}-jp"
            models[c['model']] = TTSModel(model_path=glob.glob(dd + '/*.safetensors')[0], config_path=dd + '/config.json',
                                          style_vec_path=dd + '/style_vectors.npy', device='cpu')
        af = (f"{c['post']}highpass=f=90,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,"
              "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse,"
              "acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-17:TP=-1.5:LRA=7")
        def render(weight, dst):
            sr, a = models[c['model']].infer(text=SAY.get(text, text), style=style, style_weight=weight, sdp_ratio=0.4, noise=0.6,
                                             length=c['length'], pitch_scale=c['pitch'], intonation_scale=c['inton'], line_split=False)
            sf.write(TMP, a, sr)
            subprocess.run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', TMP, '-af', af, '-ar', '24000', '-ac', '1', '-b:a', '48k', dst], check=True)
        if pick:
            takes = []
            for k, f in enumerate([1.0, 0.7, 0.45]):
                dst = os.path.join(HERE, f'take{k}.mp3'); render(w * f, dst); takes.append((score(dst, text), w * f, dst))
            best = max(t[0] for t in takes)
            sc, w, dst = next(t for t in takes if t[0] >= best - 0.03)  # most intense take that is (nearly) as clear as the best
            os.replace(dst, f'{OUT}/{vid}.mp3'); [os.remove(t[2]) for t in takes if os.path.exists(t[2])]
            style = f'{style} clarity={sc:.2f}'
        else:
            render(w, f'{OUT}/{vid}.mp3')
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f'{OUT}/{vid}.mp3'],
                                   capture_output=True, text=True).stdout)
        idx[vid] = round(dur, 2); print(vid, style, w, round(dur, 2), text, flush=True)
    if os.path.exists(TMP): os.remove(TMP)
    json.dump(dict(sorted(idx.items())), open(OUT + '/index.json', 'w'), separators=(',', ':'))

if __name__ == '__main__': main()
