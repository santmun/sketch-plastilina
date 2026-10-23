# auto_shots.py — borrador de shots.json desde el guion: general de apertura, close al que habla con ángulos alternados,
# reacción del que escucha en líneas largas, un dúo cada 4 líneas. Tiempos anclados a líneas (sobreviven al re-TTS).
#   python3 auto_shots.py <proyecto> [--sobrescribir]   -> shots.json (luego se edita a mano: ver references/tomas.md)
import json, os, sys

SK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SK, 'engine'))
from project import Project

P = os.path.abspath(sys.argv[1])
out = os.path.join(P, 'shots.json')
if os.path.exists(out) and '--sobrescribir' not in sys.argv:
    try:
        cur = json.load(open(out))
    except Exception:
        cur = []
    if [s for s in cur if not s.get('_nota')]:
        sys.exit('shots.json ya tiene planos (usa --sobrescribir)')
prj = Project(P)
L = prj.lines
human = {n: s.get('tipo', 'humano') == 'humano' for n, s in prj.cast.items()}
speakers = []
for ln in L:
    if ln['who'] not in speakers:
        speakers.append(ln['who'])
a = speakers[0]
b = speakers[1] if len(speakers) > 1 else speakers[0]
shots = [dict(n='S01 general', t='inicio', tgt=f'{a}|{b}', plano='general', angulo=-25, push=0.9, f=4.0, sub='top')]
side = {n: (25 if i % 2 == 0 else -25) for i, n in enumerate(speakers)}
for i, ln in enumerate(L, 1):
    w = ln['who']
    prev = L[i - 2]['who'] if i > 1 else b
    k = len(shots) + 1
    t = 'inicio+0.0' if i == 1 else f'L{i}-0.12'
    if i == 1:
        shots[0]['t'] = 'inicio'
        if ln['end'] - ln['start'] < 1.6:
            continue
        t = f'L1+{min(1.2, (ln["end"] - ln["start"]) / 2):.2f}'
    if i % 4 == 0 and prev != w:
        # dúo = sobre el hombro de B mirando a A: el humano (cara grande) va como A, la mascota en primer término
        a_, b_ = (w, prev) if human.get(w, True) or not human.get(prev, True) else (prev, w)
        shots.append(dict(n=f'S{k:02d} {a_} y {b_}', t=t, tgt=f'{a_}|{b_}', plano='duo', angulo=side[w] // 2, lens=40, push=0.94,
                          f=3.2, sub='top'))
    else:
        side[w] = -side[w]
        hum = human.get(w, True)
        shots.append(dict(n=f'S{k:02d} {w} L{i}', t=t, tgt=w, plano='close' if hum else 'close', angulo=side[w],
                          push=0.92 if i % 2 else 0.95, f=2.2 if hum else 2.6, focus=w, sub='low' if hum else 'top'))
    dur = ln['end'] - ln['start']
    if dur > 2.6 and prev != w:      # reacción del que escucha
        shots.append(dict(n=f'S{len(shots) + 1:02d} reacción {prev}', t=f'L{i}.mid', tgt=prev, plano='close',
                          angulo=-side.get(prev, 20), push=0.95, f=2.4, focus=prev, sub='low' if human.get(prev, True) else 'top'))
json.dump(shots, open(out, 'w'), ensure_ascii=False, indent=1)
print(f'{len(shots)} planos -> shots.json')
for s in shots:
    print(f"  {s['t']:>10}  {s['n']:28s} {s['plano']:8s} tgt={s['tgt']}")
