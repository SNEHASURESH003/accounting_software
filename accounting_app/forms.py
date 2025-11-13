from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from .models import User
from django.contrib.auth.models import Group
from django import forms
from .models import JournalEntry, JournalItem, TimeEntry
from django.forms.models import inlineformset_factory
from .models import Account  # Ensure this is imported

from django import forms
from .models import Invoice, InvoiceItem, Client
from django.forms import modelformset_factory

from .models import Project,TaxDeclaration,FilingRecord



from django import forms
from django.contrib.auth.forms import AuthenticationForm

class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email',
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
        })
    )

 
 

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django import forms
from .models import Employee  # update with your actual app name

User = get_user_model()

class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=[('Accountant', 'Accountant'), ('Employee', 'Employee')])

    class Meta:
        model = User
        fields = ['email', 'password', 'role','first_name','last_name']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password':forms.PasswordInput(attrs={'class': 'form-control'}),
            
        
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'groups': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = self.cleaned_data['role']
        # user.is_staff = True  # So they can log in

        if commit:
          user.save()
          role = self.cleaned_data['role']
          group, _ = Group.objects.get_or_create(name=role)
          user.groups.add(group)

    # ❌ Do NOT create Employee manually here — let signal handle it

        return user



from django import forms
from .models import JournalItem

from django import forms
from django.forms import inlineformset_factory
from .models import JournalItem, JournalEntry, ProjectStage
from django import forms
from django.forms import inlineformset_factory
from .models import JournalEntry, JournalItem, ProjectStage

from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from .models import JournalEntry, JournalItem, Project, ProjectStage


# JournalItemForm


    

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from .models import JournalEntry, JournalItem, ProjectStage, Account, Currency


class JournalItemForm(forms.ModelForm):
    class Meta:
        model = JournalItem
        fields = [
            'account', 'debit', 'credit', 'description',
            'project', 'stage', 'currency'
        ]

    def __init__(self, *args, **kwargs):
        project = kwargs.pop("project", None)
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # --- Initialize project from instance if editing ---
        instance_project = getattr(self.instance, "project", None)
        if instance_project and not self.initial.get('project'):
            self.initial['project'] = instance_project

        # --- Filter stage field based on project ---
        project_to_use = project or instance_project
        if project_to_use:
            self.fields["stage"].queryset = ProjectStage.objects.filter(project=project_to_use)
        else:
            self.fields["stage"].queryset = ProjectStage.objects.none()

        # --- Require project ---
        self.fields["project"].required = True
        self.fields["project"].label = "Project (Required)"

        # --- Filter accounts for this user ---
        if user:
            self.fields["account"].queryset = Account.objects.filter(owner=user)

        # --- All currencies ---
        self.fields["currency"].queryset = Currency.objects.all()



class BaseJournalItemFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop("project", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["project"] = self.project
        kwargs["user"] = self.user
        return kwargs


JournalItemFormSet = inlineformset_factory(
    JournalEntry,
    JournalItem,
    form=JournalItemForm,
    formset=BaseJournalItemFormSet,
    fields=['account', 'debit', 'credit', 'description', 'project', 'stage', 'currency'],
    extra=1,
    can_delete=True,
)


from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django import forms
from .models import Project, ProjectStage

# Form for editing project budget and other fields
class ProjectEditForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "budget",
            "start_date",
            "end_date",
            "trello_board_id",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

# Inline formset for stages
StageFormSet = forms.inlineformset_factory(
    Project,
    ProjectStage,
    fields=("name", "order"),
    extra=1,
    can_delete=True
)


from django.forms import inlineformset_factory
from .models import JournalEntry, JournalItem

JournalItemFormSet = inlineformset_factory(
    JournalEntry,
    JournalItem,
    form=JournalItemForm,
    formset=BaseJournalItemFormSet,  # use the custom FormSet
    fields=['account', 'debit', 'credit', 'description', 'project', 'stage', 'currency'],
    extra=2,
    can_delete=False
)



class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        exclude = ["client"]
        fields = ['name', 'account_type', 'is_bank', 'is_receivable', 'is_payable','currency','opening_balance']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-select'}),
            'is_bank': forms.CheckboxInput(),
            'is_receivable': forms.CheckboxInput(),
            'is_payable': forms.CheckboxInput(),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }



class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'client', 'date', 'due_date', 'currency', 'exchange_rate',
            'gst_percent', 'is_recurring', 'recurring_interval', 'notes',
            'template_style', 'last_generated', 'project'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),  # Updated for FK
            'exchange_rate': forms.NumberInput(attrs={'step': '0.0001', 'class': 'form-control'}),
            'project': forms.Select(attrs={'placeholder': 'Select a project', 'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control'}),
                'last_generated': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        help_texts = {
            'project': '🔔 Always select a related project for accurate reporting.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.fields['client'].queryset = Client.objects.filter(receivable_account__isnull=False)
        self.fields['client'].queryset = Client.objects.all()

        self.fields['project'].required = True
        self.fields['project'].label = "Project (Required)"




InvoiceItemFormSet = forms.inlineformset_factory(
    Invoice,
    InvoiceItem,
    fields=['description', 'quantity', 'unit_price'],
    extra=1,
    can_delete=False
)


class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ['description', 'hours', 'rate_per_hour', 'project']
        widgets = {
            'project': forms.Select(attrs={
                'placeholder': 'Select project',
            }),
        }
        help_texts = {
            'project': '🔔 Select the correct project for this time entry.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['project'].required = True
        self.fields['project'].label = "Project (Required)"

TimeEntryFormSet = forms.inlineformset_factory(
    Invoice,
    TimeEntry,
    form=TimeEntryForm,
    fields=['description', 'hours', 'rate_per_hour', 'project'],
    extra=1,
    can_delete=True
)



from django import forms
from django.forms import inlineformset_factory
from django.db.models import Q
from .models import Project, ProjectStage, Client

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'client', 'start_date', 'end_date', 'budget', 'trello_board_id']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        help_texts = {
            'trello_board_id': 'Paste the Trello Board ID here to link tasks to this project.',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # we pass request.user when instantiating form
        super().__init__(*args, **kwargs)

        if user:
            if user.is_superuser:
                # Superuser domain = self + their accountants
                accountants = list(user.created_users.all())
                allowed_users = [user] + accountants
            else:
                # Accountant domain = themselves + their superuser
                superuser_creator = getattr(user, "created_by", None)
                allowed_users = [user]
                if superuser_creator:
                    allowed_users.append(superuser_creator)

            # Restrict client queryset
            self.fields["client"].queryset = Client.objects.filter(
                Q(created_by__in=allowed_users) | Q(owner__in=allowed_users)
            ).distinct()

# Project stages formset
ProjectStageFormSet = inlineformset_factory(
    Project, ProjectStage, fields=['name', 'order'], extra=3, can_delete=False
)



from django.core.exceptions import ValidationError
from .models import LockPeriod

class LockPeriodValidationMixin:
    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date') or cleaned_data.get('created')
        if date:
            if LockPeriod.objects.filter(start_date__lte=date, end_date__gte=date).exists():
                raise ValidationError("This date falls within a locked accounting period.")
        return cleaned_data

from django import forms
from .models import JournalEntry, Currency, Project

class JournalEntryForm(LockPeriodValidationMixin, forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['description', 'currency', 'exchange_rate', 'project']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter a brief description...'
            }),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'exchange_rate': forms.NumberInput(attrs={
                'step': '0.0001',
                'class': 'form-control',
                'placeholder': 'e.g. 1.0000'
            }),
            'project': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        # Pop the custom 'user' argument so super().__init__ doesn't fail
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            if user.is_superuser:
                # Superuser sees their projects + projects created by their users
                allowed_users = [user] + list(user.created_users.all())
            else:
                # Normal user sees their own projects + projects created by their superuser
                superuser_creator = getattr(user, 'created_by', None)
                allowed_users = [user]
                if superuser_creator:
                    allowed_users.append(superuser_creator)

            # Filter project field
            self.fields['project'].queryset = Project.objects.filter(created_by__in=allowed_users)

    def clean_exchange_rate(self):
        rate = self.cleaned_data.get('exchange_rate')
        if rate is not None and rate <= 0:
            raise forms.ValidationError("Exchange rate must be a positive number.")
        return rate




from django import forms
from .models import Payroll, ContractorPayment

from django import forms
from .models import Payroll, Employee
from django import forms
from .models import Payroll, Employee
from django.db import models

class PayrollForm(forms.ModelForm):
    payroll_type = forms.ChoiceField(
        choices=[('employee', 'Employee'), ('contractor', 'Contractor')]
    )

    class Meta:
        model = Payroll
        fields = [
            'payroll_type', 'name', 'month',
            'basic_salary', 'other_allowances',
            'overtime_hours', 'overtime_rate'
        ]
        widgets = {
            'month': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        payroll_type = None
        if self.data.get('payroll_type'):   # form submission
            payroll_type = self.data.get('payroll_type')
        elif self.initial.get('payroll_type'):  # initial load
            payroll_type = self.initial.get('payroll_type')

        # ownership logic
        if not user:
            base_qs = Employee.objects.none()
        elif user.is_superuser:
            base_qs = Employee.objects.filter(owner=user)
        else:
            base_qs = Employee.objects.filter(owner=user.created_by)

        if payroll_type == 'contractor':
            self.fields['name'].queryset = base_qs.filter(is_contractor=True)
        elif payroll_type == 'employee':
            self.fields['name'].queryset = base_qs.filter(is_contractor=False)
        else:
            self.fields['name'].queryset = base_qs.none()

from django import forms
from .models import ContractorPayment, Employee
from .utils import get_employee_queryset_for_user

from django import forms
from .models import ContractorPayment, Employee
from .utils import get_employee_queryset_for_user

class ContractorPaymentForm(forms.ModelForm):
    class Meta:
        model = ContractorPayment
        fields = ['name', 'date', 'amount', 'description', 'filing_amount', 'payment_mode']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        base_qs = get_employee_queryset_for_user(self.user) if self.user else Employee.objects.none()
        self.fields['name'].queryset = base_qs.filter(is_contractor=True)

    def save(self, commit=True):
        payment = super().save(commit=False)

        # ✅ Set owner based on hierarchy
        if not payment.owner:
            payment.owner = self.user if self.user.is_superuser else getattr(self.user, 'created_by', None)

        # ✅ Set created_by to logged-in user
        if not payment.created_by:
            payment.created_by = self.user

        if commit:
            payment.save()
            self.save_m2m()
        return payment


        
# forms.py

from .models import Employee

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['name', 'email', 'department', 'designation', 'is_contractor']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'is_contractor': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
        
        }
from django import forms
from .models import TaxDeclaration, Employee

# forms.py
from django import forms
from decimal import Decimal
import datetime, re
from .models import TaxDeclaration, Employee

def current_fy_string(today=None):
    today = today or datetime.date.today()
    start = today.year if today.month >= 4 else today.year - 1  # Apr–Mar FY
    return f"{start}-{start+1}"

class TaxDeclarationForm(forms.ModelForm):
    # Let users type FY
    financial_year = forms.CharField(
        label="Financial Year",
        help_text="Enter as YYYY-YYYY (e.g., 2025-2026)",
        widget=forms.TextInput(attrs={"placeholder": "2025-2026", "class": "form-control"})
    )

    class Meta:
        model = TaxDeclaration
        fields = ["name", "financial_year", "declared_amount", "approved_amount"]
        widgets = {
            "declared_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "approved_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Prefill FY
        if not self.initial.get("financial_year"):
            self.fields["financial_year"].initial = current_fy_string()

        # 🔒 Tenant scoping for Employee choices
        if user:
            if user.is_superuser:
                base_qs = Employee.objects.filter(owner=user)
            else:
                base_qs = Employee.objects.filter(owner=getattr(user, "created_by", None))
            self.fields["name"].queryset = base_qs.filter(is_contractor=False)

        # ✅ Accountants can now edit approved_amount.
        # (Remove the previous disabling; keep a helpful note.)
        self.fields["approved_amount"].help_text = "You can edit this. It must not exceed the declared amount."

    def clean_financial_year(self):
        s = (self.cleaned_data.get("financial_year") or "").strip()
        if not re.match(r"^\d{4}-\d{4}$", s):
            raise forms.ValidationError("Format must be YYYY-YYYY, e.g., 2025-2026.")
        start, end = map(int, s.split("-"))
        if end - start != 1:
            raise forms.ValidationError("End year must be start year + 1.")
        if not (2000 <= start <= 2100):
            raise forms.ValidationError("Year out of acceptable range.")
        return s

    def clean(self):
        cleaned = super().clean()
        declared = cleaned.get("declared_amount") or Decimal("0")
        approved = cleaned.get("approved_amount") or Decimal("0")
        if approved > declared:
            self.add_error("approved_amount", "Approved amount cannot exceed declared amount.")
        return cleaned

        
        
        
from django import forms
from .models import Payroll

from django import forms
from .models import Payroll, FilingRecord

class FilingForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = ['tds_filed', 'tds_challan', 'pf_filed', 'pf_challan', 'esi_filed', 'esi_challan']
        widgets = {
            'tds_filed': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'tds_challan': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'}),
            'pf_filed': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'pf_challan': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'}),
            'esi_filed': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'esi_challan': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'}),
        }

class FilingRecordForm(forms.ModelForm):
    class Meta:
        model = FilingRecord
        exclude = ['payroll']
        widgets = {
            'filing_type': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'amount_filed': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'paid_to': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'payment_mode': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'payment_reference': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'filed_on': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'challan_file': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'}),
        }



# forms.py
from django import forms
from django import forms
from .models import ContractorFilingRecord

class ContractorFilingForm(forms.ModelForm):

    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('online_payment', 'Online Payment'),
        ('upi', 'UPI'),
        ('other', 'Other'),
    ]

    payment_mode = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    filed_on = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        })
    )

    amount_filed = forms.DecimalField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
        })
    )

    payment_reference = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )

    paid_to = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    challan_file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        required=False
    )

    class Meta:
        model = ContractorFilingRecord
        fields = [
            'amount_filed', 'filed_on', 'payment_mode',
            'payment_reference', 'paid_to', 'challan_file'
        ]


from django import forms
from .models import TaxRecord
from django.utils import timezone

class TaxRecordForm(forms.ModelForm):
    class Meta:
        model = TaxRecord
        fields = [
            'invoice_number', 'date', 'tax_type', 'taxable_amount',
            'tax_rate', 'filed', 'filing_date', 'remarks', 'gst_portal_reference'
        ]
        widgets = {
    'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
     
    'filing_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
}
    def clean_taxable_amount(self):
            amount = self.cleaned_data.get('taxable_amount')
            if amount is not None and amount < 0:
             raise forms.ValidationError("Taxable amount cannot be negative.")
            return amount

    def clean_tax_rate(self):
        rate = self.cleaned_data.get('tax_rate')
        if rate is None:
         return rate  # Let required validation handle empty values if needed
        if rate < 0 or rate > 100:
          raise forms.ValidationError("Tax rate must be between 0 and 100.")
        return rate
    def clean_filing_date(self):
        filing_date = self.cleaned_data.get('filing_date')
        if filing_date and filing_date > timezone.now().date():
            raise forms.ValidationError("Filing date cannot be in the future.")
        return filing_date


from django import forms
from .models import TDSRecord
from .models import Payroll, ContractorPayment
from decimal import Decimal

class TDSRecordForm(forms.ModelForm):
    class Meta:
        model = TDSRecord
        fields = '__all__'
        exclude = ['owner', 'created_by'] 
        widgets = {
    'filing_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
}
    def __init__(self, *args, **kwargs):
        # Accept custom arguments for pre-fill
        payroll = kwargs.pop('payroll', None)
        contractor = kwargs.pop('contractor', None)
        super().__init__(*args, **kwargs)

        if payroll:
            self.fields['payee_name'].initial = payroll.name.name
            self.fields['reference_id'].initial = str(payroll.id)
            self.fields['source'].initial = 'Payroll'
            self.fields['payment_date'].initial = payroll.month
            self.fields['amount_paid'].initial = payroll.basic_salary
            self.fields['tds_rate'].initial = Decimal('10.00')
            self.fields['tds_amount'].initial = payroll.tds

        if contractor:
            self.fields['payee_name'].initial = contractor.name.name
            self.fields['reference_id'].initial = str(contractor.id)
            self.fields['source'].initial = 'Contractor'
            self.fields['payment_date'].initial = contractor.date
            self.fields['amount_paid'].initial = contractor.amount / Decimal('0.90')  # assuming 10% tds
            self.fields['tds_rate'].initial = Decimal('10.00')
            self.fields['tds_amount'].initial = contractor.amount * Decimal('0.10') / Decimal('0.90')

from django import forms
from .models import ExchangeRate, CostCenter, InterCompanyTransaction, DeferredRevenue

from django import forms
from .models import ExchangeRate

class ExchangeRateForm(forms.ModelForm):
    class Meta:
        model = ExchangeRate
        fields = ['from_currency', 'to_currency', 'rate', 'date']
        widgets = {
            'from_currency': forms.Select(attrs={'class': 'w-full border border-gray-300 rounded px-3 py-2'}),
            'to_currency': forms.Select(attrs={'class': 'w-full border border-gray-300 rounded px-3 py-2'}),
            'rate': forms.NumberInput(attrs={'class': 'w-full border border-gray-300 rounded px-3 py-2'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full border border-gray-300 rounded px-3 py-2'}),
        }

from django import forms
from .models import CostCenter

class CostCenterForm(forms.ModelForm):
    class Meta:
        model = CostCenter
        fields = ['code', 'name', 'description','currency']
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'cols': 40,
                'placeholder': 'Enter a description...',
                'style': 'resize: vertical;'  # Optional
            }),
        }


class InterCompanyTransactionForm(forms.ModelForm):
    class Meta:
        model = InterCompanyTransaction
        fields = '__all__'

class DeferredRevenueForm(forms.ModelForm):
    class Meta:
        model = DeferredRevenue
        fields = ["customer", "amount", "start_date", "end_date", "description"]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
from django import forms
from .models import Currency
from django import forms
from .models import Currency
from django import forms
from .models import Currency

CURRENCY_CHOICES = [
    ('USD', 'USD - US Dollar - $'),
    ('EUR', 'EUR - Euro - €'),
    ('INR', 'INR - Indian Rupee - ₹'),
    ('GBP', 'GBP - British Pound - £'),
    ('JPY', 'JPY - Japanese Yen - ¥'),
    ('AUD', 'AUD - Australian Dollar - A$'),
    ('CAD', 'CAD - Canadian Dollar - C$'),
    ('CNY', 'CNY - Chinese Yuan - ¥'),
    ('CHF', 'CHF - Swiss Franc - CHF'),
    ('SGD', 'SGD - Singapore Dollar - S$'),
]

class CurrencyForm(forms.ModelForm):
    code = forms.ChoiceField(choices=CURRENCY_CHOICES, label="Currency")

    class Meta:
        model = Currency
        fields = ['code', 'name', 'symbol']
        widgets = {
            'name': forms.TextInput(attrs={'readonly': 'readonly'}),
            'symbol': forms.TextInput(attrs={'readonly': 'readonly'}),
        }

# forms.py
from django import forms
from .models import Plan

class PlanForm(forms.ModelForm):
    PLAN_CHOICES = [
        ('Basic', 'Basic'),
        ('Pro', 'Pro'),
        ('Enterprise', 'Enterprise'),
    ]

    name = forms.ChoiceField(choices=PLAN_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    class Meta:
        model = Plan
        fields = ['name', 'price', 'trial_days', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'trial_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        
        
        
from django import forms

from datetime import date

from django import forms
from django.apps import apps
from datetime import date
from django import forms
from django.apps import apps
from datetime import date

class RollingForecastForm(forms.ModelForm):
    class Meta:
        model = apps.get_model('accounting_app', 'Forecast')
        fields = ['project', 'account', 'cost_center', 'year', 'month', 'forecast_amount', 'notes']
        widgets = {
            'year': forms.NumberInput(attrs={'min': 2020, 'max': 2100, 'value': date.today().year}),
            'month': forms.Select(choices=[(i, i) for i in range(1, 13)]),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
from django import forms
from accounting_app.models import WhatIfScenario, Project, Account, CostCenter
from django.contrib.auth import get_user_model
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

def get_allowed_users(user):
    """Return the list of users visible to the given user within their tenant only."""
    if getattr(user, "is_superadmin", False):
        return User.objects.all()  # superadmin sees everything

    elif user.is_superuser:
        # Superuser sees only themselves + their own accountants
        return [user] + list(user.created_users.all())

    else:
        # Accountant sees only themselves + their superuser (created_by)
        superuser = getattr(user, "created_by", None)
        allowed = [user]
        if superuser:
            allowed.append(superuser)
        return allowed


   

User = get_user_model()

class WhatIfScenarioForm(forms.ModelForm):
    class Meta:
        model = WhatIfScenario
        fields = [
            "owner",
            "created_by",
            "name",
            "project",
            "account",
         
            "scenario_type",
            "percentage_change",
            "notes",
         
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if not user:
            return  # no user, don't restrict anything

        # Get allowed users as a queryset
        allowed_users_list = get_allowed_users(user)
        allowed_users_qs = (
            allowed_users_list
            if isinstance(allowed_users_list, models.QuerySet)
            else User.objects.filter(id__in=[u.id for u in allowed_users_list])
        )

        # Owner → restrict and set initial
        if "owner" in self.fields:
            self.fields["owner"].queryset = allowed_users_qs
            self.fields["owner"].initial = user

        # Created by → restrict and set initial
        if "created_by" in self.fields:
            self.fields["created_by"].queryset = allowed_users_qs
            self.fields["created_by"].initial = user

        # Project → restrict to allowed users’ projects
        if "project" in self.fields:
            self.fields["project"].queryset = Project.objects.filter(owner__in=allowed_users_qs)

        # Account → restrict to allowed users’ accounts
        if "account" in self.fields:
            self.fields["account"].queryset = Account.objects.filter(owner__in=allowed_users_qs)

        # Cost center → restrict to allowed users’ cost centers
        if "cost_center" in self.fields:
            self.fields["cost_center"].queryset = CostCenter.objects.filter(owner__in=allowed_users_qs)
            self.fields["cost_center"].empty_label = "Select Cost Center"



# profiles/forms.py
from django import forms
from .models import Profile

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['profile_photo', 'phone', 'address']

# forms_asset.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import FixedAsset



class FixedAssetForm(forms.ModelForm):
    class Meta:
        model = FixedAsset
        fields = [
            "asset_tag", "name", "category", "purchase_date", "purchase_price",
            "useful_life", "warranty_expiry", "maintenance_schedule", "next_maintenance_date",
            "disposed", "disposal_date", "disposal_value", "written_off",
        ]
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "warranty_expiry": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "disposal_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "next_maintenance_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
           allowed_users = get_allowed_users(user)

        # Example: if you add FK fields in the future
           for field_name in ["account", "project", "cost_center", "category"]:
            if field_name in self.fields and hasattr(self.fields[field_name], "queryset"):
                self.fields[field_name].queryset = (
                    self.fields[field_name].queryset.filter(owner__in=allowed_users).distinct()
                )


            # (Optional) If you later add account/project/cost_center fields → restrict them here

    def clean(self):
        cleaned_data = super().clean()
        disposed = cleaned_data.get("disposed")
        disposal_date = cleaned_data.get("disposal_date")

        if disposed and not disposal_date:
            raise ValidationError({"disposal_date": "Please provide a disposal date for disposed assets."})

        if disposal_date:
            today = timezone.localdate()
            if disposal_date <= today:
                raise ValidationError({"disposal_date": "Disposal date must be in the future."})

        # Optional: check next maintenance date
        next_maintenance_date = cleaned_data.get("next_maintenance_date")
        if next_maintenance_date and next_maintenance_date <= timezone.localdate():
            raise ValidationError({"next_maintenance_date": "Next maintenance date must be in the future."})

        return cleaned_data


# forms.py
from django import forms
from .models import Budget

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ["name", "project", "account", "cost_center", "year", "month", "period_type", "amount"]

    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get("project")
        amount = cleaned_data.get("amount")
        year = cleaned_data.get("year")

        if project and amount:
            # Calculate existing sum for this project & year
            from .models import Budget
            total = Budget.objects.filter(project=project, year=year).aggregate(
                total=forms.models.Sum("amount")
            )["total"] or 0

            # If this form is editing an existing record, exclude its amount
            if self.instance.pk:
                total -= self.instance.amount

            # Ensure project budget is not exceeded
            if total + amount > project.budget:
                raise forms.ValidationError(
                    f"Total budget for {project.name} in {year} exceeds the project budget ({project.budget})."
                )

        return cleaned_data

from django import forms
from .models import EmployeeExpense

from django import forms
from .models import EmployeeExpense
from accounting_app.models import Employee

class EmployeeExpenseForm(forms.ModelForm):
    class Meta:
        model = EmployeeExpense
        fields = ["employee", "date", "category", "amount", "description", "receipt"]
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'receipt': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)  # Pass the logged-in user
        super().__init__(*args, **kwargs)

        if user:
            # Restrict employee dropdown to only the current user's Employee profile
            employee_qs = Employee.objects.filter(user=user)
            self.fields['employee'].queryset = employee_qs
            if employee_qs.exists():
                self.fields['employee'].initial = employee_qs.first()
            # Optionally make it readonly/disabled so user can't change
            self.fields['employee'].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        # Delegate to model's clean for extra validation
        self.instance.date = cleaned_data.get('date')
        self.instance.category = cleaned_data.get('category')
        self.instance.amount = cleaned_data.get('amount')
        self.instance.clean()
        return cleaned_data

        
class EmployeeCreateForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["name", "email", "department", "designation", "is_contractor"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user_instance", None)
        super().__init__(*args, **kwargs)
        # Pre-fill from user if provided and fields are empty
        if user and not self.instance.pk:
            self.fields["name"].initial = (f"{user.first_name} {user.last_name}".strip()
                                           or user.email.split("@")[0].title())
            self.fields["email"].initial = user.email

from django import forms
from .models import ClientContract, Retainer, BillingMilestone, Phase,Deal, Commission

class ClientContractForm(forms.ModelForm):
    class Meta:
        model = ClientContract
        fields = ['client', 'name', 'start_date', 'end_date', 'details']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'details': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        # ✅ Expect request to be passed when form is instantiated
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if request:
             # import where you defined it
            allowed_users = get_allowed_users(request.user)

            # Restrict clients dropdown
            self.fields['client'].queryset = Client.objects.filter(owner__in=allowed_users)

            # Optional: add styling
            self.fields['client'].widget.attrs.update({'class': 'form-select'})


class RetainerForm(forms.ModelForm):
    class Meta:
        model = Retainer
        fields = ['amount', 'billing_day', 'active']

class MilestoneForm(forms.ModelForm):
    class Meta:
        model = BillingMilestone
        fields = ['name', 'completed_date', 'amount']
        widgets = {
            'completed_date': forms.DateInput(attrs={'type': 'date'}),
        }

class PhaseForm(forms.ModelForm):
    class Meta:
        model = Phase
        fields = ['name', 'revenue','revenue_date']
        widgets = {
            'revenue_date': forms.DateInput(attrs={'type': 'date'}),
        }
        
        
        
from django.forms import inlineformset_factory
from .models import ClientContract, Retainer, BillingMilestone, Phase,Client
from .forms import RetainerForm, MilestoneForm, PhaseForm
from integrations.models import CRMClient



RetainerFormSet = inlineformset_factory(
    ClientContract, Retainer, form=RetainerForm, extra=1, can_delete=True
)

MilestoneFormSet = inlineformset_factory(
    ClientContract, BillingMilestone, form=MilestoneForm, extra=1, can_delete=True
)

PhaseFormSet = inlineformset_factory(
    ClientContract, Phase, form=PhaseForm, extra=1, can_delete=True
)
class DealForm(forms.ModelForm):
    commission_percentage = forms.DecimalField(initial=10.00, required=False)

    class Meta:
        model = Deal
        fields = ['client', 'title', 'amount', 'expected_close', 'stage']
        widgets = {
            'expected_close': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)   # ✅ capture request
        super().__init__(*args, **kwargs)

        if request:
            allowed_users = get_allowed_users(request.user)

            # Filter CRM clients by allowed owners
            self.fields['client'].queryset = (
                Client.objects.filter(owner__in=allowed_users).order_by("name")
            )

            # Optional: add styling
            self.fields['client'].widget.attrs.update({'class': 'form-select'})



class CommissionForm(forms.ModelForm):
    class Meta:
        model = Commission
        fields = ['percentage']

from django import forms
from .models import Quote

class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ['title', 'amount', 'status', 'pdf_file', 'notes','created_date']
        widgets = {
            'created_date': forms.DateInput(attrs={'type': 'date'}),
            'pdf_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# branding/forms.py
from django import forms
from .models import BrandingSettings

class BrandingForm(forms.ModelForm):
    class Meta:
        model = BrandingSettings
        fields = ['company_name', 'logo','background']
       
from django import forms
from django.contrib.auth.password_validation import validate_password

class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(label="Enter your email", max_length=254)

class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(label="New password", widget=forms.PasswordInput)
    confirm_password = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        pw1 = cleaned.get("new_password")
        pw2 = cleaned.get("confirm_password")
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError("Passwords do not match.")
        validate_password(pw1)  # Django’s password validators
        return cleaned


from django import forms
from .models import Client

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "gstin", "email", "address", "phone", "company"]





from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class SuperuserRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name"]

    def clean_password2(self):
        if self.cleaned_data.get("password1") != self.cleaned_data.get("password2"):
            raise forms.ValidationError("Passwords don't match.")
        return self.cleaned_data.get("password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.is_staff = True
        user.is_superuser = True
        user.is_superadmin = False
        user.role = "Superuser"# ✅ mark as normal superuser
        if commit:
            user.save()
        return user
