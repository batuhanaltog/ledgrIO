from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema_view, extend_schema

from .models import Budget
from .serializers import BudgetSerializer
from .alerts import compute_budget_status
from apps.transactions.models import Transaction


@extend_schema_view(
    list=extend_schema(tags=["Budgets"]),
    create=extend_schema(tags=["Budgets"]),
    retrieve=extend_schema(tags=["Budgets"]),
    update=extend_schema(tags=["Budgets"]),
    partial_update=extend_schema(tags=["Budgets"]),
    destroy=extend_schema(tags=["Budgets"]),
)
class BudgetViewSet(ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user, is_active=True).select_related("category")

    def _get_actual_spend(self, budget):
        today = timezone.now().date()
        if budget.period == Budget.Period.MONTHLY:
            period_start = today.replace(day=1)
        elif budget.period == Budget.Period.WEEKLY:
            period_start = today - timezone.timedelta(days=today.weekday())
        else:
            period_start = today

        return (
            Transaction.objects.filter(
                user=self.request.user,
                category=budget.category,
                transaction_type=Transaction.TransactionType.EXPENSE,
                transaction_date__gte=period_start,
            ).aggregate(total=Sum("amount"))["total"] or 0
        )

    @extend_schema(tags=["Budgets"])
    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        budget = self.get_object()
        actual_spend = self._get_actual_spend(budget)
        return Response(compute_budget_status(budget, actual_spend))

    @extend_schema(tags=["Budgets"])
    @action(detail=False, methods=["get"])
    def overview(self, request):
        budgets = self.get_queryset()
        result = []
        for budget in budgets:
            actual_spend = self._get_actual_spend(budget)
            result.append(compute_budget_status(budget, actual_spend))
        return Response(result)
