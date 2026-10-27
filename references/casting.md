# Casting: voces

Modelo: `eleven_v4` (también hay `eleven_v4_turbo`; `eleven_v3` queda de respaldo). La voz de cada personaje
va en `cast.json → personajes.<NOMBRE>.voz`. Opcional: `voz_ajustes` (voice_settings de la API) por personaje.

## Dónde salen las voces

- **API de ElevenLabs** (`tts.py`): IDs de voz de la cuenta del usuario. `python3 $SK/scripts/voces.py --es` las lista.
- **MCP de ElevenLabs**: usa sus herramientas para listar voces y generar cada toma; `tts.py --plan` dice qué archivo,
  texto y voz necesita cada línea y `tts.py --registrar` las da por buenas.
- **Voces grabadas**: el usuario actúa sus personajes y guarda cada toma con el nombre que pide `tts.py --plan`.
- **Su propia voz clonada**: solo si el usuario la tiene y quiere usarla. Nunca clones la voz de otra persona sin permiso.

Los IDs de voz son de cada cuenta: no copies IDs de ejemplos o proyectos de otra persona.

## Elegir voces nuevas

```bash
python3 $SK/scripts/voces.py --es        # voces de TU cuenta de ElevenLabs (o las del MCP)
```
1. Cada personaje distinto en al menos dos ejes: género, edad, timbre (grave/brillante), acento o actitud.
   En una escena con dos IAs, que se distingan con los ojos cerrados (una calmada y una presumida con otro acento).
2. Las IAs suenan más tranquilas que los humanos: el contraste de energía es el chiste.
3. Personajes de fondo con una sola línea: voz con mucho carácter (seca, rasposa, juguetona).
4. No reutilices la voz del protagonista para otro personaje.
5. Prueba antes de fijar: genera solo una línea (`tts.py <dir> --solo 4`) y escúchala con su etiqueta.
6. Variedad: no todo el elenco de la misma edad, género y acento.
7. Si una voz queda más baja que el resto, súbela con `"voz_db": 6` en su personaje (`cast.json`).
