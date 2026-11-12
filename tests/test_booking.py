from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Booking


def test_overlapping_booking_is_rejected(session, apartment):
    # Arrange: first booking, 15/11 to 19/11
    first = Booking(
        apartment_id=apartment.id,
        guest_name="Ana",
        guest_count=2,
        check_in=date(2026, 11, 15),
        check_out=date(2026, 11, 19),
        price=100,
    )
    session.add(first)
    session.flush()
    second = Booking( 
        apartment_id=apartment.id,
        guest_name="Juan",
        guest_count=3,
        check_in=date(2026, 11, 18),
        check_out=date(2026, 11, 22),
        price=150,
    )
    with pytest.raises(IntegrityError,  match="ex_booking_no_overlap"):
        session.add(second)
        session.flush()
    

def make_booking(apartment, check_in, check_out, **extra):
    """Build a valid booking; tests only override what they care about."""
    return Booking(
        apartment_id=apartment.id,
        guest_name="Guest",
        guest_count=2,
        check_in=check_in,
        check_out=check_out,
        price=100,
        **extra,
    )


def test_checkout_day_is_free_for_next_booking(session, apartment):
    session.add(make_booking(apartment, date(2026, 11, 15), date(2026, 11, 19)))
    session.flush()

    second = make_booking(apartment, date(2026, 11, 19), date(2026, 11, 22))
    session.add(second)
    session.flush()

    assert second.id is not None


def test_cancelled_booking_does_not_block_dates(session, apartment):
    session.add(
        make_booking(
            apartment,
            date(2026, 11, 15),
            date(2026, 11, 19),
            cancelled_at=date(2026, 11, 10),
        )
    )
    session.flush()

    second = make_booking(apartment, date(2026, 11, 16), date(2026, 11, 18))
    session.add(second)
    session.flush()

    assert second.id is not None


def test_reactivating_cancelled_booking_that_overlaps_is_rejected(session, apartment):
    cancelled = make_booking(
        apartment,
        date(2026, 11, 15),
        date(2026, 11, 19),
        cancelled_at=date(2026, 11, 10),
    )
    session.add(cancelled)
    session.add(make_booking(apartment, date(2026, 11, 16), date(2026, 11, 18)))
    session.flush()

    cancelled.cancelled_at = None
    with pytest.raises(IntegrityError, match="ex_booking_no_overlap"):
        session.flush()


def test_linen_change_inside_stay_is_accepted(session, apartment):
    booking = make_booking(
        apartment,
        date(2026, 11, 15),
        date(2026, 11, 22),
        linen_change_date=date(2026, 11, 18),
    )
    session.add(booking)
    session.flush()

    assert booking.id is not None


@pytest.mark.parametrize("linen_day", [date(2026, 11, 15), date(2026, 11, 22)])
def test_linen_change_on_check_in_or_check_out_is_rejected(session, apartment, linen_day):
    session.add(
        make_booking(
            apartment,
            date(2026, 11, 15),
            date(2026, 11, 22),
            linen_change_date=linen_day,
        )
    )
    with pytest.raises(IntegrityError, match="ck_booking_linen_change_in_stay"):
        session.flush()
