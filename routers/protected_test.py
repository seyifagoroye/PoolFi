from fastapi import APIRouter, Depends
from auth import get_current_user
from models import User

router = APIRouter(prefix="/api/secure", tags=["Security Verification"])

@router.get("/dashboard")
def view_dashboard(current_user: User = Depends(get_current_user)):
    """
    A strictly non-public route. 
    FastAPI will reject anyone who doesn't pass a valid JWT token.
    """
    return {
        "message": f"Welcome to the secure dashboard, {current_user.name}!",
        "secret_data": "This data is only visible to logged-in users."
    }