from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Apartment, Booking
from app.schemas import ApartmentCreate, ApartmentRead

router = APIRouter(prefix="/api/apartments", tags=["apartments"])


def get_apartment_or_404(session: Session, apartment_id: int) -> Apartment:
    apartment = session.get(Apartment, apartment_id)
    if apartment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Apartment not found")
    return apartment


@router.post("", response_model=ApartmentRead, status_code=status.HTTP_201_CREATED)
def create_apartment(data: ApartmentCreate, session: Session = Depends(get_session)) -> Apartment:
    apartment = Apartment(**data.model_dump())
    session.add(apartment)
    session.commit()
    return apartment


@router.get("", response_model=list[ApartmentRead])
def list_apartments(
    include_deactivated: bool = False, session: Session = Depends(get_session)
) -> list[Apartment]:
    query = select(Apartment).order_by(Apartment.name)
    if not include_deactivated:
        query = query.where(Apartment.deactivated_at.is_(None))
    return list(session.scalars(query))


@router.get("/{apartment_id}", response_model=ApartmentRead)
def get_apartment(apartment_id: int, session: Session = Depends(get_session)) -> Apartment:
    return get_apartment_or_404(session, apartment_id)


@router.post("/{apartment_id}/deactivate", response_model=ApartmentRead)
def deactivate_apartment(
    apartment_id: int, confirm: bool = False, session: Session = Depends(get_session)
) -> Apartment:
    """Deactivate an apartment. Its bookings are kept.

    If it has future active bookings, the first call answers 409 with their ids
    so the owner can decide. Calling again with ?confirm=true cancels them.
    """
    apartment = get_apartment_or_404(session, apartment_id)
    if apartment.deactivated_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Apartment is already deactivated")

    today = date.today()
    future = list(
        session.scalars(
            select(Booking).where(
                Booking.apartment_id == apartment_id,
                Booking.cancelled_at.is_(None),
                Booking.check_in > today,
            )
        )
    )
    if future and not confirm:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "message": "Apartment has future bookings; repeat with confirm=true to cancel them",
                "booking_ids": [b.id for b in future],
            },
        )

    # Both changes go in the same commit (one transaction): either the apartment
    # is deactivated AND its bookings cancelled, or nothing changes.
    for booking in future:
        booking.cancelled_at = today
    apartment.deactivated_at = today
    session.commit()
    return apartment
