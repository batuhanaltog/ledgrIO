import csv
import io
from .base import BaseReportGenerator
from apps.transactions.models import Transaction


class CSVReportGenerator(BaseReportGenerator):
    def generate(self) -> bytes:
        date_from, date_to = self.get_date_range()
        transactions = (
            Transaction.objects
            .filter(user=self.user, transaction_date__range=[date_from, date_to])
            .select_related("category", "asset", "portfolio")
            .order_by("transaction_date")
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Date", "Type", "Amount", "Currency", "Category",
            "Portfolio", "Asset", "Fee", "Notes",
        ])
        for tx in transactions:
            writer.writerow([
                tx.transaction_date,
                tx.transaction_type,
                tx.amount,
                tx.currency,
                tx.category.name if tx.category else "",
                tx.portfolio.name if tx.portfolio else "",
                tx.asset.symbol if tx.asset else "",
                tx.fee,
                tx.notes,
            ])

        return output.getvalue().encode("utf-8-sig")

    def get_filename(self) -> str:
        date_from, date_to = self.get_date_range()
        return f"ledgrio_transactions_{date_from}_{date_to}.csv"
