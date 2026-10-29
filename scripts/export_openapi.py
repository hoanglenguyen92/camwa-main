"""Write the API's OpenAPI schema to frontend/openapi.json for the TypeScript client generator.

Run: python -m scripts.export_openapi
Needs no database or Keycloak; a placeholder DATABASE_URL is used when unset.
"""
import json
import os
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "frontend" / "openapi.json"

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://openapi:openapi@localhost/openapi")

from main import app  # noqa: E402  settings must be in the environment before import


def main() -> None:
    OUTPUT.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
