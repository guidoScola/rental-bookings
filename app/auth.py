import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import AppUser

router = APIRouter(tags=["auth"])

# Used when the username does not exist, so a wrong username takes as long as a
# wrong password. Otherwise response time would reveal which usernames exist.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:  # bcrypt rejects passwords longer than 72 bytes
        return False


class LoginRequest(BaseModel):
    username: str
    password: str


def require_user(request: Request) -> int:
    """Dependency for protected routes: the logged-in user's id, or 401."""
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    return user_id


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(data: LoginRequest, request: Request, session: Session = Depends(get_session)) -> Response:
    user = session.scalar(select(AppUser).where(AppUser.username == data.username))
    password_hash = user.password_hash if user else _DUMMY_HASH
    if not verify_password(data.password, password_hash) or user is None:
        # Same message for both cases: do not tell which one was wrong.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    request.session.clear()
    request.session["user_id"] = user.id
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
