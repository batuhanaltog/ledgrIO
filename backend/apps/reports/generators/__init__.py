from .csv_generator import CSVReportGenerator
from .pdf_generator import PDFReportGenerator

GENERATORS = {
    "CSV": CSVReportGenerator,
    "PDF": PDFReportGenerator,
}
