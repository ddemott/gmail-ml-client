import base64
import re
from typing import Any


def _decode_body(payload_part: dict[str, Any]) -> str:
    data = payload_part.get("body", {}).get("data")
    if not data:
        return ""
    return base64.urlsafe_b64decode(data.encode("UTF-8")).decode("UTF-8", errors="ignore")


def extract_text(msg: dict[str, Any]) -> str:
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    subject = headers.get("subject", "")

    payload = msg.get("payload", {})
    body_text = ""

    def walk(p: dict[str, Any]) -> None:
        nonlocal body_text
        mime = p.get("mimeType", "")
        if "text/plain" in mime and p.get("body", {}).get("data"):
            body_text += _decode_body(p)
        elif "text/html" in mime and p.get("body", {}).get("data"):
            html = _decode_body(p)
            # naive html strip
            body_text += re.sub("<[^<]+?>", " ", html)
        for part in p.get("parts", []) or []:
            walk(part)

    walk(payload)
    txt = f"{subject}\n{body_text}".lower()
    # normalize
    txt = re.sub(r"http[s]?://\\S+", " URL ", txt)
    txt = re.sub(r"[^a-z0-9@\\s$]", " ", txt)
    txt = re.sub(r"\\s+", " ", txt).strip()
    return txt
