"""In-memory Keycloak for tests: RS256 tokens, JWKS, the OIDC grants and the admin API calls the backend makes."""
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import parse_qs

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from backend.core.configs import settings

KID = "test-key"


@dataclass
class FakeUser:
    id: str
    username: str
    email: str
    password: Optional[str]
    roles: set[str]
    first_name: str = "Test"
    last_name: str = "User"
    enabled: bool = True
    attributes: dict = field(default_factory=dict)
    sessions_ended: int = 0
    emails_sent: int = 0

    def rep(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "enabled": self.enabled,
            "attributes": self.attributes,
        }


class FakeKeycloak:
    def __init__(self):
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.users: dict[str, FakeUser] = {}
        self.refresh_tokens: dict[str, str] = {}
        self.transport = httpx.MockTransport(self._handle)

    def add_user(self, username: str, *roles: str, password: Optional[str] = "pw", email: Optional[str] = None) -> FakeUser:
        user = FakeUser(str(uuid.uuid4()), username, email or f"{username}@example.edu", password, set(roles))
        self.users[user.id] = user
        return user

    def by_username(self, username: str) -> Optional[FakeUser]:
        return next((u for u in self.users.values() if u.username == username), None)

    def token(self, username: str, *roles: str, **overrides) -> str:
        # AC is a composite of LECTURER, as in the realm.
        realm_roles = set(roles) | ({"LECTURER"} if "AC" in roles else set())
        key = overrides.pop("_key", None) or self.private_key
        now = int(time.time())
        claims = {
            "iss": settings.keycloak_issuer,
            "aud": [settings.KEYCLOAK_CLIENT_ID, "account"],
            "azp": settings.KEYCLOAK_CLIENT_ID,
            "iat": now,
            "exp": now + 300,
            "preferred_username": username,
            "email": f"{username}@example.edu",
            "given_name": "Test",
            "family_name": "User",
            "realm_access": {"roles": sorted(realm_roles | {"offline_access"})},
            **overrides,
        }
        return jwt.encode(claims, key, algorithm="RS256", headers={"kid": KID})

    def _jwks(self) -> dict:
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.private_key.public_key()))
        return {"keys": [{**jwk, "kid": KID, "use": "sig", "alg": "RS256"}]}

    def _tokens(self, user: FakeUser) -> httpx.Response:
        refresh = str(uuid.uuid4())
        self.refresh_tokens[refresh] = user.id
        return httpx.Response(200, json={
            "access_token": self.token(user.username, *user.roles),
            "refresh_token": refresh,
            "expires_in": 300,
            "refresh_expires_in": 1800,
        })

    def _grant(self, form: dict) -> httpx.Response:
        if form.get("client_secret") != settings.KEYCLOAK_CLIENT_SECRET:
            return httpx.Response(401, json={"error": "unauthorized_client"})
        grant = form["grant_type"]
        if grant == "client_credentials":
            return httpx.Response(200, json={"access_token": "admin-token", "expires_in": 300})
        if grant == "password":
            name = form["username"]
            user = next((u for u in self.users.values() if name in (u.username, u.email)), None)
            if user is None or not user.enabled or user.password != form["password"]:
                return httpx.Response(401, json={"error": "invalid_grant", "error_description": "Invalid user credentials"})
            return self._tokens(user)
        if grant == "refresh_token":
            user_id = self.refresh_tokens.pop(form["refresh_token"], None)
            user = self.users.get(user_id)
            if user is None or not user.enabled:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return self._tokens(user)
        return httpx.Response(400, json={"error": "unsupported_grant_type"})

    def _admin(self, request: httpx.Request, path: str) -> httpx.Response:
        if request.headers.get("Authorization") != "Bearer admin-token":
            return httpx.Response(401)
        params = dict(request.url.params)
        if path == "/users" and request.method == "GET":
            users = list(self.users.values())
            if "username" in params:
                users = [u for u in users if u.username == params["username"]]
            if "email" in params:
                users = [u for u in users if u.email.lower() == params["email"].lower()]
            first, size = int(params.get("first", 0)), int(params.get("max", 100))
            return httpx.Response(200, json=[u.rep() for u in users[first:first + size]])
        if path == "/users" and request.method == "POST":
            body = json.loads(request.content)
            if self.by_username(body["username"]) or any(u.email == body["email"] for u in self.users.values()):
                return httpx.Response(409)
            user = self.add_user(body["username"], password=None, email=body["email"])
            user.attributes = body.get("attributes", {})
            return httpx.Response(201, headers={"Location": f"{request.url}/{user.id}"})
        if m := re.fullmatch(r"/roles/(\w+)", path):
            return httpx.Response(200, json={"id": m[1], "name": m[1]})
        m = re.fullmatch(r"/users/([^/]+)(/.*)?", path)
        user = self.users.get(m[1]) if m else None
        if user is None:
            return httpx.Response(404)
        action = m[2] or ""
        if action == "/role-mappings/realm":
            user.roles |= {r["name"] for r in json.loads(request.content)}
            return httpx.Response(204)
        if action == "/execute-actions-email":
            user.emails_sent += 1
            return httpx.Response(204)
        if action == "/logout":
            user.sessions_ended += 1
            self.refresh_tokens = {t: uid for t, uid in self.refresh_tokens.items() if uid != user.id}
            return httpx.Response(204)
        if action == "/reset-password":
            value = json.loads(request.content)["value"]
            if len(value) < 12:
                return httpx.Response(400, json={"error": "invalidPasswordMinLengthMessage"})
            user.password = value
            return httpx.Response(204)
        if action == "" and request.method == "GET":
            return httpx.Response(200, json=user.rep())
        if action == "" and request.method == "PUT":
            user.enabled = json.loads(request.content)["enabled"]
            return httpx.Response(204)
        return httpx.Response(405)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        oidc = f"{settings.keycloak_issuer}/protocol/openid-connect"
        admin = f"{settings.KEYCLOAK_URL}/admin/realms/{settings.KEYCLOAK_REALM}"
        if url == f"{oidc}/certs":
            return httpx.Response(200, json=self._jwks())
        if url == f"{oidc}/token":
            return self._grant({k: v[0] for k, v in parse_qs(request.content.decode()).items()})
        if url == f"{oidc}/logout":
            form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
            self.refresh_tokens.pop(form.get("refresh_token"), None)
            return httpx.Response(204)
        if request.url.path.startswith(httpx.URL(admin).path):
            return self._admin(request, request.url.path[len(httpx.URL(admin).path):])
        return httpx.Response(404)
