import os
import time
import httpx
from dotenv import load_dotenv

load_dotenv()

class NombaClient:
    def __init__(self):
        self.client_id = os.getenv("NOMBA_CLIENT_ID")
        self.private_key = os.getenv("NOMBA_PRIVATE_KEY")
        self.account_id = os.getenv("NOMBA_ACCOUNT_ID")
        self.sub_account_id = os.getenv("NOMBA_SUB_ACCOUNT_ID")
        self.base_url = "https://sandbox.nomba.com/v1"
        
        self._access_token = None
        self._token_expires_at = 0  # Unix timestamp

    async def get_access_token(self, client: httpx.AsyncClient) -> str:
        """Fetches a token or returns the cached one if it's still valid (checking 15 min buffer)."""
        current_time = time.time()
        
        if self._access_token and (self._token_expires_at - current_time > 900):
            return self._access_token

        url = f"{self.base_url}/auth/token/issue"
        headers = {
            "Content-Type": "application/json",
            "accountId": self.account_id
        }
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.private_key
        }

        response = await client.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Nomba Auth Failed: {response.json().get('description', 'Unknown Error')}")
            
        data = response.json().get("data", {})
        self._access_token = data.get("access_token")
        
        # Note: Flagged for Day 6 Security Audit to parse the explicit API response string/timestamp correctly
        expires_in = data.get("expires_in", 10800)
        self._token_expires_at = current_time + expires_in
        
        return self._access_token

    async def create_virtual_account(self, account_name: str, email: str, bvn: str, account_ref: str) -> dict:
        """Asynchronously provisions a unique virtual bank account via Nomba."""
        async with httpx.AsyncClient() as client:
            token = await self.get_access_token(client)
            url = f"{self.base_url}/accounts/virtual"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "accountId": self.account_id
            }
            
            payload = {
                "accountRef": account_ref,
                "accountName": account_name,
                "email": email,
                "currency": "NGN",
                "bvn": bvn,
                "secretKey": self.private_key,
                "subAccountId": self.sub_account_id
            }
            
            response = await client.post(url, json=payload, headers=headers)
            return response.json()

nomba_service = NombaClient()