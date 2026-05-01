from __future__ import annotations

from typing import ClassVar

from rest_framework import serializers

from .models import Category


class CategoryFlatSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source="owner.id", allow_null=True, read_only=True)

    class Meta:
        model = Category
        fields: ClassVar = [
            "id",
            "name",
            "icon",
            "color",
            "is_system",
            "owner_id",
            "parent_id",
            "ordering",
            "created_at",
        ]
        read_only_fields: ClassVar = ["id", "is_system", "owner_id", "created_at"]


class CategoryWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    parent_id = serializers.IntegerField(allow_null=True, required=False, default=None)
    icon = serializers.CharField(max_length=50, allow_blank=True, required=False, default="")
    color = serializers.CharField(max_length=7, allow_blank=True, required=False, default="")
    ordering = serializers.IntegerField(required=False, default=0)
