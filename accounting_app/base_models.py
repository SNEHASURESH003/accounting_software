from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from .versioning import VersionHistory
from decimal import Decimal
from decimal import Decimal
from datetime import date, datetime

class VersionedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True, null=True, blank=True)  # <-- changed

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Get the content type for the model instance
        content_type = ContentType.objects.get_for_model(self.__class__)

        # Get latest version number for this object (or 0 if none exists)
        last_version = VersionHistory.objects.filter(
            content_type=content_type,
            object_id=self.pk
        ).order_by('-version_number').first()

        next_version = last_version.version_number + 1 if last_version else 1

        # Serialize model instance to JSON-safe dict
        data = model_to_dict(self)
        data = self.clean_for_json(data)  # ✅ convert Decimal to float

        # Save version history
        VersionHistory.objects.create(
            content_type=content_type,
            object_id=self.pk,
            version_number=next_version,
            data=data
        )

    @staticmethod
    def clean_for_json(data):
     if isinstance(data, dict):
        return {k: VersionedModel.clean_for_json(v) for k, v in data.items()}
     elif isinstance(data, list):
        return [VersionedModel.clean_for_json(i) for i in data]
     elif isinstance(data, Decimal):
        return float(data)
     elif isinstance(data, (date, datetime)):
        return data.isoformat()
     return data
