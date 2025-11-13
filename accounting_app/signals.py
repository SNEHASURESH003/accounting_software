# # utils.py (or a signals.py file)


    
# # signals.py

# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import InvoiceItem, TimeEntry,Invoice, JournalItem, Project, Client, TaxRecord, Payroll
# from .utils import update_invoice_total

# @receiver(post_save, sender=InvoiceItem)
# def update_total_on_invoice_item_save(sender, instance, **kwargs):
#     update_invoice_total(instance.invoice)

# @receiver(post_save, sender=TimeEntry)
# def update_total_on_time_entry_save(sender, instance, **kwargs):
#     update_invoice_total(instance.invoice)


# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from django.contrib.contenttypes.models import ContentType
# from .models import AuditLog
# from django.utils.timezone import now

# def log_change(instance, user, action):
#     AuditLog.objects.create(
#         user=user,
#         action=action,
#         model_name=instance.__class__.__name__,
#         object_id=str(instance.pk),
#         change_message=f"{action} at {now()}"
#     )

# @receiver(post_save)
# def model_save_audit(sender, instance, created, **kwargs):
#     from django.contrib.auth.models import User
#     if sender in [Invoice, JournalItem, Project, Client, TaxRecord, Payroll]:
#         user = getattr(instance, 'modified_by', None) or getattr(instance, 'created_by', None)
#         action = 'created' if created else 'updated'
#         log_change(instance, user, action)

# @receiver(post_delete)
# def model_delete_audit(sender, instance, **kwargs):
#     if sender in [Invoice, JournalItem, Project, Client, TaxRecord, Payroll]:
#         user = getattr(instance, 'modified_by', None)
#         log_change(instance, user, 'deleted')

# # from .models import ComplianceLog
# # @receiver(post_save, sender=Invoice)
# # def log_invoice_creation(sender, instance, created, **kwargs):
# #     if created:
# #         ComplianceLog.objects.create(
# #             content_type=ContentType.objects.get_for_model(instance),
# #             object_id=instance.pk,  # ✅ Now it exists
# #             action='created',
# #             indas_code='IND-AS 115',
# #             ifrs_code='IFRS 15',
# #             user=instance.created_by if hasattr(instance, 'created_by') else None,
# #             description=f"Invoice #{instance.id} created for client {instance.client}."
# #         )


# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import Project, Budget, Account

# @receiver(post_save, sender=Project)
# def create_budget_for_project(sender, instance, created, **kwargs):
#     if created and instance.budget and instance.start_date:
#         account = Account.objects.first()  # or logic to get right one
#         # Prevent duplicate
#         if not Budget.objects.filter(project=instance).exists():
#             Budget.objects.create(
#                 name=f"{instance.name}",
#                 year=instance.start_date.year,
#                 month=instance.start_date.month,
#                 amount=instance.budget,
#                 account=account,
#                 project=instance
#             )

# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
# from django.utils.timezone import now
# from .models import AuditLog
# from django.contrib.auth import get_user_model

# User = get_user_model()

# from accounting_app.middleware import get_current_user  # Import this
# def get_request_user():
#     return get_current_user()


# @receiver(post_save)
# def log_model_save(sender, instance, created, **kwargs):
#     if sender.__name__ == 'AuditLog': return
#     AuditLog.objects.create(
#         user=get_request_user(),
#         action='CREATE' if created else 'UPDATE',
#         model_name=sender.__name__,
#         object_id=str(instance.pk),
#         change_message=f"{'Created' if created else 'Updated'} {sender.__name__} #{instance.pk}"
#     )

# @receiver(post_delete)
# def log_model_delete(sender, instance, **kwargs):
#     if sender.__name__ == 'AuditLog': return
#     AuditLog.objects.create(
#         user=get_request_user(),
#         action='DELETE',
#         model_name=sender.__name__,
#         object_id=str(instance.pk),
#         change_message=f"Deleted {sender.__name__} #{instance.pk}"
#     )


# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.contrib.auth import get_user_model
# from .models import Employee

# User = get_user_model()

# @receiver(post_save, sender=User)
# def create_employee_profile(sender, instance, created, **kwargs):
#     if created and getattr(instance, 'role', None) == 'Employee':
#         if not hasattr(instance, 'employee'):
#             Employee.objects.create(
#                 user=instance,
#                 name=instance.email.split('@')[0].title(),
#                 email=instance.email,
#                 is_contractor=False  # designation and department will use defaults
#             )


from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from .models import UserActivityLog
from django.contrib.auth.models import User

def get_client_info(request):
    ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
    if ip and ',' in ip:
        ip = ip.split(',')[0]
    ua = request.META.get('HTTP_USER_AGENT', '')
    return ip, ua

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip, ua = get_client_info(request)
    UserActivityLog.objects.create(user=user, action='login', ip_address=ip, user_agent=ua)

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    ip, ua = get_client_info(request)
    UserActivityLog.objects.create(user=user, action='logout', ip_address=ip, user_agent=ua)
from django.contrib.auth import get_user_model

User = get_user_model()

# @receiver(user_login_failed)
# def log_failed_login(sender, credentials, request, **kwargs):
#     ip, ua = get_client_info(request)
#     email = credentials.get('email')
#     user = User.objects.filter(email=email).first() if email else None
#     UserActivityLog.objects.create(user=user, action='failed_login', ip_address=ip, user_agent=ua)
# signals.py
from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from .models import UserActivityLog

import logging
logger = logging.getLogger(__name__)

@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    logger.warning(f"FAILED LOGIN credentials={credentials}")

    attempted_username = (
        credentials.get("email")
        or credentials.get("username")
        or next(iter(credentials.values()), None)
    )

    UserActivityLog.objects.create(
        action="failed_login",
        attempted_username=attempted_username,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )

    
# signals.py
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Employee

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_employee_exists(sender, instance, created, **kwargs):
    if instance.role != "Employee":
        return
    try:
        instance.employee
    except Employee.DoesNotExist:
        Employee.objects.create(
            user=instance,
            name=(f"{instance.first_name} {instance.last_name}".strip()
                  or instance.email.split("@")[0].title()),
            email=instance.email,
        )
# finance/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import date
from decimal import Decimal
from .models import Forecast, Budget

@receiver(post_save, sender=Forecast)
def create_or_update_budget_from_forecast(sender, instance, **kwargs):
    """Ensure budgets are always in sync with forecasts."""
    year = instance.year
    month = getattr(instance, 'month', None)

    Budget.objects.update_or_create(
        project=instance.project,
        account=instance.account,
        year=year,
        month=month,
        defaults={
            'name': f"Auto from Forecast {year}-{month or ''}",
            'period_type': 'monthly' if month else 'annual',
            'amount': instance.forecast_amount or Decimal('0.00'),
        }
    )
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils.timezone import now
def get_client_ip(request):
    # Try to get the client IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    UserActivityLog.objects.create(
        user=user,
        action='login',
        timestamp=now(),
        ip_address=ip,
        user_agent=user_agent
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    if user:
        UserActivityLog.objects.create(
            user=user,
            action='logout',
            timestamp=now(),
            ip_address=ip,
            user_agent=user_agent
        )

@receiver(user_login_failed)
def log_user_failed_login(sender, credentials, request, **kwargs):
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
    UserActivityLog.objects.create(
        user=None,  # Because no user object on failed login
        action='failed_login',
        timestamp=now(),
        ip_address=ip,
        user_agent=user_agent
    )


from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import Account


# ------------------------------
# 1. When Account is deleted → delete linked Client
# ------------------------------
@receiver(post_delete, sender=Account)
def delete_client_when_account_deleted(sender, instance, **kwargs):
    if instance.client:
        print(f"[Signal] Deleting Client {instance.client.name} because Account was deleted")
        instance.client.delete()


# ------------------------------
# 2. When Account is updated → if is_receivable goes from True → False, delete Client
# ------------------------------
@receiver(pre_save, sender=Account)
def delete_client_if_receivable_removed(sender, instance, **kwargs):
    if not instance.pk:
        return  # skip new Accounts

    try:
        old = Account.objects.get(pk=instance.pk)
    except Account.DoesNotExist:
        return

    # Detect toggle from True -> False
    if old.is_receivable and not instance.is_receivable and old.client:
        print(f"[Signal] Deleting Client {old.client.name} because is_receivable was turned off")
        old.client.delete()







# app/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Invoice
from .forecast_from_invoices import sync_ar_to_forecast

@receiver([post_save, post_delete], sender=Invoice)
def refresh_ar_forecast_on_invoice_change(*args, **kwargs):
    # Recompute AR forecast whenever an invoice is added/updated/deleted
    sync_ar_to_forecast()

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from accounting_app.models import Invoice
from .forecast_from_invoices import rebuild_cash_forecast_from_unpaid_invoices

@receiver(post_save, sender=Invoice)
def _invoice_saved(sender, instance, **kwargs):
    rebuild_cash_forecast_from_unpaid_invoices()

@receiver(post_delete, sender=Invoice)
def _invoice_deleted(sender, instance, **kwargs):
    rebuild_cash_forecast_from_unpaid_invoices()


# core/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .middleware import get_current_user

@receiver(pre_save)
def _autofill_owner(sender, instance, **kwargs):
    # Only act on models that actually have an 'owner' field
    if not hasattr(instance, "owner_id"):
        return
    if instance.owner_id:
        return
    user = get_current_user()
    if user and user.is_authenticated:
        instance.owner = user
