from datetime import date
from calendar import monthrange
from django.core.management.base import BaseCommand
from accounting_app.models import AccountingPeriod

def prev_year_month(y, m):
    return (y - 1, 12) if m == 1 else (y, m - 1)

class Command(BaseCommand):
    help = "Lock last month and ensure current month period exists and is open."

    def handle(self, *args, **opts):
        today = date.today()
        y, m = today.year, today.month
        py, pm = prev_year_month(y, m)

        # Ensure previous period exists and lock it
        prev_period, _ = AccountingPeriod.objects.get_or_create(year=py, month=pm)
        if prev_period.lock():
            self.stdout.write(self.style.SUCCESS(f"Locked {py}-{pm:02d}"))
        else:
            self.stdout.write(f"Already locked {py}-{pm:02d}")

        # Ensure current period exists and is OPEN
        curr, _ = AccountingPeriod.objects.get_or_create(year=y, month=m)
        if curr.status != AccountingPeriod.STATUS_OPEN:
            curr.unlock()
            self.stdout.write(self.style.SUCCESS(f"Opened {y}-{m:02d}"))
        else:
            self.stdout.write(f"Already open {y}-{m:02d}")
