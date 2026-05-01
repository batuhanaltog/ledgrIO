import pytest
from decimal import Decimal
from .factories import AssetFactory


@pytest.mark.django_db
class TestAssetModel:
    def test_create_asset(self):
        asset = AssetFactory()
        assert asset.pk is not None

    def test_str(self):
        asset = AssetFactory(symbol="AAPL", asset_type="STOCK")
        assert "AAPL" in str(asset)

    def test_current_value(self):
        asset = AssetFactory(quantity=Decimal("5"), current_price=Decimal("200"))
        assert asset.current_value == Decimal("1000")

    def test_unrealized_pnl_profit(self):
        asset = AssetFactory(quantity=Decimal("10"), average_cost=Decimal("100"), current_price=Decimal("150"))
        assert asset.unrealized_pnl == Decimal("500")

    def test_unrealized_pnl_loss(self):
        asset = AssetFactory(quantity=Decimal("10"), average_cost=Decimal("100"), current_price=Decimal("80"))
        assert asset.unrealized_pnl == Decimal("-200")
