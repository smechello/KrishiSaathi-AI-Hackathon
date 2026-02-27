#!/usr/bin/env python3
"""Check and attach IAM policies for voice features."""
import boto3

iam = boto3.client('iam')

# List current policies
role = 'KrishiSaathiEC2Role'
ps = iam.list_attached_role_policies(RoleName=role)
current = [p['PolicyName'] for p in ps['AttachedPolicies']]
print('Current policies:', current)

# Required policies for voice features
needed = {
    'AmazonPollyFullAccess': 'arn:aws:iam::aws:policy/AmazonPollyFullAccess',
    'AmazonTranscribeFullAccess': 'arn:aws:iam::aws:policy/AmazonTranscribeFullAccess',
    'AmazonS3FullAccess': 'arn:aws:iam::aws:policy/AmazonS3FullAccess',
}

for name, arn in needed.items():
    if name not in current:
        print(f'  Attaching {name}...')
        try:
            iam.attach_role_policy(RoleName=role, PolicyArn=arn)
            print(f'    OK: {name} attached')
        except Exception as e:
            print(f'    FAIL: {e}')
    else:
        print(f'  Already attached: {name}')

# Re-check Polly after policy attachment
import time
time.sleep(2)
try:
    polly = boto3.client('polly', region_name='ap-south-1')
    # List ALL voices (no language filter)
    voices = polly.describe_voices()
    indian = [f"{v['Id']}({v['LanguageCode']})" for v in voices['Voices']
              if v['LanguageCode'].endswith('-IN') or v['LanguageCode'] in ('hi-IN','te-IN','ta-IN')]
    print(f'\nPolly Indian voices: {indian}')

    # Also check all available voices
    all_voices = [f"{v['Id']}({v['LanguageCode']},{v['SupportedEngines']})" for v in voices['Voices']]
    print(f'\nPolly ALL voices count: {len(all_voices)}')
    # Show first 10 for reference
    for v in all_voices[:10]:
        print(f'  {v}')
except Exception as e:
    print(f'Polly check error: {e}')

# Check S3
try:
    s3 = boto3.client('s3', region_name='ap-south-1')
    buckets = s3.list_buckets()
    print(f'\nS3 buckets: {[b["Name"] for b in buckets.get("Buckets", [])]}')
except Exception as e:
    print(f'S3 check: {e}')

# Create voice temp bucket if needed
bucket_name = 'krishisaathi-voice-temp-904408286347'
try:
    s3.head_bucket(Bucket=bucket_name)
    print(f'Bucket {bucket_name} exists')
except:
    try:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'}
        )
        print(f'Created bucket: {bucket_name}')
    except Exception as e:
        print(f'Create bucket error: {e}')
