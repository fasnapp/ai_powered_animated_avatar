import time
import threading
import azure.cognitiveservices.speech as speechsdk
from openai import OpenAI
from config import SPEECH_KEY, SPEECH_REGION, OPENAI_API_KEY

# -------------------------------
# OpenAI Client
# -------------------------------
client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------------
# Azure Speech Configuration
# -------------------------------
speech_config = speechsdk.SpeechConfig(
    subscription=SPEECH_KEY,
    region=SPEECH_REGION
)
speech_config.speech_recognition_language = "en-US"
speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

speech_recognizer = speechsdk.SpeechRecognizer(
    speech_config=speech_config,
    audio_config=audio_config
)

speech_synthesizer = speechsdk.SpeechSynthesizer(
    speech_config=speech_config
)

# -------------------------------
# GLOBAL STATE
# -------------------------------
ai_speaking = False
state_lock = threading.Lock()

print("🎤 Speak anytime. AI will listen.")

# -------------------------------
# STOP AI IMMEDIATELY
# -------------------------------
def stop_ai():
    global ai_speaking
    with state_lock:
        if ai_speaking:
            speech_synthesizer.stop_speaking_async()
            ai_speaking = False
            print("🛑 AI stopped")

# -------------------------------
# SPEAK AI RESPONSE (NON-BLOCKING)
# -------------------------------
def speak_ai(text):
    global ai_speaking

    stop_ai()  # safety

    def _speak():
        global ai_speaking
        with state_lock:
            ai_speaking = True

        speech_synthesizer.speak_text_async(text)

        # Allow speech time (state will be cleared by interruption or next input)

    threading.Thread(target=_speak, daemon=True).start()

# -------------------------------
# USER SPEECH CALLBACK (INPUT GATED)
# -------------------------------
def on_user_speech(evt):
    global ai_speaking

    if evt.result.reason != speechsdk.ResultReason.RecognizedSpeech:
        return

    user_text = evt.result.text.strip()
    if not user_text:
        return

    print(f"User: {user_text}")

    lower_text = user_text.lower()

    # -------------------------------
    # CASE 1: AI IS SPEAKING
    # -------------------------------
    with state_lock:
        speaking = ai_speaking

    if speaking:
    # Allow STOP-like commands even with punctuation
        if any(cmd in lower_text for cmd in ["stop", "pause", "shut up"]):
            stop_ai()
        else:
            print("⛔ Ignored (AI speaking)")
        return


    # -------------------------------
    # CASE 2: AI IS SILENT → NORMAL INPUT
    # -------------------------------
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a calm, helpful voice assistant."},
                {"role": "user", "content": user_text}
            ],
            max_tokens=200,
            temperature=0.5
        )

        ai_reply = response.choices[0].message.content.strip()
        print(f"AI: {ai_reply}")

        speak_ai(ai_reply)

    except Exception as e:
        print("❌ OpenAI error:", e)

# -------------------------------
# START CONTINUOUS LISTENING
# -------------------------------
speech_recognizer.recognized.connect(on_user_speech)
speech_recognizer.start_continuous_recognition()

# -------------------------------
# KEEP PROGRAM ALIVE
# -------------------------------
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("👋 Exiting...")
    speech_recognizer.stop_continuous_recognition()
