# Guion: cómo escribirlo

`guion.json`:
```json
{
 "modelo": "eleven_v4",
 "lineas": [
  ["SANTI", "[whispers] [nervous] Claude... ¿mi jefe sabe que tú haces mi trabajo?", 0.24],
  ["CLAWD", "[whispers] [calm] No.", 0.17]
 ]
}
```
Cada línea: `[PERSONAJE, texto con etiquetas, pausa en segundos DESPUÉS de la línea]`. El personaje debe existir
en `cast.json` (ahí vive su voz). `timeline.py` arma el diálogo con 0.3 s de entrada (`look.json: entrada`) y la
cola final (`cola`, 0.8 s). Nunca hay dos líneas encimadas (el lip-sync usa una sola envolvente RMS).

## Etiquetas de audio (ElevenLabs v4)

En inglés, entre corchetes, al inicio de la línea (se pueden encadenar dos). Las usadas en «A escondidas»:
`[whispers]` `[nervous]` `[calm]` `[relieved sigh]` `[pleasantly surprised]` `[shocked]` `[matter-of-fact]`
`[panicked whisper]` `[suspicious]` `[softly]` `[sad]` `[gently]` `[tender]` `[quietly]` `[nervous smile]`
`[smug]` `[offended]` `[hurt]` `[slowly]` `[guilty]` `[deadpan]` `[playful]` `[cheerful]`.

- La boca abre 25 % menos en líneas con `[whispers]`: susurrar se ve.
- Puntos suspensivos al inicio (`...¿Ah, sí?`) dan una pausa de reacción natural.
- Los subtítulos quitan las etiquetas solas; la ortografía del texto es la del subtítulo (acentos, ¿¡ !?).

## Longitud y ritmo

- 26-32 líneas para 60-70 s. La mayoría de 1-7 palabras; solo las preguntas de planteamiento llegan a ~12.
- Pausas: 0.15-0.25 s entre réplicas rápidas; 0.3-0.45 antes de un remate; 0.6-1.6 s para silencios con
  intención (antes del duelo, después de «Nadie vio nada»).
- Corre `timeline.py`: imprime la duración real. Si pasa de 70 s, recorta líneas, no aceleres voces.

## Reglas de comedia

1. El humano reacciona; la IA responde corto, tranquila y literal (deadpan). La IA nunca explica el chiste.
2. Cada respuesta empeora la situación (escalada). Si una línea no sube la apuesta, sobra.
3. Números concretos y horas exactas ganan a adjetivos.
4. Callbacks: lo que se siembra en el beat tierno regresa en el giro final.
5. Un objeto en pantalla remata (diapositiva, recibo, pata en el cajón); escríbelo en el guion como acotación
   para planearlo en `blocking.json`.
6. Coherencia interna: fechas, cantidades y quién sabe qué. Lee el guion de corrido buscando contradicciones
   («Mañana capacitas…» vs «en cuatro minutos» tuvo que corregirse).
7. Español natural (México/neutro), sin emojis, sin groserías gratuitas. Nombres de marcas tal cual (Claude,
   ChatGPT, Gemini).
8. Cierra con plano general y algo que amplíe el mundo (todos tienen su IA).

## Revisión antes de pedir aprobación

- ¿La premisa está en la primera línea?  ¿Hay 2-3 escalones claros?  ¿Hay siembra y giro?
- ¿Cada personaje tiene una voz distinta y una actitud reconocible?
- ¿Cabe en 60-70 s?  ¿Algún dato se contradice?
