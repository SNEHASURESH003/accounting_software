# accounting_app/forms_procurement.py
from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth import get_user_model

from accounting_app.models_procurement import (
    PurchaseRequisition, PurchaseRequisitionLine,
    PurchaseOrder, PurchaseOrderLine,
    GoodsReceipt, GoodsReceiptLine,
    VendorBill, VendorBillLine, Vendor, Product
)
from accounting_app.models import Currency,Project, CostCenter, Account

User = get_user_model()


from django.db.models import Q

class PurchaseRequisitionForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequisition
        fields = ["number", "date", "project", "cost_center", "notes"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            allowed_users = get_allowed_users(user)

            # Restrict Project dropdown
            if "project" in self.fields:
                self.fields["project"].queryset = Project.objects.filter(
                    Q(owner__in=allowed_users) | Q(created_by__in=allowed_users)
                ).distinct()

            # Restrict CostCenter dropdown
            if "cost_center" in self.fields:
                self.fields["cost_center"].queryset = CostCenter.objects.filter(
                    Q(owner__in=allowed_users) | Q(created_by__in=allowed_users)
                ).distinct()

class PRLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequisitionLine
        fields = ["product", "description", "qty", "unit_price", "account"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # ✅ capture user
        super().__init__(*args, **kwargs)

        if user:
            allowed_users = get_allowed_users(user)

            # Restrict Product dropdown
            if "product" in self.fields:
                self.fields["product"].queryset = Product.objects.filter(
                    owner__in=allowed_users
                ).distinct()

            # Restrict Account dropdown
            if "account" in self.fields:
                self.fields["account"].queryset = Account.objects.filter(
                    owner__in=allowed_users
                ).distinct()

from django.forms import inlineformset_factory, BaseInlineFormSet

class BasePRLineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)   # ✅ capture user
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        """Inject `user` into each PRLineForm."""
        kwargs["user"] = self.user
        return super()._construct_form(i, **kwargs)

PRLineFormSet = inlineformset_factory(
    parent_model=PurchaseRequisition,
    model=PurchaseRequisitionLine,
    form=PRLineForm,
      formset=BasePRLineFormSet,# ✅ use custom form
    extra=1,
    can_delete=True,
)

from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet

from accounting_app.models_procurement import PurchaseOrder, PurchaseOrderLine, Product, Vendor
from accounting_app.models import Currency, Account, Project, CostCenter



class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            "number", "vendor", "currency", "exchange_rate",
            "order_date", "expected_date", "project", "cost_center", "notes"
        ]
        widgets = {
            "number": forms.TextInput(attrs={"class": "form-control"}),
            "vendor": forms.Select(attrs={"class": "form-select"}),
            "currency": forms.Select(attrs={"class": "form-select"}),
            "exchange_rate": forms.NumberInput(attrs={"class": "form-control"}),
            "order_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "expected_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "project": forms.Select(attrs={"class": "form-select"}),
            "cost_center": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # ✅ capture user
        super().__init__(*args, **kwargs)

        if user:
            allowed_users = get_allowed_users(user)

            # Restrict Vendor dropdown
            if "vendor" in self.fields:
                self.fields["vendor"].queryset = Vendor.objects.filter(
                    owner__in=allowed_users
                ).distinct()

            # Restrict Currency dropdown
            if "currency" in self.fields:
                self.fields["currency"].queryset = Currency.objects.filter(
                    created_by__in=allowed_users
                ).distinct()

            # Restrict Project dropdown
            if "project" in self.fields:
                self.fields["project"].queryset = Project.objects.filter(
                    owner__in=allowed_users
                ).distinct()

            # Restrict CostCenter dropdown
            if "cost_center" in self.fields:
                self.fields["cost_center"].queryset = CostCenter.objects.filter(
                    owner__in=allowed_users
                ).distinct()


class PurchaseOrderLineForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderLine
        fields = ["product", "description", "qty", "unit_price", "qty_received", "account"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "qty": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "qty_received": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "account": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # ✅ capture user
        super().__init__(*args, **kwargs)

        if user:
            allowed_users = get_allowed_users(user)

            # Restrict Product dropdown
            if "product" in self.fields:
                self.fields["product"].queryset = Product.objects.filter(
                    owner__in=allowed_users
                ).distinct()

            # Restrict Account dropdown
            if "account" in self.fields:
                self.fields["account"].queryset = Account.objects.filter(
                    owner__in=allowed_users
                ).distinct()


class BasePOLineFormSet(BaseInlineFormSet):
    """Custom FormSet to inject user into each line form."""
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs["user"] = self.user
        return super()._construct_form(i, **kwargs)


POLineFormSet = inlineformset_factory(
    parent_model=PurchaseOrder,
    model=PurchaseOrderLine,
    form=PurchaseOrderLineForm,
    formset=BasePOLineFormSet,
    extra=1,
    can_delete=True,
)

def get_allowed_users(user):
    allowed = [user]
    if user.is_superuser:
        # include all users this superuser created
        allowed.extend(user.created_users.all() if hasattr(user, "created_users") else [])
    else:
        # include their superuser creator
        if hasattr(user, "created_by") and user.created_by:
            allowed.append(user.created_by)
    return allowed

from django import forms
from .models_procurement import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["sku", "name", "uom", "default_price"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            # Example: restrict UOMs or other FK fields if needed
            if "uom" in self.fields and hasattr(self.fields["uom"], "queryset"):
                allowed_users = get_allowed_users(user)
                self.fields["uom"].queryset = self.fields["uom"].queryset.filter(
                    owner__in=allowed_users
                )
from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from accounting_app.models_procurement import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine


# ---- Goods Receipt Form ----
# ---- Goods Receipt Form ----
class GoodsReceiptForm(forms.ModelForm):
    class Meta:
        model = GoodsReceipt
        fields = ["number", "po", "date", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        qs = PurchaseOrder.objects.all()
        if user:
            allowed_users = get_allowed_users(user)
            if allowed_users:
                qs = qs.filter(owner__in=allowed_users)

        self.fields["po"].queryset = qs.distinct()


# ---- GRN Line Form ----
class GRNLineForm(forms.ModelForm):
    class Meta:
        model = GoodsReceiptLine
        fields = ["po_line", "qty_received"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        qs = PurchaseOrderLine.objects.all()
        if user:
            allowed_users = get_allowed_users(user)
            if allowed_users:
                qs = qs.filter(po__owner__in=allowed_users)

        # Filter PO lines only to the parent PO
        po_id = None
        if "po" in self.data:
            try:
                po_id = int(self.data.get("po"))
            except (ValueError, TypeError):
                pass
        elif self.instance and self.instance.pk and self.instance.po_line:
            po_id = self.instance.po_line.po_id
        elif self.initial.get("po"):
            po_id = self.initial["po"].id if hasattr(self.initial["po"], "id") else self.initial["po"]

        if po_id:
            qs = qs.filter(po_id=po_id)

        self.fields["po_line"].queryset = qs.distinct()


# ---- Formset ----
class BaseGRNLineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs["user"] = self.user
        return super()._construct_form(i, **kwargs)


GRNLineFormSet = inlineformset_factory(
    parent_model=GoodsReceipt,
    model=GoodsReceiptLine,
    form=GRNLineForm,
    formset=BaseGRNLineFormSet,
    extra=1,
    can_delete=True,
)



from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models_procurement import VendorBill, VendorBillLine, Vendor, PurchaseOrder
from accounting_app.models import Currency, Account
 # ✅ same helper you use in other forms


# ---- Vendor Bill Form ----
class VendorBillForm(forms.ModelForm):
    class Meta:
        model = VendorBill
        fields = ["number", "vendor", "po", "bill_date", "currency", "exchange_rate", "notes"]
        widgets = {
            "number": forms.TextInput(attrs={"class": "form-control"}),
            "vendor": forms.Select(attrs={"class": "form-select"}),
            "po": forms.Select(attrs={"class": "form-select"}),
            "bill_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "currency": forms.Select(attrs={"class": "form-select"}),
            "exchange_rate": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            allowed_users = get_allowed_users(user)

            # ✅ Restrict Vendor
            if "vendor" in self.fields:
                self.fields["vendor"].queryset = Vendor.objects.filter(
                    owner__in=allowed_users
                ).distinct()

            # ✅ Restrict PO
            if "po" in self.fields:
                self.fields["po"].queryset = PurchaseOrder.objects.filter(
                    owner__in=allowed_users
                ).distinct()

            # ✅ Restrict Currency
            if "currency" in self.fields:
                self.fields["currency"].queryset = Currency.objects.filter(
                    created_by__in=allowed_users
                ).distinct()


# ---- Vendor Bill Line Form ----
from .models_procurement import PurchaseOrderLine  # make sure you import it


class VendorBillLineForm(forms.ModelForm):
    class Meta:
        model = VendorBillLine
        fields = ["po_line", "description", "qty", "unit_price", "tax_amount", "account"]
        widgets = {
            "po_line": forms.Select(attrs={"class": "form-select"}),
            "description": forms.TextInput(attrs={"class": "form-control"}),
            "qty": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "tax_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "account": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        selected_po = kwargs.pop("selected_po", None)  # 👈 optional for better narrowing
        super().__init__(*args, **kwargs)

        if user:
            allowed_users = get_allowed_users(user)

            # ✅ Restrict Account
            if "account" in self.fields:
                self.fields["account"].queryset = Account.objects.filter(
                    owner__in=allowed_users
                ).distinct()

            # ✅ Restrict PO lines (use PurchaseOrderLine, not VendorBillLine)
            if "po_line" in self.fields:
                qs = PurchaseOrderLine.objects.filter(po__owner__in=allowed_users)

                # if a PO is already chosen, narrow lines to that PO
                if selected_po:
                    qs = qs.filter(po=selected_po)

                self.fields["po_line"].queryset = qs.distinct()



# ---- Formset with user injection ----
class BaseVendorBillLineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs["user"] = self.user
        return super()._construct_form(i, **kwargs)


VendorBillLineFormSet = inlineformset_factory(
    parent_model=VendorBill,
    model=VendorBillLine,
    form=VendorBillLineForm,
    formset=BaseVendorBillLineFormSet,
    extra=1,
    can_delete=True,
)


from django import forms
from accounting_app.models_procurement import Vendor
from accounting_app.models import Currency
from django.contrib.auth import get_user_model
from django.db.models import Q

def get_allowed_users(user):
    """
    Returns a list of users the current user is allowed to see:
    - Superuser: themselves + all users they created
    - Accountant: themselves + their superuser creator
    """
    allowed = [user]

    if user.is_superuser:
        # assuming you have a reverse relation `created_users`
        created_users = getattr(user, "created_users", None)
        if created_users:
            allowed.extend(created_users.all())
    else:
        # If the user has a superuser creator
        superuser_creator = getattr(user, "created_by", None)
        if superuser_creator:
            allowed.append(superuser_creator)

    return allowed


 # assuming you have this helper



class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "email", "gstin", "address", "currency", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "gstin": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "currency": forms.Select(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        # Capture current user
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            allowed_users = get_allowed_users(user)

            if user.is_superuser:
                # Superuser sees currencies they created + all other superusers’ currencies if needed
                self.fields["currency"].queryset = Currency.objects.filter(
                    created_by__in=allowed_users
                ).distinct()
            elif getattr(user, "role", "").lower() == "accountant":
                # Accountant sees only currencies created by themselves or their superuser
                self.fields["currency"].queryset = Currency.objects.filter(
                    created_by__in=allowed_users
                ).distinct()
            else:
                # Other users see no options
                self.fields["currency"].queryset = Currency.objects.none()
