"""initial schema: apartment, booking, app_user

Revision ID: 0001
Revises:
Create Date: 2026-11-06
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Needed so a GiST index can combine '=' on an integer with '&&' on a range.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.execute(
        """
        CREATE TABLE apartment (
            id             serial PRIMARY KEY,
            name           text    NOT NULL,
            address        text    NOT NULL,
            floor          text,
            max_guests     integer NOT NULL,
            deactivated_at date,
            CONSTRAINT ck_apartment_max_guests_positive CHECK (max_guests > 0)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE booking (
            id                serial PRIMARY KEY,
            apartment_id      integer        NOT NULL REFERENCES apartment (id),
            guest_name        text           NOT NULL,
            guest_phone       text,
            guest_count       integer        NOT NULL,
            check_in          date           NOT NULL,
            check_out         date           NOT NULL,
            price             numeric(10, 2) NOT NULL,
            payment_method    text,
            linen_change_date date,
            cancelled_at      date,
            notes             text,
            CONSTRAINT ck_booking_guest_count_min CHECK (guest_count >= 1),
            CONSTRAINT ck_booking_dates_order CHECK (check_out > check_in),
            CONSTRAINT ck_booking_price_non_negative CHECK (price >= 0),
            CONSTRAINT ck_booking_payment_method
                CHECK (payment_method IN ('cash', 'transfer')),
            CONSTRAINT ck_booking_linen_change_in_stay
                CHECK (linen_change_date > check_in AND linen_change_date < check_out),
            CONSTRAINT ex_booking_no_overlap EXCLUDE USING gist (
                apartment_id WITH =,
                daterange(check_in, check_out, '[)') WITH &&
            ) WHERE (cancelled_at IS NULL)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE app_user (
            id            serial PRIMARY KEY,
            username      text NOT NULL UNIQUE,
            password_hash text NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE app_user")
    op.execute("DROP TABLE booking")
    op.execute("DROP TABLE apartment")
    op.execute("DROP EXTENSION IF EXISTS btree_gist")
