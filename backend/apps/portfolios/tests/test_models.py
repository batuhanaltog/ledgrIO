import pytest
from .factories import PortfolioFactory


@pytest.mark.django_db
class TestPortfolioModel:
    def test_create_portfolio(self):
        portfolio = PortfolioFactory()
        assert portfolio.pk is not None
        assert portfolio.is_default is False

    def test_str(self):
        portfolio = PortfolioFactory(name="My Portfolio")
        assert "My Portfolio" in str(portfolio)

    def test_only_one_default_per_user(self):
        p1 = PortfolioFactory(is_default=True)
        p2 = PortfolioFactory(user=p1.user, is_default=True)
        p1.refresh_from_db()
        assert p1.is_default is False
        assert p2.is_default is True

    def test_default_flag_isolated_per_user(self):
        p1 = PortfolioFactory(is_default=True)
        p2 = PortfolioFactory(is_default=True)  # different user
        p1.refresh_from_db()
        assert p1.is_default is True
        assert p2.is_default is True
