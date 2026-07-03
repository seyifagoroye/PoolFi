"""
PoolFi - Automated Digital Infrastructure for Rotating Savings Groups (Ajo/Esusu)
Main Application Core
"""

import logging
import time
from collections import defaultdict
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("poolfi_core")

app = FastAPI(
    title="PoolFi API",
    description="Automated digital infrastructure for rotating savings groups (Ajo/Esusu) in Nigeria.",
    version="1.0.0",
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
# PHASE 10: IN-MEMORY RATE LIMITING MIDDLEWARE
# ---------------------------------------------------------------------
rate_limit_records = defaultdict(list)
RATE_LIMIT_WINDOW = 10.0
MAX_REQUESTS = 5

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    path = request.url.path

    if path.startswith("/api/auth") or path.startswith("/webhooks"):
        current_time = time.time()
        rate_limit_records[client_ip] = [
            t for t in rate_limit_records[client_ip]
            if current_time - t < RATE_LIMIT_WINDOW
        ]

        if len(rate_limit_records[client_ip]) >= MAX_REQUESTS:
            logger.warning(f"SECURITY ALERT: Rate limit breached by {client_ip} on {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Anti-brute force mechanisms triggered."}
            )
        rate_limit_records[client_ip].append(current_time)

    return await call_next(request)

@app.get("/", tags=["System Health"])
async def read_root():
    return {"message": "Welcome to PoolFi API Infrastructure"}

@app.get("/health", tags=["System Health"])
async def health_check():
    return {"status": "healthy"}

# ---------------------------------------------------------------------
# ROUTERS ROUTING MATRIX
# ---------------------------------------------------------------------
from routers import auth
app.include_router(auth.router)

from routers import groups
app.include_router(groups.router)

from routers import members
app.include_router(members.router)

from routers import webhooks
app.include_router(webhooks.router)

logger.info("PoolFi core routing layers successfully initialized.")

from routers import transfers
app.include_router(transfers.router)

from routers import transactions
app.include_router(transactions.router)

logger.info("PoolFi transaction reporting layers successfully mounted.")
