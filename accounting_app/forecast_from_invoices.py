from collections import defaultdict
from decimal import Decimal
from datetime import date
from django.db import transaction
from django.utils.timezone import now
from accounting_app.models import Invoice, Forecast
from .utils import expected_collection_date

BASE_RATE = Decimal("1")

def _invoice_amount_base(inv) -> Decimal:
    """total_with_tax * exchange_rate → Decimal(2)."""
    twt = getattr(inv, "total_with_tax", None)
    amt = twt() if callable(twt) else twt
    if amt is None:
        amt = Decimal("0")
    elif not isinstance(amt, Decimal):
        amt = Decimal(str(amt))
    rate = getattr(inv, "exchange_rate", None) or BASE_RATE
    return (amt * Decimal(str(rate))).quantize(Decimal("0.01"))

@transaction.atomic
def rebuild_cash_forecast_from_unpaid_invoices(today=None):
    """
    Build monthly cash forecast from UNPAID invoices:
      - figure expected collection date from aging
      - group by (project, year, month)
      - replace prior [AUTO-INVOICE] rows
    """
    today = today or now().date()

    # 1) Group unpaid invoices into (project, year, month) → amount
    buckets = defaultdict(Decimal)
    qs = Invoice.objects.select_related("project", "client").filter(status="unpaid")
    for inv in qs:
        if not inv.due_date:  # safety
            continue
        coll_date = expected_collection_date(inv.due_date, today)
        key = (getattr(inv, "project_id", None), coll_date.year, coll_date.month)
        buckets[key] += _invoice_amount_base(inv)

    # 2) Remove prior auto-generated rows
    Forecast.objects.filter(notes__startswith="[AUTO-INVOICE]").delete()

    # 3) Upsert new rows
    for (project_id, year, month), amt in buckets.items():
        Forecast.objects.update_or_create(
            project_id=project_id,
            account=None,                 # keep AR account null or set to your AR account
            year=year,
            month=month,
            notes="[AUTO-INVOICE] Unpaid invoices (aging-based expected collection)",
            defaults={"forecast_amount": amt},
        )
