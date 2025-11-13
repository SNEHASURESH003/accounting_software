from django.core.management.base import BaseCommand
from accounting_app.models import Account, Client

class Command(BaseCommand):
    help = "Sync all receivable accounts into clients"

    def handle(self, *args, **kwargs):
        count_created = 0
        count_skipped = 0

        for acc in Account.objects.filter(is_receivable=True):
            client, created = Client.objects.get_or_create(
                receivable_account=acc,
                defaults={
                    'name': acc.name,
                    'email': f"{acc.name.lower().replace(' ', '_')}@example.com"
                }
            )
            if created:
                count_created += 1
            else:
                count_skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"{count_created} clients created, {count_skipped} already existed."
        ))
