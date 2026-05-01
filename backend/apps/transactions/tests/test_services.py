from __future__ import annotations

import pytest

from apps.transactions.models import Transaction


@pytest.mark.django_db
def test_transaction_model_exists():
    fields = {f.name for f in Transaction._meta.get_fields()}
    assert "amount" in fields
    assert "amount_base" in fields
    assert "fx_rate_snapshot" in fields
    assert "currency_code" in fields
    assert "type" in fields
    assert "category" in fields
    assert "deleted_at" in fields
