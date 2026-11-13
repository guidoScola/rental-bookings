from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.apartments import router as apartments_router
from app.auth import require_user
from app.auth import router as auth_router
from app.bookings import router as bookings_router
from app.config import settings
from app.db import get_session
from app.web import public as web_public_router
from app.web import router as web_router

app = FastAPI(title="Rental Bookings")
# same_site="lax": the browser does not send the cookie on POSTs coming from
# other sites, which blocks CSRF on the forms.
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, same_site="lax")

# JSON API under /api. Everything except login/logout requires a logged-in user.
app.include_router(auth_router)
protected = [Depends(require_user)]
app.include_router(apartments_router, dependencies=protected)
app.include_router(bookings_router, dependencies=protected)

# HTML pages. web_router redirects to /login when there is no session.
app.include_router(web_public_router)
app.include_router(web_router)


@app.get("/health")
def health(session: Session = Depends(get_session)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
