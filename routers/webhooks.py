"""
PoolFi Webhooks Ingress Router
Receives, logs, validates, and reconciles incoming real-time payment 
notifications emitted by the Nomba banking gateway.
"""

import os
import hmac
import hashlib
import base64
import logging
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models import WebhookEvent, GroupMember, Group, Contribution

logger = logging.getLogger("poolfi_core")

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks Processing"]
)


def verify_nomba_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """
    Executes a crypto-secure constant-time comparison check against the 
    inbound payload using HMAC-SHA256 with the designated webhook secret.
    """
    secret = os.getenv("NOMBA_WEBHOOK_SECRET")
    if not secret:
        logger.error("System Configuration Fault: NOMBA_WEBHOOK_SECRET environment variable is missing.")
        return False

    computed_hmac = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).digest()
    
    expected_signature = base64.b64encode(computed_hmac).decode("utf-8")
    return hmac.compare_digest(expected_signature, signature_header)


def process_reconciliation_pipeline(payload: dict, payload_bytes: bytes, signature: str):
    """
    Asynchronous transaction processing queue executed out-of-band 
    from the initial HTTP protocol cycle.
    """
    if not signature or not verify_nomba_signature(payload_bytes, signature):
        logger.warning("Security Warning: Ingress webhook dropped due to signature authentication failure.")
        return

    db: Session = next(get_db())

    try:
        event_type = payload.get("eventType", "payment_success")
        request_id = payload.get("requestId")
        
        transaction_block = payload.get("transaction", {})
        transaction_id = transaction_block.get("transactionId")
        alias_account = transaction_block.get("aliasAccountNumber")
        amount_paid = float(transaction_block.get("transactionAmount", 0.0))

        if not transaction_id or not alias_account:
            logger.warning("Malformed Webhook Data: Dropped packet due to missing critical identification tags.")
            return

        webhook_log = WebhookEvent(
            event_type=event_type,
            nomba_request_id=request_id if request_id else transaction_id,
            transaction_id=transaction_id,
            raw_payload=payload,
            processed=False
        )
        db.add(webhook_log)
        db.commit()

        existing_contribution = db.query(Contribution).filter(
            Contribution.transaction_id == transaction_id
        ).first()
        
        if existing_contribution:
            logger.info(f"Idempotency Triggered: Transaction {transaction_id} already accounted for.")
            webhook_log.processed = True
            db.commit()
            return

        member = db.query(GroupMember).filter(
            GroupMember.virtual_account_number == alias_account
        ).first()

        if not member:
            logger.error(f"Misdirected Payment Exception: Account {alias_account} has no registered mapping.")
            return

        group = db.query(Group).filter(Group.id == member.group_id).first()
        if not group:
            logger.error(f"Data Integrity Fault: Member references an orphan group layout sequence {member.group_id}.")
            return

        contribution = db.query(Contribution).filter(
            Contribution.group_id == group.id,
            Contribution.member_id == member.user_id,
            Contribution.cycle_number == group.current_cycle
        ).first()

        if not contribution:
            contribution = Contribution(
                group_id=group.id,
                member_id=member.user_id,
                cycle_number=group.current_cycle,
                expected_amount=group.contribution_amount,
                paid_amount=0.0,
                status="unpaid"
            )
            db.add(contribution)

        contribution.paid_amount = float(contribution.paid_amount or 0.0) + amount_paid
        contribution.transaction_id = transaction_id
        contribution.paid_at = db.text('NOW()')

        expected = float(contribution.expected_amount)
        current_balance = float(contribution.paid_amount)

        if current_balance == expected:
            contribution.status = "paid"
        elif current_balance < expected:
            contribution.status = "underpaid"
        else:
            contribution.status = "overpaid"

        webhook_log.processed = True
        db.commit()
        logger.info(f"Reconciliation Success: Account {alias_account} processed. Status set to {contribution.status.upper()}.")

    except Exception as e:
        db.rollback()
        logger.error(f"Critical Ingress Processing Crash within background execution pool: {str(e)}")
    finally:
        db.close()


@router.post(
    "/payment",
    status_code=status.HTTP_200_OK,
    summary="Ingress interface endpoint for core payment gateway notifications"
)
async def handle_payment_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_nomba_signature: str = Header(None, alias="x-nomba-signature")
):
    """
    Main webhook handler gateway interface.
    """
    payload_bytes = await request.body()
    try:
        payload_json = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload structure is non-compliant with valid JSON formatting rules."
        )

    background_tasks.add_task(
        process_reconciliation_pipeline,
        payload=payload_json,
        payload_bytes=payload_bytes,
        signature=x_nomba_signature
    )

    return {"status": "received"}

