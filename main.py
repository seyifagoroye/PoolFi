"""
PoolFi - Automated Digital Infrastructure for Rotating Savings Groups (Ajo/Esusu)
Main Application Core
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize central core logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("poolfi_core")

app = FastAPI(
    title="PoolFi API",
    description="Automated digital infrastructure for rotating savings groups (Ajo/Esusu) in Nigeria.",
    version="1.0.0",
    openapi_url="/openapi.json"
)

# Cross-Origin Resource Sharing (CORS) Configuration for Frontend Handshakes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust to specific domains for production deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root & System Health Check Endpoints
@app.get("/", tags=["System Health"])
async def read_root():
    return {"message": "Welcome to PoolFi API Infrastructure"}

@app.get("/health", tags=["System Health"])
async def health_check():
    return {"status": "healthy"}

# ---------------------------------------------------------------------
# ROUTERS ROUTING MATRIX
# ---------------------------------------------------------------------

# Phase 2 & 3: Authentication Infrastructure
from routers import auth
app.include_router(auth.router)

# Phase 4: Savings Groups Management Engine
from routers import groups
app.include_router(groups.router)

# Phase 4: Members Management Router
from routers import members
app.include_router(members.router)

# Phase 5: Webhooks Ingress & Reconciliation Engine
from routers import webhooks
app.include_router(webhooks.router)

logger.info("PoolFi core routing layers successfully initialized.")