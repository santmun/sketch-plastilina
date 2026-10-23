#!/bin/zsh
# Render por tramos + mezcla + subtítulos + ensamble. UN solo Blender a la vez; espera (y luego se detiene) si el disco
# baja de MINFREE GB.
#   render.sh <proyecto> draft    -> 360x640,   4 muestras -> <proyecto>/draft.mp4
#   render.sh <proyecto> review   -> 720x1280, 12 muestras -> <proyecto>/review-$VER.mp4 (<23 MB)
#   render.sh <proyecto> final    -> 1080x1920, 40 muestras -> <proyecto>/<nombre>-$VER.mp4 + -preview (<23 MB)
# Variables: VER (v1), STEP (cuadros por tramo, 240), MINFREE (8), FORCE=1 re-renderiza tramos, BLENDER, LOOK
set -e
SK=${0:A:h:h}
P=${1:?uso: render.sh <proyecto> draft|review|final|preview}
P=${P:A}
MODE=${2:-review}
VER=${VER:-v1}
NAME=${P:t}
case $MODE in
  draft)   RES=360;  SAMPLES=4;  OUT=$P/draft.mp4 ;;
  preview) RES=540;  SAMPLES=6;  OUT=$P/preview-$VER.mp4 ;;
  review)  RES=720;  SAMPLES=12; OUT=$P/review-$VER.mp4 ;;
  final)   RES=1080; SAMPLES=40; OUT=$P/$NAME-$VER.mp4 ;;
  *) echo "modo desconocido: $MODE"; exit 1 ;;
esac
BLENDER=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}
mkdir -p $P/renders
TOTAL=$(python3 -c "import sys; sys.path.insert(0,'$SK/engine'); from project import Project; print(Project('$P').n_frames - 1)")
STEP=${STEP:-240}
python3 $SK/scripts/mix.py $P
t0=$(date +%s)
for ((a=0; a<=TOTAL; a+=STEP)); do
  b=$(( a + STEP - 1 )); (( b > TOTAL )) && b=$TOTAL
  f=renders/c${RES}_$(printf %04d $a).mp4
  [[ -s $P/$f && -z $FORCE ]] && { echo "ya existe $f"; continue; }
  free=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
  waited=0
  while (( free < ${MINFREE:-8} )); do   # disco bajo: espero (hasta 40 min) en vez de renderizar
    (( waited >= 2400 )) && { echo "DISCO BAJO (${free} GB) por 40 min: me detengo antes del tramo $a"; exit 2; }
    echo "disco bajo (${free} GB), espero..."; sleep 30; waited=$(( waited + 30 ))
    free=$(df -g /System/Volumes/Data | awk 'NR==2{print $4}')
  done
  echo "tramo $a-$b ($(date +%H:%M:%S), libre ${free} GB)"
  $BLENDER -b -P $SK/engine/scene.py -- --project $P --anim $a $b --res $RES --samples $SAMPLES --out $f > $P/renders/log_${RES}_$a.txt 2>&1
  grep -E "\[render\]" $P/renders/log_${RES}_$a.txt || { echo "falló el tramo $a"; tail -20 $P/renders/log_${RES}_$a.txt; exit 1; }
done
echo "render: $(( $(date +%s) - t0 )) s"
if [[ $MODE == final ]]; then
  python3 $SK/scripts/assemble.py $P $RES $OUT
  python3 $SK/scripts/assemble.py $P $RES ${OUT:r}-preview.mp4 --maxmb 23
else
  python3 $SK/scripts/assemble.py $P $RES $OUT --maxmb 23
fi
