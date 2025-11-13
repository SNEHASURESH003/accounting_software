from django.db import models
from .middleware import get_current_user  # if you used the thread-local middleware

class ScopedManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        user = get_current_user()

        if not user or not user.is_authenticated:
            return qs.none()

        if getattr(user, "is_superadmin", False):
            return qs

        if getattr(user, "is_superuser", False) and not getattr(user, "is_superadmin", False):
            # Only apply if model has an 'owner' field
            if "owner" in {f.name for f in self.model._meta.get_fields()}:
                return qs.filter(owner=user)

        return qs

