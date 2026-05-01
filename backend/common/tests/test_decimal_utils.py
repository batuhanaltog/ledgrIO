import pytest
from decimal import Decimal
from common.utils.decimal_utils import money_round, safe_divide, percentage, ZERO


class TestMoneyRound:
    def test_rounds_half_up(self):
        assert money_round(Decimal("0.005")) == Decimal("0.01")

    def test_rounds_half_up_negative(self):
        assert money_round(Decimal("-0.005")) == Decimal("-0.01")

    def test_rounds_to_8_places(self):
        result = money_round(Decimal("1.123456789"), places=8)
        assert result == Decimal("1.12345679")

    def test_accepts_string(self):
        assert money_round("10.555") == Decimal("10.56")

    def test_accepts_float(self):
        assert money_round(10.1) == Decimal("10.10")

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            money_round("not_a_number")

    def test_exact_amount_unchanged(self):
        assert money_round(Decimal("100.00")) == Decimal("100.00")


class TestSafeDivide:
    def test_normal_division(self):
        result = safe_divide(Decimal("10"), Decimal("4"))
        assert result == Decimal("2.5")

    def test_zero_denominator_returns_default(self):
        assert safe_divide(Decimal("10"), ZERO) == ZERO

    def test_custom_default(self):
        result = safe_divide(Decimal("10"), ZERO, default=Decimal("-1"))
        assert result == Decimal("-1")


class TestPercentage:
    def test_basic_percentage(self):
        assert percentage(Decimal("50"), Decimal("100")) == Decimal("50.00")

    def test_zero_total_returns_zero(self):
        assert percentage(Decimal("50"), ZERO) == ZERO

    def test_over_100_percent(self):
        assert percentage(Decimal("150"), Decimal("100")) == Decimal("150.00")

    def test_custom_decimal_places(self):
        result = percentage(Decimal("1"), Decimal("3"), places=4)
        assert result == Decimal("33.3333")
