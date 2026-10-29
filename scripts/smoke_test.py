"""Smoke-tests a running backend against the real Keycloak, using the accounts that seed.py creates.

    make up seed-demo
    make run            # in another terminal
    python -m scripts.smoke_test

Safe to rerun. Exits 1 if any check fails.
"""
import os
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://localhost:8000/api/v1")
IMPORT_CSV = (
    "camwa_id,email,first_name,last_name,role,program_id,intake,phone_number\n"
    "91001,smoke.import@example.com,Smoke,Import,STUDENT,CSE,2021,+4915112345678\n"
)


def wait_for(api: httpx.Client, seconds: int = 60) -> None:
    for _ in range(seconds):
        try:
            api.get("")
            return
        except httpx.HTTPError:
            time.sleep(1)
    sys.exit(f"Backend not reachable at {BASE_URL}")


def main() -> None:
    api = httpx.Client(base_url=BASE_URL, timeout=30)
    wait_for(api)
    failures = []

    def check(name: str, ok: bool, detail: object = "") -> None:
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  [{detail}]"))
        if not ok:
            failures.append(name)

    def login(email: str, password: str) -> httpx.Response:
        return api.post("/auth/login", json={"email": email, "password": password})

    def bearer(response: httpx.Response) -> dict:
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    r = login(os.environ["SEED_ADMIN_EMAIL"], os.environ["SEED_ADMIN_PASSWORD"])
    check("admin login", r.status_code == 200, r.text)
    if failures:
        sys.exit(1)
    admin = bearer(r)
    me = api.get("/me", headers=admin).json()
    check("admin /me", me.get("camwa_id") == os.environ["SEED_ADMIN_ID"] and me.get("roles") == ["ADMIN"], me)
    check("wrong password 401", login(os.environ["SEED_ADMIN_EMAIL"], "wrong").status_code == 401)
    check("garbage token 401", api.get("/me", headers={"Authorization": "Bearer x.y.z"}).status_code == 401)

    demo = os.environ["SEED_DEMO_PASSWORD"]
    r = login("demo.ac@example.com", demo)
    check("AC login", r.status_code == 200, r.text)
    ac = bearer(r)
    me = api.get("/me", headers=ac).json()
    check("AC token carries AC and LECTURER", me.get("roles") == ["AC", "LECTURER"], me)
    check("AC reads programs", api.get("/programs", headers=ac).status_code == 200)
    check("AC acts as lecturer", api.put("/me/acting-role", json={"role": "LECTURER"}, headers=ac).status_code == 200)
    check("lecturer cannot read programs", api.get("/programs", headers=ac).status_code == 403)
    api.put("/me/acting-role", json={"role": "AC"}, headers=ac)

    r = login("demo.student@example.com", demo)
    refresh_token = r.json()["refresh_token"]
    check("student blocked from users", api.get("/users/90001", headers=bearer(r)).status_code == 403)
    check("refresh", api.post("/auth/refresh", json={"refresh_token": refresh_token}).status_code == 200)
    check("reused refresh token 401", api.post("/auth/refresh", json={"refresh_token": refresh_token}).status_code == 401)

    r = api.post("/users/imports", files={"file": ("users.csv", IMPORT_CSV.encode(), "text/csv")}, headers=admin)
    outcomes = [row["outcome"] for row in r.json().get("rows", [])] if r.status_code == 200 else []
    check("CSV import", outcomes in (["created"], ["skipped"]), r.text)
    check("deactivate", api.patch("/users/91001", json={"active": False}, headers=admin).json().get("active") is False)
    check("reactivate", api.patch("/users/91001", json={"active": True}, headers=admin).json().get("active") is True)

    r = login("demo.fa@example.com", demo)
    refresh_token = r.json()["refresh_token"]
    check("logout 204", api.post("/auth/logout", json={"refresh_token": refresh_token}, headers=bearer(r)).status_code == 204)
    check("refresh after logout 401", api.post("/auth/refresh", json={"refresh_token": refresh_token}).status_code == 401)

    print(f"{len(failures)} failed" if failures else "All checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
