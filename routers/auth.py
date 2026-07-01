from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import UserCreate, UserResponse
from auth import hash_password, verify_password, create_access_token
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Helper request validator schema for incoming logins
class UserLogin(BaseModel):
    email: str = Field(..., description="Registered user email address")
    password: str = Field(..., description="Plaintext account password")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Registers a new participant. Passwords are securely hashed via bcrypt.
    Includes explicit unique field checks to prevent dirty database states.
    """
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user account with this email address already exists."
        )
        
    if db.query(User).filter(User.phone == user_in.phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user account with this phone number already exists."
        )

    # Securely transform plaintext password to cryptographic hash
    hashed = hash_password(user_in.password)
    
    db_user = User(
        name=user_in.name,
        email=user_in.email,
        phone=user_in.phone,
        role=user_in.role,
        bank_account_number=user_in.bank_account_number,
        bank_code=user_in.bank_code,
        password_hash=hashed
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login")
def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticates user credentials against stored bcrypt signatures and issues a signed JWT.
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or account password validation failed."
        )

    # Scoping parameters inside the secure payload token claims
    token_claims = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value
    }
    access_token = create_access_token(data=token_claims)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "role": user.role.value
        }
    }