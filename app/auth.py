import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import AppUser

router = APIRouter(prefix="/api", tags=["auth"])

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
    """Dependency for protected API routes: the logged-in user's id, or 401."""
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    return user_id


def require_user_page(request: Request) -> int:
    """Same as require_user, but for pages: send the browser to the login form."""
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user_id


def authenticate(session: Session, username: str, password: str) -> AppUser | None:
    """The user if username and password match, otherwise None (never says which failed)."""
    user = session.scalar(select(AppUser).where(AppUser.username == username))
    password_hash = user.password_hash if user else _DUMMY_HASH
    if not verify_password(password, password_hash) or user is None:
        return None
    return user


def start_session(request: Request, user: AppUser) -> None:
    request.session.clear()  # drop anything from before the login
    request.session["user_id"] = user.id


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(data: LoginRequest, request: Request, session: Session = Depends(get_session)) -> Response:
    user = authenticate(session, data.username, data.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")
    start_session(request, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
