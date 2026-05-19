from pathlib import Path

from django.core.management.base import BaseCommand

from core.services.reports.program_report import generate_program_report_pdf, mock_program_report_data


class Command(BaseCommand):
    help = "Generate a mock Program Outcome Report PDF for report design review."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="reports/mock-program-outcome-report.pdf",
            help="Output PDF path, relative to the backend project root unless absolute.",
        )

    def handle(self, *args, **options):
        output = Path(options["output"])
        if not output.is_absolute():
            output = Path.cwd() / output
        output.parent.mkdir(parents=True, exist_ok=True)

        pdf_bytes = generate_program_report_pdf(mock_program_report_data())
        output.write_bytes(pdf_bytes)

        self.stdout.write(self.style.SUCCESS(f"Generated mock program report: {output}"))
