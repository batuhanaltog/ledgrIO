import django_filters
from .models import Transaction


class TransactionFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="transaction_date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="transaction_date", lookup_expr="lte")
    portfolio = django_filters.UUIDFilter(field_name="portfolio__id")
    category = django_filters.UUIDFilter(field_name="category__id")
    transaction_type = django_filters.ChoiceFilter(choices=Transaction.TransactionType.choices)
    min_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="gte")
    max_amount = django_filters.NumberFilter(field_name="amount", lookup_expr="lte")

    class Meta:
        model = Transaction
        fields = ["date_from", "date_to", "portfolio", "category", "transaction_type", "min_amount", "max_amount"]
