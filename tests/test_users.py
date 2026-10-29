from backend.models import AcademicCoordinator, Lecturer, Student

HEADER = "camwa_id,email,first_name,last_name,role,program_id,intake,phone_number\n"


def upload(client, headers, body: str, name="users.csv"):
    return client.post("/users/imports", files={"file": (name, (HEADER + body).encode(), "text/csv")}, headers=headers)


def test_import_creates_accounts_and_profiles(client, kc, as_user, db):
    admin = as_user("1", "ADMIN")
    kc.add_user("500", "STUDENT", email="old@example.edu")
    r = upload(client, admin,
               "500,old@example.edu,Old,Student,STUDENT,CSE,2021,\n"
               "501,new@example.edu,New,Student,STUDENT,CSE,2021,+4915112345678\n"
               "502,ac@example.edu,New,Coordinator,AC,EE,,\n")
    assert r.status_code == 200, r.text
    report = r.json()
    assert (report["created"], report["skipped"], report["failed"]) == (2, 1, 0)

    new = kc.by_username("501")
    assert new.roles == {"STUDENT"} and new.emails_sent == 1
    assert new.attributes == {"phone_number": ["+4915112345678"]}
    assert kc.by_username("502").roles == {"AC"}

    async def profiles(s):
        return (await s.get(Student, "500"), await s.get(Student, "501"),
                await s.get(Lecturer, "502"), await s.get(AcademicCoordinator, "502"))
    assert all(db(profiles)), "skipped rows still get their profile"

    again = upload(client, admin, "501,new@example.edu,New,Student,STUDENT,CSE,2021,\n").json()
    assert again["skipped"] == 1 and kc.by_username("501").emails_sent == 1


def test_import_rejects_whole_file_on_bad_rows(client, kc, as_user):
    r = upload(client, as_user("1", "ADMIN"),
               "501,a@example.edu,A,B,STUDENT,CSE,2021,\n"
               "abc,b@example.edu,A,B,STUDENT,CSE,2021,\n"
               "503,c@example.edu,A,B,STUDENT,NOPE,2021,\n"
               "504,d@example.edu,A,B,STUDENT,CSE,,\n"
               "505,e@example.edu,A,B,ADMIN,CSE,,\n"
               "501,f@example.edu,A,B,FA,CSE,,\n")
    assert r.status_code == 422
    assert [row["row"] for row in r.json()["detail"]["rows"]] == [3, 4, 5, 6, 7]
    assert kc.by_username("501") is None


def test_import_file_checks(client, as_user):
    admin = as_user("1", "ADMIN")
    assert upload(client, as_user("100", "FA"), "").status_code == 403
    assert upload(client, admin, "", name="users.xlsx").status_code == 400
    assert upload(client, admin, "").status_code == 400
    missing = client.post("/users/imports", files={"file": ("u.csv", b"camwa_id,email\n1,a@b.c\n", "text/csv")}, headers=admin)
    assert missing.status_code == 400


def test_import_email_owned_by_other_account(client, kc, as_user):
    kc.add_user("600", "STUDENT", email="taken@example.edu")
    report = upload(client, as_user("1", "ADMIN"), "601,taken@example.edu,A,B,STUDENT,CSE,2021,\n").json()
    assert report["failed"] == 1 and "600" in report["rows"][0]["reason"]


def test_deactivate(client, kc, as_user):
    admin = as_user("1", "ADMIN")
    user = kc.add_user("400", "STUDENT", password="pw-long-enough")
    login = {"email": "400@example.edu", "password": "pw-long-enough"}
    tokens = client.post("/auth/login", json=login).json()

    r = client.patch("/users/400", json={"active": False}, headers=admin)
    assert r.status_code == 200 and r.json()["active"] is False
    assert user.sessions_ended == 1
    assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.post("/auth/login", json=login).status_code == 401

    assert client.patch("/users/400", json={"active": True}, headers=admin).json()["active"] is True
    assert client.get("/users/nobody", headers=admin).status_code == 404
    kc.add_user("1", "ADMIN")
    assert client.patch("/users/1", json={"active": False}, headers=admin).status_code == 409
