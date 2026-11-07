from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, func, text
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Apartment(Base):
    __tablename__ = "apartment"
    __table_args__ = (
        CheckConstraint("max_guests > 0", name="ck_apartment_max_guests_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    address: Mapped[str]
    floor: Mapped[str | None]
    max_guests: Mapped[int]
    deactivated_at: Mapped[date | None]


class Booking(Base):
    __tablename__ = "booking"
    __table_args__ = (
        CheckConstraint("guest_count >= 1", name="ck_booking_guest_count_min"),
        CheckConstraint("check_out > check_in", name="ck_booking_dates_order"),
        CheckConstraint("price >= 0", name="ck_booking_price_non_negative"),
        CheckConstraint(
            "payment_method IN ('cash', 'transfer')",
            name="ck_booking_payment_method",
        ),
        CheckConstraint(
            "linen_change_date > check_in AND linen_change_date < check_out",
            name="ck_booking_linen_change_in_stay",
        ),
        # Two active bookings of the same apartment cannot share a night.
        # '[)' = half-open interval: check-out day is free for the next guest.
        ExcludeConstraint(
            ("apartment_id", "="),
            (func.daterange(text("check_in"), text("check_out"), text("'[)'")), "&&"),
            name="ex_booking_no_overlap",
            using="gist",
            where=text("cancelled_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    apartment_id: Mapped[int] = mapped_column(ForeignKey("apartment.id"))
    guest_name: Mapped[str]
    guest_phone: Mapped[str | None]
    guest_count: Mapped[int]
    check_in: Mapped[date]
    check_out: Mapped[date]
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    payment_method: Mapped[str | None]
    linen_change_date: Mapped[date | None]
    cancelled_at: Mapped[date | None]
    notes: Mapped[str | None]


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
