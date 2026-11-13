from datetime import date, timedelta

import pytest

from app.models import Apartment

TODAY = date.today()


def day(offset: int) -> str:
    """A date relative to today, as the API expects it (ISO string)."""
    return (TODAY + timedelta(days=offset)).isoformat()


@pytest.fixture
def payload(apartment):
    """A valid request body: 4 nights starting in 10 days."""
    return {
        "apartment_id": apartment.id,
        "guest_name": "Ana",
        "guest_count": 2,
        "check_in": day(10),
        "check_out": day(14),
        "price": "400.00",
    }


def create(client, payload, **changes):
    return client.post("/api/bookings", json={**payload, **changes})


# --- create ---------------------------------------------------------------


def test_create_booking_returns_201_with_nights(client, payload):
    response = create(client, payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["nights"] == 4
    assert body["price"] == "400.00"
    assert body["cancelled_at"] is None


def test_overlapping_booking_returns_409(client, payload):
    create(client, payload)

    response = create(client, payload, check_in=day(12), check_out=day(16))

    assert response.status_code == 409


def test_booking_starting_on_previous_checkout_is_created(client, payload):
    create(client, payload)

    response = create(client, payload, check_in=day(14), check_out=day(16))

    assert response.status_code == 201


@pytest.mark.parametrize(
    "changes",
    [
        {"check_out": day(10)},  # same day as check_in
        {"guest_count": 5},  # apartment max is 4
        {"guest_count": 0},
        {"price": "-1"},
        {"payment_method": "card"},
        {"linen_change_date": day(10)},  # check-in day
        {"guest_name": ""},
    ],
)
def test_invalid_booking_returns_422(client, payload, changes):
    response = create(client, payload, **changes)

    assert response.status_code == 422


def test_unknown_apartment_returns_422(client, payload):
    response = create(client, payload, apartment_id=999_999)

    assert response.status_code == 422


def test_deactivated_apartment_returns_422(client, session, payload):
    closed = Apartment(name="Old", address="X", max_guests=4, deactivated_at=TODAY)
    session.add(closed)
    session.commit()

    response = create(client, payload, apartment_id=closed.id)

    assert response.status_code == 422


# --- read -----------------------------------------------------------------


def test_get_booking(client, payload):
    booking_id = create(client, payload).json()["id"]

    response = client.get(f"/api/bookings/{booking_id}")

    assert response.status_code == 200
    assert response.json()["guest_name"] == "Ana"


def test_get_missing_booking_returns_404(client):
    assert client.get("/api/bookings/999999").status_code == 404


def test_list_shows_current_and_upcoming_but_not_past_or_cancelled(client, payload):
    upcoming = create(client, payload).json()["id"]
    current = create(client, payload, check_in=day(-1), check_out=day(2)).json()["id"]
    past = create(client, payload, check_in=day(-10), check_out=day(-5)).json()["id"]
    cancelled = create(client, payload, check_in=day(20), check_out=day(22)).json()["id"]
    client.post(f"/api/bookings/{cancelled}/cancel")

    mine = {upcoming, current, past, cancelled}
    # The dev database may already hold real bookings: only look at ours.
    ids = [b["id"] for b in client.get("/api/bookings").json() if b["id"] in mine]

    assert ids == [current, upcoming]  # ordered by check_in
    assert past not in ids
    assert cancelled not in ids


def test_list_filters_by_status(client, payload):
    upcoming = create(client, payload).json()["id"]
    current = create(client, payload, check_in=day(-1), check_out=day(2)).json()["id"]

    mine = {upcoming, current}

    def ids_for(status):
        bookings = client.get(f"/api/bookings?status={status}").json()
        return [b["id"] for b in bookings if b["id"] in mine]

    current_ids = ids_for("current")
    upcoming_ids = ids_for("upcoming")

    assert current_ids == [current]
    assert upcoming_ids == [upcoming]


# --- update ---------------------------------------------------------------


def test_mark_booking_as_paid(client, payload):
    booking_id = create(client, payload).json()["id"]

    response = client.patch(f"/api/bookings/{booking_id}", json={"payment_method": "cash"})

    assert response.status_code == 200
    assert response.json()["payment_method"] == "cash"
    assert response.json()["guest_name"] == "Ana"  # untouched fields stay


def test_update_into_overlap_returns_409(client, payload):
    create(client, payload)
    other = create(client, payload, check_in=day(20), check_out=day(22)).json()["id"]

    response = client.patch(f"/api/bookings/{other}", json={"check_in": day(13)})

    assert response.status_code == 409


def test_failed_update_leaves_booking_unchanged(client, payload):
    booking_id = create(client, payload).json()["id"]

    response = client.patch(f"/api/bookings/{booking_id}", json={"guest_count": 9})

    assert response.status_code == 422
    assert client.get(f"/api/bookings/{booking_id}").json()["guest_count"] == 2


def test_update_cancelled_booking_returns_409(client, payload):
    booking_id = create(client, payload).json()["id"]
    client.post(f"/api/bookings/{booking_id}/cancel")

    response = client.patch(f"/api/bookings/{booking_id}", json={"notes": "late"})

    assert response.status_code == 409


# --- cancel ---------------------------------------------------------------


def test_cancel_booking_sets_date_and_frees_the_nights(client, payload):
    booking_id = create(client, payload).json()["id"]

    response = client.post(f"/api/bookings/{booking_id}/cancel")

    assert response.status_code == 200
    assert response.json()["cancelled_at"] == TODAY.isoformat()
    assert create(client, payload).status_code == 201


def test_cancel_twice_returns_409(client, payload):
    booking_id = create(client, payload).json()["id"]
    client.post(f"/api/bookings/{booking_id}/cancel")

    assert client.post(f"/api/bookings/{booking_id}/cancel").status_code == 409
