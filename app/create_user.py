"""Create the system's only user, or change its password.

Usage: python -m app.create_user <username>
The password is asked interactively so it never ends up in the shell history.
"""

import sys
from getpass import getpass

from sqlalchemy import select

from app.auth import hash_password
from app.db import SessionLocal
from app.models import AppUser


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m app.create_user <username>")
    username = sys.argv[1]

    password = getpass("Password: ")
    if len(password) < 8:
        sys.exit("Password must have at least 8 characters")
    if len(password.encode()) > 72:
        sys.exit("Password must have at most 72 bytes (bcrypt limit)")
    if getpass("Repeat password: ") != password:
        sys.exit("Passwords do not match")

    with SessionLocal() as session:
        users = list(session.scalars(select(AppUser)))
        existing = next((u for u in users if u.username == username), None)
        if existing:
            existing.password_hash = hash_password(password)
            print(f"Password updated for '{username}'")
        elif users:
            sys.exit(f"There is already a user ('{users[0].username}'); the system has only one")
        else:
            session.add(AppUser(username=username, password_hash=hash_password(password)))
            print(f"User '{username}' created")
        session.commit()


if __name__ == "__main__":
    main()
