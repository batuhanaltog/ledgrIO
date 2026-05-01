from django.db import models
from common.models import TimestampedModel


class Asset(TimestampedModel):
    class AssetType(models.TextChoices):
        STOCK = "STOCK", "Stock"
        CRYPTO = "CRYPTO", "Cryptocurrency"
        CASH = "CASH", "Cash"
        OTHER = "OTHER", "Other"

    portfolio = models.ForeignKey("portfolios.Portfolio", on_delete=models.CASCADE, related_name="assets")
    name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=20)
    asset_type = models.CharField(max_length=10, choices=AssetType.choices, default=AssetType.OTHER)
    quantity = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    average_cost = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    current_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    currency = models.CharField(max_length=3, default="USD")
    last_price_update = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "assets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["portfolio"]),
            models.Index(fields=["symbol", "asset_type"]),
        ]

    def __str__(self):
        return f"{self.symbol} ({self.asset_type})"

    @property
    def current_value(self):
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self):
        return (self.current_price - self.average_cost) * self.quantity
