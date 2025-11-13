from django.core.management.base import BaseCommand
from accounting_app.models import Invoice, Payment, EmployeeExpense
from django.template.loader import get_template
from django.core.mail import EmailMessage
from django.utils.timezone import now
from xhtml2pdf import pisa
from io import BytesIO


class Command(BaseCommand):
    help = 'Send monthly summary report as a PDF attachment'

    def handle(self, *args, **kwargs):
        today = now().date()
        month = today.strftime('%B')
        year = today.year

        invoice_count = Invoice.objects.filter(date__year=year, date__month=today.month).count()
        payment_count = Payment.objects.filter(date__year=year, date__month=today.month).count()
        expense_count = EmployeeExpense.objects.filter(date__year=year, date__month=today.month).count()

        # Render HTML to PDF
        template = get_template('reports/monthly_summary_pdf.html')
        html = template.render({
            'month': month,
            'year': year,
            'invoice_count': invoice_count,
            'payment_count': payment_count,
            'expense_count': expense_count,
        })

        pdf_file = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_file)

        if pisa_status.err:
            self.stderr.write("❌ Failed to generate PDF.")
            return

        pdf_file.seek(0)

        # Send the email with PDF attachment
        email = EmailMessage(
            subject=f"📈 Monthly Summary Report – {month} {year}",
            body="Please find attached the monthly summary report in PDF format.",
            from_email="snehasuresh98723@gmail.com",
            to=["snehasureshinventuratech@gmail.com"]
        )
        email.attach(f"Monthly_Report_{month}_{year}.pdf", pdf_file.read(), "application/pdf")
        email.send()

        self.stdout.write("✅ Monthly summary PDF email sent.")
