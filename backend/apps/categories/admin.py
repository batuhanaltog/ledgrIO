from __future__ import annotations

from django.contrib import admin

from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_system", "owner", "parent", "ordering")
    list_filter = ("is_system",)
    search_fields = ("name",)
