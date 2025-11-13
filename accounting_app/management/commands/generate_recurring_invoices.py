from django.core.management.base import BaseCommand
from datetime import timedelta, date
from accounting_app.models import Invoice, InvoiceItem, TimeEntry

def get_next_date(current_date, interval):
    if interval == 'monthly':
        return current_date.replace(day=1) + timedelta(days=32)
    elif interval == 'quarterly':
        return current_date + timedelta(days=90)
    elif interval == 'yearly':
        return current_date + timedelta(days=365)
    return None

class Command(BaseCommand):
    help = 'Generate recurring invoices'

    def handle(self, *args, **kwargs):
        today = date.today()
        recurring_invoices = Invoice.objects.filter(is_recurring=True)

        for invoice in recurring_invoices:
            last_date = invoice.last_generated or invoice.date
            next_due = get_next_date(last_date, invoice.recurring_interval)
            if not next_due or next_due > today:
                continue

            # Clone invoice
            new_invoice = Invoice.objects.create(
                client=invoice.client,
                date=today,
                due_date=today + timedelta(days=7),
                currency=invoice.currency,
                exchange_rate=invoice.exchange_rate,
                gst_percent=invoice.gst_percent,
                is_recurring=False,  # Don't repeat the clone
                template_style=invoice.template_style,
                notes=invoice.notes
            )

            # Copy items
            for item in invoice.items.all():
                InvoiceItem.objects.create(
                    invoice=new_invoice,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price
                )

            # Copy time entries
            for te in invoice.time_entries.all():
                TimeEntry.objects.create(
                    invoice=new_invoice,
                    description=te.description,
                    hours=te.hours,
                    rate_per_hour=te.rate_per_hour
                )

            # Update the original invoice’s last_generated
            invoice.last_generated = today
            invoice.save()

            self.stdout.write(self.style.SUCCESS(f'Created recurring invoice #{new_invoice.pk} for {invoice.client}'))
