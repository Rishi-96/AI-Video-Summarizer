import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Cookie, HTTPException, Depends, Response, status

from ..core.config import settings
from ..core.database import get_database
from ..core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_user_from_refresh,
    get_password_hash,
    verify_password,
)
from ..models.user import Token, TokenPair, UserCreate, UserLogin, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def get_user_by_email(email: str):
    db = await get_database()
    return await db.users.find_one({"email": email})


async def get_user_by_id(user_id: str):
    db = await get_database()
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        return None
    return await db.users.find_one({"_id": obj_id})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, response: Response):
    """Register a new user and return access + refresh tokens."""
    try:
        db = await get_database()

        existing = await db.users.find_one({"email": user_data.email})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "EMAIL_TAKEN", "message": "Email already registered."},
            )

        user_dict = {
            "email": user_data.email,
            "username": user_data.username,
            "full_name": user_data.full_name,
            "hashed_password": get_password_hash(user_data.password),
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        result = await db.users.insert_one(user_dict)
        user_id = str(result.inserted_id)

        access_token  = create_access_token({"sub": user_id}, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        refresh_token = create_refresh_token({"sub": user_id})

        # Set refresh token in HttpOnly cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )

        logger.info("New user registered: %s", user_data.email)
        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Registration error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "REGISTER_FAILED", "message": "Registration failed. Please try again."},
        )


@router.post("/login", response_model=TokenPair)
async def login(login_data: UserLogin, response: Response):
    """Authenticate and return access + refresh tokens."""
    db = await get_database()
    user = await db.users.find_one({"email": login_data.email})

    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password."},
        )

    user_id = str(user["_id"])
    access_token  = create_access_token({"sub": user_id}, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_refresh_token({"sub": user_id})

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    logger.info("User logged in: %s", login_data.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    response: Response,
    refresh_token: str = Cookie(default=None),
):
    """Issue a new short-lived access token from the HttpOnly refresh cookie."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "NO_REFRESH_TOKEN", "message": "Refresh token not found. Please log in again."},
        )

    user = await get_current_user_from_refresh(refresh_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid or expired. Please log in again."},
        )

    user_id = str(user["_id"])
    access_token = create_access_token({"sub": user_id}, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    """Clear the refresh token cookie."""
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Return information about the currently authenticated user."""
    return {
        "id": str(current_user["_id"]),
        "email": current_user["email"],
        "username": current_user["username"],
        "full_name": current_user.get("full_name"),
        "is_active": current_user.get("is_active", True),
        "created_at": current_user.get("created_at"),
    }