from __future__ import annotations

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.categories.tests.factories import CategoryFactory, SystemCategoryFactory
from apps.users.tests.factories import UserFactory


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    client.user = user
    return client


@pytest.mark.django_db
def test_list_categories_tree_includes_system_and_own(auth_client):
    system = SystemCategoryFactory(name="Food")
    own = CategoryFactory(owner=auth_client.user, name="MyFood")
    other = CategoryFactory(name="OtherFood")  # different user

    resp = auth_client.get("/api/v1/categories/")
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert system.id in ids
    assert own.id in ids
    assert other.id not in ids


@pytest.mark.django_db
def test_list_categories_flat_format(auth_client):
    SystemCategoryFactory(name="Food")
    CategoryFactory(owner=auth_client.user, name="MyFood")

    resp = auth_client.get("/api/v1/categories/?format=flat")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert "parent_id" in resp.json()[0]


@pytest.mark.django_db
def test_create_category(auth_client):
    resp = auth_client.post(
        "/api/v1/categories/",
        {"name": "Travel", "icon": "✈️", "color": "#2196F3", "ordering": 1},
        format="json",
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Travel"
    assert data["is_system"] is False


@pytest.mark.django_db
def test_update_own_category(auth_client):
    cat = CategoryFactory(owner=auth_client.user, name="Old")
    resp = auth_client.patch(
        f"/api/v1/categories/{cat.id}/",
        {"name": "New"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


@pytest.mark.django_db
def test_update_system_category_forbidden(auth_client):
    system = SystemCategoryFactory()
    resp = auth_client.patch(
        f"/api/v1/categories/{system.id}/",
        {"name": "Hacked"},
        format="json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_delete_own_category(auth_client):
    cat = CategoryFactory(owner=auth_client.user)
    resp = auth_client.delete(f"/api/v1/categories/{cat.id}/")
    assert resp.status_code == 204
    cat.refresh_from_db()
    assert cat.deleted_at is not None


@pytest.mark.django_db
def test_delete_system_category_forbidden(auth_client):
    system = SystemCategoryFactory()
    resp = auth_client.delete(f"/api/v1/categories/{system.id}/")
    assert resp.status_code == 403


@pytest.mark.django_db
def test_unauthenticated_request_rejected(db):
    client = APIClient()
    resp = client.get("/api/v1/categories/")
    assert resp.status_code == 401
