import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routers.auth import router as auth_router
from routers.protected_test import router as test_router # 1. Import the test lock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("poolfi_core")

app = FastAPI(
    title="PoolFi API",
    description="Automated digital infrastructure for rotating savings groups (Ajo/Esusu) in Nigeria.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth_router)
app.include_router(test_router) # 2. Register the locked route handler

@app.get("/")
def read_root():
    return {"message": "PoolFi API is live and running"}

@app.get("/health", tags=["System Health"])
def health_check():
    return {"status": "healthy", "service": "poolfi_backend"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled system exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."}
    )