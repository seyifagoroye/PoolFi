import os
import requests
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

load_dotenv()

NOMBA_CLIENT_ID = os.getenv("NOMBA_CLIENT_ID")
NOMBA_PRIVATE_KEY = os.getenv("NOMBA_PRIVATE_KEY")
NOMBA_ACCOUNT_ID = os.getenv("NOMBA_ACCOUNT_ID")

app = FastAPI(title="PoolFi API")

def get_nomba_access_token() -> str:
    """Fetches an OAuth2 access token from Nomba using sandbox credentials."""
    url = "https://sandbox.nomba.com/v1/auth/token/issue"
    
    headers = {
        "Content-Type": "application/json",
        "accountId": NOMBA_ACCOUNT_ID
    }
    
    payload = {
        "grant_type": "client_credentials",
        "client_id": NOMBA_CLIENT_ID,
        "client_secret": NOMBA_PRIVATE_KEY
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        
        if response.status_code != 200:
            error_msg = response_data.get('description', 'Unknown Authorization Error')
            raise HTTPException(status_code=response.status_code, detail=f"Nomba Auth: {error_msg}")
            
        return response_data.get("data", {}).get("access_token")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "PoolFi API is live and running"}

@app.get("/test-token")
def test_token():
    token = get_nomba_access_token()
    if token:
        return {"status": "Connected to Nomba", "token_preview": f"{token[:15]}..."}
    return {"status": "Failed to retrieve token"}