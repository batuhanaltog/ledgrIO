from django.db import models, connection
from decimal import Decimal


class PortfolioQuerySet(models.QuerySet):

    def for_user(self, user):
        return self.filter(user=user)

    def with_asset_count(self):
        return self.annotate(asset_count=models.Count("assets"))

    def with_total_value(self):
        return self.annotate(
            total_value=models.Sum(
                models.F("assets__quantity") * models.F("assets__current_price"),
                output_field=models.DecimalField(max_digits=20, decimal_places=8),
            )
        )


def get_portfolio_allocation(portfolio_id: str) -> list[dict]:
    """
    CTE query: per-asset allocation percentage within a portfolio.
    Returns list of {symbol, current_value, allocation_pct}.
    """
    sql = """
        WITH portfolio_values AS (
            SELECT
                a.id,
                a.symbol,
                a.name,
                a.asset_type,
                a.quantity * a.current_price AS current_value
            FROM assets a
            WHERE a.portfolio_id = %s
        ),
        total AS (
            SELECT COALESCE(SUM(current_value), 0) AS total_value
            FROM portfolio_values
        )
        SELECT
            pv.id,
            pv.symbol,
            pv.name,
            pv.asset_type,
            pv.current_value,
            CASE
                WHEN t.total_value = 0 THEN 0
                ELSE ROUND(pv.current_value / t.total_value * 100, 2)
            END AS allocation_pct
        FROM portfolio_values pv, total t
        ORDER BY pv.current_value DESC;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [str(portfolio_id)])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_portfolio_performance(portfolio_id: str, date_from: str, date_to: str) -> list[dict]:
    """
    CTE query: daily portfolio value over time for performance line chart.
    """
    sql = """
        WITH daily_transactions AS (
            SELECT
                t.transaction_date,
                SUM(
                    CASE
                        WHEN t.transaction_type IN ('BUY', 'INCOME', 'DIVIDEND') THEN t.amount
                        WHEN t.transaction_type IN ('SELL', 'EXPENSE') THEN -t.amount
                        ELSE 0
                    END
                ) AS daily_net
            FROM transactions t
            WHERE t.portfolio_id = %s
              AND t.transaction_date BETWEEN %s AND %s
            GROUP BY t.transaction_date
        ),
        cumulative AS (
            SELECT
                transaction_date,
                daily_net,
                SUM(daily_net) OVER (
                    ORDER BY transaction_date
                    ROWS UNBOUNDED PRECEDING
                ) AS cumulative_value
            FROM daily_transactions
        )
        SELECT transaction_date, cumulative_value
        FROM cumulative
        ORDER BY transaction_date;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [str(portfolio_id), date_from, date_to])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
