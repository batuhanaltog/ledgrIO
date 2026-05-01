import pytest
from apps.users.models import User
from .factories import UserFactory


@pytest.mark.django_db
class TestUserModel:
    def test_create_user(self):
        user = UserFactory()
        assert user.pk is not None
        assert user.is_active is True
        assert user.is_staff is False

    def test_email_is_required(self):
        with pytest.raises(ValueError, match="Email is required"):
            User.objects.create_user(email="", password="pass")

    def test_full_name_with_both_names(self):
        user = UserFactory(first_name="John", last_name="Doe")
        assert user.full_name == "John Doe"

    def test_full_name_falls_back_to_email(self):
        user = UserFactory(first_name="", last_name="")
        assert user.full_name == user.email

    def test_str_returns_email(self):
        user = UserFactory(email="test@example.com")
        assert str(user) == "test@example.com"

    def test_create_superuser(self):
        user = User.objects.create_superuser(email="admin@example.com", password="adminpass")
        assert user.is_staff is True
        assert user.is_superuser is True

    def test_email_normalized(self):
        user = User.objects.create_user(email="Test@EXAMPLE.COM", password="pass")
        assert user.email == "Test@example.com"
