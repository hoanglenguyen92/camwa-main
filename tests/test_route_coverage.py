from fastapi.routing import APIRoute

from backend.core.deps import get_principal
from main import API_PREFIX, ROUTERS, app

PUBLIC = {
    ("GET", API_PREFIX),
    ("POST", f"{API_PREFIX}/auth/login"),
    ("POST", f"{API_PREFIX}/auth/refresh"),
    ("POST", f"{API_PREFIX}/auth/password-reset"),
}


def _routes():
    # include_router mounts routers lazily in FastAPI 0.162, so walk each controller's own router.
    for controller in ROUTERS:
        for route in controller.router.routes:
            for method in route.methods:
                yield method, f"{API_PREFIX}{route.path}", route
    for route in app.router.routes:
        if isinstance(route, APIRoute):
            for method in route.methods:
                yield method, route.path, route


def _calls(dependant):
    for dep in dependant.dependencies:
        yield dep.call
        yield from _calls(dep)


def test_every_route_requires_a_principal_unless_public():
    unguarded = []
    for method, path, route in _routes():
        if get_principal not in set(_calls(route.dependant)) and (method, path) not in PUBLIC:
            unguarded.append(f"{method} {path}")
    assert unguarded == []


def test_routes_are_in_openapi():
    paths = app.openapi()["paths"]
    for method, path, _ in _routes():
        assert method.lower() in paths.get(path, {}), f"{method} {path}"
