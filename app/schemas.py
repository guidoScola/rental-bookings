from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

PaymentMethod = Literal["cash", "transfer"]


class ApartmentCreate(BaseModel):
    name: str = Field(min_length=1)
    address: str = Field(min_length=1)
    floor: str | None = None
    max_guests: int = Field(gt=0)


class ApartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    floor: str | None
    max_guests: int
    deactivated_at: date | None


class BookingCreate(BaseModel):
    apartment_id: int
    guest_name: str = Field(min_length=1)
    guest_phone: str | None = None
    guest_count: int = Field(ge=1)
    check_in: date
    check_out: date
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    payment_method: PaymentMethod | None = None
    linen_change_date: date | None = None
    notes: str | None = None


class BookingUpdate(BaseModel):
    """Every field is optional: only the fields that are sent get changed."""

    guest_name: str | None = Field(default=None, min_length=1)
    guest_phone: str | None = None
    guest_count: int | None = Field(default=None, ge=1)
    check_in: date | None = None
    check_out: date | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    payment_method: PaymentMethod | None = None
    linen_change_date: date | None = None
    notes: str | None = None


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    apartment_id: int
    guest_name: str
    guest_phone: str | None
    guest_count: int
    check_in: date
    check_out: date
    price: Decimal
    payment_method: PaymentMethod | None
    linen_change_date: date | None
    cancelled_at: date | None
    notes: str | None

    @computed_field
    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days
