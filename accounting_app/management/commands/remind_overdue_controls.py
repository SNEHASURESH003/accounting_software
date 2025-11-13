from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail  # configure EMAIL settings to actually send
from django.conf import settings
from accounting_app.models import ControlTaskInstance

class Command(BaseCommand):
    help = "Notify owners about overdue or pending control instances."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Print instead of sending emails")

    def handle(self, *args, **opts):
        today = date.today()
        pending = ControlTaskInstance.objects.filter(completed=False)

        # If you maintain due_date, consider only overdue: .filter(due_date__lt=today)
        count = 0
        for inst in pending.select_related("task", "task__owner"):
            owner = inst.task.owner
            if not owner or not owner.email:
                continue
            subject = f"[Controls] Pending: {inst.task.title} ({inst.period_year}-{inst.period_month or '--'})"
            body = (
                f"Hello {owner.get_full_name() or owner.username},\n\n"
                f"The following control is pending:\n"
                f" - Task: {inst.task.title}\n"
                f" - Period: {inst.period_year}-{inst.period_month or '--'}\n\n"
                f"Please mark it complete in the Controls Dashboard."
            )
            if opts["dry_run"]:
                self.stdout.write(f"Would email {owner.email}: {subject}")
            else:
                send_mail(subject, body,
                          getattr(settings, "DEFAULT_FROM_EMAIL", None),
                          [owner.email], fail_silently=True)
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Reminders processed: {count}"))
