#!/usr/bin/env bash
set -euo pipefail

OUT=/tmp/voiceflow_diagnose_$(date +%s).log
echo "VoiceFlow diagnose started at $(date)" | tee "$OUT"

echo "\n--- ENVIRONMENT ---" | tee -a "$OUT"
echo "AZURE_SPEECH_KEY set: ${AZURE_SPEECH_KEY:+yes}" | tee -a "$OUT"
echo "AZURE_SPEECH_REGION: ${AZURE_SPEECH_REGION:-<not set>}" | tee -a "$OUT"
echo "VOICEFLOW_USE_REAL_AGENTS: ${VOICEFLOW_USE_REAL_AGENTS:-<not set>}" | tee -a "$OUT"

echo "\n--- AUDIO FILES (searching /app and /app/examples) ---" | tee -a "$OUT"
AUDIO_FILES=()
while IFS= read -r -d $'\0' f; do AUDIO_FILES+=("$f"); done < <(find /app /app/examples 2>/dev/null -type f \( -iname "*.wav" -o -iname "*.mp3" \) -print0 || true)

if [ ${#AUDIO_FILES[@]} -eq 0 ]; then
  echo "No audio files found under /app or /app/examples" | tee -a "$OUT"
else
  for f in "${AUDIO_FILES[@]}"; do
    echo "\nFILE: $f" | tee -a "$OUT"
    ls -l "$f" 2>&1 | tee -a "$OUT"
    file "$f" 2>&1 | tee -a "$OUT"
    if command -v ffprobe >/dev/null 2>&1; then
      echo "ffprobe info:" | tee -a "$OUT"
      ffprobe -hide_banner -loglevel error -show_streams "$f" 2>&1 | tee -a "$OUT"
    fi
  done
fi

echo "\n--- CONVERTING FIRST WAV TO /tmp/audio_for_azure.wav (if exists) ---" | tee -a "$OUT"
if [ ${#AUDIO_FILES[@]} -gt 0 ]; then
  SRC="${AUDIO_FILES[0]}"
  echo "Using source: $SRC" | tee -a "$OUT"
  if command -v ffmpeg >/dev/null 2>&1; then
    ffmpeg -y -i "$SRC" -ac 1 -ar 16000 -sample_fmt s16 /tmp/audio_for_azure.wav -hide_banner -loglevel error && echo "Converted to /tmp/audio_for_azure.wav" | tee -a "$OUT" || echo "ffmpeg conversion failed" | tee -a "$OUT"
  else
    echo "ffmpeg not installed; skipping conversion" | tee -a "$OUT"
  fi
else
  echo "No source audio to convert" | tee -a "$OUT"
fi

echo "\n--- AZURE SDK: package path and native libs ---" | tee -a "$OUT"
python - <<'PY' 2>&1 | tee -a "$OUT"
import os, inspect, glob
try:
    import azure.cognitiveservices.speech as s
    p = os.path.dirname(inspect.getfile(s))
    print('azure package:', p)
    so_files = glob.glob(os.path.join(p, '**', '*.so'), recursive=True)
    print('so files found:')
    for so in so_files:
        print(so)
except Exception as e:
    print('Failed to import azure.cognitiveservices.speech:', e)
    so_files = []
print('\nEnd python listing')
PY

echo "\n--- LDD on native libs (if any found) ---" | tee -a "$OUT"
python - <<'PY' 2>/dev/null | tee -a "$OUT" || true
import os, inspect, glob
try:
    import azure.cognitiveservices.speech as s
    p = os.path.dirname(inspect.getfile(s))
    so_files = glob.glob(os.path.join(p, '**', '*.so'), recursive=True)
    for so in so_files:
        print('\nLDD for', so)
        import subprocess
        try:
            out = subprocess.check_output(['ldd', so], stderr=subprocess.STDOUT, text=True)
            print(out)
        except Exception as e:
            print('ldd failed:', e)
except Exception as e:
    print('Could not enumerate .so files:', e)
PY

echo "\n--- RUN Azure minimal recognition test (if SDK present) ---" | tee -a "$OUT"
python - <<'PY' 2>&1 | tee -a "$OUT" || true
import os
try:
    import azure.cognitiveservices.speech as speechsdk
except Exception as e:
    print('Azure SDK import failed:', e)
    raise SystemExit(0)

cfg = speechsdk.SpeechConfig(subscription=os.getenv('AZURE_SPEECH_KEY',''), region=os.getenv('AZURE_SPEECH_REGION',''))
audio_path = '/tmp/audio_for_azure.wav' if os.path.exists('/tmp/audio_for_azure.wav') else None
if not audio_path:
    # try common example path
    for candidate in ['/app/ejemplos/audio_prueba.wav', '/app/examples/user_voice_input.wav', '/app/examples/audio_prueba.wav']:
        if os.path.exists(candidate):
            audio_path = candidate
            break

print('Test audio path:', audio_path)
if not audio_path:
    print('No audio file available for test; skipping recognition')
else:
    try:
        audio = speechsdk.audio.AudioConfig(filename=audio_path)
        rec = speechsdk.SpeechRecognizer(speech_config=cfg, audio_config=audio)
        res = rec.recognize_once()
        print('Result reason:', res.reason)
        if res.cancellation_details:
            print('Cancellation reason:', res.cancellation_details.reason)
            print('Error details:', getattr(res.cancellation_details, 'error_details', None))
            try:
                raw = res.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
                print('Raw JSON result:', raw)
            except Exception as e:
                print('Could not get raw JSON result:', e)
    except Exception as e:
        print('Recognition threw exception:', e)
PY

echo "\nDiagnose complete. Log saved to: $OUT" | tee -a "$OUT"
echo "----- LOG START -----"
cat "$OUT"
echo "----- LOG END -----"
