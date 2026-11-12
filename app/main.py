from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.apartments import router as apartments_router
from app.bookings import router as bookings_router
from app.db import get_session

app = FastAPI(title="Rental Bookings")
app.include_router(apartments_router)
app.include_router(bookings_router)


@app.get("/health")
def health(session: Session = Depends(get_session)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
