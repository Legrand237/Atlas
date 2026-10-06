"""Vérifie la connexion à la base : ``python -m app.db_check`` (depuis backend/)."""

import sys

from app.db import (
    DatabaseNotConfigured,
    DatabaseUnavailable,
    check_connection,
    get_engine,
)


def main() -> int:
    try:
        version = check_connection(get_engine())
    except DatabaseNotConfigured as exc:
        print(f"ECHEC : {exc}")
        return 2
    except DatabaseUnavailable as exc:
        print(f"ECHEC : {exc}")
        return 1
    print(f"OK : connecté à PostgreSQL (version {version}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
