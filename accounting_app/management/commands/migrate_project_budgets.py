from django.core.management.base import BaseCommand
from accounting_app.models import Project, Account, Budget


class Command(BaseCommand):
    help = "Migrate project budgets into Budget model"

    def handle(self, *args, **kwargs):
        account = Account.objects.first()
        if not account:
            self.stderr.write("No account found. Please create an Account first.")
            return

        count = 0
        for project in Project.objects.all():
            if project.budget and project.start_date:
                # Avoid duplicate entries
                exists = Budget.objects.filter(project=project, month=project.start_date.month, year=project.start_date.year).exists()
                if exists:
                    continue

                Budget.objects.create(
                    name=f"Auto - {project.name}",
                    year=project.start_date.year,
                    month=project.start_date.month,
                    amount=project.budget,
                    account=account,
                    project=project
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Migrated {count} project budgets."))
