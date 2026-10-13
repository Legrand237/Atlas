"""Commandes d'administration (depuis backend/, environnement activé).

    python -m app.manage create-user ton@email.com --name "Ton nom"

Le mot de passe est demandé au clavier (il ne s'affiche pas et n'est jamais dans l'historique du terminal).
"""

import argparse
import getpass
import sys

from app.auth.passwords import WeakPassword
from app.auth.service import UserAlreadyExists, create_user
from app.db.session import DatabaseNotConfigured, DatabaseUnavailable, session_scope


def _create_user(email: str, name: str | None) -> int:
    password = getpass.getpass("Mot de passe (12 caractères minimum) : ")
    if password != getpass.getpass("Confirme le mot de passe : "):
        print("ECHEC : les deux mots de passe sont différents.")
        return 1
    try:
        with session_scope() as session:
            user = create_user(session, email=email, password=password, display_name=name)
            print(f"OK : compte créé pour {user.email}.")
    except WeakPassword as exc:
        print(f"ECHEC : {exc}")
        return 1
    except UserAlreadyExists:
        print("ECHEC : un compte existe déjà avec cette adresse e-mail.")
        return 1
    except ValueError:
        print("ECHEC : adresse e-mail invalide.")
        return 1
    except DatabaseNotConfigured as exc:
        print(f"ECHEC : {exc}")
        return 2
    except DatabaseUnavailable as exc:
        print(f"ECHEC : {exc}")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.manage", description="Administration d'Atlas")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user", help="crée un compte (mot de passe demandé au clavier)")
    create.add_argument("email")
    create.add_argument("--name", default=None, help="nom affiché (facultatif)")
    args = parser.parse_args(argv)
    return _create_user(args.email, args.name)


if __name__ == "__main__":
    sys.exit(main())
