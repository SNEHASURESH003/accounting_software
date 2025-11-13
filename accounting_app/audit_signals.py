# core/audit_signals.py
import json
from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.apps import apps
from .models import AuditLog
from .middleware import get_current_user

EXCLUDE_APPS  = {"contenttypes","sessions","admin","auth"}  # tweak as you like
EXCLUDE_MODELS= {AuditLog}  # avoid recursion

def _model_name(instance):
    return f"{instance._meta.app_label}.{instance._meta.model_name}"

def _should_log(instance):
    if instance.__class__ in EXCLUDE_MODELS: return False
    if instance._meta.app_label in EXCLUDE_APPS: return False
    return True

def _serialize(obj):
    try:
        return model_to_dict(obj)
    except Exception:
        # fallback (e.g. unmanaged models)
        return {}

@receiver(post_save)
def audit_save(sender, instance, created, **kwargs):
    if not _should_log(instance): 
        return
    user = get_current_user()
    model = _model_name(instance)
    pk = str(getattr(instance, "pk", None))

    if created:
        AuditLog.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            model_name=model,
            object_id=pk,
            object_repr=str(instance),
            action="create",
            change_message=json.dumps({"new": _serialize(instance)}),
        )
    else:
        # compute diff vs DB
        try:
            old = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            old = None
        old_dict = _serialize(old) if old else {}
        new_dict = _serialize(instance)
        diff = {k: [old_dict.get(k), new_dict.get(k)]
                for k in new_dict.keys()
                if old_dict.get(k) != new_dict.get(k)}
        AuditLog.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            model_name=model,
            object_id=pk,
            object_repr=str(instance),
            action="update",
            change_message=json.dumps({"diff": diff}),
        )

@receiver(pre_delete)
def audit_delete(sender, instance, **kwargs):
    if not _should_log(instance): 
        return
    user = get_current_user()
    AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        model_name=_model_name(instance),
        object_id=str(getattr(instance, "pk", None)),
        object_repr=str(instance),
        action="delete",
        change_message=json.dumps({"old": _serialize(instance)}),
    )

@receiver(m2m_changed)
def audit_m2m(sender, instance, action, reverse, model, pk_set, **kwargs):
    # sender is the through model; instance is one side
    if not _should_log(instance): 
        return
    if action not in {"post_add","post_remove","post_clear"}:
        return
    user = get_current_user()
    field_name = sender._meta.model_name
    AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        model_name=_model_name(instance),
        object_id=str(getattr(instance, "pk", None)),
        object_repr=str(instance),
        action="m2m",
        change_message=json.dumps({
            "field": field_name,
            "op": action,
            "ids": list(pk_set) if pk_set else [],
        }),
    )
