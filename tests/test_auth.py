import time

from cryptography.hazmat.primitives.asymmetric import rsa


def test_login_refresh_logout(client, kc):
    kc.add_user("400", "STUDENT", password="correct-horse-battery")
    tokens = client.post("/auth/login", json={"email": "400@example.edu", "password": "correct-horse-battery"}).json()
    assert tokens["token_type"] == "Bearer"

    me = client.get("/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["camwa_id"] == "400" and me.json()["has_profile"] is True

    refreshed = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    reused = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401, "refresh tokens are single use"

    new = refreshed.json()
    out = client.post("/auth/logout", json={"refresh_token": new["refresh_token"]},
                      headers={"Authorization": f"Bearer {new['access_token']}"})
    assert out.status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": new["refresh_token"]}).status_code == 401


def test_wrong_password_is_401(client, kc):
    kc.add_user("400", "STUDENT", password="correct-horse-battery")
    r = client.post("/auth/login", json={"email": "400@example.edu", "password": "nope"})
    assert r.status_code == 401 and r.headers["WWW-Authenticate"] == "Bearer"


def test_rejects_bad_tokens(client, kc):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    bad = {
        "missing": None,
        "wrong signature": kc.token("400", "STUDENT", _key=other_key),
        "expired": kc.token("400", "STUDENT", exp=int(time.time()) - 10),
        "wrong issuer": kc.token("400", "STUDENT", iss="http://evil/realms/camwa"),
        "wrong audience": kc.token("400", "STUDENT", aud="someone-else"),
        "other client": kc.token("400", "STUDENT", azp="other-client"),
        "garbage": "not.a.jwt",
    }
    for name, token in bad.items():
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        assert client.get("/me", headers=headers).status_code == 401, name


def test_password_reset_does_not_reveal_accounts(client, kc):
    user = kc.add_user("400", "STUDENT")
    assert client.post("/auth/password-reset", json={"email": "400@example.edu"}).status_code == 202
    assert client.post("/auth/password-reset", json={"email": "nobody@example.edu"}).status_code == 202
    assert user.emails_sent == 1


def test_change_password(client, kc, as_user):
    user = kc.add_user("400", "STUDENT", password="old-password-123")
    headers = as_user("400", "STUDENT")
    body = lambda current, new: {"current_password": current, "new_password": new}
    assert client.put("/me/password", json=body("nope", "new-password-123"), headers=headers).status_code == 403
    assert client.put("/me/password", json=body("old-password-123", "short"), headers=headers).status_code == 422
    ok = client.put("/me/password", json=body("old-password-123", "new-password-123"), headers=headers)
    assert ok.status_code == 200 and ok.json()["access_token"]
    assert user.password == "new-password-123" and user.sessions_ended == 1


def test_acting_role_switch(client, as_user):
    ac = as_user("300", "AC")
    assert client.get("/me", headers=ac).json()["acting_role"] == "AC"
    assert client.get("/programs", headers=ac).status_code == 200

    assert client.put("/me/acting-role", json={"role": "LECTURER"}, headers=ac).status_code == 200
    assert client.get("/me", headers=ac).json()["acting_role"] == "LECTURER"
    assert client.get("/programs", headers=ac).status_code == 403, "acting as LECTURER drops AC rights"
    assert client.get("/me/modules", headers=ac).status_code == 200

    lecturer = as_user("200", "LECTURER")
    assert client.put("/me/acting-role", json={"role": "AC"}, headers=lecturer).status_code == 403
