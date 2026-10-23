# recibo.py — textura de ticket térmico (cuando el chiste ES el objeto: se construye como prop real).
#   python3 recibo.py <proyecto>   lee <proyecto>/recibo.json -> build/recibo.png
#   recibo.json: {"titulo": "ChatGPT", "subtitulo": "ticket de conversación", "fecha": "anoche",
#                 "lineas": [["03:02", "hola"], ...], "total": ["TOTAL:", "47 MENSAJES"], "pie": ["de 03:02 a 04:10", "¡gracias!"]}
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

P = os.path.abspath(sys.argv[1])
R = json.load(open(os.path.join(P, 'recibo.json')))
W, H = 320, int(R.get('alto_px', 6400))
im = Image.new('RGB', (W, H), (246, 243, 236))
d = ImageDraw.Draw(im)
mono = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 26)
monob = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 34, index=1)
y = 60
d.text((W // 2, y), R.get('titulo', ''), font=monob, fill=(20, 20, 20), anchor='mt'); y += 50
for s in (R.get('subtitulo'), R.get('fecha')):
    if s:
        d.text((W // 2, y), s, font=mono, fill=(40, 40, 40), anchor='mt'); y += 40
y += 10
d.text((14, y), '-' * 22, font=mono, fill=(60, 60, 60)); y += 50
msgs = R.get('lineas', [])
step = (H - y - 420) / max(1, len(msgs))
for hora, m in msgs:
    words, line, lines = m.split(), '', []
    for w in words:
        if len(line) + len(w) + 1 > 15:
            lines.append(line); line = w
        else:
            line = (line + ' ' + w).strip()
    lines.append(line)
    d.text((14, y), hora, font=mono, fill=(25, 25, 25))
    for k, l in enumerate(lines):
        d.text((110, y + k * 30), l, font=mono, fill=(25, 25, 25))
    y += max(step, 30 * len(lines) + 12)
y = H - 380
d.text((14, y), '=' * 22, font=mono, fill=(30, 30, 30)); y += 50
for s in R.get('total', []):
    d.text((W // 2, y), s, font=monob, fill=(10, 10, 10), anchor='mt'); y += 55
for s in R.get('pie', []):
    d.text((W // 2, y), s, font=mono, fill=(40, 40, 40), anchor='mt'); y += 45
os.makedirs(os.path.join(P, 'build'), exist_ok=True)
im.save(os.path.join(P, 'build', 'recibo.png'))
print('build/recibo.png', im.size, f'{len(msgs)} renglones')
