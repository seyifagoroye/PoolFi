from fastapi import FastAPI, HTTPException
from nomba_client import nomba_service

app = FastAPI(title="PoolFi API")

@app.get("/")
def read_root():
    return {"message": "PoolFi API is live, running async, and fully secure"}

@app.post("/api/v1/pools")
async def create_savings_pool(account_name: str, email: str, bvn: str, pool_id: str):
    """Production endpoint to dynamically provision sub-pool accounts."""
    try:
        # account_ref must be unique per pool created
        account_ref = f"poolfi_{pool_id}"
        
        account_data = await nomba_service.create_virtual_account(
            account_name=account_name,
            email=email,
            bvn=bvn,
            account_ref=account_ref
        )
        return account_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))