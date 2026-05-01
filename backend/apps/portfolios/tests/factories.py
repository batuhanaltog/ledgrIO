import factory
from factory.django import DjangoModelFactory
from apps.portfolios.models import Portfolio
from apps.users.tests.factories import UserFactory


class PortfolioFactory(DjangoModelFactory):
    class Meta:
        model = Portfolio

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Portfolio {n}")
    description = factory.Faker("sentence")
    currency = "USD"
    is_default = False
