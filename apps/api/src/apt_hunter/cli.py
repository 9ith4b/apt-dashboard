import argparse
import getpass
import os

from sqlalchemy import select

from apt_hunter.db.session import SessionLocal
from apt_hunter.models import User
from apt_hunter.services.auth import hash_password


def _password() -> str:
    password = os.getenv("APT_HUNTER_NEW_USER_PASSWORD")
    if password is None:
        password = getpass.getpass("Password: ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")
    return password


def create_user(args: argparse.Namespace) -> None:
    username = args.username.strip().casefold()
    display_name = args.display_name.strip() or username
    with SessionLocal.begin() as session:
        if session.scalar(select(User.id).where(User.username == username)):
            raise SystemExit(f"User {username!r} already exists")
        session.add(
            User(
                username=username,
                display_name=display_name,
                password_hash=hash_password(_password()),
                role=args.role,
                enabled=True,
            )
        )
    print(f"Created {args.role} user {username!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="APT Hunter administration")
    subparsers = parser.add_subparsers(required=True)
    user_parser = subparsers.add_parser("create-user", help="Create a local user")
    user_parser.add_argument("--username", required=True)
    user_parser.add_argument("--display-name", default="")
    user_parser.add_argument("--role", choices=("viewer", "analyst", "admin"), default="viewer")
    user_parser.set_defaults(func=create_user)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
