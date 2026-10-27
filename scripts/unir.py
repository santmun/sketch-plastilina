# unir.py — une varias escenas (un proyecto por set) en un solo video, con un letrero opcional al arrancar cada una.
#   python3 unir.py <salida.mp4> <escena1.mp4> [<escena2.mp4> --letrero "Esa noche…"] [<escena3.mp4> ...]
# El letrero va sobre los primeros ~2 s de la escena que lo sigue, centrado, con fundido (deja «entrada» de ~1.8 s en
# el look.json de esa escena para que no tape subtítulos). Todas las escenas deben tener la misma resolución.
import os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entorno


def probe(path, key):
    return subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', f'stream={key}', '-of',
                           'csv=p=0', path], capture_output=True, text=True, check=True).stdout.strip()


def card_png(text, w, h, out):
    from PIL import Image, ImageDraw
    f = entorno.find_font(int(w * 0.085))
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((w // 2, int(h * 0.5)), text, font=f, fill=(255, 255, 255, 255), anchor='mm',
                             stroke_width=max(2, w // 180), stroke_fill=(0, 0, 0, 200))
    img.save(out)


def main():
    argv = sys.argv[1:]
    if len(argv) < 2:
        sys.exit('uso: unir.py <salida.mp4> <escena1.mp4> [<escena2.mp4> --letrero "Esa noche…"] ...')
    out, rest = os.path.abspath(argv[0]), argv[1:]
    scenes, i = [], 0
    while i < len(rest):
        if rest[i] == '--letrero':
            scenes[-1]['letrero'] = rest[i + 1]
            i += 2
            continue
        scenes.append(dict(path=os.path.abspath(rest[i])))
        i += 1
    w, h = int(probe(scenes[0]['path'], 'width')), int(probe(scenes[0]['path'], 'height'))
    tmp = tempfile.mkdtemp(prefix='unir-')
    parts = []
    for k, sc in enumerate(scenes):
        src = sc['path']
        if sc.get('letrero'):
            png = os.path.join(tmp, f'letrero{k}.png')
            card_png(sc['letrero'], w, h, png)
            dst = os.path.join(tmp, f'escena{k}.mp4')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-loop', '1', '-t', '2.2', '-i', png, '-filter_complex',
                            '[1:v]format=rgba,fade=t=in:st=0.15:d=0.25:alpha=1,fade=t=out:st=1.35:d=0.35:alpha=1[t];'
                            '[0:v][t]overlay=0:0:eof_action=pass[v]', '-map', '[v]', '-map', '0:a', '-c:v', 'libx264',
                            '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', dst],
                           check=True)
            src = dst
        parts.append(src)
    ins = sum([['-i', p] for p in parts], [])
    streams = ''.join(f'[{k}:v][{k}:a]' for k in range(len(parts)))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', f'{streams}concat=n={len(parts)}:v=1:a=1[v][a]',
                    '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', '20', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
    print(f'{out}  {os.path.getsize(out) / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
