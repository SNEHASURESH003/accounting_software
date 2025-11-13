from django.apps import apps as django_apps
from django.db import models
from django.db.models import ForeignKey
try:
    from .scoping import ScopedManager
except Exception:
    ScopedManager = None

def _apply():
    if ScopedManager is None:
        return
    for model in django_apps.get_models():
        if model._meta.abstract or model._meta.proxy:
            continue
        if getattr(model, "_scoped_manager_patched", False):
            continue
        try:
            field = model._meta.get_field("owner")
        except Exception:
            continue
        if isinstance(field, ForeignKey):
            if not hasattr(model, "unscoped"):
                model.add_to_class("unscoped", models.Manager())
            model.add_to_class("objects", ScopedManager())
            model._scoped_manager_patched = True

_apply()
