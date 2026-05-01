"""Reusable abstract base models."""
from __future__ import annotations

from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    """Adds created_at and updated_at to a model."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    """Queryset helpers — usable on both `objects` (alive only) and `all_objects` (everything)."""

    def alive(self) -> SoftDeleteQuerySet:
        return self.filter(deleted_at__isnull=True)

    def dead(self) -> SoftDeleteQuerySet:
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):  # type: ignore[misc]
    """Default manager that hides soft-deleted rows.

    Consumers MUST query through this manager (`.objects`) for normal flows.
    Auditing / admin / restore flows should use `.all_objects` (defined on the
    model) which returns every row, deleted or not.
    """

    def get_queryset(self) -> SoftDeleteQuerySet:
        qs: SoftDeleteQuerySet = super().get_queryset().filter(deleted_at__isnull=True)
        return qs


class SoftDeleteModel(models.Model):
    """Adds soft-delete semantics. Use `objects` for live rows, `all_objects` for everything."""

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager.from_queryset(SoftDeleteQuerySet)()

    class Meta:
        abstract = True
        base_manager_name = "all_objects"  # FK reverse lookups must see deleted rows

    def soft_delete(self) -> None:
        if self.deleted_at is None:
            self.deleted_at = timezone.now()
            self.save(update_fields=["deleted_at"])

    def restore(self) -> None:
        if self.deleted_at is not None:
            self.deleted_at = None
            self.save(update_fields=["deleted_at"])
