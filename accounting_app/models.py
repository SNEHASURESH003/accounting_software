from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import now
from .base_models import VersionedModel
from django.conf import settings



# ----------------------
# 🔐 Custom User Model
# ----------------------

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email must be provided')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault("is_superadmin", True)
        extra_fields.setdefault('role', 'SuperAdmin')
        if not extra_fields.get('is_staff') or not extra_fields.get('is_superuser'):
            raise ValueError('Superuser must have is_staff=True and is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_users",null=True, blank=True
    )
    # name = models.CharField(max_length=150,null=True, blank=True)
    created_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_users')
    email = models.EmailField(max_length=191, unique=True)
    is_active = models.BooleanField(default=True)
    first_name = models.CharField(max_length=30, blank=True)  # ✅ Add this
    last_name = models.CharField(max_length=30, blank=True)
  
    is_staff = models.BooleanField(default=False)
    is_superadmin = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    ROLE_CHOICES = [
         ('SuperAdmin', 'SuperAdmin'),
        ('Superuser', 'Superuser'),
        ('Accountant', 'Accountant'),
        ('Staff', 'Staff'),
        ('Employee', 'Employee'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Employee')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()
    
    def clean(self):
        if self.email:
            self.email = UserManager.normalize_email(self.email)
    def __str__(self):
        return self.email

    def is_verified(self):
        # Example logic (customize as needed)
        return self.is_active and self.email and self.is_authenticated
    @property
    def is_normal_superuser(self):
        """True for superusers who are NOT superadmins."""
        return self.is_superuser and not self.is_superadmin
    @property
    def is_accountant(self):
        return self.role == 'Accountant'
 
    # def __str__(self):
    #         return self.name 

# ----------------------
# 📊 Chart of Accounts
# ----------------------




class Account(models.Model):
    ACCOUNT_TYPES = [
        ('Asset', 'Asset'),
        ('Liability', 'Liability'),
        ('Equity', 'Equity'),
        ('Revenue', 'Revenue'),
        ('Expense', 'Expense'),
    ]
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_accounts",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_accounts", null=True, blank=True
    )
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPES)
    
    currency = models.ForeignKey('Currency', on_delete=models.PROTECT,null=True, blank=True, default=None)
    is_bank = models.BooleanField(default=False)
    is_receivable = models.BooleanField(default=False)
    is_payable = models.BooleanField(default=False)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    client = models.OneToOneField(
        "Client",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="receivable_account"   # ✅ so you can do client.receivable_account
    )

    def __str__(self):
        return self.name

# ----------------------
# 🧾 Journal Entries
# ----------------------








# ----------------------
# 👥 Clients
# ----------------------

class Client(models.Model):
    name = models.CharField(max_length=100)
    gstin = models.CharField(max_length=15,null=True, blank=True)
    email = models.EmailField()
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=100, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_clients",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_clients", null=True, blank=True
    )
   

    def __str__(self):
        return self.name
from django.db.models import Sum
from django.conf import settings
class Project(VersionedModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_projects",null=True, blank=True
    )
   
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_projects", null=True, blank=True
    )
    
   
    name = models.CharField(max_length=100)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    trello_board_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

    @property
    def expenses(self):
        # Example: expenses from JournalItem or TimeEntry
        from .models import JournalItem  # adjust path as needed
        return JournalItem.objects.filter(project=self).aggregate(total=Sum('debit'))['total'] or 0

    @property
    def income(self):
        from .models import Invoice  # adjust path as needed
        return Invoice.objects.filter(project=self).aggregate(
            total=Sum('items__quantity') * Sum('items__unit_price'))['total'] or 0
    

    @property
    def profit(self):
        return self.income - self.expenses

    @property
    def budget_variance(self):
        return self.budget - self.expenses
    
    def total_budget(self):
        """Sum of all related Budget.amounts"""
        return self.budgets.aggregate(total=Sum('amount'))['total'] or 0

    def total_allocated_budget(self):
        """Sum of all related Budget.amounts without overwriting Project.budget"""
        return self.budgets.aggregate(total=Sum('amount'))['total'] or 0
    def sync_budget(self):
        """
        Keep budget entries in sync for forecasts or reporting.
        DOES NOT overwrite Project.budget (original planned budget).
        """
        # Optional: return total allocated budget for use in forecasts
        return self.total_allocated_budget()
    
class ProjectStage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="stages")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_projectstages",null=True, blank=True
    )
   
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_projectstages", null=True, blank=True
    )
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)  # to keep them in sequence
    class Meta:
            ordering = ('order', 'id')
            constraints = [
            models.UniqueConstraint(fields=('project', 'name'),  name='uniq_stage_name_per_project'),
            models.UniqueConstraint(fields=('project', 'order'), name='uniq_stage_order_per_project'),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.name}"
# accounting_app/models.py (where JournalEntry is defined)
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.contrib.contenttypes.models import ContentType


# ... your existing JournalEntry fields ...
class JournalEntry(models.Model):
    date = models.DateField(default=now) # ← editable, recommended
    description = models.TextField()

    currency = models.ForeignKey('Currency', on_delete=models.SET_NULL, null=True, blank=True, default=None)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)

    project = models.ForeignKey('Project', on_delete=models.SET_NULL, null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_journals",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_journals", null=True, blank=True
    )

    # NEW: posting/approval fields
    from django.conf import settings
    is_posted = models.BooleanField(default=False)
    posted_on = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="journal_entries_posted"
    )

    def __str__(self):
        return f"Journal Entry on {self.date} ({self.currency})"

    def save(self, *args, **kwargs):
        # Default currency fallback
        if not self.currency:
            try:
                from .models import Currency
                self.currency = Currency.objects.get(code='INR')
            except Exception:
                pass
        super().save(*args, **kwargs)

    # --- Approval and lock enforcement ---

    def is_approved(self) -> bool:
        """
        Returns True if an ApprovalRequest exists with APPROVED status for this JE.
        """
        ct = ContentType.objects.get_for_model(JournalEntry)
        from .models import ApprovalRequest  # local import avoids circulars
        return ApprovalRequest.objects.filter(
            target_ct=ct, target_id=str(self.pk), status="APPROVED"
        ).exists()
   
    def clean(self):
        super().clean()
        from accounting_app.utils import is_date_locked
        if self.is_posted:
         if not self.pk or not self.is_approved():
            raise ValidationError("This journal entry must be APPROVED before posting.")
         if self.date and is_date_locked(self.date):
            raise ValidationError("This date falls in a locked accounting period.")


    def mark_posted(self, user=None):
        """
        Service method to post the entry programmatically (e.g., from a view or admin action).
        Will validate approval and lock period.
        """
        self.is_posted = True
        self.full_clean()  # runs approval + lock checks
        self.posted_on = now()
        if user:
            self.posted_by = user
        self.save(update_fields=["is_posted", "posted_on", "posted_by"])



  

  



# ----------------------
# 🧾 Invoicing
# ----------------------
class Invoice(VersionedModel):
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_invoice",null=True, blank=True
    )
   
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_invoice", null=True, blank=True
    )
    deal = models.ForeignKey('Deal', on_delete=models.CASCADE, null=True, blank=True,related_name="invoices")
    razopay_order_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=[('paid', 'Paid'), ('unpaid', 'Unpaid')], default='unpaid')
    date = models.DateField()
    due_date = models.DateField()
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    
    # 👇 Replace CharField with ForeignKey to Currency
    currency = models.ForeignKey('Currency', on_delete=models.PROTECT, default=1)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)


    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18.0)
    is_recurring = models.BooleanField(default=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    TEMPLATE_CHOICES = [
        ('default', 'Default'),
        ('clean', 'Clean (No border)'),
        ('bold', 'Bold Header')
    ]
    template_style = models.CharField(max_length=20, choices=TEMPLATE_CHOICES, default='default')

    recurring_interval = models.CharField(
        max_length=20,
        blank=True,
        choices=[('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')]
    )

    from django.utils.timezone import now
    last_generated = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def total_without_tax(self):
        item_total = sum(item.total() for item in self.items.all())
        time_total = sum(te.total() for te in self.time_entries.all())
        return item_total + time_total

    def gst_amount(self):
        return self.total_without_tax() * (self.gst_percent / 100)

    def total_with_tax(self): 
        return self.total_without_tax() + self.gst_amount()
  


    def __str__(self):
        return f"Invoice #{self.pk} – {self.client.name}"
from django.conf import settings
   
class SubscriptionInvoice(models.Model):
    user= models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="owned_subscriptioninvoice", null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="created_subscriptioninvoice", null=True, blank=True
    )

    subscription = models.ForeignKey('Subscription', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=190)
    paid = models.BooleanField(default=False)
    name = models.ForeignKey('Plan', on_delete=models.CASCADE,null=True, blank=True)
    

    def __str__(self):
        return f"Invoice: {self.subscription.user} - ${self.amount}"    

class Payment(models.Model):
    invoice = models.ForeignKey(SubscriptionInvoice, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_date = models.DateField(default=now)
    payment_gateway = models.CharField(max_length=50)

    def __str__(self):
        return f"Payment #{self.id} - {self.amount}"
class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=190)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def total(self):
        return self.quantity * self.unit_price
    
class TimeEntry(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='time_entries')
    description = models.CharField(max_length=190)
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    rate_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)

    def total(self):
        return self.hours * self.rate_per_hour

    def save(self, *args, **kwargs):
        # Automatically assign project from invoice if not set
        if self.invoice and not self.project:
            self.project = self.invoice.project
        super().save(*args, **kwargs)

class JournalItem(VersionedModel):

    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='items')
    
    currency = models.ForeignKey(
        'Currency',  # or 'yourapp.Currency' if in different app
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_journalitems",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_journalitems", null=True, blank=True
    )
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reconciled = models.BooleanField(default=False)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    stage = models.ForeignKey(ProjectStage, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=155, blank=True)

    def save(self, *args, **kwargs):
        if self.entry and not self.project:
            self.project = self.entry.project  # Ensure project is set from the JournalEntry

        # Ensure stage is set when project is set
        if self.project and not self.stage:
            # Check if there is a valid stage for the project
            stage = ProjectStage.objects.filter(project=self.project).first()
            if stage:
                self.stage = stage  # Assign the first valid stage for the project
            else:
                # Optionally, raise an error or assign a default stage here
                print(f"No stage found for project {self.project.id}, assigning default stage")
                # You can set a default stage if needed, or raise an exception if stage is critical
                self.stage = ProjectStage.objects.first()  # Example: setting the first stage if none exists

        if not self.currency and self.account and self.account.currency:
            self.currency = self.account.currency

        super().save(*args, **kwargs) 



# ----------------------
# 📄 Invoice Detail View
# ----------------------


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Account)
def create_client_if_receivable(sender, instance, created, **kwargs):
    if instance.is_receivable:
        Client.objects.get_or_create(
            receivable_account=instance,
            defaults={
                'name': instance.name,
                'email': f"{instance.name.lower().replace(' ', '_')}@example.com"
            }
        )



from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal

# User = get_user_model()

# class Employee(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     designation = models.CharField(max_length=100)
#     basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
#     is_contractor = models.BooleanField(default=False)

#     def __str__(self):
#         return self.user.get_full_name()
    
# # models.py

# class Employee(models.Model):
#     DEPARTMENT_CHOICES = [
#         ('HR', 'HR'),
#         ('Finance', 'Finance'),
#         ('Engineering', 'Engineering'),
#         ('Marketing', 'Marketing'),
#         # Add more as needed
#     ]
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee', null=True, blank=True)

#     name = models.CharField(max_length=100, blank=True, null=True)
#     email = models.EmailField(max_length=100, blank=True, null=True)
#     department = models.CharField(max_length=100, null=True, blank=True, choices=DEPARTMENT_CHOICES)
#     is_contractor = models.BooleanField(default=True) 

#     designation = models.CharField(max_length=100, blank=True, null=True)
    

#     def __str__(self):
#         return self.name or "Unnamed Employee"



from decimal import Decimal
from django.db import models

from decimal import Decimal
from django.db import models


from decimal import Decimal
from django.db import models

from django.db import models
from decimal import Decimal


# class Payroll(models.Model):
#     name = models.ForeignKey('Employee', on_delete=models.CASCADE)
#     month = models.DateField()
#     basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
#     hra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#     other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#     tds = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#     pf = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#     esi = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#     net_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#     is_paid = models.BooleanField(default=False)
#     tds_filed = models.BooleanField(default=False)
#     pf_filed = models.BooleanField(default=False)
#     esi_filed = models.BooleanField(default=False)
#     tds_challan = models.CharField(max_length=100, blank=True, null=True)
#     pf_challan = models.CharField(max_length=100, blank=True, null=True)
#     esi_challan = models.CharField(max_length=100, blank=True, null=True)
#     challan_file = models.FileField(upload_to='challans/', null=True, blank=True)

#     def calculate(self):
#         if self.name.is_contractor:
#             self.hra = Decimal('0.00')
#             self.pf = Decimal('0.00')
#             self.esi = Decimal('0.00')
#             self.tds = self.basic_salary * Decimal('0.10')
#         else:
#             self.hra = self.basic_salary * Decimal('0.40')
#             self.pf = self.basic_salary * Decimal('0.12')
#             self.esi = self.basic_salary * Decimal('0.0075')
#             annual_income = self.basic_salary * Decimal('12')
#             slab_limit = Decimal('250000')
#             tax_rate = Decimal('0.05')
#             taxable = max(Decimal('0.00'), annual_income - slab_limit)
#             annual_tds = taxable * tax_rate
#             self.tds = annual_tds / Decimal('12')

#         self.net_salary = self.total_earnings - self.total_deductions

#     @property
#     def total_earnings(self):
#         return self.basic_salary + self.hra + self.other_allowances

#     @property
#     def total_deductions(self):
#         return self.pf + self.esi + self.tds

#     def __str__(self):
#         return f"{self.name.name} - {self.month.strftime('%B %Y')}"
class EmployeeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_contractor=False)
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Employee(models.Model):
    DEPARTMENT_CHOICES = [
        ('HR', 'HR'),
        ('Finance', 'Finance'),
        ('Engineering', 'Engineering'),
        ('Marketing', 'Marketing'),
    ]

    DESIGNATION_CHOICES = [
        ('Manager', 'Manager'),
        ('Software Engineer', 'Software Engineer'),
        ('HR Executive', 'HR Executive'),
        ('Accountant', 'Accountant'),
    ]
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_employee",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_employee", null=True, blank=True
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='employee', null=True, blank=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, choices=DEPARTMENT_CHOICES, default='Finance')
    designation = models.CharField(max_length=100, choices=DESIGNATION_CHOICES, default='Manager')
    is_contractor = models.BooleanField(default=False)
    

    def __str__(self):
        return self.name or "Unnamed Employee"

from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.db import models

# ---------- helpers ----------
def q(n):
    """Safe Decimal conversion."""
    return n if isinstance(n, Decimal) else Decimal(str(n or 0))

def q2(n):
    """Round to 2 decimals HALF_UP."""
    return q(n).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

class Payroll(models.Model):
    name = models.ForeignKey('Employee', on_delete=models.CASCADE)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="owned_payroll", null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="created_payroll", null=True, blank=True
    )

    month = models.DateField()  # store the payroll month as a date

    basic_salary     = models.DecimalField(max_digits=10, decimal_places=2)
    hra              = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tds              = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pf               = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    esi              = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary       = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_paid       = models.BooleanField(default=False)
    overtime_hours = models.DecimalField(max_digits=5,  decimal_places=2, default=0)
    overtime_rate  = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # filing flags (optional)
    pf_filed  = models.BooleanField(default=False)
    esi_filed = models.BooleanField(default=False)
    tds_filed = models.BooleanField(default=False)

    pf_challan  = models.CharField(max_length=100, blank=True, null=True)
    esi_challan = models.CharField(max_length=100, blank=True, null=True)
    tds_challan = models.CharField(max_length=100, blank=True, null=True)
    challan_file = models.FileField(upload_to='challans/', null=True, blank=True)

    def calculate(self):
        """Canonical salary computation used by save()."""
        ot_pay = q(self.overtime_hours) * q(self.overtime_rate)

        if self.name.is_contractor:
            # --- Contractors: no HRA/PF/ESI; TDS = 10% of gross ---
            self.hra = q2(0)
            self.pf  = q2(0)
            self.esi = q2(0)

            gross = q(self.basic_salary) + q(self.other_allowances) + ot_pay
            self.tds = q2(gross * Decimal('0.10'))
            self.net_salary = q2(gross - self.tds)
            return  # IMPORTANT: do not fall through to employee logic

        # --- Employees ---
        basic = q(self.basic_salary)

        self.hra = q2(basic * Decimal('0.40'))
        self.pf  = q2(basic * Decimal('0.12'))
        self.esi = q2(basic * Decimal('0.0075'))

        # simple slab: 5% of amount above 2.5L (only basic considered, as per your code)
        annual_income = basic * Decimal('12')
        slab_limit = Decimal('250000')
        taxable = max(Decimal('0.00'), annual_income - slab_limit)
        self.tds = q2((taxable * Decimal('0.05')) / Decimal('12'))

        # approved, unpaid expenses add to take-home
        from .models import EmployeeExpense
        expenses = EmployeeExpense.objects.filter(
            employee=self.name, status='APPROVED', is_paid=False,
            submitted_at__year=self.month.year, submitted_at__month=self.month.month
        )
        expense_total = q(expenses.aggregate(models.Sum('amount'))['amount__sum'])

        total_earnings   = basic + q(self.hra) + q(self.other_allowances) + ot_pay
        total_deductions = q(self.pf) + q(self.esi) + q(self.tds)
        self.net_salary  = q2(total_earnings - total_deductions + expense_total)

    def save(self, *args, **kwargs):
        # Always recalc once, reliably
        self.calculate()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name.name} - {self.month.strftime('%B %Y')}"

from django.db import models
from django.db.models import Q
from decimal import Decimal

class ContractorPaymentQuerySet(models.QuerySet):
    def for_user(self, user, include_unowned=False):
        if getattr(user, "is_superuser", False):
            qs = self.filter(Q(owner=user) | (Q(owner__isnull=True) if include_unowned else Q()))
        elif getattr(user, "is_accountant", False):
            qs = self.filter(Q(created_by=user) | Q(owner=getattr(user, "created_by", None)))
        else:
            qs = self.none()
        return qs

class ContractorPaymentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("name", "created_by", "owner")
    def for_user(self, user, include_unowned=False):
        return self.get_queryset().for_user(user, include_unowned=include_unowned)



class ContractorPayment(models.Model):
    name = models.ForeignKey('Employee', on_delete=models.CASCADE,
                             limit_choices_to={'is_contractor': True})

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="owned_contractor", null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="created_contractor", null=True, blank=True
    )

    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # store GROSS here
    filing_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    description = models.TextField(blank=True, null=True)
    is_paid     = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    remarks = models.TextField(blank=True, null=True)

    payment_mode = models.CharField(
        max_length=50,
        choices=[('bank_transfer', 'Bank Transfer'),
                 ('cash', 'Cash'),
                 ('cheque', 'Cheque')],
        default='bank_transfer'
    )

    # ---- amounts ----
    def net_salary(self):
        """Legacy helper: gross - filing only. Prefer net_paid()."""
        return q2(q(self.amount) - q(self.filing_amount))

    def net_paid(self):
        """Gross − TDS(10%) − filing adjustments."""
        from .models import ContractorFilingRecord
        tds = q2(q(self.amount) * Decimal('0.10'))
        fr = ContractorFilingRecord.objects.filter(contractor_payment=self).first()
        filed = q2(fr.amount_filed) if fr else q2(0)
        return q2(q(self.amount) - (tds + filed))

    # ---- optional: basic from payroll for the same month (for display) ----
    def basic_salary_amount(self):
        from .models import Payroll
        p = Payroll.objects.filter(
            name=self.name, month__year=self.date.year, month__month=self.date.month
        ).first()
        return p.basic_salary if p else Decimal('0.00')

    def __str__(self):
        return f"{self.name.name} - {self.date.strftime('%B %Y')}"

class TDSRecord(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="owned_tds", null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="created_tds", null=True, blank=True
    )
    source = models.CharField(max_length=100)              # "Payroll" | "Contractor"
    reference_id = models.CharField(max_length=100, blank=True)  # link to Payroll.id or ContractorPayment.id
    payee_name = models.CharField(max_length=100)
    payment_date = models.DateField()
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    tds_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'))  # %
    tds_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    filed = models.BooleanField(default=False)
    filing_date = models.DateField(null=True, blank=True)
    challan_number = models.CharField(max_length=100, blank=True, null=True)

    def calculate_tds(self):
        """Use only when you want to derive tds_amount from amount_paid & tds_rate."""
        self.tds_amount = q2(q(self.amount_paid) * q(self.tds_rate) / Decimal('100'))

    def __str__(self):
        return f"TDS for {self.payee_name} on {self.payment_date}"

    # ------- factories you call from views --------

    @staticmethod
    def create_from_payroll(payroll):
        """
        Create or update a TDS record for an EMPLOYEE payroll.
        Uses payroll.tds (slab result). Does NOT recompute at 10%.
        Keeps your original field choices (amount_paid = basic, tds_rate default 10.00).
        """
        if payroll.tds <= 0:
            return None

        record = TDSRecord.objects.filter(
            source="Payroll",
            reference_id=str(payroll.id),
        ).first()

        if record:
            # update existing (idempotent)
            record.payee_name   = payroll.name.name
            record.payment_date = payroll.month
            record.amount_paid  = payroll.basic_salary     # base you chose
            record.tds_rate     = Decimal('10.00')         # keep your original default
            record.tds_amount   = payroll.tds              # keep slab amount from payroll
            record.save(update_fields=[
                "payee_name","payment_date","amount_paid","tds_rate","tds_amount"
            ])
        else:
            # create new
            record = TDSRecord(
                source="Payroll",
                reference_id=str(payroll.id),
                payee_name=payroll.name.name,
                payment_date=payroll.month,
                amount_paid=payroll.basic_salary,
                tds_rate=Decimal('10.00'),
                tds_amount=payroll.tds  # DO NOT call calculate_tds(); keep slab amount
            )
            record.save()
        return record

    @staticmethod
    def create_from_contractor_payment(payment, gross_amount=None):
        """
        Create or update a TDS record for a CONTRACTOR payment.
        Contractor TDS = 10% of gross (amount).
        """
        tds_rate = Decimal('10.00')
        amount = q2(q(gross_amount) if gross_amount is not None else q(payment.amount))
        tds_amount = q2(amount * tds_rate / Decimal('100'))

        record = TDSRecord.objects.filter(
            source="Contractor",
            reference_id=str(payment.id),
        ).first()

        if record:
            record.payee_name   = payment.name.name
            record.payment_date = payment.date
            record.amount_paid  = amount
            record.tds_rate     = tds_rate
            record.tds_amount   = tds_amount
            record.save(update_fields=[
                "payee_name","payment_date","amount_paid","tds_rate","tds_amount"
            ])
        else:
            record = TDSRecord(
                source="Contractor",
                reference_id=str(payment.id),
                payee_name=payment.name.name,
                payment_date=payment.date,
                amount_paid=amount,
                tds_rate=tds_rate,
                tds_amount=tds_amount
            )
            record.save()
        return record

    class Meta:
        constraints = [
            # one record per (source, reference_id)
            models.UniqueConstraint(fields=['source', 'reference_id'], name='unique_tds_source_ref')
        ]

from django.db import models
from decimal import Decimal

class TaxDeclaration(models.Model):
    name = models.ForeignKey('Employee', on_delete=models.CASCADE,limit_choices_to={'is_contractor': False})
    financial_year = models.CharField(max_length=9)  # Format: "2024-2025"
    declared_amount = models.DecimalField(max_digits=10, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    submitted_on = models.DateField(auto_now_add=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="owned_taxdeclaration", null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="created_taxdeclaration", null=True, blank=True
    )

    def __str__(self):
        return f"{self.name.name} - {self.financial_year}"


class EmployeeTaxSummary(models.Model):
    name = models.ForeignKey('Employee', on_delete=models.CASCADE)
    year = models.CharField(max_length=9)
    total_income = models.DecimalField(max_digits=12, decimal_places=2)
    approved_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    taxable_income = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    total_tds = models.DecimalField(max_digits=12, decimal_places=2)
    generated_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
        models.UniqueConstraint(fields=['name', 'year'], name='unique_employee_year')
    ]
 # 👈 ensures no duplicate summaries

    def __str__(self):
        return f"{self.name.name} - {self.year}"


# models.py
class FilingRecord(models.Model):
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE)
    filing_type = models.CharField(max_length=20, choices=[
        ('TDS', 'TDS'),
        ('PF', 'Provident Fund'),
        ('ESI', 'ESI'),
    ])
    amount_filed = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = models.CharField(max_length=50)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    filed_on = models.DateField()
    paid_to = models.CharField(max_length=100)
    challan_file = models.FileField(upload_to='filing_challans/', blank=True, null=True)

    def __str__(self):
        return f"{self.filing_type} filed on {self.filed_on} for {self.payroll}"

# models.py
class ContractorFilingRecord(models.Model):
    contractor_payment = models.ForeignKey(ContractorPayment, on_delete=models.CASCADE)
    amount_filed = models.DecimalField(max_digits=10, decimal_places=2)
    filing_type = models.CharField(max_length=10, default='TDS')  # Always TDS
    filed_on = models.DateField()
    payment_mode = models.CharField(max_length=50)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    paid_to = models.CharField(max_length=100)
    challan_file = models.FileField(upload_to='contractor_challans/', blank=True, null=True)

    def __str__(self):
        return f"TDS filed on {self.filed_on} for {self.contractor_payment.name}"



from django.db import models
from decimal import Decimal

TAX_TYPE_CHOICES = [
    ('GST', 'GST'),
    ('IGST', 'IGST'),
    ('CGST', 'CGST'),
    ('SGST', 'SGST'),
    ('TDS', 'TDS'),
]

class TaxRecord(models.Model):
    invoice_number = models.CharField(max_length=100)
    date = models.DateField()
    tax_type = models.CharField(max_length=10, choices=TAX_TYPE_CHOICES)
    taxable_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    filed = models.BooleanField(default=False)
    filing_date = models.DateField(blank=True, null=True)
    remarks = models.TextField(blank=True)
    gst_portal_reference = models.CharField(max_length=100, blank=True, null=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="owned_taxrecord", null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="created_taxrecord", null=True, blank=True
    )
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['invoice_number', 'owner'], name='unique_invoice_per_owner')
        ]

    def calculate_tax(self):
        self.tax_amount = (self.taxable_amount * self.tax_rate) / Decimal('100.00')

    def __str__(self):
        return f"{self.tax_type} - {self.invoice_number}"


from django.db import models
from decimal import Decimal
from .models import Payroll, ContractorPayment


# class GSTFilingRecord(models.Model):
#     gstin = models.CharField(max_length=15)
#     filing_type = models.CharField(max_length=10, choices=[("GSTR1", "GSTR-1"), ("GSTR3B", "GSTR-3B")])
#     period = models.CharField(max_length=6)  # '072024'
#     filed_on = models.DateField(auto_now_add=True)
#     json_payload = models.JSONField()
#     status = models.CharField(max_length=20, default="Pending")
#     reference_id = models.CharField(max_length=100, blank=True, null=True)

from django.conf import settings

from django.conf import settings
from django.db import models

class AuditLog(models.Model):
    ACTIONS = (("create","create"),("update","update"),("delete","delete"),("m2m","m2m"))
    timestamp     = models.DateTimeField(auto_now_add=True)
    user          = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                      on_delete=models.SET_NULL)
    model_name    = models.CharField(max_length=120)     # e.g. "app.Model"
    object_id     = models.CharField(max_length=64)
    object_repr   = models.TextField(blank=True)
    action        = models.CharField(max_length=10, choices=ACTIONS)
    change_message= models.TextField(blank=True)         # JSON/text diff

    class Meta:
        indexes = [models.Index(fields=["model_name","object_id","timestamp"])]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp} {self.model_name} {self.object_id} {self.action}"


class LockPeriod(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    locked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    locked_on = models.DateTimeField(auto_now_add=True)

    def is_locked(self, date):
        return self.start_date <= date <= self.end_date

    def __str__(self):
        return f"Locked from {self.start_date} to {self.end_date}"
    
    
    
# accounting_app/models_period.py
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now

class AccountingPeriod(models.Model):
    """
    Monthly accounting period that can be locked/unlocked.
    One row per (year, month).
    """
    STATUS_OPEN = "OPEN"
    STATUS_LOCKED = "LOCKED"
    STATUS_CHOICES = (
        (STATUS_OPEN, "Open"),
        (STATUS_LOCKED, "Locked"),
    )

    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()  # 1..12
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default=STATUS_OPEN)

    locked_on = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="periods_locked"
    )

    class Meta:
        unique_together = (("year", "month"),)
        ordering = ("-year", "-month")

    def __str__(self):
        return f"{self.year}-{self.month:02d} [{self.status}]"

    def clean(self):
        if not (1 <= int(self.month) <= 12):
            raise ValidationError({"month": "Month must be 1..12."})

    def lock(self, user=None):
        if self.status == self.STATUS_LOCKED:
            return False
        self.status = self.STATUS_LOCKED
        self.locked_on = now()
        if user:
            self.locked_by = user
        self.save(update_fields=["status", "locked_on", "locked_by"])
        return True

    def unlock(self, user=None):
        if self.status == self.STATUS_OPEN:
            return False
        self.status = self.STATUS_OPEN
        # keep locked_on/locked_by history
        self.save(update_fields=["status"])
        return True


class Approval(models.Model):
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    approved_on = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved')])

from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now

class ApprovalRequest(models.Model):
    """Attach an approval flow to any object (JournalEntry, Invoice, etc.)."""
    STATUS = [
        ("PENDING", "Pending"),
        ("REVIEWED", "Reviewed"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]
    target_ct = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_id = models.CharField(max_length=50)
    target = GenericForeignKey("target_ct", "target_id")

    title = models.CharField(max_length=190)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="approvals_requested")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approvals_assigned")
    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "created_on"])]

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}] -> {self.target_ct.model}#{self.target_id}"
# accounting_app/models_controls.py
from django.conf import settings
from django.db import models
from django.utils.timezone import now

class ControlArea(models.Model):
    """Optional grouping for controls, e.g., 'AP', 'AR', 'GL', 'Revenue'."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

class ControlTask(models.Model):
    CADENCE_DAILY = "DAILY"
    CADENCE_WEEKLY = "WEEKLY"
    CADENCE_MONTHLY = "MONTHLY"
    CADENCE_QUARTERLY = "QUARTERLY"
    CADENCE_ANNUAL = "ANNUAL"
    CADENCE_CHOICES = (
        (CADENCE_DAILY, "Daily"),
        (CADENCE_WEEKLY, "Weekly"),
        (CADENCE_MONTHLY, "Monthly"),
        (CADENCE_QUARTERLY, "Quarterly"),
        (CADENCE_ANNUAL, "Annual"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="owned_controltask", null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="created_controltask", null=True, blank=True
    )

    area = models.ForeignKey(ControlArea, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    cadence = models.CharField(max_length=12, choices=CADENCE_CHOICES, default=CADENCE_MONTHLY)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("area__name", "title")
        permissions = [
            ("complete_controltaskinstance", "Can mark control task instances complete"),
            ("view_controls_dashboard", "Can view controls dashboard"),
        ]

    def __str__(self):
        return self.title

class ControlTaskInstance(models.Model):
    """
    A concrete occurrence of a ControlTask for a period (year + optional month).
    For weekly/daily cadences, you can extend with week number or date fields.
    """
    task = models.ForeignKey(ControlTask, related_name="instances", on_delete=models.CASCADE)
    period_year = models.PositiveIntegerField()
    period_month = models.PositiveSmallIntegerField(null=True, blank=True)  # null for non-monthly cadences
    due_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="owned_controlinstance", null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        related_name="created_controlinstance", null=True, blank=True
    )

    completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    completed_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (("task", "period_year", "period_month"),)
        ordering = ("-period_year", "-period_month", "task__title")

    def __str__(self):
        pm = f"-{self.period_month:02d}" if self.period_month else ""
        return f"{self.task.title} [{self.period_year}{pm}]"


from django.conf import settings  # ✅ Import this
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

# class ComplianceLog(models.Model):
#     content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#     object_id = models.PositiveIntegerField()
#     object_ref = GenericForeignKey('content_type', 'object_id')

#     action = models.CharField(max_length=100)
#     indas_code = models.CharField(max_length=50, blank=True)
#     ifrs_code = models.CharField(max_length=50, blank=True)
#     description = models.TextField()
#     timestamp = models.DateTimeField(auto_now_add=True)

#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL,  # ✅ use this instead of 'auth.User'
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True
#     )

#     class Meta:
#         ordering = ['-timestamp']


from django.db import models
from django.utils import timezone

class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)  # e.g., USD, EUR
    name = models.CharField(max_length=50, blank=True, null=True)
    symbol = models.CharField(max_length=10, blank=True, null=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_currency",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_currency", null=True, blank=True
    )

    def __str__(self):
        return f"{self.code} - {self.name or ''}"

    def save(self, *args, **kwargs):
        code_upper = self.code.upper()

        default_data = {
            'USD': {'name': 'US Dollar', 'symbol': '$'},
            'EUR': {'name': 'Euro', 'symbol': '€'},
            'INR': {'name': 'Indian Rupee', 'symbol': '₹'},
            'GBP': {'name': 'British Pound', 'symbol': '£'},
            'JPY': {'name': 'Japanese Yen', 'symbol': '¥'},
            'AUD': {'name': 'Australian Dollar', 'symbol': 'A$'},
            'CAD': {'name': 'Canadian Dollar', 'symbol': 'C$'},
            'CNY': {'name': 'Chinese Yuan', 'symbol': '¥'},
            'CHF': {'name': 'Swiss Franc', 'symbol': 'CHF'},
            'SGD': {'name': 'Singapore Dollar', 'symbol': 'S$'},
        }

        if code_upper in default_data:
            if not self.name:
                self.name = default_data[code_upper]['name']
            if not self.symbol:
                self.symbol = default_data[code_upper]['symbol']

        self.code = code_upper  # always store in uppercase
        super().save(*args, **kwargs)


class ExchangeRate(models.Model):
    from_currency = models.ForeignKey(Currency, related_name='from_rates', on_delete=models.CASCADE)
    to_currency = models.ForeignKey(Currency, related_name='to_rates', on_delete=models.CASCADE)
    rate = models.DecimalField(max_digits=12, decimal_places=6)
    date = models.DateField(default=timezone.now)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_exchangerate",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_exchangerate", null=True, blank=True
    )

    class Meta:
        unique_together = ('from_currency', 'to_currency', 'date')

class CostCenter(models.Model):
    code = models.CharField(max_length=3,null=True, blank=True)  # e.g., CC1, CC2
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    currency = models.ForeignKey('Currency', on_delete=models.SET_NULL, null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_costcenter",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_costcenter", null=True, blank=True
    )

    
    

    def __str__(self):
        return self.name

class InterCompanyTransaction(models.Model):
    from_company = models.CharField(max_length=100)
    to_company = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_inter",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_inter", null=True, blank=True
    )

    def __str__(self):
        return f"{self.from_company} → {self.to_company} : {self.amount}"

class DeferredRevenue(models.Model):
    customer = models.ForeignKey(Client, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_deferred",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_deferred", null=True, blank=True
    )

    def recognition_per_month(self):
        months = max(1, ((self.end_date.year - self.start_date.year) * 12 + self.end_date.month - self.start_date.month + 1))
        return round(self.amount / months, 2)
    
    
    
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta, date

class Plan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # monthly
    trial_days = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_plan",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_plan", null=True, blank=True
    )

    interval = models.CharField(max_length=20,null=True, choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')])
    def get_interval_delta(self):
        if self.interval == 'yearly':
            return timedelta(days=365)
        return timedelta(days=30)
    def __str__(self):
        return f"{self.name} (${self.price}/mo)"


class Subscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    trial = models.BooleanField(default=False)
    trial_end_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_subscription",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_subscription", null=True, blank=True
    )

    active = models.BooleanField(default=True)
    next_billing_date = models.DateField(null=True, blank=True)
    last_renewed_at = models.DateTimeField(null=True, blank=True)
    def is_trialing(self):
        return self.trial and self.next_billing_date and date.today() < self.next_billing_date

    def is_active(self):
        return self.active and (self.next_billing_date is None or date.today() <= self.next_billing_date)
    
    def renew(self):
        self.last_renewed_at = now()
        self.next_billing_date += self.plan.get_interval_delta()
        self.save()
        
    def __str__(self):
        return f"{self.user} - {self.plan.name} ({'Trial' if self.trial else 'Active'})"

class Credit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=155, blank=True)
    
    
    
    


from django.db import models
from django.utils.timezone import now
from decimal import Decimal
from datetime import date
from accounting_app.models import Account, Project, CostCenter, Currency


# ----------------------
# 📘 Budget Model
# ----------------------
class Budget(models.Model):
    PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ]

    name = models.CharField(max_length=100)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='budgets')

    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True)
    year = models.PositiveIntegerField(default=date.today().year)
    month = models.PositiveIntegerField(null=True, blank=True)  # used only if period is monthly
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='monthly')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_budget",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_budget", null=True, blank=True
    )

    def __str__(self):
        label = f"{self.name} - {self.year}"
        if self.month:
            label += f"-{self.month:02d}"
        return label
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.project:
         self.project.sync_budget()
    def delete(self, *args, **kwargs):
        project = self.project
        super().delete(*args, **kwargs)
        if project:
         project.sync_budget()



# ----------------------
# 🔁 Rolling Forecasts
# ----------------------
from accounting_app.utils import generate_forecast_variance
import calendar
class Forecast(models.Model):
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True)
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    forecast_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_forecast",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_forecast", null=True, blank=True
    )
    @property
    def month_name(self):
        if self.month:
            return calendar.month_name[self.month]
        return ""

    def __str__(self):
        return f"{self.project or self.account} - {self.month}/{self.year}"
    
    # Forecast save override
    def save(self, *args, **kwargs):
     super().save(*args, **kwargs)
     CashFlowProjection.objects.get_or_create(
        project=self.project,
        account=self.account,
        date=date(self.year, self.month, 1),
        amount=self.forecast_amount,
        direction='inflow',
        description='Auto from Forecast',
        currency=None,
        created_by=self.created_by or self.owner # if you add this to Forecast
    )
    # In Forecast model
    
    
    




# ----------------------
# 🔮 What-if Scenarios
# ----------------------
class WhatIfScenario(models.Model):
    SCENARIO_TYPE = [
        ('revenue', 'Revenue Increase'),
        ('expense', 'Expense Reduction'),
        ('custom', 'Custom or Strategic Scenarios'),
        ('project','Project-Based Scenarios')
    ]
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_whatif",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_whatif", null=True, blank=True
    )
    name = models.CharField(max_length=190)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.SET_NULL, null=True, blank=True)
    scenario_type = models.CharField(max_length=20, choices=SCENARIO_TYPE)
    percentage_change = models.DecimalField(max_digits=5, decimal_places=2, help_text="e.g. 10 for +10%", default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def apply_scenario(self, base_amount: Decimal) -> Decimal:
        return base_amount * (1 + (self.percentage_change / 100))

    def __str__(self):
        return f"{self.name} - {self.scenario_type}"
    # models.py


    

    @property
    def base_amount(self):
     from accounting_app.models import Forecast, Budget  # avoid circular import
     forecast_qs = Forecast.objects.filter(
        project=self.project,
        account=self.account
     ).order_by('-year', '-month')

     if forecast_qs.exists():
        return forecast_qs.first().forecast_amount

     budget_qs = Budget.objects.filter(
        project=self.project,
        account=self.account,
        year=date.today().year
    )
     return budget_qs.first().amount if budget_qs.exists() else Decimal('0.00')

    # @property
    @property
    def impact_amount(self):
              return self.apply_scenario(self.base_amount)

    def save(self, *args, **kwargs):
        # Optionally update impact_amount before saving
        if self.base_amount:
            self.impact_amount = self.apply_scenario(self.base_amount)

        super().save(*args, **kwargs)

        # Then create a Cash Flow Projection
        CashFlowProjection.objects.get_or_create(
            project=self.project,
            account=self.account,
            date=date.today(),
            amount=abs(self.impact_amount),
    direction='inflow' if self.impact_amount > 0 else 'outflow',
            description=f'Auto from Scenario: {self.name}',
            currency=None ,
            created_by=self.owner# Set if your scenario model includes currency
        )




# ----------------------
# 💰 Cash Flow Projections
# ----------------------
class CashFlowProjection(models.Model):
    DIRECTION_CHOICES = [('inflow', 'Inflow'), ('outflow', 'Outflow')]

    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    description = models.CharField(max_length=190, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_cashflow",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_cashflow", null=True, blank=True
    )

    def __str__(self):
        return f"{self.date} - {self.direction} - {self.amount}"



# ----------------------
# 📈 Forecast vs Actual Variance
# ----------------------
class ForecastVariance(models.Model):
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    forecast = models.ForeignKey(Forecast, on_delete=models.CASCADE)
    actual_amount = models.DecimalField(max_digits=12, decimal_places=2)
    calculated_on = models.DateTimeField(auto_now_add=True)

    @property
    def variance(self):
        return self.actual_amount - self.forecast.forecast_amount

    @property
    def variance_percent(self):
        if self.forecast.forecast_amount == 0:
            return None
        return (self.variance / self.forecast.forecast_amount) * 100

    def __str__(self):
        name = self.project.name if self.project else self.account.name if self.account else "N/A"
        forecast_amt = self.forecast.forecast_amount
        variance_amt = self.variance
        variance_pct = f"{self.variance_percent:.2f}%" if self.variance_percent is not None else "N/A"
        return (
            f"{name} ({self.forecast.month}/{self.forecast.year}) - "
            f"Forecast: {forecast_amt}, Actual: {self.actual_amount}, "
            f"Variance: {variance_amt}, Variance %: {variance_pct}"
        )


from django.db import models
from django.utils import timezone
from datetime import date, timedelta

ASSET_CATEGORY_CHOICES = [
    ('IT', 'IT Equipment'),
    ('FURN', 'Furniture'),
    ('VEH', 'Vehicle'),
    ('PLANT', 'Plant & Machinery'),
    ('OTH', 'Other'),
]

class FixedAsset(models.Model):
    asset_tag = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=ASSET_CATEGORY_CHOICES)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_fixed",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_fixed", null=True, blank=True
    )
    
    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    useful_life = models.PositiveIntegerField(help_text="Useful life in years")
    
    # Capitalization
    capitalized = models.BooleanField(default=True)

    # Warranty & maintenance
    warranty_expiry = models.DateField(blank=True, null=True)
    maintenance_schedule = models.TextField(blank=True, null=True)
    next_maintenance_date = models.DateField(blank=True, null=True)

    # Disposal/Write-off
    disposed = models.BooleanField(default=False)
    disposal_date = models.DateField(blank=True, null=True)
    disposal_value = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    written_off = models.BooleanField(default=False)

    # Depreciation
    accumulated_depreciation = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_depreciation_date = models.DateField(blank=True, null=True)

    def calculate_depreciation(self):
        """Straight-line depreciation calculation"""
        if not self.capitalized or self.disposed:
            return 0

        today = date.today()
        total_months = self.useful_life * 12
        monthly_depreciation = self.purchase_price / total_months

        if self.last_depreciation_date:
            months_elapsed = (today.year - self.last_depreciation_date.year) * 12 + (today.month - self.last_depreciation_date.month)
        else:
            months_elapsed = (today.year - self.purchase_date.year) * 12 + (today.month - self.purchase_date.month)

        months_elapsed = max(0, min(months_elapsed, total_months))

        expected_depreciation = monthly_depreciation * months_elapsed
        depreciation_to_record = expected_depreciation - self.accumulated_depreciation
        return round(depreciation_to_record, 2)

    def net_book_value(self):
        """Current value of the asset after depreciation"""
        return max(self.purchase_price - self.accumulated_depreciation, 0)

    def __str__(self):
        return f"{self.asset_tag} - {self.name}"
    def is_maintenance_due(self):
        if self.next_maintenance_date:
            return self.next_maintenance_date <= timezone.now().date()
        return False
def post_monthly_depreciation(self):
    """Posts depreciation for the next month if due."""
    from datetime import timedelta
    from .models import DepreciationEntry  # ensure import if needed

    if not self.capitalized or self.disposed:
        return

    today = date.today()
    next_date = self.last_depreciation_date or self.purchase_date

    # Align to first of month
    if next_date.day != 1:
        next_date = next_date.replace(day=1)

    if next_date > today:
        return

    total_months = self.useful_life * 12
    monthly_depr = self.purchase_price / total_months
    months_used = (next_date.year - self.purchase_date.year) * 12 + (next_date.month - self.purchase_date.month)

    if months_used >= total_months:
        return

    # Update asset fields
    self.accumulated_depreciation += monthly_depr
    self.last_depreciation_date = next_date
    self.save()

    # Create entry
    DepreciationEntry.objects.create(
        asset=self,
        date=next_date,
        amount=monthly_depr,
        accumulated=self.accumulated_depreciation
    )


# models.py

# fixedassets/models.py

class DepreciationEntry(models.Model):
    asset = models.ForeignKey(FixedAsset, on_delete=models.CASCADE, related_name="depreciation_entries")
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    accumulated = models.DecimalField(max_digits=12, decimal_places=2,null=True)

    class Meta:
        unique_together = ('asset', 'date')
        ordering = ['date']

    def __str__(self):
        return f"{self.asset.name} - {self.date} - {self.amount}"






# expenses/models.py

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from datetime import date

EXPENSE_CATEGORIES = [
    ("TRAVEL", "Travel"),
    ("MEALS", "Meals"),
    ("SUPPLIES", "Supplies"),
    ("OTHER", "Other"),
]

APPROVAL_STATUS = [
    ("PENDING", "Pending"),
    ("APPROVED", "Approved"),
    ("REJECTED", "Rejected"),
]

# ✳️ Policy limits per category
EXPENSE_LIMITS = {
    "TRAVEL": 5000,
    "MEALS": 2000,
    "SUPPLIES": 1000,
    "OTHER": 3000,
}

class EmployeeExpense(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()
    category = models.CharField(max_length=20, choices=EXPENSE_CATEGORIES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    receipt = models.FileField(upload_to="expense_receipts/", blank=True, null=True)
    status = models.CharField(max_length=10, choices=APPROVAL_STATUS, default="PENDING")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="reviewed_expenses",
        on_delete=models.SET_NULL
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_employeeexpense",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_employeeexpense", null=True, blank=True
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)

    def clean(self):
        # ✳️ Block future-dated expenses
        if self.date > date.today():
            raise ValidationError("Expense date cannot be in the future.")

        # ✳️ Enforce category limit
        max_allowed = EXPENSE_LIMITS.get(self.category, 999999)
        if self.amount > max_allowed:
            raise ValidationError(f"Amount exceeds allowed limit for {self.category} (₹{max_allowed}).")

    def __str__(self):
        return f"{self.employee.email} - {self.category} - ₹{self.amount}"


from django.db import models
from django.utils.timezone import now
from accounting_app.models import Invoice
from .models import Client, Project


class ClientContract(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    details = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_clientcontract",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_clientcontract", null=True, blank=True
    )

    def __str__(self):
        return f"{self.client.name} – {self.name}"


class Retainer(models.Model):
    contract = models.ForeignKey(ClientContract, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    billing_day = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_retainer",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_retainer", null=True, blank=True
    )

class BillingMilestone(models.Model):
    contract = models.ForeignKey(ClientContract, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    completed_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_billed = models.BooleanField(default=False)
    billed_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_milestone",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_milestone", null=True, blank=True
    )

class Phase(models.Model):
    
    contract = models.ForeignKey(ClientContract, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    revenue_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_phase",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_phase", null=True, blank=True
    )
    
    

class Deal(models.Model):
  
    client = models.ForeignKey(Client, on_delete=models.CASCADE,default=None, null=True, blank=True)
    contract = models.ForeignKey(ClientContract, on_delete=models.CASCADE,default=None, null=True, blank=True)
    title = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expected_close = models.DateField()
    stage = models.CharField(max_length=50)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_deal",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_deal", null=True, blank=True
    )
    def __str__(self):
        return self.name or self.email or f"CRM-{self.pk}"

class Commission(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE,related_name="commissions")
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    paid = models.BooleanField(default=False)
    # Example for Invoice model
    razorpay_order_id = models.CharField(max_length=255, null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_commission",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_commission", null=True, blank=True
    )


class Quote(models.Model):
    deal = models.ForeignKey('Deal', on_delete=models.CASCADE, related_name='quotes')
    client = models.ForeignKey(Client, on_delete=models.CASCADE,null=True, blank=True)
    title = models.CharField(max_length=100,default="Quote for Deal")
    amount = models.DecimalField(max_digits=12, decimal_places=2,default=0)
    status = models.CharField(max_length=20, choices=[('draft', 'Draft'), ('approved', 'Approved')],default='draft')
    created_date = models.DateField(default=now)
    approved = models.BooleanField(default=False)
    pdf_file = models.FileField(upload_to='quotes/', null=True, blank=True)  # optional
    notes = models.TextField(blank=True)
    paid = models.BooleanField(default=False)
    # Example for Invoice model
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_quote",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_quote", null=True, blank=True
    )


    def __str__(self):
        return f"Quote for {self.deal.title}"


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_payment",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_payment", null=True, blank=True
    )
    date = models.DateField(default=now)
    method = models.CharField(max_length=50, choices=[('razorpay', 'Razorpay'), ('manual', 'Manual')],default='razorpay')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    paid_on = models.DateTimeField(default=now)
    confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f"Payment of ₹{self.amount} for Invoice #{self.invoice.id}"
    
    
    
from django.db import models
from django.utils import timezone

class ScheduledTask(models.Model):
    name = models.CharField(max_length=100, unique=True)
    last_run = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

class GSTR1(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE,null=True, blank=True)
    month = models.CharField(max_length=15)
    year = models.IntegerField()

    # You may want to link invoices
    invoices = models.ManyToManyField(Invoice, blank=True)

    total_sales = models.DecimalField(max_digits=12, decimal_places=2)
    taxable_value = models.DecimalField(max_digits=12, decimal_places=2)
    cgst = models.DecimalField(max_digits=10, decimal_places=2)
    sgst = models.DecimalField(max_digits=10, decimal_places=2)
    igst = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

# -------------------------------
# 2. GSTR-3B: Monthly Summary
# -------------------------------

class GSTR3B(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE,null=True, blank=True)
    month = models.CharField(max_length=15)
    year = models.IntegerField()

    outward_supplies = models.DecimalField(max_digits=12, decimal_places=2)
    inward_supplies = models.DecimalField(max_digits=12, decimal_places=2)
    net_tax_liability = models.DecimalField(max_digits=12, decimal_places=2)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_gstr3",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_gstr3", null=True, blank=True
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

# -------------------------------
# 3. GSTR-9: Annual Summary
# -------------------------------

class GSTR9(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE,null=True, blank=True)
    year = models.IntegerField()

    annual_turnover = models.DecimalField(max_digits=15, decimal_places=2)
    total_tax_paid = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

# -------------------------------
# 4. E-Invoice Record
# -------------------------------

class EInvoice(models.Model):
    invoice = models.OneToOneField(Invoice, on_delete=models.CASCADE,null=True, blank=True)
    irn = models.CharField(max_length=50)
    ack_no = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
    generated_on = models.DateField()

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

# -------------------------------
# 5. TDS Report
# -------------------------------

class TDSReport(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE,null=True, blank=True)
    form_26q = models.TextField()  # OR use FileField if storing PDFs
    form_24q = models.TextField()

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

# -------------------------------
# 6. E-Way Bill
# -------------------------------

class EWayBill(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE,default=None, null=True, blank=True)
    eway_bill_no = models.CharField(max_length=50)
    valid_until = models.DateField()
    status = models.CharField(max_length=20)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    
# models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now

class UserActivityLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('failed_login', 'Failed Login'),
    ]
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_useractivity",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_useractivity", null=True, blank=True
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    attempted_username = models.CharField(max_length=100, null=True, blank=True) 
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(default=now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    def __str__(self):
        if self.user:
            identifier = self.user.email or self.user.username
        else:
            identifier = self.attempted_username or "Unknown"
        return f"{identifier} - {self.get_action_display()} @ {self.timestamp:%Y-%m-%d %H:%M}"


from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now

class GdprRequest(models.Model):
    REQUEST_TYPES = [
        ('delete', 'Delete Account'),
        ('export', 'Export Data'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    timestamp = models.DateTimeField(default=now)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_gdpr",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_gdpr", null=True, blank=True
    )

    def __str__(self):
        return f"{self.user.email} - {self.request_type} ({self.status})"
    
    
    
class BrandingSettings(models.Model):
    admin_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,null=True, blank=True)
    background = models.ImageField(upload_to='invoice_backgrounds/', blank=True, null=True)
    company_name = models.CharField(max_length=100)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_branding",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_branding", null=True, blank=True
    )
    logo = models.ImageField(upload_to='branding/logos/')
    primary_color = models.CharField(max_length=7, default='#007bff', help_text='Hex color like #007bff')

    def __str__(self):
        return f"Branding for {self.company_name}"

# accounting_app/models.py
from django.db import models
from django.contrib.auth.models import User

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    title = models.CharField(max_length=100,null=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']  # newest first

    def __str__(self):
        return f"{self.title} ({self.created_at:%Y-%m-%d %H:%M})"

# profiles/models.py
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
User = get_user_model()


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_profile",null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_profile", null=True, blank=True
    )

    def __str__(self):
        return self.user.username

import uuid
from django.conf import settings
from django.db import models
from django.utils.timezone import now, timedelta

class PasswordResetToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return now() > self.created_at + timedelta(hours=1)  # token valid 1 hour

    def __str__(self):
        return f"PasswordResetToken for {self.user.email}"

# core/models.py
from django.conf import settings
from django.db import models

class ErrorLog(models.Model):
    created_at     = models.DateTimeField(auto_now_add=True)
    path           = models.CharField(max_length=190)
    method         = models.CharField(max_length=8)
    user           = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    exception_type = models.CharField(max_length=128)
    exception_msg  = models.TextField()
    traceback      = models.TextField()
    get_data       = models.JSONField(default=dict, blank=True)
    post_data      = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

# core/models.py (add this)
from django.conf import settings
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class ModelMessage(models.Model):
    LEVELS = (
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    )
    created_at     = models.DateTimeField(auto_now_add=True)
    created_by     = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    level          = models.CharField(max_length=16, choices=LEVELS, default='info')
    text           = models.TextField()

    # generic relation to ANY model instance
    content_type   = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id      = models.CharField(max_length=64)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-created_at']
