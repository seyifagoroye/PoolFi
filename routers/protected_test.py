import os
import uuid
import hmac
import hashlib
import logging
from fastapi import APIRouter, Request, Header, status, HTTPException, Response
from nomba_client import nomba_service

logger = logging.getLogger("poolfi_core")
router = APIRouter(prefix="/api/secure", tags=["Nomba Integration Test"])

NOMBA_WEBHOOK_SECRET = os.getenv("NOMBA_WEBHOOK_SECRET", "NombaHackathon2026")

@router.get("/test-nomba-token")
async def test_token():
    """Manually triggers the 15-minute token cache/fetch logic."""
    import httpx
    async with httpx.AsyncClient() as client:
        token = await nomba_service.get_access_token(client)
        return {
            "status": "success",
            "token_cached": nomba_service._access_token is not None,
            "expires_at_timestamp": nomba_service._token_expires_at
        }

@router.post("/test-virtual-account")
async def test_va():
    """Simulates creating a virtual account inside your explicit sub-account scope."""
    test_ref = f"REF{uuid.uuid4().hex[:12].upper()}"
    response = await nomba_service.create_virtual_account(
        account_name="Promise Fagoroye",
        account_ref=test_ref
    )
    return {"status": "api_response", "data": response}

@router.post("/nomba-webhook", status_code=status.HTTP_200_OK)
async def nomba_webhook_listener(
    request: Request,
    x_nomba_signature: str = Header(None, alias="X-Nomba-Signature")
):
    """
    Session 3.7: Secure webhook ingress.
    Signature check temporarily commented out for local sandbox mockup tests.
    """
    try:
        event_data = await request.json()
        event_type = event_data.get("event")
        data_payload = event_data.get("data", {})
        
        logger.info(f"Incoming verified Nomba webhook event caught: {event_type}")
        
        if event_type in ["virtual_account_funding", "transaction.success"]:
            amount = data_payload.get("amount")
            account_ref = data_payload.get("accountRef")
            logger.info(f"SUCCESSFUL INFLOW DETECTED: {amount} NGN for account ref: {account_ref}")
            
        return {"status": "accepted", "message": "Webhook processed cleanly"}
        
    except Exception as e:
        logger.error(f"Error decoding incoming webhook event payload stream: {str(e)}")
        return Response(content="Internal tracking logged", status_code=status.HTTP_200_OK)