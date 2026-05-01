import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client):
    user = UserFactory()
    response = api_client.post(reverse("auth-login"), {"email": user.email, "password": "testpass123!"})
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    api_client.user = user
    return api_client


@pytest.mark.django_db
class TestRegisterView:
    def test_register_success(self, api_client):
        payload = {
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "first_name": "John",
            "last_name": "Doe",
        }
        response = api_client.post(reverse("auth-register"), payload)
        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["email"] == "new@example.com"

    def test_register_password_mismatch(self, api_client):
        payload = {
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "WrongPass123!",
        }
        response = api_client.post(reverse("auth-register"), payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client):
        UserFactory(email="existing@example.com")
        payload = {
            "email": "existing@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }
        response = api_client.post(reverse("auth-register"), payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLoginView:
    def test_login_success(self, api_client):
        user = UserFactory()
        response = api_client.post(reverse("auth-login"), {"email": user.email, "password": "testpass123!"})
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "user" in response.data

    def test_login_wrong_password(self, api_client):
        user = UserFactory()
        response = api_client.post(reverse("auth-login"), {"email": user.email, "password": "wrongpassword"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestProfileView:
    def test_get_profile(self, authenticated_client):
        response = authenticated_client.get(reverse("auth-profile"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == authenticated_client.user.email

    def test_update_profile(self, authenticated_client):
        response = authenticated_client.patch(reverse("auth-profile"), {"first_name": "Updated"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Updated"

    def test_profile_requires_auth(self, api_client):
        response = api_client.get(reverse("auth-profile"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
