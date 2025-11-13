# accounting_app/apps.py
from django.apps import AppConfig

class AccountingAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounting_app"

    def ready(self):
        # Import things that must run after apps are loaded.
        # Keep these inside try/except to avoid boot loops while cleaning.
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
        # Optional: global scoping patch if you use it
        try:
            from . import scoping_patch  # noqa: F401
        except Exception:
            pass
