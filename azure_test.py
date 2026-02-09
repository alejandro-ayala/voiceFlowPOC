import azure.cognitiveservices.speech as speechsdk
import os

cfg = speechsdk.SpeechConfig(
    subscription=os.getenv("AZURE_SPEECH_KEY"), region=os.getenv("AZURE_SPEECH_REGION")
)
audio = speechsdk.audio.AudioConfig(filename="/app/ejemplos/audio_prueba.wav")
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
