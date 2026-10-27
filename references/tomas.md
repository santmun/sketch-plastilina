# Planos: `shots.json` y gramática

Lista de planos; cada uno dura hasta que empieza el siguiente (corte seco). Al construir, `scene.py` escribe
`build/shots_resolved.json` (`n`, `t`, `end`, `sub`, `lens`), que usan subtítulos y mezcla (mismo esquema que el
formato de `shots.json`).

## Esquema

| Campo | Ejemplo | Qué hace |
|---|---|---|
| `n` | `"S07 Clawd contrapicado"` | nombre (marcador en Blender) |
| `t` | `"L4-0.12"`, `"L1:receta"`, `"inicio"`, `9.62` | inicio del plano (referencia de tiempo, ver blocking.md) |
| `tgt` | `"SANTI.cara"`, `"CLAWD"`, `"JEFE\|CHATGPT"`, `"set:monitor"`, `[0, -0.3, 0.8]` | a dónde mira la cámara. `A\|B` = dúo |
| `plano` | `extremo`, `detalle`, `close`, `medio`, `duo`, `americano`, `general` | encuadre automático (si no das `pos`/`off`) |
| `angulo` | `20` | grados alrededor del sujeto desde su cara (+ = hacia su izquierda). En `duo`, el signo elige el lado |
| `altura` | `0.05`, `"contrapicado"`, `"picado"`, `"ojos"` | altura de cámara respecto al objetivo |
| `desde` | `"sujeto"` (default) \| `"set"` | `set` = desde el lado del público del set (default en `general`) |
| `distancia` | `0.85` | multiplica la distancia automática |
| `lens` | `40` | lente en mm (sensor 36 mm vertical) |
| `pos` / `off` | `[0.3, -1.08, 0.36]` / `[0.55, -0.95, 0.06]` | posición absoluta, o relativa al objetivo (desactivan lo automático) |
| `f` | `2.2` | f/ (se multiplica por `look.dof`, 0.6 de noche) |
| `focus` | `"SANTI"` | punto de foco si no es el objetivo |
| `push` | `0.92` | dolly propio (0.92 = se acerca 8 %) |
| `drift` | `[0, 0.05, 0.02]` | deriva en metros a lo largo del plano |
| `track` | `true` | sigue al objetivo (alguien que camina) |
| `shake` | `["L4:qué", 0.9]` | sacudida que decae (sustos, portazos) |
| `dutch` | `8` | ángulo holandés en grados |
| `end_off`, `end_lens`, `ease_dur` | | movimiento de grúa de cierre (remate) |
| `duelo` | `true` | duelo de miradas: barras de cine + viraje cálido, sin micro push (`letterbox`, `tinte` para apagarlos) |
| `fijo` | `true` | quita el micro push |
| `libre` | `false` | no mover la cámara aunque algo la tape |
| `trucos` | `{"CLAWD": {"dyaw": 180, "dpos": [0, -0.07, 0.03]}}` | trampa de continuidad solo durante el plano |
| `sub` | `top` \| `low` \| `mid` | posición del subtítulo en ese plano |
| `probe_frac` | `[0.3, 0.97]` | cuadros para `--shotstills` |

**Micro push-in/out en TODOS los planos (automático):** 4 % de dolly alternando entrada/salida + 1.5 % de deriva
lateral + respiración de cámara en mano. Es parte del look; no lo apagues salvo en duelos.

**Encuadre automático**: tamaño de plano calibrado para 9:16 (close = 0.62 m de alto); para mascotas se escala
por su altura. La cámara se pone donde mira la cara del sujeto (si mira abajo, baja con ella). Si un mueble tapa la
vista, prueba subir, acercarse o girar (lo reporta como `[ajuste: …]`). `duo` = sobre el hombro de B mirando a A:
pon como A al humano y como B a la mascota (`"CHEF|BOLLO"`). Para clavar un encuadre exacto, usa `pos` + `tgt`.

## Gramática del formato

- **Muchos cortes**: 1.5-2.5 s de promedio (≈40 planos en 70 s). Corta 0.1-0.15 s ANTES de que empiece la línea
  (`"L5-0.12"`): la cara que va a hablar ya está en pantalla.
- **Close al que habla**, alternando ángulo (±15-25°) cada vez que vuelve el mismo personaje.
- **Reacción del que escucha** en líneas largas (`"L5.mid"`) y en cada remate: la cara del que recibe la noticia
  vende el chiste.
- **Inserto del objeto** cuando el objeto es el chiste (diapositiva, recibo, pata en el cajón).
- **Contrapicado** para la mascota que se impone; **picado** o plano lejano para el humano en problemas.
- **Duelo solo de IAs**: 5-6 cortes de 0.25-0.3 s alternando closes de los ojos de cada IA, cada vez más cerca
  (`extremo`, lentes 55-70, `dutch` ±8-10, `f` 9-14), y al final las dos frente a frente. Sin humanos en cuadro.
  Silencio o tensión del banco; nada de silbidos/twang de western.
- **Sacudida** en sustos («¿¡Qué!?», portazo). **Grúa de salida** en el remate (`end_off` + `end_lens`).
- **Subtítulos**: `low` en closes de humanos (sobre el pecho), `top` en generales y planos de mascota. Nunca
  cruzan un corte: `subs.py` los parte y el resto aparece en la posición del plano nuevo.
- Plano general de apertura (contexto en 1-2 s) y de cierre.

## Iterar

```bash
python3 $SK/scripts/auto_shots.py <dir> --sobrescribir         # borrador desde el guion (luego edítalo)
$B -b -P $SK/engine/scene.py -- --project <dir> --shotstills --check --res 360 --samples 8
python3 $SK/scripts/contact.py <dir>/test/shots <dir>/test/planos.jpg --cols 8
$B -b -P $SK/engine/scene.py -- --project <dir> --stills L4:descargó,9.3 --res 540   # cuadros sueltos
$B -b -P $SK/engine/scene.py -- --project <dir> --frames 5:8:0.5 --vista "0,-1.25,0.95;0,-0.25,0.68"  # cámara de depuración
```
El log imprime cada plano (`[plano] … cam=… obj=…`) para corregir coordenadas a mano.
