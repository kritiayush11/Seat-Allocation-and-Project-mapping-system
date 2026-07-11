"""
Auth router — sign up, login, and profile endpoints.
Single Responsibility: handles HTTP request/response parsing for authentication.
Rate limits applied here (Open/Closed — add new routes without touching limiter config):
  POST /auth/login  → 5/minute  (brute-force protection)
  POST /auth/signup → 5/minute  (account spam protection)
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..limiter import limiter
from ..models.user import User
from ..schemas.user import UserCreate, UserLogin, UserResponse, Token
from ..dependencies import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sign up a new admin account",
)
@limiter.limit("5/minute")
def signup(request: Request, data: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new administrator account.
    - **username** must be unique.
    - **email** must be unique.
    """
    # Check duplicate username
    existing_username = db.query(User).filter(User.username == data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered",
        )

    # Check duplicate email
    existing_email = db.query(User).filter(User.email == data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address is already registered",
        )

    # Hash the password
    hashed_pw = get_password_hash(data.password)

    # Create new user
    new_user = User(
        username=data.username,
        email=data.email,
        hashed_password=hashed_pw,
        is_admin=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=Token,
    summary="Log in and retrieve JWT access token",
)
@limiter.limit("5/minute")
def login(request: Request, data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate administrative credentials.
    - Returns a bearer JWT access token.
    """
    # Query user by username or email
    user = (
        db.query(User)
        .filter((User.username == data.username_or_email) | (User.email == data.username_or_email))
        .first()
    )

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get details of the currently logged in administrator",
)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the active user session metadata."""
    return current_user
