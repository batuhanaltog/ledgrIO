from django.contrib import admin
from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ["symbol", "name", "asset_type", "quantity", "current_price", "portfolio"]
    list_filter = ["asset_type", "currency"]
    search_fields = ["symbol", "name"]
    raw_id_fields = ["portfolio"]
