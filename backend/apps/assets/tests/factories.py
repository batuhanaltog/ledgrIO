import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
from apps.assets.models import Asset
from apps.portfolios.tests.factories import PortfolioFactory


class AssetFactory(DjangoModelFactory):
    class Meta:
        model = Asset

    portfolio = factory.SubFactory(PortfolioFactory)
    name = factory.Faker("company")
    symbol = factory.Sequence(lambda n: f"SYM{n}")
    asset_type = Asset.AssetType.STOCK
    quantity = Decimal("10.00000000")
    average_cost = Decimal("100.00000000")
    current_price = Decimal("110.00000000")
    currency = "USD"
