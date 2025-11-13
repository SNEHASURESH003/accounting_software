from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now
from django.conf import settings
from django.contrib.auth import get_user_model
from accounting_project.middleware.current_user import get_current_user

from .models import AuditLog, Invoice, Project, JournalItem,Client,TaxRecord,Payroll # Adjust as needed

User = get_user_model()  # ✅ Load actual user model

def get_user_from_instance(instance):
    return getattr(instance, 'modified_by', None) or getattr(instance, 'user', None)

@receiver(post_save)
def log_model_save(sender, instance, created, **kwargs):
    if sender in [Invoice, Project, JournalItem,Client,TaxRecord,Payroll]:
        action = 'created' if created else 'updated'
        user = get_user_from_instance(instance) or get_current_user()

      
        AuditLog.objects.create(
            user=user if user else User.objects.filter(is_superuser=True).first(),  # ✅ FIXED
            action=action,
            model_name=sender.__name__,
            object_id=str(instance.pk),
            change_message=f"{sender.__name__} {action} at {now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    if sender in [Invoice, Project, JournalItem,Client,TaxRecord,Payroll]:
        user = get_user_from_instance(instance)
        AuditLog.objects.create(
            user=user if user else User.objects.filter(is_superuser=True).first(),  # ✅ FIXED
            action='deleted',
            model_name=sender.__name__,
            object_id=str(instance.pk),
            change_message=f"{sender.__name__} deleted at {now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
