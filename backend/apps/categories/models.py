from __future__ import annotations

from typing import ClassVar

from django.contrib.auth import get_user_model
from django.db import models

from common.models import SoftDeleteModel, TimestampedModel

User = get_user_model()

MAX_CATEGORY_DEPTH = 10


class Category(TimestampedModel, SoftDeleteModel):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    owner = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    is_system = models.BooleanField(default=False)
    ordering = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "categories"
        indexes: ClassVar = [
            models.Index(fields=["owner"]),
            models.Index(fields=["is_system"]),
        ]

    def __str__(self) -> str:
        return self.name
