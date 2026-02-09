import os
import azure.cognitiveservices.speech as speechsdk

p = "/tmp/audio_for_azure.wav"
if not os.path.exists(p):
    p = "/app/ejemplos/audio_prueba.wav"
print("Using audio:", p, "exists=", os.path.exists(p))
cfg = speechsdk.SpeechConfig(
    subscription=os.getenv("AZURE_SPEECH_KEY"), region=os.getenv("AZURE_SPEECH_REGION")
)
audio = speechsdk.audio.AudioConfig(filename=p)
rec = speechsdk.SpeechRecognizer(speech_config=cfg, audio_config=audio)
res = rec.recognize_once()
print("reason:", res.reason)
if res.cancellation_details:
    print("cancel reason:", res.cancellation_details.reason)
    print("error_details:", getattr(res.cancellation_details, "error_details", None))
    try:
        print(
            "raw:",
            res.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult),
        )
    except Exception:
        pass
