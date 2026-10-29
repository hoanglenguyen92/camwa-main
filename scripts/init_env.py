"""Creates .env from .env.example, with a random value for every empty secret.

    python scripts/init_env.py
Refuses to overwrite an existing .env. Prints no secret values.
"""
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SECRETS = (
    "APP_DB_PASSWORD",
    "KEYCLOAK_CLIENT_SECRET",
    "KC_DB_PASSWORD",
    "KC_BOOTSTRAP_ADMIN_PASSWORD",
    "SEED_ADMIN_PASSWORD",
    "SEED_DEMO_PASSWORD",
)


def main() -> None:
    target = ROOT / ".env"
    if target.exists():
        sys.exit(".env already exists. Delete it first to generate a new one.")
    # URL-safe, so APP_DB_PASSWORD can sit inside DATABASE_URL unescaped.
    values = {name: secrets.token_urlsafe(24) for name in SECRETS}
    lines = []
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        name, sep, value = line.partition("=")
        if sep and name in values and not value:
            line = f"{name}={values[name]}"
        lines.append(line.replace("<APP_DB_PASSWORD>", values["APP_DB_PASSWORD"]))
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {target}. The CAMWA admin password is SEED_ADMIN_PASSWORD in that file.")


if __name__ == "__main__":
    main()
