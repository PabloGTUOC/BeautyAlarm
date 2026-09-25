#!/usr/bin/env python
"""Create a household account, reset a password, or adopt unowned rows (D4a).

  python scripts/create_user.py                       create an account
  python scripts/create_user.py --adopt               ...and claim pre-Phase-9 rows
  python scripts/create_user.py --adopt-to you@x.com  claim them for an account
                                                      you already registered
  python scripts/create_user.py --reset you@x.com     set a new password

There is no mail server, so this is also the password-reset path. The password
is read from a prompt with echo off, never from an argument: arguments end up in
shell history and in `ps`.
"""

import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth import hash_password  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import DailyLog, Product, PushSubscription, Routine, User  # noqa: E402
from app.services import utcnow  # noqa: E402

OWNED = (Product, Routine, DailyLog, PushSubscription)
MIN_PASSWORD = 10


def read_password() -> str:
    while True:
        first = getpass.getpass("Password: ")
        if len(first) < MIN_PASSWORD:
            print(f"  At least {MIN_PASSWORD} characters, please.")
            continue
        if first != getpass.getpass("Repeat password: "):
            print("  Those do not match.")
            continue
        return first


def adopt(db, user: User) -> None:
    """Claim every row that belongs to nobody.

    Safe to run more than once: once a row has an owner it is never reassigned,
    so a second person running --adopt does not steal the first person's data.
    """
    total = 0
    for model in OWNED:
        claimed = (
            db.query(model)
            .filter(model.user_id.is_(None))
            .update({model.user_id: user.id}, synchronize_session=False)
        )
        if claimed:
            print(f"  {model.__tablename__}: {claimed} row(s) adopted")
        total += claimed
    db.commit()
    print(f"  {total} row(s) now belong to {user.email}" if total else "  nothing to adopt")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adopt", action="store_true",
                        help="claim rows written before accounts existed")
    parser.add_argument("--adopt-to", metavar="EMAIL", dest="adopt_to",
                        help="claim those rows for an account that already exists")
    parser.add_argument("--reset", metavar="EMAIL",
                        help="set a new password for an existing account")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.adopt_to:
            email = args.adopt_to.strip().lower()
            user = db.query(User).filter(User.email == email).one_or_none()
            if user is None:
                print(f"No account for {email}. Register in the app first, or run "
                      "this without --adopt-to to create one.", file=sys.stderr)
                return 1
            adopt(db, user)
            return 0

        if args.reset:
            email = args.reset.strip().lower()
            user = db.query(User).filter(User.email == email).one_or_none()
            if user is None:
                print(f"No account for {email}", file=sys.stderr)
                return 1
            user.password_hash = hash_password(read_password())
            # Every existing session is invalidated: a password reset that
            # leaves old sessions alive is not a reset.
            from app.models import Session as UserSession
            killed = db.query(UserSession).filter(UserSession.user_id == user.id).delete()
            db.commit()
            print(f"Password updated for {email}; {killed} session(s) signed out.")
            return 0

        email = input("Email: ").strip().lower()
        if "@" not in email:
            print("That does not look like an email address", file=sys.stderr)
            return 1
        if db.query(User).filter(User.email == email).first() is not None:
            print(f"{email} already has an account", file=sys.stderr)
            return 1

        display_name = input("Display name: ").strip() or email.split("@")[0]
        user = User(
            email=email,
            display_name=display_name,
            password_hash=hash_password(read_password()),
            created_at=utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created {email} (id {user.id})")

        if args.adopt:
            adopt(db, user)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
