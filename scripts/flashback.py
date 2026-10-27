# flashback.py — inserta un recuerdo (otro proyecto, otro set) dentro de una escena con look de flashback: cálido,
# desaturado, brillo suave, viñeta y grano, con destello blanco al entrar y al salir. El audio es el de la escena (la
# voz en off va en su guion); el subtítulo lo pone el render del flashback.
#   python3 flashback.py <escena.mp4> <flashback.mp4> <t_entra> <t_sale> <salida.mp4>
# Cómo armarlo: en la escena deja pausas para el recuerdo (p. ej. L15 pausa 1.5 → voz en off L16 → pausa 2.0);
# t_entra = L15.end + 0.25, t_sale = L16.end + 1.3 (léelos de build/timeline.json). El proyecto del flashback lleva la
# misma línea en off (copia el mp3 y su firma del manifest) con "entrada" = L16.start − t_entra y dura t_sale − t_entra.
import os, subprocess, sys


def probe(path, key):
    return subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', f'stream={key}', '-of',
                           'csv=p=0', path], capture_output=True, text=True, check=True).stdout.strip()


def main():
    if len(sys.argv) != 6:
        sys.exit('uso: flashback.py <escena.mp4> <flashback.mp4> <t_entra> <t_sale> <salida.mp4>')
    J, F, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[5])
    A, Z = float(sys.argv[3]), float(sys.argv[4])
    W, H = probe(J, 'width'), probe(J, 'height')
    L = round(Z - A, 3)
    fi, fo = round(A - 0.12, 3), round(Z - 0.3, 3)
    fc = (f'[1:v]trim=0:{L},setpts=PTS-STARTPTS,eq=saturation=0.5:gamma=1.04,'
          'colorbalance=rs=0.09:gs=0.03:bs=-0.09:rm=0.05:bm=-0.05,split[a][b];[b]gblur=sigma=14[g];'
          '[a][g]blend=all_mode=screen:all_opacity=0.32,vignette=angle=PI/3.3,noise=alls=7:allf=t,format=yuva420p,'
          f'fade=t=in:st=0:d=0.35:alpha=1,fade=t=out:st={round(L - 0.35, 3)}:d=0.35:alpha=1,setpts=PTS+{A}/TB[f];'
          f'[2:v]format=yuva420p,colorchannelmixer=aa=0.65,fade=t=in:st=0:d=0.12:alpha=1,fade=t=out:st=0.14:d=0.34:alpha=1,'
          f'setpts=PTS+{fi}/TB[w1];'
          f'[3:v]format=yuva420p,colorchannelmixer=aa=0.55,fade=t=in:st=0:d=0.15:alpha=1,fade=t=out:st=0.17:d=0.33:alpha=1,'
          f'setpts=PTS+{fo}/TB[w2];'
          '[0:v][f]overlay=0:0:eof_action=pass[v1];[v1][w1]overlay=0:0:eof_action=pass[v2];'
          '[v2][w2]overlay=0:0:eof_action=pass,format=yuv420p[v]')
    white = f'color=white:s={W}x{H}:r=24:d=0.5'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', J, '-i', F, '-f', 'lavfi', '-i', white, '-f', 'lavfi', '-i', white,
                    '-filter_complex', fc, '-map', '[v]', '-map', '0:a', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium',
                    '-c:a', 'copy', '-movflags', '+faststart', out], check=True)
    print(f'{out}  {os.path.getsize(out) / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
