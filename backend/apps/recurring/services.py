from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, cast

from django.db import transaction as db_transaction

from apps.recurring.models import RecurringTemplate
from common.exceptions import RecurringTemplateInvalidError, RecurringTemplateNotFoundError


def create_recurring_template(
    *,
    user: Any,
    type: str,
    amount: Decimal,
    currency_code: str,
    account_id: int,
    category_id: int | None,
    description: str,
    frequency: str,
    day_of_period: int,
    start_date: date,
    end_date: date | None = None,
) -> RecurringTemplate:
    from apps.accounts.models import Account

    try:
        account = Account.objects.get(pk=account_id, user=user)
    except Account.DoesNotExist:
        raise RecurringTemplateInvalidError(
            f"Account {account_id} not found or does not belong to this user."
        ) from None

    if account.currency_code != currency_code:
        raise RecurringTemplateInvalidError(
            f"Template currency '{currency_code}' does not match account currency "
            f"'{account.currency_code}'."
        )

    return cast(RecurringTemplate, RecurringTemplate.objects.create(
        user=user,
        type=type,
        amount=amount,
        currency_code=currency_code,
        account=account,
        category_id=category_id,
        description=description,
        frequency=frequency,
        day_of_period=day_of_period,
        start_date=start_date,
        end_date=end_date,
    ))


def update_recurring_template(
    *, template: RecurringTemplate, **fields: Any
) -> RecurringTemplate:
    from apps.accounts.models import Account

    # Resolve account if account_id is changing so we can validate currency match.
    new_account: Any = None
    if "account_id" in fields:
        try:
            new_account = Account.objects.get(pk=fields["account_id"], user=template.user)
        except Account.DoesNotExist:
            raise RecurringTemplateInvalidError(
                f"Account {fields['account_id']} not found or does not belong to this user."
            ) from None

    effective_currency = fields.get("currency_code", template.currency_code)
    effective_account_currency = (
        new_account.currency_code if new_account is not None else template.account.currency_code
    )
    if effective_currency != effective_account_currency:
        raise RecurringTemplateInvalidError(
            f"Template currency '{effective_currency}' does not match account currency "
            f"'{effective_account_currency}'."
        )

    # Scheduling changes invalidate the last_generated_date idempotency key.
    if "frequency" in fields or "day_of_period" in fields:
        template.last_generated_date = None

    if new_account is not None:
        template.account = new_account
        fields.pop("account_id")

    for attr, value in fields.items():
        setattr(template, attr, value)

    template.save()
    return template


def soft_delete_recurring_template(*, template: RecurringTemplate) -> None:
    template.soft_delete()


def compute_next_due_date(
    *,
    template: RecurringTemplate,
    after_date: date | None = None,
) -> date | None:
    """
    Pure function — no DB writes. Returns the next date this template should
    generate a Transaction, or None if no such date exists.
    """
    if not template.is_active:
        return None

    if after_date is not None:
        reference = after_date
    elif template.last_generated_date is not None:
        reference = template.last_generated_date
    else:
        # One day before start_date so that start_date itself is a candidate.
        reference = template.start_date - timedelta(days=1)

    next_due: date | None = _advance_from(
        reference=reference,
        frequency=template.frequency,
        day_of_period=template.day_of_period,
    )

    if next_due is None:
        return None

    if next_due < template.start_date:
        return None

    if template.end_date is not None and next_due > template.end_date:
        return None

    return next_due


def _advance_from(
    *,
    reference: date,
    frequency: str,
    day_of_period: int,
) -> date | None:
    """Return the next occurrence strictly after *reference*."""
    if frequency == "weekly":
        # day_of_period: 1 = Monday, ..., 7 = Sunday (ISO weekday)
        ref_weekday = reference.isoweekday()  # 1–7
        days_ahead = day_of_period - ref_weekday
        if days_ahead <= 0:
            days_ahead += 7
        return reference + timedelta(days=days_ahead)

    if frequency == "monthly":
        # Try the target day in the same month first, then next month.
        year, month = reference.year, reference.month
        clamped_day = min(day_of_period, calendar.monthrange(year, month)[1])
        candidate = date(year, month, clamped_day)
        if candidate <= reference:
            # Move to next month.
            if month == 12:
                year, month = year + 1, 1
            else:
                month += 1
            clamped_day = min(day_of_period, calendar.monthrange(year, month)[1])
            candidate = date(year, month, clamped_day)
        return candidate

    if frequency == "yearly":
        # day_of_period is day-of-year (1–366).
        year = reference.year
        candidate = _day_of_year_to_date(year, day_of_period)
        if candidate <= reference:
            candidate = _day_of_year_to_date(year + 1, day_of_period)
        return candidate

    return None


def _day_of_year_to_date(year: int, day_of_year: int) -> date:
    """Convert a 1-indexed day-of-year to a date, clamping for leap-year edge cases."""
    max_day = 366 if calendar.isleap(year) else 365
    clamped = min(day_of_year, max_day)
    return date(year, 1, 1) + timedelta(days=clamped - 1)


@db_transaction.atomic
def materialize_template_for_date(
    *, template: RecurringTemplate, target_date: date
) -> Any:
    """
    Idempotent. Creates the Transaction for *target_date* and updates
    last_generated_date. Returns None if generation is skipped for any reason.
    """
    if not template.is_active:
        return None

    if target_date < template.start_date:
        return None

    if template.end_date is not None and target_date > template.end_date:
        return None

    if (
        template.last_generated_date is not None
        and template.last_generated_date >= target_date
    ):
        return None

    from apps.transactions.services import create_transaction

    transaction = create_transaction(
        user=template.user,
        account=template.account,
        type=template.type,
        amount=template.amount,
        currency_code=template.currency_code,
        category_id=template.category_id,
        date=target_date,
        description=template.description,
        reference="",
    )

    template.last_generated_date = target_date
    template.save(update_fields=["last_generated_date"])

    return transaction
