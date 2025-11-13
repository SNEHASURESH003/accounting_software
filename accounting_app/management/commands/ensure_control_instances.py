from datetime import date
from django.core.management.base import BaseCommand
from accounting_app.models import ControlTask, ControlTaskInstance

class Command(BaseCommand):
    help = "Ensure ControlTaskInstance rows exist for the current period."

    def handle(self, *args, **opts):
        today = date.today()
        y, m = today.year, today.month
        created = 0
        for task in ControlTask.objects.filter(active=True).select_related("owner"):
            # For MONTHLY and QUARTERLY cadences we materialize month-based instances.
            # Extend here for WEEKLY/DAILY if needed.
            period_month = m if task.cadence in ("MONTHLY", "QUARTERLY") else None
            _, was_created = ControlTaskInstance.objects.get_or_create(
                task=task, period_year=y, period_month=period_month
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Ensured instances. Created: {created}"))
