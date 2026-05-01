"""Currency catalog and historical FX snapshots."""
from __future__ import annotations

from typing import ClassVar

from django.core.exceptions import ValidationError
from django.db import models

from apps.users.models import CURRENCY_CODE_VALIDATOR


class Currency(models.Model):
    """ISO-4217 (or pseudo-ISO for crypto) currency definition."""

    code = models.CharField(
        primary_key=True,
        max_length=3,
        validators=[CURRENCY_CODE_VALIDATOR],
    )
    name = models.CharField(max_length=64)
    symbol = models.CharField(max_length=8, blank=True)
    decimal_places = models.PositiveSmallIntegerField(
        default=2,
        help_text="Display precision (e.g. 2 for USD, 8 for BTC).",
    )
    is_crypto = models.BooleanField(default=False)

    class Meta:
        db_table = "currencies_currency"
        ordering = ("code",)
        verbose_name_plural = "currencies"

    def __str__(self) -> str:
        return self.code


class FxRate(models.Model):
    """Daily FX snapshot — one row per (base, quote, date).

    Storing rates flat instead of FK-to-Currency keeps inserts cheap and
    avoids cascading deletes from currency catalog edits.
    """

    base_code = models.CharField(max_length=3, validators=[CURRENCY_CODE_VALIDATOR])
    quote_code = models.CharField(max_length=3, validators=[CURRENCY_CODE_VALIDATOR])
    rate = models.DecimalField(max_digits=20, decimal_places=8)
    rate_date = models.DateField(db_index=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "currencies_fxrate"
        ordering = ("-rate_date", "base_code", "quote_code")
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=("base_code", "quote_code", "rate_date"),
                name="uniq_fx_pair_date",
            ),
            models.CheckConstraint(
                check=~models.Q(base_code=models.F("quote_code")),
                name="fx_base_quote_differ",
            ),
        ]
        indexes: ClassVar[list] = [
            models.Index(fields=("base_code", "quote_code", "-rate_date")),
        ]

    def __str__(self) -> str:
        return f"{self.base_code}->{self.quote_code} @ {self.rate_date}: {self.rate}"

    def clean(self) -> None:
        super().clean()
        if self.base_code == self.quote_code:
            raise ValidationError({"quote_code": "Base and quote currencies must differ."})
