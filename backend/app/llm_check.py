"""Vérification réelle de la passerelle IA depuis le terminal (utilise ta clé de backend/.env).

    python -m app.llm_check models        # liste les modèles de TON compte et signale ceux configurés
    python -m app.llm_check ping simple   # un petit appel réel (niveau simple, medium ou hard)

Le ``ping`` envoie une phrase de test sans donnée personnelle et affiche la réponse et le nombre de jetons.
La clé n'est jamais affichée.
"""

import argparse
import sys

from app.config import get_settings
from app.llm.base import TIERS, ChatMessage, LLMError
from app.llm.gemini import GeminiProvider


def _provider() -> GeminiProvider:
    settings = get_settings()
    if settings.gemini_api_key is None:
        print("GEMINI_API_KEY manquante dans backend/.env.")
        raise SystemExit(2)
    return GeminiProvider(settings.gemini_api_key.get_secret_value(), timeout_seconds=settings.llm_timeout_seconds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.llm_check")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("models")
    ping = sub.add_parser("ping")
    ping.add_argument("tier", choices=TIERS)
    args = parser.parse_args(argv)
    settings = get_settings()
    try:
        provider = _provider()
        if args.command == "models":
            names = provider.list_models()
            print(f"{len(names)} modèles utilisables avec generateContent :")
            for name in names:
                configured = [t for t in TIERS if settings.model_for_tier(t) == name]
                print(f"  {name}" + (f"   <- configuré pour : {', '.join(configured)}" if configured else ""))
            return 0
        model = settings.model_for_tier(args.tier)
        if model is None:
            print(f"Aucun modèle configuré pour le niveau {args.tier} (LLM_MODEL_{args.tier.upper()} dans backend/.env).")
            return 2
        result = provider.generate(
            model=model,
            messages=[ChatMessage("user", "Réponds uniquement par le mot : OK")],
            system=None, max_output_tokens=32, temperature=0.0,
        )  # fmt: skip
    except LLMError as exc:
        print(f"Échec ({exc.code}) : {exc}")
        return 1
    print(f"Modèle : {result.model}\nRéponse : {result.text.strip()}")
    print(f"Jetons : entrée={result.prompt_tokens} sortie={result.output_tokens} total={result.total_tokens}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
