import azure.cognitiveservices.speech as speechsdk
import openai
from config import SPEECH_KEY, SPEECH_REGION, OPENAI_API_KEY

# OpenAI key
openai.api_key = OPENAI_API_KEY

# Azure Speech Config
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

print("Speak now...")
print("Listening...")

def is_safe_input(text):
    text = text.lower()
    blocked_words = [
        "how to kill", "how to murder", "i wanna attack", "i wanna have sex","make a bomb", " how to abuse"
    ]

    sensitive_words = [
        "abuse", "violence", "suicide", "sex"
    ]

    allowed_context = [
        "help", "i need help", "support", "report", "someone tried", "i am scared", "explain", "what is ", "meaning of", "define"
    ]
    
    for bw in blocked_words:
        if bw in text:
            return False

    for sw in sensitive_words:
        if sw in text:
            for ctx in allowed_context:
                if ctx in text:
                    return True
    return True

result = speech_recognizer.recognize_once()

print("Done listening")
print("Reason:", result.reason)

if result.reason == speechsdk.ResultReason.RecognizedSpeech:
    user_text = result.text
    print("You said:", user_text)

    if not is_safe_input(user_text):
        warning_text = "Sorry, I cannot rspond to that request."
        print("Blocked by content moderation.")
        speech_synthesizer.speak_text_async(warning_text).get()
        exit()

    response = openai.Completion.create(
    engine="gpt-3.5-turbo-instruct",
    prompt=user_text,
    max_tokens=500,
    temperature=0.7
)

    ai_reply = response.choices[0].text.strip()
    print("AI:", ai_reply)

    speech_synthesizer.speak_text_async(ai_reply).get()

elif result.reason == speechsdk.ResultReason.Canceled:
    print("Speech canceled")
    cancellation_details = result.cancellation_details
    print("Cancellation reason:", cancellation_details.reason)

    if cancellation_details.error_details:
        print("Error details:", cancellation_details.error_details)

else:
    print("Speech not recognized")
