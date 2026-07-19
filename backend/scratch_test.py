import urllib.request
import json
import sys

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/chat',
    data=json.dumps({'question': 'Hello'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
try:
    response = urllib.request.urlopen(req)
    print("SUCCESS")
    print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"ERROR: {e.code}")
    print(e.read().decode())
