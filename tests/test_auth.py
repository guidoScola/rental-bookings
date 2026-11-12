import pytest

from tests.conftest import TEST_PASSWORD


def login(client, username, password):
    return client.post("/login", json={"username": username, "password": password})


def test_protected_routes_require_login(anon_client):
    assert anon_client.get("/bookings").status_code == 401
    assert anon_client.get("/apartments").status_code == 401
    assert anon_client.post("/bookings", json={}).status_code == 401


def test_health_is_public(anon_client):
    assert anon_client.get("/health").status_code == 200


def test_login_gives_access(anon_client, user):
    response = login(anon_client, "test-owner", TEST_PASSWORD)

    assert response.status_code == 204
    assert anon_client.get("/bookings").status_code == 200


@pytest.mark.parametrize(
    ("username", "password"),
    [("test-owner", "wrong-password"), ("nobody", TEST_PASSWORD)],
)
def test_wrong_credentials_give_the_same_error(anon_client, user, username, password):
    response = login(anon_client, username, password)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"
    assert anon_client.get("/bookings").status_code == 401


def test_logout_removes_access(anon_client, user):
    login(anon_client, "test-owner", TEST_PASSWORD)

    assert anon_client.post("/logout").status_code == 204
    assert anon_client.get("/bookings").status_code == 401


def test_password_is_stored_hashed(user):
    assert user.password_hash != TEST_PASSWORD
    assert user.password_hash.startswith("$2b$")  # bcrypt format
