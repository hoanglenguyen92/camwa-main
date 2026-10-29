def ids(response, key):
    assert response.status_code == 200, response.text
    return sorted(item[key] for item in response.json()["items"])


def test_role_needs_exactly_one_camwa_role(client, as_user):
    assert client.get("/me", headers=as_user("1", "ADMIN", "STUDENT")).status_code == 403
    assert client.get("/me", headers=as_user("1")).status_code == 403


def test_fa_without_profile_is_blocked(client, as_user):
    headers = as_user("999", "FA")
    assert client.get("/me", headers=headers).json()["has_profile"] is False
    assert client.get("/programs", headers=headers).status_code == 403


def test_programs_reach(client, as_user):
    assert ids(client.get("/programs", headers=as_user("1", "ADMIN")), "program_id") == ["CSE", "EE"]
    assert ids(client.get("/programs", headers=as_user("100", "FA")), "program_id") == ["CSE"]
    assert ids(client.get("/programs", headers=as_user("300", "AC")), "program_id") == ["CSE"]
    assert client.get("/programs/EE", headers=as_user("100", "FA")).status_code == 404
    assert client.get("/programs", headers=as_user("400", "STUDENT")).status_code == 403


def test_admin_only_writes(client, as_user):
    body = {"program_id": "ME", "name": "Mechanical"}
    assert client.post("/programs", json=body, headers=as_user("100", "FA")).status_code == 403
    created = client.post("/programs", json=body, headers=as_user("1", "ADMIN"))
    assert created.status_code == 201 and created.headers["Location"].endswith("/programs/ME")
    assert client.delete("/programs/ME", headers=as_user("1", "ADMIN")).status_code == 204


def test_module_reach(client, as_user):
    assert ids(client.get("/modules", headers=as_user("100", "FA")), "module_id") == ["M-CSE"]
    assert client.get("/modules/M-EE", headers=as_user("100", "FA")).status_code == 404
    assert client.get("/modules/M-EE", headers=as_user("400", "STUDENT")).status_code == 404
    assert client.get("/modules/M-CSE", headers=as_user("1", "ADMIN")).status_code == 200


def test_attendance_request_reach(client, as_user):
    assert ids(client.get("/attendance-requests", headers=as_user("400", "STUDENT")), "request_id") == [1]
    assert ids(client.get("/attendance-requests", headers=as_user("101", "FA")), "request_id") == [2]
    assert client.get("/attendance-requests/2", headers=as_user("400", "STUDENT")).status_code == 404
    assert client.get("/attendance-requests/1", headers=as_user("200", "LECTURER")).status_code == 200
    assert client.get("/attendance-requests/2", headers=as_user("200", "LECTURER")).status_code == 404


def test_notification_scope(client, as_user):
    assert ids(client.get("/me/notifications", headers=as_user("1", "ADMIN")), "notification_id") == [1, 2]
    assert ids(client.get("/me/notifications", headers=as_user("100", "FA")), "notification_id") == [1]
    assert ids(client.get("/me/notifications", headers=as_user("400", "STUDENT")), "notification_id") == [3]
    assert ids(client.get("/me/notifications", headers=as_user("401", "STUDENT")), "notification_id") == []

    fa = as_user("100", "FA")
    assert client.patch("/me/notifications/2", json={"status": "READ"}, headers=fa).status_code == 404
    assert client.get("/me/notifications/unread-count", headers=fa).json() == {"count": 1}
    assert client.patch("/me/notifications", json={"status": "READ"}, headers=fa).json() == {"count": 1}
    assert client.get("/me/notifications/unread-count", headers=as_user("1", "ADMIN")).json() == {"count": 1}
    assert client.delete("/me/notifications/3", headers=fa).status_code == 404
    assert client.delete("/me/notifications/3", headers=as_user("400", "STUDENT")).status_code == 204
