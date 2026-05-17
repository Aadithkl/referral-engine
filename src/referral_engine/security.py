"""HMAC webhook signing and verification utilities."""

import hmac
import hashlib
import httpx
from .config import settings


async def webhook_notify(callback_url: str, payload_json: str) -> bool:
    """POST results to callback_url with HMAC-SHA256 signature header."""
    if not settings.WEBHOOK_SECRET:
        return False

    signature = hmac.new(
        settings.WEBHOOK_SECRET.encode(),
        payload_json.encode(),
        hashlib.sha256,
    ).hexdigest()

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                callback_url,
                content=payload_json,
                headers={
                    "Content-Type": "application/json",
                    settings.WEBHOOK_SIGNATURE_HEADER: f"hmac-sha256={signature}",
                },
                timeout=10,
            )
            return resp.status_code == 200
        except httpx.RequestError:
            return False


def verify_webhook_signature(payload: str, signature_header: str) -> bool:
    """Verify an incoming webhook's HMAC signature."""
    if not settings.WEBHOOK_SECRET:
        return False

    expected = hmac.new(
        settings.WEBHOOK_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    received = signature_header.replace("hmac-sha256=", "")
    return hmac.compare_digest(expected, received)
