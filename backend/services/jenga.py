"""
CursorCode AI - JengaHQ Payment Service
Handles OAuth2 authentication, payment link creation, IPN verification,
and recurring billing via JengaHQ (Finserve Africa).

When JENGA_API_KEY is not set, operates in demo mode.
"""

import hmac
import hashlib
import logging
import uuid
from base64 import b64encode
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

from core.config import (
    JENGA_API_KEY, JENGA_MERCHANT_CODE, JENGA_CONSUMER_SECRET,
    JENGA_WEBHOOK_SECRET, JENGA_BASE_URL, JENGA_CURRENCY, FRONTEND_URL
)

logger = logging.getLogger(__name__)

# Cached token
_token_cache = {"token": None, "expires_at": None}


def is_demo_mode() -> bool:
    return not JENGA_API_KEY


async def get_auth_token() -> str:
    """Get OAuth2 Bearer token from JengaHQ. Caches until expiry."""
    if is_demo_mode():
        return "demo_token_mock"

    now = datetime.now(timezone.utc)
    if _token_cache["token"] and _token_cache["expires_at"] and _token_cache["expires_at"] > now:
        return _token_cache["token"]

    url = f"{JENGA_BASE_URL}/authentication/api/v3/authenticate/merchant"
    auth_string = b64encode(f"{JENGA_API_KEY}:{JENGA_CONSUMER_SECRET}".encode()).decode()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json={
            "merchantCode": JENGA_MERCHANT_CODE,
            "consumerSecret": JENGA_CONSUMER_SECRET,
        }, headers={
            "Api-Key": JENGA_API_KEY,
            "Content-Type": "application/json",
        })

        if resp.status_code != 200:
            logger.error(f"JengaHQ auth failed: {resp.status_code} {resp.text}")
            raise Exception("JengaHQ authentication failed")

        data = resp.json()
        token = data.get("accessToken") or data.get("access_token")
        expires_in = data.get("expiresIn", data.get("expires_in", 3600))

        _token_cache["token"] = token
        _token_cache["expires_at"] = now + timedelta(seconds=int(expires_in) - 60)

        logger.info("JengaHQ OAuth2 token acquired")
        return token


def generate_signature(payload_string: str) -> str:
    """Generate HMAC-SHA256 signature for JengaHQ requests."""
    if is_demo_mode():
        return "demo_signature"
    return hmac.new(
        JENGA_CONSUMER_SECRET.encode(),
        payload_string.encode(),
        hashlib.sha256
    ).hexdigest()


async def create_payment_link(
    amount: float,
    reference: str,
    description: str,
    customer_email: str,
    customer_name: str,
    callback_url: str,
    redirect_url: str,
) -> dict:
    """Create a JengaHQ payment link for checkout."""
    if is_demo_mode():
        demo_ref = f"DEMO-{reference}"
        return {
            "demo": True,
            "checkout_url": f"{FRONTEND_URL}/dashboard?plan_pending=true&ref={demo_ref}",
            "reference": demo_ref,
            "message": "Demo mode — JengaHQ keys not configured",
        }

    token = await get_auth_token()
    url = f"{JENGA_BASE_URL}/api-checkout/api/v1/create/payment-link"

    payload = {
        "customer": {
            "firstName": customer_name.split()[0] if customer_name else "Customer",
            "lastName": customer_name.split()[-1] if customer_name and len(customer_name.split()) > 1 else "",
            "email": customer_email,
            "countryCode": "SS",
        },
        "transaction": {
            "amount": str(amount),
            "currency": JENGA_CURRENCY,
            "description": description,
            "reference": reference,
            "callbackUrl": callback_url,
            "redirectUrl": redirect_url,
        },
        "amountOption": "RESTRICTED",
        "externalRef": reference,
        "notifications": {
            "email": True,
        },
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

        if resp.status_code not in (200, 201):
            logger.error(f"JengaHQ payment link failed: {resp.status_code} {resp.text}")
            raise Exception(f"JengaHQ payment link creation failed: {resp.text}")

        data = resp.json()
        checkout_url = data.get("paymentLink") or data.get("checkoutUrl") or data.get("link", "")

        return {
            "demo": False,
            "checkout_url": checkout_url,
            "reference": reference,
            "raw_response": data,
        }


async def process_card_payment(
    amount: float,
    reference: str,
    card_token: str,
    customer_email: str,
) -> dict:
    """Process a recurring payment using a stored card token."""
    if is_demo_mode():
        return {
            "demo": True,
            "success": True,
            "transaction_id": f"DEMO-TXN-{uuid.uuid4().hex[:8].upper()}",
            "reference": reference,
        }

    token = await get_auth_token()
    url = f"{JENGA_BASE_URL}/v3-apis/transaction-api/v3.0/payments"

    sig_string = f"{JENGA_MERCHANT_CODE}{amount}{JENGA_CURRENCY}{reference}"
    signature = generate_signature(sig_string)

    payload = {
        "source": {"merchantCode": JENGA_MERCHANT_CODE},
        "transaction": {
            "amount": str(amount),
            "currency": JENGA_CURRENCY,
            "reference": reference,
            "description": "CursorCode AI subscription renewal",
        },
        "cardToken": card_token,
        "customer": {"email": customer_email},
        "signature": signature,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

        if resp.status_code not in (200, 201):
            logger.error(f"JengaHQ card payment failed: {resp.status_code} {resp.text}")
            return {"success": False, "error": resp.text}

        data = resp.json()
        return {
            "demo": False,
            "success": True,
            "transaction_id": data.get("transactionId", ""),
            "reference": reference,
            "raw_response": data,
        }


def verify_ipn_signature(payload: dict, signature: str) -> bool:
    """Verify JengaHQ IPN webhook signature."""
    if is_demo_mode():
        return True

    if not JENGA_WEBHOOK_SECRET:
        logger.warning("JENGA_WEBHOOK_SECRET not set, skipping IPN verification")
        return True

    try:
        # JengaHQ IPN signature: HMAC-SHA256 of the raw body
        import json
        raw = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        expected = hmac.new(
            JENGA_WEBHOOK_SECRET.encode(),
            raw.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception as e:
        logger.error(f"IPN signature verification error: {e}")
        return False
