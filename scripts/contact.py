# contact.py — hoja de contactos para REVISAR con los ojos (bocas, choques, cortes).
#   python3 contact.py <carpeta_con_jpgs | video.mp4> <salida.jpg> [--cols 6] [--cell 240] [--cada 0.5] [--desde 0] [--hasta 99]
import glob, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
argv = sys.argv[3:]


def opt(n, d):
    return type(d)(argv[argv.index(n) + 1]) if n in argv else d


cols, cw = opt('--cols', 6), opt('--cell', 240)
labels = []
if src.lower().endswith(('.mp4', '.mov', '.mkv')):
    every, a, b = opt('--cada', 0.5), opt('--desde', 0.0), opt('--hasta', 1e9)
    tmp = tempfile.mkdtemp(prefix='contact_')
    subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(a), '-i', src, '-t', str(max(0.1, b - a)), '-vf', f'fps=1/{every}',
                    '-q:v', '3', os.path.join(tmp, 'f_%04d.jpg')], check=True)
    files = sorted(glob.glob(os.path.join(tmp, '*.jpg')))
    labels = [f'{a + i * every:.1f}s' for i in range(len(files))]
else:
    files = sorted(glob.glob(os.path.join(src, '*.jpg')))
    labels = [os.path.basename(f)[:-4] for f in files]
if not files:
    sys.exit('sin cuadros')
im0 = Image.open(files[0])
ch = int(cw * im0.height / im0.width)
rows = (len(files) + cols - 1) // cols
sheet = Image.new('RGB', (cols * cw, rows * (ch + 18)), (20, 18, 16))
try:
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 13)
except Exception:
    font = ImageFont.load_default()
d = ImageDraw.Draw(sheet)
for i, f in enumerate(files):
    im = Image.open(f).convert('RGB').resize((cw, ch))
    x, y = (i % cols) * cw, (i // cols) * (ch + 18)
    sheet.paste(im, (x, y + 18))
    d.text((x + 4, y + 2), labels[i], fill=(240, 200, 120), font=font)
sheet.save(out, quality=86)
if src.lower().endswith(('.mp4', '.mov', '.mkv')):
    for f in files:
        os.remove(f)
    os.rmdir(os.path.dirname(files[0]))
print(out, sheet.size)
