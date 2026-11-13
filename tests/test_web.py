"""Page tests: the business rules are tested in the API tests, here only that
the pages are wired to them (forms, redirects, messages)."""

from datetime import date, timedelta

from app.models import Booking
from tests.conftest import TEST_PASSWORD

TODAY = date.today()


def day(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


def booking_form(apartment, **changes):
    form = {
        "apartment_id": str(apartment.id),
        "guest_name": "Ana",
        "guest_phone": "",
        "guest_count": "2",
        "check_in": day(10),
        "check_out": day(14),
        "price": "400",
        "payment_method": "",
        "linen_change_date": "",
        "notes": "",
    }
    return {**form, **changes}


def test_pages_redirect_to_login_without_session(anon_client):
    response = anon_client.get("/", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_form_opens_the_home_page(anon_client, user):
    response = anon_client.post(
        "/login", data={"username": "test-owner", "password": TEST_PASSWORD}
    )

    assert response.status_code == 200
    assert "En curso" in response.text


def test_wrong_login_shows_error(anon_client, user):
    response = anon_client.post("/login", data={"username": "test-owner", "password": "nope"})

    assert response.status_code == 401
    assert "Usuario o contraseña incorrectos" in response.text


def test_create_booking_from_form_shows_it_in_the_list(client, apartment):
    response = client.post("/bookings/new", data=booking_form(apartment))

    assert response.status_code == 200  # after the redirect to /
    assert "Reserva cargada" in response.text
    assert "Ana" in response.text


def test_overlapping_booking_shows_message_and_keeps_the_values(client, apartment):
    client.post("/bookings/new", data=booking_form(apartment))

    response = client.post("/bookings/new", data=booking_form(apartment, guest_name="Juan"))

    assert response.status_code == 422
    assert "Esas noches ya están ocupadas" in response.text
    assert 'value="Juan"' in response.text


def test_edit_booking_marks_it_as_paid(client, session, apartment):
    client.post("/bookings/new", data=booking_form(apartment))
    booking = session.query(Booking).filter_by(guest_name="Ana").one()

    response = client.post(
        f"/bookings/{booking.id}", data=booking_form(apartment, payment_method="transfer")
    )

    assert response.status_code == 200
    session.refresh(booking)
    assert booking.payment_method == "transfer"


def test_cancel_booking_from_page(client, session, apartment):
    client.post("/bookings/new", data=booking_form(apartment))
    booking = session.query(Booking).filter_by(guest_name="Ana").one()

    response = client.post(f"/bookings/{booking.id}/cancel")

    assert "Reserva cancelada" in response.text
    session.refresh(booking)
    assert booking.cancelled_at == TODAY


def test_deactivate_with_future_bookings_asks_and_then_cancels(client, session, apartment):
    client.post("/bookings/new", data=booking_form(apartment))
    booking = session.query(Booking).filter_by(guest_name="Ana").one()

    ask = client.post(f"/apartments/{apartment.id}/deactivate")
    assert "Dar de baja y cancelar las reservas" in ask.text
    session.refresh(booking)
    assert booking.cancelled_at is None

    client.post(f"/apartments/{apartment.id}/deactivate", data={"confirm": "true"})
    session.refresh(booking)
    session.refresh(apartment)
    assert booking.cancelled_at == TODAY
    assert apartment.deactivated_at == TODAY


def test_names_with_quotes_do_not_break_the_page(client, apartment):
    client.post("/bookings/new", data=booking_form(apartment, guest_name="O'Connor"))

    response = client.get("/")

    assert "O&#39;Connor" in response.text  # escaped by Jinja


def test_every_page_renders(client, session, apartment):
    client.post("/bookings/new", data=booking_form(apartment))
    booking = session.query(Booking).filter_by(guest_name="Ana").one()

    for url in ["/", "/bookings/new", f"/bookings/{booking.id}", "/apartments", "/login"]:
        assert client.get(url).status_code == 200, url
