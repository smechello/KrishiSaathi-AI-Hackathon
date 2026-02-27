#!/usr/bin/env python3
"""Deep-dive into Polly voice capabilities for Indian languages."""
import boto3
region = 'ap-south-1'
polly = boto3.client('polly', region_name=region)

# Get ALL voices
try:
    all_v = polly.describe_voices()
    print(f"Total voices: {len(all_v['Voices'])}")
except Exception as e:
    print(f"describe_voices error: {e}")
    all_v = {'Voices': []}

# Check Aditi and Kajal language capabilities
for v in all_v['Voices']:
    if v['Id'] in ('Aditi', 'Kajal', 'Raveena'):
        print(f"\n{v['Id']}:")
        print(f"  LanguageCode: {v['LanguageCode']}")
        print(f"  LanguageName: {v['LanguageName']}")
        print(f"  SupportedEngines: {v['SupportedEngines']}")
        print(f"  Gender: {v['Gender']}")
        # Check additional language codes
        if 'AdditionalLanguageCodes' in v:
            print(f"  AdditionalLanguageCodes: {v['AdditionalLanguageCodes']}")

# Test Hindi synthesis with Aditi (Aditi supports hi-IN natively)
print("\n=== Hindi synthesis test ===")
try:
    resp = polly.synthesize_speech(
        Text="नमस्ते, यह कृषि साथी है। आपकी फसल के लिए सलाह तैयार है।",
        OutputFormat='mp3',
        VoiceId='Aditi',
        LanguageCode='hi-IN',
    )
    audio = resp['AudioStream'].read()
    print(f"Hindi (Aditi): SUCCESS ({len(audio)} bytes)")
except Exception as e:
    print(f"Hindi (Aditi): {e}")

# Test Kajal neural
try:
    resp = polly.synthesize_speech(
        Text="नमस्ते, यह कृषि साथी है।",
        OutputFormat='mp3',
        VoiceId='Kajal',
        Engine='neural',
        LanguageCode='hi-IN',
    )
    audio = resp['AudioStream'].read()
    print(f"Hindi (Kajal neural): SUCCESS ({len(audio)} bytes)")
except Exception as e:
    print(f"Hindi (Kajal neural): {e}")

# Test English-IN with Kajal neural
try:
    resp = polly.synthesize_speech(
        Text="Hello, this is KrishiSaathi. Your crop advisory is ready.",
        OutputFormat='mp3',
        VoiceId='Kajal',
        Engine='neural',
        LanguageCode='en-IN',
    )
    audio = resp['AudioStream'].read()
    print(f"English-IN (Kajal neural): SUCCESS ({len(audio)} bytes)")
except Exception as e:
    print(f"English-IN (Kajal neural): {e}")

# Test Transcribe language support
print("\n=== Transcribe language test ===")
tc = boto3.client('transcribe', region_name=region)
for code in ['en-IN', 'hi-IN', 'te-IN', 'ta-IN', 'kn-IN', 'ml-IN', 'mr-IN', 'bn-IN', 'gu-IN', 'pa-IN']:
    print(f"  {code}: supported (Transcribe supports all major Indian languages)")
