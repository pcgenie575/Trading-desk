"""HMAC binds durable single-use approval to the exact queued proposal."""
import json,hashlib,hmac
VERSION='decision-contract-v1'
def digest(payload):return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sign(body,key):return hmac.new(key.encode(),json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False).encode(),hashlib.sha256).hexdigest()
def verify(body,signature,key):return bool(key) and hmac.compare_digest(sign(body,key),signature)
