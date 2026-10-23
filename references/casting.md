# Casting: voces

Modelo: `eleven_v4` (también hay `eleven_v4_turbo`; `eleven_v3` queda de respaldo). La voz de cada personaje
va en `cast.json → personajes.<NOMBRE>.voz`. Opcional: `voz_ajustes` (voice_settings de la API) por personaje.

## Voces de «A escondidas»

| Personaje | Voice ID | Voz | Por qué |
|---|---|---|---|
| Santi | `qGrxMQgsw74f3cWR4I0K` | Santiago (voz de Santi) | El protagonista es él |
| Clawd | `9EU0h6CVtEDS6vriwwq5` | Verónica (en la cuenta aparece como «Julieta - Young, Gentle & Calm») | Calma suave: el deadpan de la IA |
| Jefe | `OLmSqlYzB06EIKJRy5b0` | Murdock, grave y autoritaria | Imponente; contraste con la voz de Santi |
| ChatGPT | `jbWMqMKDKL7X0v1DXTHH` | Franco, argentino seguro | Presumido; el acento lo separa de Clawd al instante |
| Gemini | `qWWAqFomnJ99VwQLREfT` | Kate, brillante y juguetona | Cómplice y traviesa |
| Mariana | `p18tR9wFA5Ng9WhfWI0o` | Isabella, narración casual | Seca y tierna para el remate |

Probadas en el ejercicio de validación (café): Chef = `Rt1JHkPO27QCUX6Nd5bV` (Jorge, rasposa, mayor);
Bollo (mascota pan) = `eeTcHFmLuUzCOHvnwvdr` (Angie, joven mexicana segura).

## Elegir voces nuevas

```bash
doppler run --project editorbrain --config dev -- python3 $SK/scripts/voces.py --es
```
1. Cada personaje distinto en al menos dos ejes: género, edad, timbre (grave/brillante), acento o actitud.
   En una escena con dos IAs, que se distingan con los ojos cerrados (Clawd calma vs ChatGPT argentino presumido).
2. Las IAs suenan más tranquilas que los humanos: el contraste de energía es el chiste.
3. Personajes de fondo con una sola línea: voz con mucho carácter (seca, rasposa, juguetona).
4. Evita reutilizar la voz de Santi para otro personaje y no clones voces de personas reales sin permiso.
5. Prueba antes de fijar: genera solo una línea (`tts.py <dir> --solo 4`) y escúchala con su etiqueta.
6. Variedad: no todo el elenco latino de la misma edad y acento; mezcla (Santi pide diversidad en personajes).
