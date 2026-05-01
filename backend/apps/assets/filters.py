import django_filters
from .models import Asset


class AssetFilter(django_filters.FilterSet):
    portfolio = django_filters.UUIDFilter(field_name="portfolio__id")
    asset_type = django_filters.ChoiceFilter(choices=Asset.AssetType.choices)
    symbol = django_filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = Asset
        fields = ["portfolio", "asset_type", "symbol"]
