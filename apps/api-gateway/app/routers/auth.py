from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from datetime import timedelta

from app.database import get_db
from app.models.user import User
from app.models.subscription import Subscription, PlanType
from app.core.security import (
    verify_password, hash_password,
    create_access_token, create_refresh_token,
    get_current_active_user, settings
)

router = APIRouter()


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization: str = ""


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    organization: str
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        organization=user_in.organization,
    )
    db.add(user)
    await db.flush()

    # Create free tier subscription
    subscription = Subscription(user_id=user.id, plan=PlanType.FREE)
    db.add(subscription)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.delete("/token")
async def logout():
    # Stateless JWT — client discards the token
    return {"message": "Successfully logged out"}
