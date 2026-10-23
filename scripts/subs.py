# subs.py — subtítulos en trozos cortos (sin etiquetas de voz), tiempos de AssemblyAI, PNG por trozo.
# Regla: un subtítulo NUNCA cruza un corte de plano (se parte en el corte y cada trozo toma la posición de su plano).
#   python3 subs.py <proyecto> <ancho> [carpeta]  -> subs.json + PNGs
import json, os, re, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

P = os.path.abspath(sys.argv[1])
W = int(sys.argv[2]) if len(sys.argv) > 2 else 720
OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(P, 'renders', f'subs_{W}')
H = W * 16 // 9
os.makedirs(OUT, exist_ok=True)
tl = json.load(open(os.path.join(P, 'build', 'timeline.json')))
wp = os.path.join(P, 'audio', 'palabras.json')
words = json.load(open(wp)) if os.path.exists(wp) else []
shots = json.load(open(os.path.join(P, 'build', 'shots_resolved.json')))
cuts = sorted(s['t'] for s in shots if s['t'] > 0.01)


def font(size):
    path = '/System/Library/Fonts/Avenir Next.ttc'
    for i in range(12):
        try:
            f = ImageFont.truetype(path, size, index=i)
        except Exception:
            break
        if f.getname()[1] in ('Bold',):
            return f
    return ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf', size)


def clean(s):
    s = re.sub(r'\[[^\]]*\]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


WEAK = {'a', 'la', 'el', 'de', 'que', 'con', 'en', 'tan', 'mi', 'lo', 'le', 'tu', 'te', 'y', 'si', 'me', 'los', 'las', 'un',
        'una', 'por', 'su', 'se', 'no', 'del', 'al'}


def chunks_of(toks, times, maxw=4, maxc=22):
    cutb = [k > 0 and any(times[k - 1][0] < c <= times[k][0] + 0.02 for c in cuts) for k in range(len(toks))]
    out, cur = [], []
    for k, tk in enumerate(toks):
        crosses = bool(cur) and cutb[k]
        cand = cur + [k]
        text_c = ' '.join(toks[j] for j in cand)
        # si un corte obliga a partir en 1-2 palabras, mejor alargar este trozo que dejar un fragmento suelto
        soon = any(cutb[j] for j in range(k + 1, min(len(toks), k + 3)))
        too_long = len(cand) > maxw or len(text_c) > maxc
        if too_long and soon and len(text_c) <= maxc + 12 and len(cand) <= maxw + 2:
            too_long = False
        if cur and (crosses or too_long):
            out.append(cur)
            cur = [k]
        else:
            cur = cand
        if cur and tk[-1] in '.,?!…' and (len(cur) >= 2 or tk[-1] in '?!'):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    for i in range(len(out) - 1):     # no terminar un trozo en palabra débil (si no hay corte de por medio)
        while len(out[i]) > 1 and toks[out[i][-1]].lower().strip('¿¡') in WEAK and \
                not any(times[out[i][-1]][0] < c <= times[out[i + 1][0]][0] + 0.02 for c in cuts):
            out[i + 1].insert(0, out[i].pop())
    return out


subs = []
lines = tl['lineas']
for li, ln in enumerate(lines):
    toks = clean(ln['text']).split(' ')
    nxt = lines[li + 1]['start'] if li + 1 < len(lines) else tl['t_end']
    ws = [w for w in words if ln['start'] - 0.2 <= w['start'] / 1000 <= ln['end'] + 0.1]
    if len(ws) == len(toks):
        times = [(w['start'] / 1000, w['end'] / 1000) for w in ws]
        t1 = ws[-1]['end'] / 1000
    else:   # AssemblyAI no oyó todo (suspiros, «Uf»): reparte por caracteres dentro de la línea
        t0, t1 = ln['start'], ln['end']
        tot = sum(len(t) + 1 for t in toks)
        acc, times = 0, []
        for tk in toks:
            a = t0 + (t1 - t0) * acc / tot
            acc += len(tk) + 1
            times.append((a, t0 + (t1 - t0) * acc / tot))
    groups = chunks_of(toks, times)
    for gi, g in enumerate(groups):
        a = times[g[0]][0]
        b = times[groups[gi + 1][0]][0] if gi + 1 < len(groups) else min(max(t1, ln['end']) + 0.3, nxt - 0.03)
        a = max(0.0, a - 0.04)
        txt = ' '.join(toks[j] for j in g)
        for c in cuts:                     # nunca cruzar un corte
            if a < c < a + 0.2:
                a = c                      # empieza pegado al corte: aparece con el plano nuevo
        segs, cur = [], a
        for c in cuts:
            if cur + 0.2 <= c < b - 0.001:
                segs.append((cur, c))      # se parte en el corte; el resto sigue en el plano nuevo (otra posición)
                cur = c
        segs.append((cur, b))
        for x, y in segs:
            if y - x >= 0.12:
                subs.append(dict(text=txt, a=round(x, 3), b=round(y, 3)))
subs.sort(key=lambda s: s['a'])
for i in range(len(subs) - 1):             # nunca dos subtítulos a la vez
    subs[i]['b'] = min(subs[i]['b'], subs[i + 1]['a'])


def pos_for(t):
    cur = shots[0]
    for s in shots:
        if t >= s['t'] - 1e-6:
            cur = s
    return cur.get('sub', 'low')


fs = int(W * 0.062)
fnt = font(fs)
for i, s in enumerate(subs):
    txt = s['text']
    bb = fnt.getbbox(txt)
    if bb[2] - bb[0] > W * 0.9:
        ws_ = txt.split(' ')
        h = len(ws_) // 2
        txt = ' '.join(ws_[:h]) + '\n' + ' '.join(ws_[h:])
    img = Image.new('RGBA', (W, int(fs * 3.2)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.multiline_text((W // 2, img.height // 2), txt, font=fnt, fill=(255, 255, 255, 255), anchor='mm', align='center',
                     stroke_width=max(2, fs // 11), stroke_fill=(24, 18, 14, 235), spacing=int(fs * 0.12))
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.multiline_text((W // 2 + 2, img.height // 2 + 4), txt, font=fnt, fill=(0, 0, 0, 120), anchor='mm', align='center',
                      stroke_width=max(2, fs // 11), stroke_fill=(0, 0, 0, 120), spacing=int(fs * 0.12))
    sh = sh.filter(ImageFilter.GaussianBlur(fs * 0.12))
    comp = Image.alpha_composite(sh, img)
    bbox = comp.getbbox()
    comp = comp.crop((0, bbox[1] - 2, W, bbox[3] + 2))
    p = os.path.join(OUT, f'sub_{i:03d}.png')
    comp.save(p)
    where = pos_for(s['a'] + 0.01)
    yc = {'top': 0.205, 'mid': 0.5, 'low': 0.735}[where]
    s.update(png=p, y=int(H * yc - comp.height / 2), where=where)
json.dump(subs, open(os.path.join(OUT, 'subs.json'), 'w'), ensure_ascii=False, indent=1)
bad = [s for s in subs if any(s['a'] + 0.001 < c < s['b'] - 0.001 for c in cuts)]
for s in subs:
    print(f"{s['a']:6.2f}-{s['b']:6.2f} {s['where']:4s} {s['text']}")
print(f'{len(subs)} subtítulos, {len(bad)} cruzan un corte')
