#!/usr/bin/env python3
"""Test actual AWS service calls for voice features."""
import boto3, json, time

region = 'ap-south-1'

# Test 1: Polly - Try synthesizing speech directly
print("=== POLLY TEST ===")
try:
    polly = boto3.client('polly', region_name=region)
    # List ALL voices - no language filter
    all_v = polly.describe_voices()
    indian_voices = [v for v in all_v['Voices'] if 'IN' in v.get('LanguageCode','')]
    print(f"Indian voices found: {len(indian_voices)}")
    for v in indian_voices:
        print(f"  {v['Id']} | {v['LanguageCode']} | {v['SupportedEngines']} | {v['Gender']}")

    # Try to actually synthesize speech
    resp = polly.synthesize_speech(
        Text="Hello, this is a test from KrishiSaathi.",
        OutputFormat='mp3',
        VoiceId='Aditi',
    )
    audio = resp['AudioStream'].read()
    print(f"Polly synthesis: SUCCESS ({len(audio)} bytes)")
except Exception as e:
    print(f"Polly error: {e}")

# Test 2: Transcribe - Check if we can list jobs
print("\n=== TRANSCRIBE TEST ===")
try:
    tc = boto3.client('transcribe', region_name=region)
    jobs = tc.list_transcription_jobs(MaxResults=1)
    print(f"Transcribe list jobs: SUCCESS (found {len(jobs.get('TranscriptionJobSummaries',[]))} jobs)")
except Exception as e:
    print(f"Transcribe error: {e}")

# Test 3: S3 - Try creating bucket
print("\n=== S3 TEST ===")
bucket = 'krishisaathi-voice-temp-904408286347'
try:
    s3 = boto3.client('s3', region_name=region)
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"Bucket {bucket}: EXISTS")
    except:
        s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={'LocationConstraint': region}
        )
        print(f"Bucket {bucket}: CREATED")

    # Test upload
    s3.put_object(Bucket=bucket, Key='test.txt', Body=b'hello')
    print(f"S3 put_object: SUCCESS")
    s3.delete_object(Bucket=bucket, Key='test.txt')
    print(f"S3 cleanup: SUCCESS")
except Exception as e:
    print(f"S3 error: {e}")
