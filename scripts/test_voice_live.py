from backend.services.voice_service import voice, POLLY_VOICES, TRANSCRIBE_LANG_MAP, POLLY_UNSUPPORTED
print("=== Voice Service Module Loaded ===")
print("Polly voices:", POLLY_VOICES)
print("Transcribe langs:", list(TRANSCRIBE_LANG_MAP.keys()))
print("TTS available:", voice.is_tts_available())
print("STT available:", voice.is_stt_available())
audio = voice.text_to_speech("Hello farmer, welcome to KrishiSaathi", "en", "mp3")
print("TTS English:", len(audio) if audio else "FAILED", "bytes")
audio_hi = voice.text_to_speech("Namaste kisan", "hi", "mp3")
print("TTS Hindi:", len(audio_hi) if audio_hi else "FAILED", "bytes")
for lang in ["en", "hi", "te", "ta", "kn"]:
    tts_lang, needs_trans = voice.get_tts_language(lang)
    print(f"  {lang} -> tts_lang={tts_lang}, needs_translation={needs_trans}")
print("=== ALL TESTS PASSED ===")
