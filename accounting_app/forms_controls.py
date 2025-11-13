# accounting_app/forms_controls.py
from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction

# If your models live in models_controls.py (as in your code):
from accounting_app.models import ControlTask, ControlArea

User = get_user_model()

# ---- Defaults you asked to seed ----
DEFAULT_CONTROL_AREAS = [
    "General Ledger (GL)", "Cash & Bank / Treasury", "Accounts Payable (AP)",
    "Accounts Receivable (AR)", "Revenue & Billing", "Projects & Cost Centers",
    "Budgeting & Forecasting", "Tax Compliance (GST/TDS)", "Payroll & Statutory",
    "Intercompany", "Compliance & Audit", "FX / Exchange Rates",
]

def ensure_default_control_areas():
    """
    Seed default ControlArea rows only if none exist.
    Kept idempotent: if table already has rows, does nothing.
    """
    if ControlArea.objects.exists():
        return
    with transaction.atomic():
        for name in DEFAULT_CONTROL_AREAS:
            ControlArea.objects.get_or_create(name=name)


from django import forms
from .models import ControlTask, ControlArea, User


from django import forms
from django.contrib.auth import get_user_model
from .models import ControlTask, ControlArea


User = get_user_model()


class ControlTaskForm(forms.ModelForm):
    area = forms.ModelChoiceField(
        queryset=ControlArea.objects.none(),
        required=False,
        empty_label="— Select area —",
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Control area",
    )
    owner = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by("email"),
        required=False,
        empty_label="— Unassigned —",
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Owner",
    )

    class Meta:
        model = ControlTask
        fields = ["area", "title", "description", "cadence", "owner", "active"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "cadence": forms.Select(attrs={"class": "form-control"}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Ensure control areas exist
        ensure_default_control_areas()

        self.fields["area"].queryset = ControlArea.objects.all().order_by("name")
        self.fields["area"].required = True
        self.fields["owner"].required = True

        # --- Filter owner dropdown ---
        if user:
            if getattr(user, "is_superadmin", False):
                allowed_users = User.objects.all()
            elif user.is_superuser:
                allowed_users = [user] + list(user.created_users.all())
            else:
                superuser = getattr(user, "owner", None)
                allowed_users = [user]
                if superuser:
                    allowed_users.append(superuser)

            self.fields["owner"].queryset = User.objects.filter(id__in=[u.id for u in allowed_users])
