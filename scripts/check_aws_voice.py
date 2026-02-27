#!/usr/bin/env python3
"""Check AWS service access for voice features."""
import boto3, json

# Check IAM role
sts = boto3.client('sts')
identity = sts.get_caller_identity()
print('IAM ARN:', identity['Arn'])

# Check Polly
try:
    polly = boto3.client('polly', region_name='ap-south-1')
    for lc in ['hi-IN', 'en-IN', 'te-IN', 'ta-IN', 'kn-IN', 'ml-IN']:
        try:
            voices = polly.describe_voices(LanguageCode=lc)
            vlist = [f"{v['Id']}({v['SupportedEngines']})" for v in voices['Voices']]
            print(f'  Polly {lc}: {vlist}')
        except:
            print(f'  Polly {lc}: NO VOICES')
except Exception as e:
    print('Polly error:', e)

# Check Transcribe
try:
    tc = boto3.client('transcribe', region_name='ap-south-1')
    print('Transcribe client: OK')
except Exception as e:
    print('Transcribe error:', e)

# Check S3
try:
    s3 = boto3.client('s3', region_name='ap-south-1')
    buckets = s3.list_buckets()
    print('S3 buckets:', [b['Name'] for b in buckets.get('Buckets', [])])
except Exception as e:
    print('S3 error:', e)
