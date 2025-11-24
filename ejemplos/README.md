# Carpeta para archivos de audio de ejemplo

Coloca aquí tus archivos de audio para probar el agente STT.

## Formatos recomendados:
- **WAV 16kHz mono** (mejor calidad para STT)
- MP3
- M4A
- FLAC

## Archivos de ejemplo sugeridos:
- `audio_prueba.wav` - Audio de prueba básico
- `audio_espanol.wav` - Audio en español
- `audio_ingles.wav` - Audio en inglés

## Conversión de audio:
Si tienes archivos en otros formatos, puedes convertirlos usando FFmpeg:

```bash
# Convertir a WAV 16kHz mono (óptimo para STT)
ffmpeg -i tu_audio.mp3 -ar 16000 -ac 1 audio_prueba.wav

# Convertir manteniendo calidad original
ffmpeg -i tu_audio.mp4 -vn audio_prueba.wav
```

## Notas:
- Los archivos de audio no se suben al repositorio (están en .gitignore)
- Para la PoC, puedes grabar audio directamente desde tu micrófono
- Duración recomendada: 10-60 segundos para pruebas
