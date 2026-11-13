"""HTML pages (Jinja templates) for the owners.

The pages call the same functions as the JSON API, so every business rule lives
in one place (app/bookings.py, app/apartments.py). This module only turns form
fields into schemas and errors into messages in Spanish.
"""

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import apartments as apartments_api
from app import bookings as bookings_api
from app.auth import authenticate, require_user_page, start_session
from app.db import get_session
from app.models import Apartment
from app.schemas import ApartmentCreate, BookingCreate, BookingUpdate

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def format_money(value) -> str:
    """Argentine format: 40000.5 -> '$ 40.000,50' (cents only when there are any)."""
    text = f"{value:,.2f}".translate(str.maketrans(",.", ".,"))
    return "$ " + text.removesuffix(",00")


templates.env.filters["fdate"] = lambda d: d.strftime("%d/%m/%Y") if d else ""
templates.env.filters["money"] = format_money

public = APIRouter(include_in_schema=False)
router = APIRouter(include_in_schema=False, dependencies=[Depends(require_user_page)])

ERRORS = {
    "Apartment not found": "El departamento no existe.",
    "Apartment is deactivated": "El departamento está dado de baja.",
    "check_out must be after check_in": "La fecha de egreso tiene que ser posterior a la de ingreso.",
    "linen_change_date must be strictly between check_in and check_out": (
        "El cambio de ropa blanca tiene que ser después del ingreso y antes del egreso."
    ),
    "Dates overlap with another booking": "Esas noches ya están ocupadas por otra reserva.",
    "Booking is cancelled": "La reserva está cancelada y no se puede modificar.",
    "Booking is already cancelled": "La reserva ya estaba cancelada.",
    "Apartment is already deactivated": "El departamento ya estaba dado de baja.",
}

FIELD_LABELS = {
    "apartment_id": "departamento",
    "guest_name": "nombre del huésped",
    "guest_count": "personas",
    "check_in": "ingreso",
    "check_out": "egreso",
    "price": "precio",
    "payment_method": "medio de pago",
    "linen_change_date": "cambio de ropa blanca",
    "name": "nombre",
    "address": "dirección",
    "max_guests": "máximo de huéspedes",
}


def error_message(error: HTTPException | ValidationError) -> str:
    if isinstance(error, ValidationError):
        fields = {FIELD_LABELS.get(str(e["loc"][0]), str(e["loc"][0])) for e in error.errors()}
        return "Revisá estos datos: " + ", ".join(sorted(fields)) + "."
    detail = str(error.detail)
    if detail.startswith("Apartment allows at most"):
        return "Hay más personas que el máximo permitido en el departamento."
    return ERRORS.get(detail, detail)


def flash(request: Request, message: str) -> None:
    """A message shown once, on the next page (survives the redirect)."""
    request.session["flash"] = message


def render(request: Request, template: str, status_code: int = 200, **context) -> HTMLResponse:
    context["flash"] = request.session.pop("flash", None)
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def redirect(url: str) -> RedirectResponse:
    # 303: after a POST, the browser follows with a GET (refreshing won't resend the form).
    return RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)


def blank_to_none(form: dict[str, str]) -> dict[str, str | None]:
    """Empty form inputs arrive as '' but mean 'no value'."""
    return {key: (value.strip() or None) for key, value in form.items()}


def active_apartments(session: Session) -> list[Apartment]:
    return apartments_api.list_apartments(include_deactivated=False, session=session)


# --- login ----------------------------------------------------------------


@public.get("/login")
def login_page(request: Request):
    return render(request, "login.html")


@public.post("/login")
def login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    session: Session = Depends(get_session),
):
    user = authenticate(session, username, password)
    if user is None:
        return render(
            request,
            "login.html",
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="Usuario o contraseña incorrectos.",
            username=username,
        )
    start_session(request, user)
    return redirect("/")


@public.post("/logout")
def logout_submit(request: Request):
    request.session.clear()
    return redirect("/login")


# --- bookings -------------------------------------------------------------


@router.get("/")
def home(request: Request, session: Session = Depends(get_session)):
    today = date.today()
    bookings = bookings_api.list_bookings(status_filter=None, session=session)
    names = {a.id: a.name for a in session.scalars(select(Apartment))}
    return render(
        request,
        "bookings.html",
        current=[b for b in bookings if b.check_in <= today],
        upcoming=[b for b in bookings if b.check_in > today],
        names=names,
    )


BOOKING_FIELDS = (
    "guest_name",
    "guest_phone",
    "guest_count",
    "check_in",
    "check_out",
    "price",
    "payment_method",
    "linen_change_date",
    "notes",
)


async def booking_form(request: Request) -> dict[str, str | None]:
    form = await request.form()
    fields = ("apartment_id", *BOOKING_FIELDS)
    return blank_to_none({f: str(form.get(f, "")) for f in fields})


@router.get("/bookings/new")
def new_booking_page(request: Request, session: Session = Depends(get_session)):
    return render(
        request, "booking_form.html", values={}, apartments=active_apartments(session)
    )


@router.post("/bookings/new")
def new_booking_submit(
    request: Request,
    values: dict = Depends(booking_form),
    session: Session = Depends(get_session),
):
    try:
        data = BookingCreate(**values)
        bookings_api.create_booking(data, session)
    except (ValidationError, HTTPException) as error:
        return render(
            request,
            "booking_form.html",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error=error_message(error),
            values=values,
            apartments=active_apartments(session),
        )
    flash(request, "Reserva cargada.")
    return redirect("/")


@router.get("/bookings/{booking_id}")
def edit_booking_page(booking_id: int, request: Request, session: Session = Depends(get_session)):
    booking = bookings_api.get_booking_or_404(session, booking_id)
    values = {f: getattr(booking, f) for f in BOOKING_FIELDS}
    return render(
        request,
        "booking_form.html",
        booking=booking,
        values=values,
        apartment=session.get(Apartment, booking.apartment_id),
    )


@router.post("/bookings/{booking_id}")
def edit_booking_submit(
    booking_id: int,
    request: Request,
    values: dict = Depends(booking_form),
    session: Session = Depends(get_session),
):
    booking = bookings_api.get_booking_or_404(session, booking_id)
    values.pop("apartment_id")  # the apartment of a booking is not editable
    try:
        # Every field is sent, so emptying an input clears that value.
        data = BookingUpdate(**values)
        bookings_api.update_booking(booking_id, data, session)
    except (ValidationError, HTTPException) as error:
        return render(
            request,
            "booking_form.html",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error=error_message(error),
            booking=booking,
            values=values,
            apartment=session.get(Apartment, booking.apartment_id),
        )
    flash(request, "Reserva guardada.")
    return redirect("/")


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking_submit(booking_id: int, request: Request, session: Session = Depends(get_session)):
    try:
        bookings_api.cancel_booking(booking_id, session)
        flash(request, "Reserva cancelada.")
    except HTTPException as error:
        if error.status_code == status.HTTP_404_NOT_FOUND:
            raise
        flash(request, error_message(error))
    return redirect("/")


# --- apartments -----------------------------------------------------------


def apartments_page_response(request: Request, session: Session, status_code: int = 200, **extra):
    all_apartments = apartments_api.list_apartments(include_deactivated=True, session=session)
    return render(
        request, "apartments.html", status_code=status_code, apartments=all_apartments, **extra
    )


@router.get("/apartments")
def apartments_page(request: Request, session: Session = Depends(get_session)):
    return apartments_page_response(request, session, values={})


@router.post("/apartments")
async def apartments_submit(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    values = blank_to_none({f: str(form.get(f, "")) for f in ("name", "address", "floor", "max_guests")})
    try:
        apartments_api.create_apartment(ApartmentCreate(**values), session)
    except ValidationError as error:
        return apartments_page_response(
            request,
            session,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error=error_message(error),
            values=values,
        )
    flash(request, "Departamento cargado.")
    return redirect("/apartments")


@router.post("/apartments/{apartment_id}/deactivate")
def deactivate_submit(
    apartment_id: int,
    request: Request,
    confirm: bool = Form(False),
    session: Session = Depends(get_session),
):
    try:
        apartments_api.deactivate_apartment(apartment_id, confirm, session)
    except HTTPException as error:
        if isinstance(error.detail, dict):
            # Future bookings: ask before cancelling them.
            ids = error.detail["booking_ids"]
            bookings = [bookings_api.get_booking_or_404(session, i) for i in ids]
            return render(
                request,
                "confirm_deactivate.html",
                apartment=session.get(Apartment, apartment_id),
                bookings=bookings,
            )
        if error.status_code == status.HTTP_404_NOT_FOUND:
            raise
        flash(request, error_message(error))
        return redirect("/apartments")
    flash(request, "Departamento dado de baja.")
    return redirect("/apartments")
