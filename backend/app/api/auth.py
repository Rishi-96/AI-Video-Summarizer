from fastapi import APIRouter, HTTPException, Depends, status
from datetime import timedelta
from ..models.user import UserCreate, UserLogin, UserResponse, Token
from ..core.security import verify_password, get_password_hash, create_access_token, get_current_user
from ..core.database import get_database
from ..core.config import settings

router = APIRouter()

async def get_user_by_email(email: str):
    """Get user by email"""
    db = await get_database()
    user = await db.users.find_one({"email": email})
    return user

async def get_user_by_id(user_id: str):
    """Get user by ID"""
    db = await get_database()
    user = await db.users.find_one({"_id": user_id})
    return user

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    """Register a new user"""
    try:
        db = await get_database()
        
        # Check if user exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        from datetime import datetime
        user_dict = {
            "email": user_data.email,
            "username": user_data.username,
            "full_name": user_data.full_name,
            "hashed_password": get_password_hash(user_data.password),
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.users.insert_one(user_dict)
        
        # Create JWT token
        access_token = create_access_token(
            data={"sub": str(result.inserted_id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
async def login(login_data: UserLogin):
    """Login user with JWT"""
    db = await get_database()
    
    # Find user by email
    user = await db.users.find_one({"email": login_data.email})
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create JWT token
    access_token = create_access_token(
        data={"sub": str(user["_id"])},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": str(current_user["_id"]),
        "email": current_user["email"],
        "username": current_user["username"],
        "full_name": current_user.get("full_name"),
        "is_active": current_user.get("is_active", True),
        "created_at": current_user.get("created_at")
    }