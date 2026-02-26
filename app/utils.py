import json
import time
import uuid
import hashlib
from datetime import datetime, timezone
from flask import g, request

def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()

def new_uuid():
    return str(uuid.uuid4())

def get_request_id():
    rid = request.headers.get("X-Request-Id")
    return rid if rid else new_uuid()

def canonical_json_bytes(obj) -> bytes:
    """
    Stable JSON serialization so logically-identical payloads hash the same.
    """
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return s.encode("utf-8")

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def request_fingerprint(payload: dict) -> str:
    return sha256_hex(canonical_json_bytes(payload))

def json_dumps(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)

def json_loads(s: str):
    return json.loads(s)

def log_event(event, **fields):
    payload = {
        "event": event,
        "request_id": getattr(g, "request_id", None),
        **fields,
    }
    print(json.dumps(payload, ensure_ascii=False))