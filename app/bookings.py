from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Apartment, Booking
from app.schemas import BookingCreate, BookingRead, BookingUpdate

router = APIRouter(prefix="/bookings", tags=["bookings"])


def validate_booking(session: Session, booking: Booking) -> None:
    """Business rules checked in the app.

    The database also enforces the single-row rules (dates order, linen day),
    but checking them here gives a clear 422 message. The rules that need the
    apartment row can only be checked here: a CHECK sees one row only.
    """
    # no_autoflush: a query here must not send pending changes to the database
    # yet; that happens in commit_or_conflict, which turns errors into 409/422.
    with session.no_autoflush:
        apartment = session.get(Apartment, booking.apartment_id)
    if apartment is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Apartment not found")
    if apartment.deactivated_at is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Apartment is deactivated")
    if booking.check_out <= booking.check_in:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "check_out must be after check_in")
    if booking.guest_count > apartment.max_guests:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Apartment allows at most {apartment.max_guests} guests",
        )
    linen = booking.linen_change_date
    if linen is not None and not (booking.check_in < linen < booking.check_out):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "linen_change_date must be strictly between check_in and check_out",
        )


def commit_or_conflict(session: Session) -> None:
    """Commit, turning the overlap constraint into a 409.

    The overlap check lives only in the database (EXCLUDE constraint): checking
    it in Python first would race with a concurrent request.
    """
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if constraint == "ex_booking_no_overlap":
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Dates overlap with another booking"
            ) from error
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Constraint violated: {constraint}"
        ) from error


def get_booking_or_404(session: Session, booking_id: int) -> Booking:
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return booking


@router.post("", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def create_booking(data: BookingCreate, session: Session = Depends(get_session)) -> Booking:
    booking = Booking(**data.model_dump())
    validate_booking(session, booking)
    session.add(booking)
    commit_or_conflict(session)
    return booking


@router.get("", response_model=list[BookingRead])
def list_bookings(
    status_filter: Literal["current", "upcoming"] | None = Query(default=None, alias="status"),
    session: Session = Depends(get_session),
) -> list[Booking]:
    """Active bookings that have not ended yet: current + upcoming by default."""
    today = date.today()
    query = select(Booking).where(Booking.cancelled_at.is_(None))
    if status_filter == "current":
        query = query.where(Booking.check_in <= today, Booking.check_out > today)
    elif status_filter == "upcoming":
        query = query.where(Booking.check_in > today)
    else:
        query = query.where(Booking.check_out > today)
    return list(session.scalars(query.order_by(Booking.check_in)))


@router.get("/{booking_id}", response_model=BookingRead)
def get_booking(booking_id: int, session: Session = Depends(get_session)) -> Booking:
    return get_booking_or_404(session, booking_id)


@router.patch("/{booking_id}", response_model=BookingRead)
def update_booking(
    booking_id: int, data: BookingUpdate, session: Session = Depends(get_session)
) -> Booking:
    booking = get_booking_or_404(session, booking_id)
    if booking.cancelled_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Booking is cancelled")
    # exclude_unset: only the fields present in the request body.
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(booking, field, value)
    try:
        validate_booking(session, booking)
    except HTTPException:
        session.rollback()  # discard the half-applied changes
        raise
    commit_or_conflict(session)
    return booking


@router.post("/{booking_id}/cancel", response_model=BookingRead)
def cancel_booking(booking_id: int, session: Session = Depends(get_session)) -> Booking:
    booking = get_booking_or_404(session, booking_id)
    if booking.cancelled_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Booking is already cancelled")
    booking.cancelled_at = date.today()
    session.commit()
    return booking
