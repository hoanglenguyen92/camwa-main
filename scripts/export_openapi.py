"""Write the API's OpenAPI schema to frontend/openapi.json for the TypeScript client generator.

Run: python -m scripts.export_openapi
Needs no database or identity credentials; placeholder settings are used only when unset.
"""
import json
import os
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "frontend" / "openapi.json"

for name, placeholder in {
    "DATABASE_URL": "postgresql+asyncpg://openapi:openapi@localhost/openapi",
    "JWT_SECRET_KEY": "openapi-export-placeholder-secret-0000",
    "JWT_REFRESH_SECRET_KEY": "openapi-export-placeholder-secret-0000",
}.items():
    os.environ.setdefault(name, placeholder)

from main import app  # noqa: E402  settings must be in the environment before import


def main() -> None:
    OUTPUT.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
