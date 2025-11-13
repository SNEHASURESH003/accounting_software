

def update_invoice_total(invoice):
    from accounting_app.models import Invoice
    item_total = sum(item.quantity * item.unit_price for item in invoice.items.all())
    time_total = sum(te.hours * te.rate_per_hour for te in invoice.time_entries.all())
    invoice.total_amount = item_total + time_total
    invoice.save(update_fields=['total_amount'])
    
    

def compliance_check(entry):
    """
    Apply standard IND-AS / IFRS validation rules
    """
    warnings = []
    
    if entry.project and entry.date > entry.project.end_date:
        warnings.append("Date occurs after project end date (IND-AS 10).")

    if entry.account.account_type == 'Liability' and entry.amount == 0:
        warnings.append("Zero liability recorded (Check IND-AS 37).")
    
    if entry.account.account_type == 'Revenue' and entry.date is None:
        warnings.append("Missing date of revenue recognition (IFRS 15).")

    return warnings


from django.db.models import Sum, F
from datetime import date
from accounting_app.helpers import get_actuals_for_month
def generate_forecast_variance():
    
    from accounting_app.models import Forecast, ForecastVariance
    ForecastVariance.objects.all().delete()  # Optional: clean slate

    for forecast in Forecast.objects.all():
        project = forecast.project
        month = forecast.month
        year = forecast.year

        actuals = get_actuals_for_month(project, month, year)
        actual_amount = actuals['income'] - actuals['expenses']

        ForecastVariance.objects.create(
            project=project,
            account=forecast.account,
            forecast=forecast,
            actual_amount=actual_amount
        )

# from datetime import date as _date
# from django.db.models import Q
# from accounting_app.models import LockPeriod  # your existing model

# def is_date_locked(date_obj):
#     if not isinstance(date_obj, _date):
#         return False
#     return LockPeriod.objects.filter(
#         Q(start_date__lte=date_obj) & Q(end_date__gte=date_obj)
#     ).exists()
    
    
    
# accounting_app/utils.py
from datetime import date as _date
from django.core.exceptions import ValidationError


def period_key(date_obj: _date) -> tuple[int, int]:
    return (date_obj.year, date_obj.month)

def is_date_locked(date_obj: _date) -> bool:
    from .models import AccountingPeriod
    y, m = period_key(date_obj)
    try:
        p = AccountingPeriod.objects.get(year=y, month=m)
        return p.status == AccountingPeriod.STATUS_LOCKED
    except AccountingPeriod.DoesNotExist:
        # default: not locked unless a period row says so
        return False

def require_open_period(date_obj: _date):
    if is_date_locked(date_obj):
        raise ValidationError("This date falls in a locked accounting period.")

from django.db.models import Sum

def get_total_net_salary(employee):
    from .models import Payroll
    return Payroll.objects.filter(name=employee).aggregate(total=Sum('net_salary'))['total'] or 0

# accounting_app/utils.py

from datetime import date, datetime

def convert_dates(obj):
    """Recursively convert date/datetime objects to ISO strings."""
    if isinstance(obj, dict):
        return {k: convert_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_dates(i) for i in obj]
    elif isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj

from django.utils.timezone import now
from django.core.management import call_command


def check_monthly_report():
    today = now().date()
    first_day = today.replace(day=1)
    from accounting_app.models import ScheduledTask
    task, created = ScheduledTask.objects.get_or_create(name='monthly_report')

    # If task hasn't run this month
    if not task.last_run or task.last_run.date() < first_day:
        print("Running scheduled monthly report...")
        call_command('send_monthly_report')  # Your custom mgmt command
        task.last_run = now()
        task.save()

# utils.py

def get_client_info(request):
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    ip = ip.split(',')[0] if ip else None
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    return ip, user_agent


# core/utils.py
from django.contrib.contenttypes.models import ContentType


def add_model_message(obj, text, *, level='info', user=None):
    ct = ContentType.objects.get_for_model(obj.__class__)
    from accounting_app.models import ModelMessage
    return ModelMessage.objects.create(
        content_type=ct,
        object_id=str(obj.pk),
        text=text,
        level=level,
        created_by=user,
    )



# app/utils/arith.py
from decimal import Decimal

D0 = Decimal("0.00")

def as_decimal(val, default=D0):
    if val is None:
        return default
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except Exception:
        return default

def total_with_tax_decimal(invoice):
    twt = getattr(invoice, "total_with_tax", None)
    val = twt() if callable(twt) else twt
    return as_decimal(val, D0)

# app/utils/ar_account.py
from .models import Account

def get_ar_account():
    # Tweak to match your Account fields
    acc, _ = Account.objects.get_or_create(
        name="Accounts Receivable",
        defaults={"account_type": "Asset"},
    )
    return acc


from datetime import date, timedelta

def aging_bucket(due: date, today: date) -> str:
    """Return one of: current, d1_30, d31_60, d61_90, d90_plus."""
    days = (today - due).days
    if days <= 0:   return "current"
    if days <= 30:  return "d1_30"
    if days <= 60:  return "d31_60"
    if days <= 90:  return "d61_90"
    return "d90_plus"

# You can tweak these lags to match your collection pattern
BUCKET_LAG_DAYS = {
    "current":  15,
    "d1_30":    30,
    "d31_60":   45,
    "d61_90":   60,
    "d90_plus": 90,
}

def expected_collection_date(due: date, today: date) -> date:
    """Shift due date by an aging-based lag → expected cash receipt date."""
    from .utils import aging_bucket, BUCKET_LAG_DAYS  # safe import if moved
    bucket = aging_bucket(due, today)
    return due + timedelta(days=BUCKET_LAG_DAYS[bucket])



# utils.py
from .models import Employee

def get_employee_queryset_for_user(user):
    """
    Returns the restricted Employee queryset for the logged-in user
    (superuser sees only their own, accountant sees only their superuser’s).
    """
    if user.is_superuser:
        return Employee.objects.filter(owner=user)
    else:
        return Employee.objects.filter(owner=user.owner)
    
    


