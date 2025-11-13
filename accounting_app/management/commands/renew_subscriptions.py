from django.core.management.base import BaseCommand
from accounting_app.views import renew_subscriptions

class Command(BaseCommand):
    help = 'Renew all subscriptions and generate invoices if needed'

    def handle(self, *args, **kwargs):
        renew_subscriptions()
        self.stdout.write(self.style.SUCCESS("✅ Subscriptions renewed."))

from django.core.management.base import BaseCommand
from accounting_app.views import renew_subscriptions

class Command(BaseCommand):
    help = 'Renew all due subscriptions and generate invoices'

    def handle(self, *args, **kwargs):
        renew_subscriptions()
        self.stdout.write(self.style.SUCCESS("✅ Subscriptions renewed."))
