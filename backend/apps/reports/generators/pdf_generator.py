import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from .base import BaseReportGenerator
from apps.transactions.models import Transaction


class PDFReportGenerator(BaseReportGenerator):
    def generate(self) -> bytes:
        date_from, date_to = self.get_date_range()
        transactions = (
            Transaction.objects
            .filter(user=self.user, transaction_date__range=[date_from, date_to])
            .select_related("category")
            .order_by("transaction_date")[:500]
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("LedgrIO — Transaction Report", styles["Title"]))
        elements.append(Paragraph(f"Period: {date_from} to {date_to}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        data = [["Date", "Type", "Amount", "Currency", "Category"]]
        for tx in transactions:
            data.append([
                str(tx.transaction_date),
                tx.transaction_type,
                str(tx.amount),
                tx.currency,
                tx.category.name if tx.category else "—",
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)

        doc.build(elements)
        return buffer.getvalue()

    def get_filename(self) -> str:
        date_from, date_to = self.get_date_range()
        return f"ledgrio_report_{date_from}_{date_to}.pdf"
