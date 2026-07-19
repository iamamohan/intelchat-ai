"""
End-to-end test: POST /api/chat with a real question to see full pipeline output.
"""
import urllib.request
import json

payload = json.dumps({
    "question": "tell me about this resume person"
}).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:8000/api/chat",
    data=payload,
    headers={"Content-Type": "application/json"}
)

try:
    resp = urllib.request.urlopen(req, timeout=60)
    data = json.loads(resp.read().decode())
    print("=== SUCCESS ===")
    print(f"Answer: {data.get('answer', '')[:500]}")
    print(f"Confidence: {data.get('retrieval_confidence')}")
    print(f"Sources: {len(data.get('sources', []))}")
    for s in data.get('sources', []):
        print(f"  - {s.get('document_name')} | score={s.get('similarity_score')}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"=== HTTP ERROR {e.code} ===")
    print(body)
except Exception as e:
    print(f"=== ERROR ===")
    print(type(e).__name__, e)
