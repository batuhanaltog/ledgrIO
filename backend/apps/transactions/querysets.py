from django.db import connection


def get_running_balance(user_id: str) -> list[dict]:
    """
    Window Function: cumulative running balance per user ordered by transaction date.
    """
    sql = """
        SELECT
            id,
            transaction_date,
            transaction_type,
            amount,
            currency,
            SUM(
                CASE
                    WHEN transaction_type IN ('BUY', 'EXPENSE', 'TRANSFER') THEN -amount
                    ELSE amount
                END
            ) OVER (
                PARTITION BY user_id
                ORDER BY transaction_date, created_at
                ROWS UNBOUNDED PRECEDING
            ) AS running_balance
        FROM transactions
        WHERE user_id = %s
        ORDER BY transaction_date, created_at;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [str(user_id)])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_transaction_summary(user_id: str, date_from: str, date_to: str) -> list[dict]:
    """
    CTE: total amounts grouped by transaction_type and category for a date range.
    """
    sql = """
        WITH filtered AS (
            SELECT
                t.transaction_type,
                c.name AS category_name,
                t.currency,
                t.amount
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.user_id = %s
              AND t.transaction_date BETWEEN %s AND %s
        )
        SELECT
            transaction_type,
            category_name,
            currency,
            SUM(amount) AS total_amount,
            COUNT(*) AS transaction_count
        FROM filtered
        GROUP BY transaction_type, category_name, currency
        ORDER BY total_amount DESC;
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [str(user_id), date_from, date_to])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
