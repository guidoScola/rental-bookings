from datetime import date, timedelta

import pytest

TODAY = date.today()


def day(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


def book(client, apartment_id, check_in, check_out):
    response = client.post(
        "/bookings",
        json={
            "apartment_id": apartment_id,
            "guest_name": "Ana",
            "guest_count": 2,
            "check_in": check_in,
            "check_out": check_out,
            "price": "100.00",
        },
    )
    return response.json()["id"]


# --- create / read --------------------------------------------------------


def test_create_apartment_is_active(client):
    response = client.post(
        "/apartments", json={"name": "Depto", "address": "Calle 1", "max_guests": 3}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["deactivated_at"] is None
    assert body["floor"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"address": "Calle 1", "max_guests": 3},  # no name
        {"name": "Depto", "max_guests": 3},  # no address
        {"name": "Depto", "address": "Calle 1"},  # no max_guests
        {"name": "Depto", "address": "Calle 1", "max_guests": 0},
    ],
)
def test_invalid_apartment_returns_422(client, body):
    assert client.post("/apartments", json=body).status_code == 422


def test_get_missing_apartment_returns_404(client):
    assert client.get("/apartments/999999").status_code == 404


def test_list_hides_deactivated_unless_asked(client, apartment):
    client.post(f"/apartments/{apartment.id}/deactivate")

    active_ids = [a["id"] for a in client.get("/apartments").json()]
    all_ids = [a["id"] for a in client.get("/apartments?include_deactivated=true").json()]

    assert apartment.id not in active_ids
    assert apartment.id in all_ids


# --- deactivate -----------------------------------------------------------


def test_deactivate_without_future_bookings(client, apartment):
    response = client.post(f"/apartments/{apartment.id}/deactivate")

    assert response.status_code == 200
    assert response.json()["deactivated_at"] == TODAY.isoformat()


def test_deactivate_with_future_bookings_asks_for_confirmation(client, apartment):
    booking_id = book(client, apartment.id, day(10), day(12))

    response = client.post(f"/apartments/{apartment.id}/deactivate")

    assert response.status_code == 409
    assert response.json()["detail"]["booking_ids"] == [booking_id]
    # nothing changed
    assert client.get(f"/apartments/{apartment.id}").json()["deactivated_at"] is None
    assert client.get(f"/bookings/{booking_id}").json()["cancelled_at"] is None


def test_confirmed_deactivate_cancels_future_bookings_only(client, apartment):
    future = book(client, apartment.id, day(10), day(12))
    past = book(client, apartment.id, day(-10), day(-5))

    response = client.post(f"/apartments/{apartment.id}/deactivate?confirm=true")

    assert response.status_code == 200
    assert client.get(f"/bookings/{future}").json()["cancelled_at"] == TODAY.isoformat()
    assert client.get(f"/bookings/{past}").json()["cancelled_at"] is None  # kept as is


def test_deactivate_twice_returns_409(client, apartment):
    client.post(f"/apartments/{apartment.id}/deactivate")

    assert client.post(f"/apartments/{apartment.id}/deactivate").status_code == 409
