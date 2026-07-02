import os
import time
import logging
import httpx
from fastapi import HTTPException, status
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("poolfi_core")

class NombaClient:
    def __init__(self):
        self.client_id = os.getenv("NOMBA_CLIENT_ID")
        self.private_key = os.getenv("NOMBA_PRIVATE_KEY")
        self.parent_account_id = os.getenv("NOMBA_PARENT_ACCOUNT_ID")
        self.sub_account_id = os.getenv("NOMBA_SUB_ACCOUNT_ID")
        self.base_url = "https://sandbox.nomba.com/v1"
        
        self._access_token = None
        self._token_expires_at = 0  # Unix timestamp

    async def get_access_token(self, client: httpx.AsyncClient) -> str:
        """
        Session 3.1 & 3.2: Handles authentication and token lifetime tracking.
        """
        current_time = time.time()
        
        if self._access_token and (self._token_expires_at - current_time > 900):
            return self._access_token

        logger.info("Nomba access token missing or within 15-minute buffer window. Re-authenticating...")
        
        url = f"{self.base_url}/auth/token/issue"
        headers = {
            "Content-Type": "application/json",
            "accountId": self.parent_account_id
        }
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.private_key
        }

        try:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            if response.status_code != 200:
                logger.error(f"Nomba Auth downstream failure: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY, 
                    detail="Failed to authenticate with downstream payment provider."
                )
                
            data = response.json().get("data", {})
            self._access_token = data.get("access_token")
            expires_in = data.get("expires_in", 10800)
            self._token_expires_at = current_time + expires_in
            
            logger.info("Successfully fetched fresh Nomba Access Token.")
            return self._access_token

        except httpx.HTTPError as e:
            logger.error(f"Network subsystem error during Nomba handshake: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Nomba payment server is currently unreachable."
            )

    async def create_virtual_account(self, account_name: str, account_ref: str) -> dict:
        """
        Session 3.3: Provisions virtual bank accounts isolated via URL path parameters
        directly to your sub-account workspace balance.
        """
        # CRITICAL REFACTOR: Points directly to Nomba's sub-account path structure
        url = f"{self.base_url}/accounts/virtual/{self.sub_account_id}"
        
        async with httpx.AsyncClient() as client:
            token = await self.get_access_token(client)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "accountId": self.parent_account_id  # Parent required here for organizational validation
            }
            
            payload = {
                "accountRef": account_ref,
                "accountName": account_name,
                "currency": "NGN"
            }
            
            try:
                logger.info(f"Initiating sub-account virtual registration for ref: {account_ref}")
                response = await client.post(url, json=payload, headers=headers, timeout=15.0)
                
                if response.status_code not in [200, 201]:
                    logger.error(f"Nomba Virtual Account generation error: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Downstream account provisioning rejected by payment gateway."
                    )
                
                return response.json()
                
            except httpx.HTTPError as e:
                logger.error(f"Network error during Nomba account provisioning: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Payment infrastructure timed out while generating virtual account details."
                )

    async def initiate_payout(
        self, 
        amount: float, 
        account_number: str, 
        account_name: str, 
        bank_code: str, 
        merchant_tx_ref: str,
        narration: str = "PoolFi Ajo Payout Cycle"
    ) -> dict:
        """
        Session 3.4: Executes outbound transfers from your sub-account balance pocket.
        """
        url = "https://sandbox.nomba.com/v2/transfers/bank"
        
        async with httpx.AsyncClient() as client:
            token = await self.get_access_token(client)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "accountId": self.parent_account_id,
                "X-Idempotent-Key": merchant_tx_ref
            }
            
            payload = {
                "amount": amount,
                "accountNumber": account_number,
                "accountName": account_name,
                "bankCode": bank_code,
                "merchantTxRef": merchant_tx_ref,
                "senderName": "PoolFi Automated",
                "narration": narration
            }
            
            try:
                logger.info(f"Initiating outbound payout transfer for ref: {merchant_tx_ref}")
                response = await client.post(url, json=payload, headers=headers, timeout=20.0)
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Nomba Payout transport error: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Payout settlement communication timed out."
                )

    async def fetch_transactions(self, page: int = 0, size: int = 20) -> dict:
        """
        Session 3.5: Retrieves financial histories targeted explicitly to your sub-account container.
        """
        url = f"{self.base_url}/transactions/accounts/{self.sub_account_id}"
        params = {"page": page, "size": size}
        
        async with httpx.AsyncClient() as client:
            token = await self.get_access_token(client)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "accountId": self.parent_account_id
            }
            
            try:
                logger.info(f"Fetching transaction logs for sub-account: {self.sub_account_id}")
                response = await client.get(url, headers=headers, params=params, timeout=15.0)
                
                if response.status_code != 200:
                    logger.error(f"Nomba Transactions retrieval failure: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Could not retrieve historical statements from payment gateway."
                    )
                return response.json()
                
            except httpx.HTTPError as e:
                logger.error(f"Network exception tracking Nomba statement ledger: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Downstream ledger service currently unavailable."
                )

nomba_service = NombaClient()