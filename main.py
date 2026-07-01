from fastapi import FastAPI

app = FastAPI(title="PoolFi API")

@app.get("/")
def read_root():
    return {"message": "PoolFi API is live and running"}

@app.post("/webhooks/nomba")
def nomba_webhook(data: dict):
    print("Received Webhook Data:", data)
    return {"status": "success"}