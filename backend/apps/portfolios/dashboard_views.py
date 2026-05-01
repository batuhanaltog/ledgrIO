from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.portfolios.models import Portfolio
from apps.transactions.models import Transaction
from apps.budgets.models import Budget
from apps.notifications.models import Notification


@extend_schema(tags=["Dashboard"])
class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        month_start = today.replace(day=1)

        portfolios = Portfolio.objects.filter(user=user).prefetch_related("assets")
        total_value = sum(
            float(asset.quantity * asset.current_price)
            for p in portfolios
            for asset in p.assets.all()
        )

        monthly_expenses = (
            Transaction.objects.filter(
                user=user,
                transaction_type=Transaction.TransactionType.EXPENSE,
                transaction_date__gte=month_start,
            ).aggregate(total=Sum("amount"))["total"] or 0
        )

        recent_transactions = (
            Transaction.objects.filter(user=user)
            .select_related("category", "asset")
            .order_by("-transaction_date", "-created_at")[:5]
        )

        unread_notifications = Notification.objects.filter(user=user, is_read=False).count()

        from apps.transactions.serializers import TransactionListSerializer
        return Response({
            "net_worth": round(total_value, 2),
            "currency": user.currency,
            "monthly_expenses": float(monthly_expenses),
            "portfolio_count": portfolios.count(),
            "recent_transactions": TransactionListSerializer(recent_transactions, many=True).data,
            "unread_notifications": unread_notifications,
        })
