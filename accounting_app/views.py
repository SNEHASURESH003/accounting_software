from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from .models import Project
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.utils.timezone import now
from django.contrib.admin.views.decorators import staff_member_required
from datetime import timedelta

from django.db.models import Sum, F, FloatField

from .models import Project, Invoice, InvoiceItem, JournalItem, Account, User,TaxRecord,TDSRecord

from .forms import ProjectForm,FilingRecord
from datetime import date


from .models import (
    User, Account, JournalEntry, JournalItem,
    Invoice, InvoiceItem, TimeEntry, Client,EmployeeTaxSummary,TaxDeclaration
)
from .forms import (
    EmailLoginForm, UserCreateForm, JournalItemForm, JournalItemFormSet,
    AccountForm, InvoiceForm, InvoiceItemFormSet, TimeEntryFormSet,JournalEntryForm,TaxDeclarationForm,FilingRecordForm
)

# -----------------------------
# ✅ Login / Logout Views
# -----------------------------

# class CustomLoginView(LoginView):
#     template_name = 'registration/login.html'
#     authentication_form = EmailLoginForm

#     def get_success_url(self):
#         next_url = self.request.POST.get('next') or self.request.GET.get('next')
#         if next_url:
#             return next_url

#         user = self.request.user
#         if user.is_superuser:
#             return reverse('users_list')
#         if user.groups.filter(name='Accountant').exists():
#             return reverse('dashboard')
#         if user.groups.filter(name='Staff').exists():
#             return reverse('invoice_list')

#         return super().get_success_url()
    
    
# forms.py

from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.views import LoginView

from .models import UserActivityLog   # <-- adjust import path if different
from .forms import EmailLoginForm         # your form

def _ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR'))


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = EmailLoginForm

    # ✅ Log successful logins
    def form_valid(self, form):
        response = super().form_valid(form)   # logs user in
        user = self.request.user if self.request.user.is_authenticated else None
        now = timezone.now()

        # Avoid duplicate row if auth signal also fires (3s window)
        if user and not UserActivityLog.objects.filter(
            user=user, action='login', timestamp__gte=now - timedelta(seconds=3)
        ).exists():
            UserActivityLog.objects.create(
                user=user,
                action='login',
                timestamp=now,
                ip_address=_ip(self.request),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            )
        return response

    # ✅ Log failed logins
    def form_invalid(self, form):
        UserActivityLog.objects.create(
            user=None,
            action='failed_login',
            timestamp=timezone.now(),
            ip_address=_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
        )
        return super().form_invalid(form)

    # your existing redirect logic
    def get_success_url(self):
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url:
            return next_url

        user = self.request.user
        if user.is_superadmin:
            return reverse('superuser_list')
        if getattr(user, "is_superuser", False):
            return reverse('dashboard')
        if user.groups.filter(name='Accountant').exists():
            return reverse('dashboard')
        if user.groups.filter(name='Staff').exists():
            return reverse('invoice_list')
        if getattr(user, "role", "") == "Employee":
            return reverse('my_expenses')

        return super().get_success_url()

from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.utils.translation import gettext_lazy as _

class EmailLoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                _("Your account is inactive due to GDPR policy or admin restriction."),
                code='inactive',
            )


from django.contrib.auth.views import LogoutView

from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views import View

# class MyLogoutView(View):
#     def get(self, request):
#         logout(request)
#         return redirect('login')  # Redirect to your login page or wherever you want

#     def post(self, request):
#         logout(request)
#         return redirect('login')

# views.py
from django.utils import timezone
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views import View
from .models import UserActivityLog

def _ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return (xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR'))

class MyLogoutView(View):
    def get(self, request):
        if request.user.is_authenticated:
            UserActivityLog.objects.create(
                user=request.user, action='logout', timestamp=timezone.now(),
                ip_address=_ip(request), user_agent=request.META.get('HTTP_USER_AGENT','')
            )
        logout(request)  # will also trigger user_logged_out signal
        return redirect('login')
    post = get





# -----------------------------
# ✅ Permission Checks
# -----------------------------

def is_superuser(user):
    return user.is_superuser

def is_accountant(user):
    return user.groups.filter(name='Accountant').exists()
def is_employee(user):
    return user.groups.filter(name='Employee').exists()

def is_accountant_or_superuser(user):
    return user.is_superuser or is_accountant(user)

def is_staff_only(user):
    return user.is_staff and not user.is_superuser
def is_superadmin(user):
    return user.is_authenticated and user.is_superadmin


# -----------------------------
# ✅ User Management (Superuser)
# -----------------------------
from django.contrib.auth import get_user_model

User = get_user_model()
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    User = get_user_model()

    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    # Base queryset (excluding superusers)
    users = User.objects.exclude(is_superuser=True)

    # Apply search filter
    if query:
        parts = query.split()
        if len(parts) > 1:
            users = users.filter(
                Q(first_name__icontains=parts[0]) & Q(last_name__icontains=parts[1])
            )
        else:
            users = users.filter(
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )

    # Apply active/inactive status filter
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    # Apply owner or created_by filter (similar to `account_list`)
    if request.user.is_superuser:
        # Superuser sees users they created, or accounts created by users they created
        users = users.filter(
            Q(created_by=request.user) | Q(owner=request.user)
        )
    else:
        # Regular users see users they own or users created by the superuser who created them
        users = users.filter(
            Q(created_by=request.user.created_by) | Q(owner=request.user)
        )

    # Order by latest created
    users = users.order_by('-date_joined')

    # Pagination logic
    paginator = Paginator(users, 5)  # 5 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'users/user_list.html', {
        'users': page_obj,
        'query': query,
        'status_filter': status_filter,
    })


# @user_passes_test(is_superuser)
# def create_user(request):
#     form = UserCreateForm(request.POST or None)
#     if form.is_valid():
#         form.save()
#         return redirect('users_list')
#     return render(request, 'users/create_user.html', {'form': form})
# views.py
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from django.contrib.auth import get_user_model
from .forms import UserCreateForm, EmployeeCreateForm
from .models import Employee
from django.contrib.auth.models import Group 

User = get_user_model()

def is_superuser(u): return u.is_superuser

@user_passes_test(lambda u: u.is_superuser)
@transaction.atomic
def create_user(request):
    form = UserCreateForm(request.POST or None)

    if form.is_valid():
        user = form.save(commit=False)  # get unsaved user
        user.created_by = request.user   # set created_by superuser
        user.save()  # save user with role + password

        # Add group handling after save
        role = form.cleaned_data["role"]
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)

        if user.role == "Employee":
            return redirect("employee_create_for_user", user_id=user.id)

        messages.success(request, "User created successfully.")
        return redirect("users_list")

    return render(request, "users/create_user.html", {"form": form})


def is_superadmin(user):
    return user.is_authenticated and user.is_superadmin

@login_required
@user_passes_test(is_superadmin)
def superuser_list(request):
    superusers = User.objects.filter(is_superuser=True, is_superadmin=False).order_by("-date_joined")
    return render(request, "users/superuser_list.html", {"superusers": superusers})


@login_required
@user_passes_test(is_superadmin)
def edit_superuser(request, user_id):
    superuser = get_object_or_404(User, id=user_id, is_superuser=True, is_superadmin=False)

    if request.method == "POST":
        form = SuperuserRegistrationForm(request.POST, instance=superuser)
        if form.is_valid():
            form.save()
            messages.success(request, f"Superuser {superuser.email} updated successfully.")
            return redirect("superuser_list")
    else:
        form = SuperuserRegistrationForm(instance=superuser)

    return render(request, "users/edit_superuser.html", {"form": form, "superuser": superuser})


@login_required
@user_passes_test(is_superadmin)
def delete_superuser(request, user_id):
    superuser = get_object_or_404(User, id=user_id, is_superuser=True, is_superadmin=False)

    if request.method == "POST":
        email = superuser.email
        superuser.delete()
        messages.success(request, f"Superuser {email} deleted successfully.")
        return redirect("superuser_list")

    return render(request, "users/delete_superuser.html", {"superuser": superuser})
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import SuperuserRegistrationForm
from .models import User

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

@login_required
@user_passes_test(is_superadmin)
def toggle_superuser_status(request, user_id):
    superuser = get_object_or_404(User, id=user_id, is_superuser=True, is_superadmin=False)
    superuser.is_active = not superuser.is_active
    superuser.save()
    messages.success(request, f"Superuser {superuser.email} status updated.")
    return redirect("superuser_list")




@login_required
@user_passes_test(is_superadmin)
def register_superuser(request):
    if request.method == "POST":
        form = SuperuserRegistrationForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            messages.success(
                request,
                f"Superuser {new_user.email} created successfully! They can now log in."
            )
            # ✅ Instead of redirecting to dashboard, send back to login page
            return redirect("superuser_list")
    else:
        form = SuperuserRegistrationForm()
    return render(request, "users/register_superuser.html", {"form": form})



from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

@user_passes_test(lambda u: u.is_superuser or u.is_accountant)  # allow both
@transaction.atomic
def employee_create_for_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    # Block linking employees to superusers
    if user.is_superuser:
        raise PermissionDenied("Superusers cannot have an Employee profile.")

    # Check if employee already exists for this user
    emp = Employee.objects.filter(user=user).first()

    # Pre-fill if creating
    initial = {}
    if not emp:
        initial = {
            "name": (f"{user.first_name} {user.last_name}".strip()
                     or user.email.split("@")[0].title()),
            "email": user.email,
        }

    form = EmployeeCreateForm(request.POST or None, instance=emp, user_instance=user)

    if form.is_valid():
        emp = form.save(commit=False)
        emp.user = user

        # 🔑 Ownership logic (consistent)
        if request.user.is_superuser:
            # Superuser-created employee
            emp.created_by = request.user
            emp.owner = request.user
        else:
            # Accountant-created employee
            emp.created_by = request.user
            emp.owner = request.user.created_by  # must be superuser

        emp.save()
        messages.success(request, "Employee profile saved.")
        return redirect("users_list")

    return render(request, "employees/employee_create_for_user.html", {
        "form": form,
        "user_obj": user,
    })



from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Employee

@user_passes_test(lambda u: u.is_superuser)
@login_required
def delete_employee(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == "POST":
        employee.delete()
        messages.success(request, "Employee deleted successfully.")
    return redirect("employee_list")  # update to your list view name




from django.views.decorators.http import require_POST

from django.db import IntegrityError, transaction

@user_passes_test(lambda u: u.is_superuser)
@login_required
@require_POST
def delete_user(request, user_id):
    User = get_user_model()
    user_to_delete = get_object_or_404(User, id=user_id)

    if request.user.id == user_to_delete.id:
        messages.error(request, "❌ You cannot delete yourself.")
        return redirect('users_list')

    try:
        with transaction.atomic():
            user_to_delete.delete()
            messages.success(request, f"✅ User {user_to_delete.email} deleted successfully.")
    except IntegrityError as e:
        messages.error(request, f"⚠️ Could not delete user {user_to_delete.email}. They may be referenced elsewhere.")
    except Exception as e:
        messages.error(request, f"❌ Error: {str(e)}")

    return redirect('users_list')




from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .forms import UserCreateForm  # You can reuse this form for edit

User = get_user_model()


@user_passes_test(lambda u: u.is_superuser)
@login_required
def view_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    return render(request, 'users/view_user.html', {'user_obj': user})


@user_passes_test(lambda u: u.is_superuser)
@login_required
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    form = UserCreateForm(request.POST or None, instance=user)

    if form.is_valid():
        form.save()
        messages.success(request, f"✅ User {user.email} updated successfully.")
        return redirect('users_list')

    return render(request, 'users/edit_user.html', {'form': form, 'user_obj': user})


# -----------------------------
# ✅ Accountant Views
# -----------------------------
# dashboards/views.py
from datetime import date, timedelta
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from django.utils.timezone import now
from django.shortcuts import render

from accounting_app.models import (
    Invoice, EmployeeExpense, GSTR3B, TDSRecord, CashFlowProjection,
    FixedAsset, DepreciationEntry, Client, Project, Deal, Quote,
    Employee, Payroll, ApprovalRequest, AccountingPeriod, Subscription, Credit
)
# Procurement
from accounting_app.models_procurement import (
    PurchaseRequisition, PurchaseOrder, VendorBill, VendorPayment
)
# CRM (use your actual app path)
try:
    from integrations.models import CRMClient
except Exception:
    from accounting_app.models import CRMClient  # fallback if you moved it here

# Version history store
from .versioning import VersionHistory


from django.db.models import Sum
from django.db.models.functions import TruncMonth
from datetime import date
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Value
from datetime import date
from decimal import Decimal
from django.db.models import Subquery, OuterRef, DecimalField
from django.db.models.functions import Coalesce, Greatest



User = get_user_model()
D0 = Value(Decimal("0"))
HUNDRED = Value(Decimal("100"))

# simple test used below
def is_accountant_or_superuser(u):
    return bool(u.is_superuser or u.groups.filter(name="Accountant").exists())

@login_required
@user_passes_test(is_accountant_or_superuser)
def dashboard(request):
    u = request.user
    today = now().date()
    start_this_month = today.replace(day=1)

    # -----------------------------
    # Tenant scoping (no helpers)
    # -----------------------------
    # org root = user if superadmin/superuser; otherwise walk created_by chain
    root = u
    if not (getattr(u, "is_superadmin", False) or getattr(u, "is_superuser", False) or getattr(u, "role", "") in ("SuperAdmin", "Superuser")):
        seen = set()
        cur = u
        while getattr(cur, "created_by_id", None) and cur.created_by_id not in seen:
            seen.add(cur.id)
            cur = cur.created_by
        root = cur

    ids = {root.id}
    frontier = {root.id}
    while frontier:
        children = list(User.objects.filter(created_by_id__in=frontier).values_list("id", flat=True))
        new_ids = set(children) - ids
        if not new_ids:
            break
        ids |= new_ids
        frontier = new_ids
    tenant_users = User.objects.filter(id__in=ids)

    def scope(qs):
        fields = {f.name for f in qs.model._meta.get_fields()}
        cond = Q()
        if "created_by" in fields:
            cond |= Q(created_by__in=tenant_users)
        if "owner" in fields:
            cond |= Q(owner__in=tenant_users)
        return qs.filter(cond) if cond != Q() else qs.none()

    # -----------------------------
    # KPIs (Invoices with correct Outstanding)
    # -----------------------------
    inv_qs = scope(Invoice.objects.all())

    # inclusive total (amount + GST) and payments
    inv_qs = inv_qs.annotate(
        inclusive_total=ExpressionWrapper(
            F("total_amount") + (F("total_amount") * Coalesce(F("gst_percent"), D0) / HUNDRED),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        paid_sum=Coalesce(Sum("payment__amount"), D0),  # sums related payments
    ).annotate(
        amount_due_inclusive=ExpressionWrapper(
            F("inclusive_total") - F("paid_sum"),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        )
    )

    invoices_total  = inv_qs.count()
    invoices_paid   = inv_qs.filter(Q(status__iexact="paid") | Q(is_paid=True)).count()
    invoices_unpaid = invoices_total - invoices_paid

    # Revenue (Paid) = tax-inclusive total of PAID invoices
    revenue_total = inv_qs.filter(Q(status__iexact="paid") | Q(is_paid=True))\
                          .aggregate(s=Coalesce(Sum("inclusive_total"), D0))["s"] or 0

    # Outstanding (Unpaid) = tax-inclusive dues (unpaid/partial)
    outstanding_total = inv_qs.filter(
        Q(status__iexact="unpaid") | Q(status__iexact="partial") | Q(is_paid=False)
    ).aggregate(s=Coalesce(Sum("amount_due_inclusive"), D0))["s"] or 0

    # Employee expenses
    exp_qs = scope(EmployeeExpense.objects.all())
    expense_total   = exp_qs.filter(status="APPROVED").aggregate(s=Coalesce(Sum("amount"), D0))["s"] or 0
    expense_pending = exp_qs.filter(status="PENDING").aggregate(s=Coalesce(Sum("amount"), D0))["s"] or 0

    # Compliance
    gst_qs = scope(GSTR3B.objects.all())
    tds_qs = scope(TDSRecord.objects.all())
    gst_liability = gst_qs.aggregate(s=Coalesce(Sum("net_tax_liability"), D0))["s"] or 0
    tds_total     = tds_qs.aggregate(s=Coalesce(Sum("tds_amount"), D0))["s"] or 0

    # Assets
    assets_qs = FixedAsset.objects.all()
    assets_count = assets_qs.count()
    assets_maintenance_due = assets_qs.filter(next_maintenance_date__isnull=False, next_maintenance_date__lte=today).count()

    # Procurement
    prs_qs   = scope(PurchaseRequisition.objects.all())
    pos_qs   = scope(PurchaseOrder.objects.all())
    bills_qs = scope(VendorBill.objects.all())
    vpay_qs  = scope(VendorPayment.objects.all())

    pr_count = prs_qs.count()
    po_count = pos_qs.count()
    bills_count  = bills_qs.count()
    bills_posted = bills_qs.filter(status="POSTED").count()
    vendor_payments_month = vpay_qs.filter(date__gte=start_this_month).aggregate(s=Coalesce(Sum("amount"), D0))["s"] or 0
    vendor_payments_count = vpay_qs.filter(date__gte=start_this_month).count()

    # -----------------------------
    # Time series (6 months) — always provide zeros so charts render
    # -----------------------------
    def last_n_month_starts(start_month, n=6):
        y, m = start_month.year, start_month.month
        out = []
        for _ in range(n):
            out.append(date(y, m, 1))
            m -= 1
            if m == 0:
                y -= 1
                m = 12
        return list(reversed(out))

    months = last_n_month_starts(start_this_month, 6)
    labels = [m.strftime("%b %Y") for m in months]
    start_6mo = months[0]

    def norm(d): return date(d.year, d.month, 1) if d else None
    def mapp(rows, k="m", v="v"):
        d = {}
        for r in rows:
            key = norm(r[k]); 
            if key: d[key] = float(r[v] or 0)
        return d

    rev_series = inv_qs.filter(date__gte=start_6mo)\
        .annotate(m=TruncMonth("date"))\
        .values("m").annotate(v=Coalesce(Sum("inclusive_total"), D0)).order_by("m")

    exp_series = exp_qs.filter(submitted_at__date__gte=start_6mo, status="APPROVED")\
        .annotate(m=TruncMonth("submitted_at"))\
        .values("m").annotate(v=Coalesce(Sum("amount"), D0)).order_by("m")

    gst_series = gst_qs.filter(created_at__date__gte=start_6mo)\
        .annotate(m=TruncMonth("created_at"))\
        .values("m").annotate(v=Coalesce(Sum("net_tax_liability"), D0)).order_by("m")

    tds_series = tds_qs.filter(payment_date__gte=start_6mo)\
        .annotate(m=TruncMonth("payment_date"))\
        .values("m").annotate(v=Coalesce(Sum("tds_amount"), D0)).order_by("m")

    revenue_arr  = [mapp(rev_series).get(m, 0.0) for m in months]
    expenses_arr = [mapp(exp_series).get(m, 0.0) for m in months]
    gst_arr      = [mapp(gst_series).get(m, 0.0) for m in months]
    tds_arr      = [mapp(tds_series).get(m, 0.0) for m in months]

    context = {
        # headline KPIs
        "revenue_total": float(revenue_total),
        "outstanding_total": float(outstanding_total),
        "invoices_total": invoices_total,
        "invoices_paid": invoices_paid,
        "invoices_unpaid": invoices_unpaid,

        "expense_total": float(expense_total),
        "expense_pending": float(expense_pending),
        "gst_liability": float(gst_liability),
        "tds_total": float(tds_total),

        "assets_count": assets_count,
        "assets_maintenance_due": assets_maintenance_due,

        "pr_count": pr_count,
        "po_count": po_count,
        "bills_count": bills_count,
        "bills_posted": bills_posted,
        "vendor_payments_month": float(vendor_payments_month),
        "vendor_payments_count": vendor_payments_count,

        # charts
        "labels": labels,
        "revenue": revenue_arr,
        "expenses": expenses_arr,
        "gst": gst_arr,
        "tds": tds_arr,
    }
    return render(request, "dashboard/accountant_dashboard.html", context)




from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.shortcuts import render
from .models import Account

# Ensure that only accountants or superusers can access this view
def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

@login_required
@user_passes_test(is_accountant_or_superuser)
def trial_balance(request):
    # Filter accounts based on the user’s role
    if request.user.is_superuser:
        # Superusers can see all accounts they own or created by them
        accounts = Account.objects.filter(
            Q(owner=request.user) | Q(created_by=request.user)
        )
    else:
        # Regular users or accountants can see only their own accounts and those created by the superuser who created them
        accounts = Account.objects.filter(
            Q(owner=request.user) | Q(created_by=request.user.created_by)
        )

    # Annotate accounts with the total debit and credit from the journal items
    accounts = accounts.annotate(
        total_debit=Sum('journalitem__debit'),
        total_credit=Sum('journalitem__credit'),
    )

    # Prepare the rows for the trial balance
    rows = []
    for acc in accounts:
        debit = acc.total_debit or 0
        credit = acc.total_credit or 0
        opening = acc.opening_balance or 0   # <-- Ensure your Account model has this field

        # Calculate closing balance based on account type
        if acc.account_type in ['Asset', 'Expense']:
            balance = opening + (debit - credit)
        else:  # Liability, Equity, Revenue
            balance = opening + (credit - debit)

        rows.append({
            'account': acc.name,
            'debit': debit,
            'credit': credit,
            'opening': opening,
            'balance': balance,
        })

    return render(request, 'reports/trial_balance.html', {
        'rows': rows,
        'readonly': not request.user.is_superuser,
    })


    return render(request, 'reports/trial_balance.html', {
        'rows': rows,
        'readonly': not request.user.is_superuser,
    })

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.db.models import Sum

# Helper function to check if the user is an accountant or superuser
def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

@login_required
@user_passes_test(is_accountant_or_superuser)
def balance_sheet(request):
    # Filter accounts based on the logged-in user's role
    if request.user.is_superuser:
        # Superusers see all accounts they created or created by them
        accounts = Account.objects.filter(
            Q(owner=request.user) | Q(created_by=request.user)
        )
    else:
        # Regular users see their own accounts and accounts created by the superuser who created them
        accounts = Account.objects.filter(
            Q(owner=request.user) | Q(created_by=request.user.created_by)
        )

    # Function to calculate the balance for each account
    def get_balance(acc):
        debits = sum(i.debit for i in acc.journalitem_set.all())
        credits = sum(i.credit for i in acc.journalitem_set.all())
        opening = acc.opening_balance or 0

        # Balance calculation follows the rule as in trial balance
        if acc.account_type in ['Asset', 'Expense']:
            return opening + (debits - credits)
        else:  # Liability, Equity, Revenue
            return opening + (credits - debits)

    # Prepare the context with assets, liabilities, and equity
    context = {
        'assets': [(a.name, get_balance(a)) for a in accounts.filter(account_type='Asset')],
        'liabilities': [(l.name, get_balance(l)) for l in accounts.filter(account_type='Liability')],
        'equity': [(e.name, get_balance(e)) for e in accounts.filter(account_type='Equity')],
        'readonly': request.user.is_superuser
    }

    return render(request, 'reports/balance_sheet.html', context)



from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.db.models import Sum

# Helper function to check if the user is an accountant or superuser
def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

@login_required
@user_passes_test(is_accountant_or_superuser)
def profit_loss(request):
    # Filter accounts based on the logged-in user's role
    if request.user.is_superuser:
        # Superusers can see all revenue and expense accounts they own or created by them
        revenue_accounts = Account.objects.filter(
            Q(owner=request.user) | Q(created_by=request.user),
            account_type='Revenue'
        )
        expense_accounts = Account.objects.filter(
            Q(owner=request.user) | Q(created_by=request.user),
            account_type='Expense'
        )
    else:
        # Regular users can see their own revenue and expense accounts and those created by the superuser who created them
        revenue_accounts = Account.objects.filter(
            Q(owner=request.user) | Q(created_by=request.user.created_by),
            account_type='Revenue'
        )
        expense_accounts = Account.objects.filter(
            Q(owner=request.user) | Q(created_by=request.user.created_by),
            account_type='Expense'
        )

    # Function to get the balance of an account
    def get_balance(acc):
        debits = sum(i.debit for i in acc.journalitem_set.all())
        credits = sum(i.credit for i in acc.journalitem_set.all())
        opening = acc.opening_balance or 0

        if acc.account_type == 'Revenue':
            return opening + (credits - debits)  # Revenue increases with credit
        elif acc.account_type == 'Expense':
            return opening + (debits - credits)  # Expense increases with debit
        return 0

    # Prepare revenue and expense data
    revenue_data = [(r.name, get_balance(r)) for r in revenue_accounts]
    expense_data = [(e.name, get_balance(e)) for e in expense_accounts]

    # Calculate net profit: Revenue - Expenses
    net_profit = sum(r[1] for r in revenue_data) - sum(e[1] for e in expense_data)

    return render(request, 'reports/profit_loss.html', {
        'revenues': revenue_data,
        'expenses': expense_data,
        'net_profit': net_profit,
        'readonly': request.user.is_superuser
    })


from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.db.models import Q
from .models import JournalItem

# Helper function to check if the user is an accountant or superuser
def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

@login_required
@user_passes_test(is_accountant_or_superuser)
def reconcile_items(request):
    # Filter journal items based on the user’s role
    if request.user.is_superuser:
        # Superusers can see all journal items they own or created by them
        items = JournalItem.objects.select_related('account', 'currency').filter(
            Q(account__is_bank=True) & Q(reconciled=False) & 
            (Q(owner=request.user) | Q(created_by=request.user))
        )
    else:
        # Regular users can only see journal items they own or those created by the superuser who created them
        items = JournalItem.objects.select_related('account', 'currency').filter(
            Q(account__is_bank=True) & Q(reconciled=False) & 
            (Q(owner=request.user) | Q(created_by=request.user.created_by))
        )

    # If the request is a POST and the user is not a superuser, reconcile selected items
    if request.method == 'POST' and not request.user.is_superuser:
        ids = request.POST.getlist('reconcile_ids')
        # Mark the selected journal items as reconciled
        JournalItem.objects.filter(id__in=ids).update(reconciled=True)
        return redirect('reconcile')  # Redirect after reconciliation

    return render(request, 'ledger/reconcile.html', {
        'items': items,
        'readonly': request.user.is_superuser,  # Allow superusers to view/edit, others are read-only
    })

from django.db.models import Sum, F
from decimal import Decimal
from decimal import Decimal
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import JournalEntry, JournalItem, ProjectStage
from .forms import JournalEntryForm, JournalItemFormSet


from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, F
from django.db.models import Sum
from django.core.exceptions import ValidationError
from .models import JournalEntry, JournalItem, Project
from .forms import JournalEntryForm, JournalItemFormSet
from decimal import Decimal

# Helper function to check if the user is an accountant
def is_accountant(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from .models import JournalEntry, Project
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from .forms import JournalEntryForm, JournalItemFormSet
from .models import JournalEntry, Project


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import JournalEntry, JournalItem, Project
from .forms import JournalEntryForm, JournalItemFormSet

# ✅ import your helper

@login_required
@user_passes_test(lambda u: u.is_superuser or getattr(u, "is_accountant", False))
def manage_journal_entry(request, pk=None):
    """
    Create/Edit JournalEntry with items.
    Restricts projects, stages, and currencies based on user ownership
    for both superusers and accountants.
    """
    user = request.user
    entry = get_object_or_404(JournalEntry, pk=pk) if pk else None
    is_edit = bool(pk)

    # --- Determine allowed projects ---
    allowed_projects = Project.objects.filter(Q(created_by=user) | Q(owner=user))
    allowed_stages = ProjectStage.objects.filter(project__in=allowed_projects)

    # --- Determine allowed currencies ---
    allowed_users = get_allowed_users(user)
    allowed_currencies = Currency.objects.filter(created_by__in=allowed_users)

    # --- Permission check for editing existing entry ---
    if entry:
        if entry.project not in allowed_projects or entry.created_by != user:
            return render(request, 'ledger/permission_denied.html')

    project_for_forms = entry.project if entry else None

    if request.method == "POST":
        form = JournalEntryForm(request.POST, instance=entry, user=user)
        form.fields['project'].queryset = allowed_projects  # restrict parent form project field
        form.fields['currency'].queryset = allowed_currencies  # ✅ restrict currency

        formset = JournalItemFormSet(
            request.POST,
            instance=entry,
            project=project_for_forms,
            user=user
        )

        # Restrict project/stage/currency for each item in the formset
        for item_form in formset.forms:
            item_form.fields['project'].queryset = allowed_projects
            item_form.fields['stage'].queryset = allowed_stages
            item_form.fields['currency'].queryset = allowed_currencies  # ✅

        if form.is_valid() and formset.is_valid():
            entry = form.save(commit=False)

            # If project missing, inherit from first filled item
            if not entry.project:
                for item_form in formset:
                    if item_form.cleaned_data.get('DELETE'):
                        continue
                    project_item = item_form.cleaned_data.get('project')
                    if project_item:
                        entry.project = project_item
                        break

            # Assign ownership if new
            if not entry.pk:
                entry.created_by = user
                entry.owner = user
            entry.save()

            # Save child items
            formset.instance = entry
            formset.save()

            return redirect('journal_entry_list')

    else:
        form = JournalEntryForm(instance=entry, user=user)
        form.fields['project'].queryset = allowed_projects
        form.fields['currency'].queryset = allowed_currencies  # ✅ restrict currency

        formset = JournalItemFormSet(
            instance=entry,
            project=project_for_forms,
            user=user
        )
        # Restrict project/stage/currency for each form
        for item_form in formset.forms:
            item_form.fields['project'].queryset = allowed_projects
            item_form.fields['stage'].queryset = allowed_stages
            item_form.fields['currency'].queryset = allowed_currencies  # ✅

    return render(request, 'ledger/create_entry.html', {
        'form': form,
        'formset': formset,
        'readonly': False,
        'update': is_edit,
    })


from django.http import JsonResponse
from .models import ProjectStage

@login_required
def get_stages(request, project_id):
    stages = ProjectStage.objects.filter(project_id=project_id).values("id", "name")
    return JsonResponse({"stages": list(stages)})


@login_required
@user_passes_test(lambda u: u.is_superuser or getattr(u, "is_accountant", False))
def edit_journal_entry(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk)
    user = request.user

    # Permission check
    allowed = (user.is_superuser and (entry.owner == user or (entry.created_by and entry.created_by.created_by == user))) \
              or (not user.is_superuser and entry.created_by == user)
    if not allowed:
        return render(request, 'ledger/permission_denied.html')

    # --- Determine project for filtering stages ---
    project_for_forms = entry.project  # Important: use instance project

    if request.method == "POST":
        form = JournalEntryForm(request.POST, instance=entry, user=user)
        formset = JournalItemFormSet(
            request.POST,
            instance=entry,
            project=project_for_forms,  # pass instance project
            user=user,
        )
        if form.is_valid() and formset.is_valid():
            entry = form.save(commit=False)
            entry.save()

            formset.instance = entry
            formset.save()

            return redirect('journal_entry_list')
    else:
        form = JournalEntryForm(instance=entry, user=user)
        formset = JournalItemFormSet(
            instance=entry,
            project=project_for_forms,  # pass instance project
            user=user,
        )

    return render(request, 'ledger/create_entry.html', {
        'form': form,
        'formset': formset,
        'readonly': False,
        'update': True,
    })



@login_required
@user_passes_test(is_accountant)
def delete_journal_entry(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk)
    if request.method == "POST":
        entry.delete()
        return redirect('journal_entry_list')
    return render(request, 'ledger/confirm_delete.html', {'entry': entry})

# views.py
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.shortcuts import render

from accounting_app.models import JournalEntry, JournalItem  # adjust import path if different
from accounting_app.models import ApprovalRequest  # generic approval model

def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_accountant)
def journal_entry_list(request):
    user = request.user

    entries_qs = (
        JournalEntry.objects
        .select_related('currency', 'project')
        .prefetch_related(
            Prefetch('items', queryset=JournalItem.objects.select_related('account', 'project', 'stage'))
        )
        .order_by('-date', '-id')
    )

    if user.is_superadmin:
        # SuperAdmin sees everything
        pass
    elif user.is_normal_superuser:
        # Superuser sees only their own entries + accountants they created
        entries_qs = entries_qs.filter(
            Q(created_by=user) |
            Q(created_by__created_by=user)  # accountants created by this superuser
        )
    elif user.is_accountant:
        # Accountant sees only their own entries
        entries_qs = entries_qs.filter(created_by=user)

    # Optional filter by project
    project_id = request.GET.get('project')
    if project_id:
        entries_qs = entries_qs.filter(project_id=project_id)

    # Pagination
    paginator = Paginator(entries_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Approvals map
    ct = ContentType.objects.get_for_model(JournalEntry)
    page_ids = [str(e.id) for e in page_obj.object_list]
    approvals_qs = ApprovalRequest.objects.filter(
        target_ct=ct, target_id__in=page_ids
    ).select_related('requested_by', 'assigned_to').order_by('-created_on')

    approvals_by_entry = {}
    approved_ids = set()
    for appr in approvals_qs:
        key = int(appr.target_id)
        approvals_by_entry.setdefault(key, []).append(appr)
        if appr.status == "APPROVED":
            approved_ids.add(key)

    return render(
        request,
        'ledger/journal_entry_list.html',
        {
            'page_obj': page_obj,
            'approvals_by_entry': approvals_by_entry,
            'approved_ids': approved_ids,
        }
    )




from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from .models import JournalEntry, ApprovalRequest

@login_required
def journalentry_approvals(request, pk):
    # Get the JournalEntry object
    entry = get_object_or_404(JournalEntry, pk=pk)

    # Get approvals for this entry
    ct = ContentType.objects.get_for_model(JournalEntry)
    approvals = ApprovalRequest.objects.filter(
        target_ct=ct,
        target_id=str(entry.pk)  # convert to string if stored as CharField
    ).select_related("requested_by", "assigned_to").order_by('-created_on')

    return render(request, "ledger/journalentry_approval_list.html", {
        "entry": entry,
        "approvals": approvals,
    })

# @login_required
# def journal_entry_list(request):
#     entries = JournalEntry.objects.prefetch_related('items', 'project').order_by('-date')
#     return render(request, 'ledger/journal_entry_list.html', {'entries': entries})


# -----------------------------
# ✅ Accounts
# -----------------------------
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import AccountForm
from .models import Account
import json

def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

ACCOUNT_NAME_CHOICES = {
    "Asset": ["Cash", "Accounts Receivable", "Inventory", "Fixed Assets"],
    "Liability": ["Accounts Payable", "Loans", "GST Payable"],
    "Equity": ["Owner's Capital", "Retained Earnings"],
    "Revenue": ["Sales", "Consulting Income"],
    "Expense": ["Rent", "Utilities", "Salary", "Office Supplies"],
}
@login_required
@user_passes_test(is_accountant_or_superuser)
def create_account(request):
    user = request.user

    # Determine allowed users (superuser + its accountants)
    allowed_users = [user] if user.is_superuser else get_allowed_users(user)

    # Filter clients owned by allowed users
    clients = list(Client.objects.filter(owner__in=allowed_users).values_list('name', flat=True))

    # Filter currencies created by allowed users only
    allowed_currencies = Currency.objects.filter(created_by__in=allowed_users)

    # Initialize the form
    form = AccountForm(request.POST or None)

    # ✅ Restrict the currency field to tenant-specific currencies
    form.fields['currency'].queryset = allowed_currencies

    if form.is_valid():
        account = form.save(commit=False)
        account.owner = user
        if not user.is_superuser:
            account.created_by = user.created_by
        account.save()
        return redirect('account_list')

    return render(request, 'accounts/create_account.html', {
        'form': form,
        'readonly': user.is_superuser,
        'account_name_choices': json.dumps(ACCOUNT_NAME_CHOICES),
        'clients': clients,
    })



from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

# Make sure the decorator function is correctly defined
def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

# Ensure the decorator for accountants or superusers
def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

# Ensure the decorator for accountants or superusers
def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

@login_required
@user_passes_test(is_accountant_or_superuser)
def account_list(request):
    if request.user.is_superuser:
        # Superusers can see all accounts they created or accounts created by users they created
        accounts = Account.objects.filter(
            Q(owner=request.user) | Q(created_by=request.user)
        )
    else:
        # Regular users see their own accounts and accounts created by the superuser who created them
        accounts = Account.objects.filter(
            Q(owner=request.user) | Q(created_by=request.user.created_by)  # Accounts created by the superuser who created them
        )

    # Pagination logic
    paginator = Paginator(accounts, 5)  # 5 accounts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/account_list.html', {
        'page_obj': page_obj,
        'readonly': not request.user.groups.filter(name='Accountant').exists(),
    })





@login_required
@user_passes_test(is_accountant_or_superuser)
def update_account(request, account_id):
    account = get_object_or_404(Account, pk=account_id)
    form = AccountForm(request.POST or None, instance=account)

    if form.is_valid():
        old_is_receivable = account.is_receivable
        old_client = account.client
        new_is_receivable = form.cleaned_data.get("is_receivable")

        with transaction.atomic():
            updated_account = form.save(commit=False)

            if old_is_receivable and not new_is_receivable:
                # unlink client first
                if old_client:
                    updated_account.client = None
                    updated_account.save()
                    old_client.delete()
                else:
                    updated_account.save()
            elif new_is_receivable:
                # attach existing client if exists, avoid creating duplicates
                if not updated_account.client:
                    client_name = updated_account.name  # or any logic to get client name
                    client, created = Client.objects.get_or_create(name=client_name)
                    updated_account.client = client
                updated_account.save()
            else:
                updated_account.save()

        messages.success(request, "Account updated.")
        return redirect("account_list")

    return render(request, "accounts/account_form.html", {
        "form": form,
        "readonly": request.user.is_superuser,
        "title": "Edit Account",
        "account_name_choices": ACCOUNT_NAME_CHOICES,
    })


@login_required
@user_passes_test(is_accountant_or_superuser)
def view_account(request, account_id):
    account = get_object_or_404(Account, pk=account_id)
    return render(request, 'accounts/account_detail.html', {
        'account': account,
        'readonly': not request.user.groups.filter(name='Accountant').exists()
    })


# @login_required
# @user_passes_test(is_accountant_or_superuser)
# def update_account(request, account_id):
#     account = get_object_or_404(Account, pk=account_id)
#     form = AccountForm(request.POST or None, instance=account)
#     if form.is_valid() and not request.user.is_superuser:
#         form.save()
#         return redirect('account_list')
#     return render(request, 'accounts/account_form.html', {'form': form, 'readonly': request.user.is_superuser, 'title': 'Edit Account'})

@login_required
@user_passes_test(is_accountant_or_superuser)
def delete_account(request, account_id):
    account = get_object_or_404(Account, pk=account_id)

    if request.method == 'POST':
        if account.is_receivable:
            # delete clients linked to this receivable account
            Client.objects.filter(receivable_account=account).delete()

        # delete the account itself
        account.delete()
        return redirect('account_list')

    return render(request, 'accounts/account_confirm_delete.html', {'account': account})




# views.py
from django.shortcuts import get_object_or_404, render
from accounting_app.models import JournalEntry
from accounting_app.utils import is_date_locked  # <- import the helper

@login_required
@user_passes_test(is_accountant_or_superuser)
def journal_entry_detail(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk)
    ctx = {
        "object": entry,
        "locked": bool(entry.date and is_date_locked(entry.date)),  # for template
        "is_approved": entry.is_approved(),                        # for template
    }
    return render(request, "ledger/journal_entry_detail.html", ctx)

# -----------------------------
# ✅ Invoicing & Billing
# -----------------------------





from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test

from decimal import Decimal
from collections import defaultdict

from decimal import Decimal
from collections import defaultdict

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import Invoice, Client, Project  # ensure these exist


def _as_decimal(val, default=Decimal("0.00")):
    if val is None:
        return default
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except Exception:
        return default
@login_required
@user_passes_test(is_accountant_or_superuser)
def invoice_print_group(request, client_id, project_id):
    from decimal import Decimal
    D0 = Decimal("0.00")

    proj_id = None if str(project_id).lower() == "none" else int(project_id)

    client = get_object_or_404(Client, pk=client_id)
    project = get_object_or_404(Project, pk=proj_id) if proj_id is not None else None

    invoices = (
        Invoice.objects
        .select_related("client", "project")
        .prefetch_related("items", "time_entries")
        .filter(client_id=client_id, project_id=proj_id)
        .order_by("date", "id")
    )

    # --- Calculate sums from methods ---
    subtotal_sum = D0
    gst_sum = D0
    grand_sum = D0

    for inv in invoices:
        subtotal_sum += Decimal(inv.total_without_tax())
        gst_sum      += Decimal(inv.gst_amount())
        grand_sum    += Decimal(inv.total_with_tax())

    all_paid = all((inv.status or "").lower() == "paid" for inv in invoices)

    context = {
        "client": client,
        "project": project,
        "invoices": invoices,
        "subtotal_sum": subtotal_sum,
        "gst_sum": gst_sum,
        "grand_sum": grand_sum,
        "all_paid": all_paid,
    }
    return render(request, "invoices/invoice_print_group.html", context)

from django.db.models import Q

def get_allowed_users(user):
    """
    Returns a queryset of users whose data the given user can access.
    - SuperAdmin → all users
    - Normal Superuser → themselves + their accountants
    - Accountant → themselves + their superuser
    """
    User = get_user_model()

    if getattr(user, "is_superadmin", False):
        return User.objects.all()

    if getattr(user, "is_normal_superuser", False):
        return User.objects.filter(Q(id=user.id) | Q(created_by=user))

    if getattr(user, "is_accountant", False):
        return User.objects.filter(Q(id=user.id) | Q(id=user.created_by_id))

    # fallback: only self
    return User.objects.filter(id=user.id)


@login_required
@user_passes_test(is_accountant_or_superuser)
def invoice_list(request):
    D0 = Decimal("0.00")
    user = request.user

    allowed_users = get_allowed_users(user)

    invoices_all = (
        Invoice.objects
        .select_related('client', 'project', 'created_by')
        .prefetch_related('items', 'time_entries')
        .filter(created_by__in=allowed_users)  # 🔑 apply restriction here
        .order_by('-date', '-id')
    )

    # --- Group summaries ---
    groups = defaultdict(lambda: {
        "client_id": None,
        "client_name": None,
        "project_id": None,
        "project_name": None,
        "count": 0,
        "paid_count": 0,
        "unpaid_count": 0,
        "total_with_tax": D0,
        "paid_total": D0,
        "unpaid_total": D0,
    })
    group_invoices = defaultdict(list)

    for inv in invoices_all:
        client_name = getattr(inv.client, "name", str(inv.client))
        proj = getattr(inv, "project", None)
        proj_id = getattr(proj, "id", None)
        proj_name = getattr(proj, "name", "—")

        key = (inv.client_id, proj_id)
        g = groups[key]
        g["client_id"] = inv.client_id
        g["client_name"] = client_name
        g["project_id"] = proj_id
        g["project_name"] = proj_name
        g["count"] += 1

        twt_attr = getattr(inv, "total_with_tax", None)
        amt = _as_decimal(twt_attr() if callable(twt_attr) else twt_attr, D0)

        g["total_with_tax"] += amt
        if (inv.status or "").lower() == "paid":
            g["paid_count"] += 1
            g["paid_total"] += amt
        else:
            g["unpaid_count"] += 1
            g["unpaid_total"] += amt

        group_invoices[key].append(inv)

    group_summaries = []
    for key, g in groups.items():
        g_row = dict(g)
        g_row["invoices"] = group_invoices[key]
        group_summaries.append(g_row)

    group_summaries.sort(key=lambda r: (r["client_name"] or "", r["project_name"] or ""))
    grand_total_with_tax = sum((g["total_with_tax"] for g in group_summaries), D0)

    # --- Optional filters ---
    client_id = request.GET.get("client")
    project_id = request.GET.get("project")
    invoices = invoices_all
    active_filter = None

    if client_id:
        invoices = invoices.filter(client_id=client_id)
    if project_id is not None:
        if project_id == "None":
            invoices = invoices.filter(project__isnull=True)
        else:
            invoices = invoices.filter(project_id=project_id)

    if client_id or (project_id is not None):
        client_obj = Client.objects.filter(id=client_id).only("name").first() if client_id else None
        project_obj = None
        if project_id and project_id != "None":
            project_obj = Project.objects.filter(id=project_id).only("name").first()
        active_filter = {
            "client_name": getattr(client_obj, "name", "All Clients") if client_id else "All Clients",
            "project_name": getattr(project_obj, "name", "—") if project_id not in (None, "None") else "—",
        }

    # --- Pagination ---
    paginator = Paginator(invoices, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'invoices/invoice_list.html',
        {
            'page_obj': page_obj,
            'group_summaries': group_summaries,
            'grand_total_with_tax': grand_total_with_tax,
            'razorpay_key_id': getattr(settings, 'RAZORPAY_KEY_ID', ''),
            'active_filter': active_filter,
        }
    )



from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

@login_required
@user_passes_test(is_accountant_or_superuser)
def invoice_print(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related("client", "project").prefetch_related("items", "time_entries"),
        pk=pk,
    )
    return render(request, "invoices/invoice_print.html", {"invoice": invoice})




@login_required
@user_passes_test(is_accountant_or_superuser)
def manage_invoice(request, pk=None):
    user = request.user

    # For existing invoice, superuser can see invoices created by self or their accountants
    if pk:
        if user.is_superuser:
            allowed_users = [user] + list(user.created_users.filter(groups__name='Accountant'))
            invoice = get_object_or_404(Invoice, pk=pk, created_by__in=allowed_users)
        else:
            invoice = get_object_or_404(Invoice, pk=pk, created_by=user)
    else:
        invoice = None

    form = InvoiceForm(request.POST or None, instance=invoice)

    # ----- Restrict client choices -----
    if user.is_superuser:
        form.fields['client'].queryset = Client.objects.all()
    else:
        # Accountant sees clients tied to their superuser
        superuser = getattr(user, 'created_by', user)
        form.fields['client'].queryset = Client.objects.filter(created_by=superuser)

    # ----- Restrict project choices -----
    if user.is_superuser:
        form.fields['project'].queryset = Project.objects.all()
    else:
        superuser = getattr(user, 'created_by', user)
        form.fields['project'].queryset = Project.objects.filter(created_by=superuser)

    # ----- Restrict currency choices -----
    allowed_users = get_allowed_users(user)  # includes superuser + their accountants
    form.fields['currency'].queryset = Currency.objects.filter(created_by__in=allowed_users)

    # ----- Form submission -----
    if request.method == "POST" and form.is_valid():
        invoice = form.save(commit=False)
        invoice.created_by = user

        # Razorpay order logic
        if not invoice.razorpay_order_id and invoice.total_amount > 0:
            import razorpay
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            razorpay_order = client.order.create({
                'amount': int(invoice.total_amount * 100),
                'currency': 'INR',
                'payment_capture': 1,
            })
            invoice.razorpay_order_id = razorpay_order['id']

        invoice.save()
        return redirect('invoice_list')

    return render(request, 'invoices/invoice_form.html', {
        'form': form,
        'update': bool(pk),
    })


@login_required
@user_passes_test(is_accountant_or_superuser)

@login_required
@user_passes_test(is_accountant_or_superuser)
def delete_invoice(request, pk):
    if request.user.is_superuser:
        invoice = get_object_or_404(Invoice, pk=pk)
    else:
        invoice = get_object_or_404(Invoice, pk=pk, created_by=request.user)

    if request.method == "POST":
        invoice.delete()
        return redirect('invoice_list')

    return render(request, 'invoices/confirm_delete.html', {'invoice': invoice})

 # make sure you import this

@login_required
@user_passes_test(is_accountant_or_superuser)
def create_invoice(request):
    form = InvoiceForm(request.POST or None)

    # Allowed users (superuser + its accountants, or accountant + their superuser)
    allowed_users = get_allowed_users(request.user)

    # Restrict client choices
    form.fields['client'].queryset = Client.objects.filter(created_by__in=allowed_users)

    # Restrict project choices
    allowed_projects = Project.objects.filter(created_by__in=allowed_users)
    form.fields['project'].queryset = allowed_projects

    # Restrict currency choices
    form.fields['currency'].queryset = Currency.objects.filter(created_by__in=allowed_users)

    # Formsets
    formset = InvoiceItemFormSet(request.POST or None, prefix='items')
    timeset = TimeEntryFormSet(request.POST or None, prefix='time')

    # Restrict project choices in TimeEntryFormSet
    for time_form in timeset.forms:
        time_form.fields['project'].queryset = allowed_projects

    if form.is_valid() and formset.is_valid() and timeset.is_valid():
        invoice = form.save(commit=False)
        invoice.created_by = request.user

        # attach formsets
        formset.instance = invoice
        timeset.instance = invoice

        invoice.save()
        formset.save()
        timeset.save()

        # calculate totals
        item_total = sum(item.quantity * item.unit_price for item in invoice.items.all())
        time_total = sum(te.hours * te.rate_per_hour for te in invoice.time_entries.all())
        invoice.total_amount = item_total + time_total
        invoice.save(update_fields=['total_amount'])

        return redirect('invoice_list')

    return render(request, 'invoices/create_invoice.html', {
        'form': form,
        'formset': formset,
        'timeset': timeset,
    })



@user_passes_test(is_accountant_or_superuser)
def mark_paid(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if invoice.status != 'paid':
        invoice.status = 'paid'
        invoice.save()
        messages.success(request, f'Invoice #{invoice.id} marked as paid.')
    else:
        messages.info(request, f'Invoice #{invoice.id} is already marked as paid.')
    return redirect('invoice_list')  # or wherever you want to redirect

from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test

# Make sure these are imported:
# from .models import Invoice
# (Your user_passes_test: is_accountant_or_superuser already exists)

def _as_decimal(val, default=Decimal("0.00")):
    if val is None:
        return default
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except Exception:
        return default

def _call_or_value(obj, attr_name, default=Decimal("0.00")):
    attr = getattr(obj, attr_name, None)
    if callable(attr):
        return _as_decimal(attr(), default)
    return _as_decimal(attr, default)
@login_required
@user_passes_test(is_accountant_or_superuser)
def invoice_detail(request, pk):
    user = request.user

    if user.is_superuser:
        # Superuser sees invoices they created OR invoices created by their accountants
        allowed_users = [user]  # include self
        # optionally, include accountants created by this superuser
        accountants = user.created_users.filter(groups__name="Accountant")
        allowed_users += list(accountants)

        invoice = get_object_or_404(
            Invoice.objects.select_related("client", "project").prefetch_related("items", "time_entries"),
            pk=pk,
            created_by__in=allowed_users
        )
    else:
        # Accountant sees only their own invoices
        invoice = get_object_or_404(
            Invoice.objects.select_related("client", "project").prefetch_related("items", "time_entries"),
            pk=pk,
            created_by=user
        )

    # ----- rest of your calculations remain the same -----
    subtotal = _call_or_value(invoice, "total_without_tax", Decimal("0.00"))
    gst_percent = getattr(invoice, "gst_percent", 0) or 0
    gst_amount = _call_or_value(invoice, "gst_amount", Decimal("0.00"))
    total_with_tax = _call_or_value(invoice, "total_with_tax", Decimal("0.00"))

    if subtotal == Decimal("0.00") and (hasattr(invoice, "items") or hasattr(invoice, "time_entries")):
        items_sum = sum(
            _as_decimal(getattr(it, "unit_price", 0)) * _as_decimal(getattr(it, "quantity", 0))
            for it in getattr(invoice, "items").all()
        )
        time_sum = sum(
            _as_decimal(getattr(te, "hours", 0)) * _as_decimal(getattr(te, "rate_per_hour", 0))
            for te in getattr(invoice, "time_entries").all()
        )
        subtotal = items_sum + time_sum
        if gst_amount == Decimal("0.00") and gst_percent:
            gst_amount = (subtotal * Decimal(str(gst_percent))) / Decimal("100")
        if total_with_tax == Decimal("0.00"):
            total_with_tax = subtotal + gst_amount

    # ----- Summary for SAME Client + Project as this invoice -----
    same_group_qs = Invoice.objects.filter(
        client=invoice.client,
        project=invoice.project,
        created_by__in=allowed_users if user.is_superuser else [user]
    )

    group_count = group_paid_count = group_unpaid_count = 0
    group_total_with_tax = group_paid_total = group_unpaid_total = Decimal("0.00")

    for inv in same_group_qs:
        amt = _call_or_value(inv, "total_with_tax", Decimal("0.00"))
        group_total_with_tax += amt
        group_count += 1
        if (inv.status or "").lower() == "paid":
            group_paid_count += 1
            group_paid_total += amt
        else:
            group_unpaid_count += 1
            group_unpaid_total += amt

    ctx = {
        "invoice": invoice,
        "subtotal": subtotal,
        "gst_percent": gst_percent,
        "gst_amount": gst_amount,
        "total_with_tax": total_with_tax,
        "group_count": group_count,
        "group_paid_count": group_paid_count,
        "group_unpaid_count": group_unpaid_count,
        "group_total_with_tax": group_total_with_tax,
        "group_paid_total": group_paid_total,
        "group_unpaid_total": group_unpaid_total,
    }

    return render(request, "invoices/templates/default.html", ctx)




from django.http import HttpResponse
from django.template.loader import get_template
from django.shortcuts import get_object_or_404
from xhtml2pdf import pisa
from .models import Invoice
import io



from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO
from .models import Invoice

def invoice_pdf(request, pk):
    invoice = Invoice.objects.get(pk=pk)
    html = render_to_string('invoices/invoice_pdf.html', {'invoice': invoice})
    
    result = BytesIO()
    pdf = pisa.CreatePDF(src=html, dest=result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.id}.pdf"'
        return response
    else:
        return HttpResponse("Error generating PDF", status=500)



from .models import Subscription, Plan, SubscriptionInvoice
from datetime import date, timedelta

from datetime import date, timedelta
from .models import Plan, Subscription

@login_required
@user_passes_test(is_accountant_or_superuser)
def create_subscription(user, plan_id):
    plan = Plan.objects.get(id=plan_id)
    today = date.today()

    # Step 1: Deactivate any existing active subscriptions
    Subscription.objects.filter(user=user, active=True).update(active=False)

    # Step 2: Setup new subscription details
    trial = plan.trial_days > 0
    next_billing = today + timedelta(days=plan.trial_days) if trial else today + timedelta(days=30)

    # Step 3: Create the new active subscription
    return Subscription.objects.create(
        user=user,
        plan=plan,
        trial=trial,
        next_billing_date=next_billing,
        start_date=today,
        active=True,
        created_by=user,
        owner=user,
    )


from datetime import date, timedelta
from .models import Subscription, SubscriptionInvoice


@login_required
@user_passes_test(is_accountant_or_superuser)
def generate_invoice(subscription, prorated=False):
    user = subscription.user
    plan = subscription.plan
    price = plan.price
    description = f"{plan.name} Monthly Subscription"

    if prorated:
        days_in_month = 30
        days_used = (date.today() - subscription.start_date).days
        price = (price / days_in_month) * days_used
        description += f" (Prorated for {days_used} days)"

    return SubscriptionInvoice.objects.create(
        user=user,
        subscription=subscription,
        name=plan,  # Save the plan in the name field (FK to Plan)
        amount=round(price, 2),
        description=description,
        paid=True,  # You can adjust this if real payments are involved
        created_by=user,
        owner=user,
    )

from django.core.paginator import Paginator  

@login_required
@user_passes_test(is_accountant_or_superuser)
def invoices_list(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    all_invoices = (
        SubscriptionInvoice.objects
        .filter(user__in=allowed_users)
        .order_by('-created')
    )

    paginator = Paginator(all_invoices, 5)  # 5 invoices per page
    page_number = request.GET.get('page')
    invoices = paginator.get_page(page_number)

    return render(request, 'billing/invoices_list.html', {
        'invoices': invoices
    })


@login_required
@user_passes_test(is_accountant_or_superuser)
def invoices_history(request):
    invoices = SubscriptionInvoice.objects.filter(subscription__user=request.user).order_by('-created')
    return render(request, 'billing/invoice_history.html', {'invoices': invoices})

@login_required
@user_passes_test(is_accountant_or_superuser)
def delete_invoices(request, invoice_id):
    user = request.user
    allowed_users = get_allowed_users(user)

    invoice = get_object_or_404(
        SubscriptionInvoice,
        id=invoice_id,
        user__in=allowed_users
    )

    if request.method == "POST":
        invoice.delete()
        messages.success(request, "Invoice deleted successfully.")
    else:
        messages.error(request, "Invalid request method.")

    return redirect("invoices_list")

from django.utils.timezone import now
from .models import Subscription, SubscriptionInvoice

@login_required
@user_passes_test(is_accountant_or_superuser)
def renew_subscriptions():
    today = now().date()

    # Get all active subscriptions due today or earlier
    subscriptions = Subscription.objects.filter(active=True, next_billing_date__lte=today)

    for sub in subscriptions:
        if sub.is_trialing():
            continue  # 🔁 Skip trial period

        # Renew logic: extend the next billing date
        delta = sub.plan.get_interval_delta()
        sub.next_billing_date += delta
        sub.last_renewed_at = now()
        sub.save()

        # Generate invoice for renewal
        SubscriptionInvoice.objects.create(
            user=sub.user,
            subscription=sub,
            amount=sub.plan.price,
            description=f"Auto-renewal for {sub.plan.name}"
        )


from datetime import timedelta
from django.utils.timezone import now
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Subscription, Plan, SubscriptionInvoice

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils.timezone import now
from .models import Subscription, Plan, SubscriptionInvoice


@login_required
@user_passes_test(is_accountant_or_superuser)
def change_plan(request, sub_id, new_plan_id):
    sub = get_object_or_404(Subscription, id=sub_id, user=request.user, active=True)
    new_plan = get_object_or_404(Plan, id=new_plan_id)

    if sub.plan_id == new_plan_id:
        messages.warning(request, "You are already subscribed to this plan.")
        return redirect('plan_list')

    if request.method == 'POST':
        sub.plan = new_plan
        sub.save()

        messages.success(request, f"Plan changed to {new_plan.name}. Your billing will update on the next cycle.")
        return redirect('plan_list')

    return render(request, 'billing/change_plan.html', {
        'subscription': sub,
        'new_plan': new_plan,
    })

from django.shortcuts import render, redirect
from .models import Plan, Subscription
from .views import create_subscription
from django.contrib.auth.decorators import login_required

from django.shortcuts import get_object_or_404

from django.utils.timezone import now
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from datetime import timedelta
from django.utils.timezone import now
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from .models import Subscription, Plan, SubscriptionInvoice

# ----------------------------
# ✅ Auto-renew logic (run via cron)
# ----------------------------

@login_required
@user_passes_test(is_accountant_or_superuser)
def renew_subscriptions():
    today = now().date()

    subscriptions = Subscription.objects.filter(active=True, next_billing_date__lte=today)

    for sub in subscriptions:
        if sub.is_trialing():
            continue  # Skip active trial subscriptions

        delta = sub.plan.get_interval_delta()
        sub.next_billing_date += delta
        sub.last_renewed_at = now()
        sub.save()

        # Create invoice
        SubscriptionInvoice.objects.create(
            user=sub.user,
            subscription=sub,
            amount=sub.plan.price,
            description=f"Auto-renewal for {sub.plan.name}"
        )


# ----------------------------
# ✅ Change plan view — no renewals, only plan switch
# ----------------------------

@login_required
@user_passes_test(is_accountant_or_superuser)
def change_plan(request, sub_id, new_plan_id):
    user = request.user
    allowed_users = get_allowed_users(user)

    # 🔒 Restrict subscription access
    sub = get_object_or_404(
        Subscription,
        id=sub_id,
        user__in=allowed_users,
        active=True
    )
    new_plan = get_object_or_404(Plan, id=new_plan_id)

    if sub.plan_id == new_plan.id:
        messages.info(request, "You are already on this plan.")
        return redirect("plan_list")

    if request.method == "POST":
        old_plan = sub.plan
        sub.plan = new_plan
        sub.save()

        # Generate prorated invoice for this subscription
        generate_invoice(sub, prorated=True)

        messages.success(
            request,
            f"Plan changed from {old_plan.name} to {new_plan.name}. "
            "Billing cycle remains unchanged."
        )
        return redirect("plan_list")

    return render(request, "billing/change_plan.html", {
        "subscription": sub,
        "new_plan": new_plan,
    })


# ----------------------------
# ✅ Manual renew view
# ----------------------------

@login_required
@user_passes_test(is_accountant_or_superuser)
def manual_renew(request, sub_id):
    user = request.user
    allowed_users = get_allowed_users(user)

    # 🔒 Restrict subscription access
    subscription = get_object_or_404(
        Subscription,
        id=sub_id,
        user__in=allowed_users
    )

    today = now().date()

    if request.method == 'POST':
        if subscription.last_renewed_at and subscription.last_renewed_at.date() == today:
            messages.info(request, "You already renewed today.")
        else:
            delta = subscription.plan.get_interval_delta()

            if subscription.next_billing_date:
                subscription.next_billing_date += delta
            else:
                subscription.next_billing_date = today + delta

            subscription.last_renewed_at = now()
            subscription.save()

            SubscriptionInvoice.objects.create(
                user=subscription.user,
                subscription=subscription,
                amount=subscription.plan.price,
                description=f"Manual renewal for {subscription.plan.name}"
            )

            messages.success(request, "Subscription renewed successfully!")

        return redirect("manual_renew", sub_id=sub_id)

    already_renewed = (
        subscription.last_renewed_at and subscription.last_renewed_at.date() == today
    )

    return render(request, "billing/manual_renew.html", {
        "subscription": subscription,
        "today": today,
        "already_renewed": already_renewed,
    })



# ----------------------------
# ✅ Plan List View
# ----------------------------
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import Plan, Subscription
from django.contrib.auth import get_user_model

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import Plan, Subscription # your helper
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
@user_passes_test(lambda u: u.is_superuser or getattr(u, "role", None) == "Accountant")
def plan_list(request):
    user = request.user
    allowed_users = get_allowed_users(user)  # superuser + accountants / accountant + superuser

    # Only plans owned by the group
    plans = Plan.objects.filter(owner__in=allowed_users)

    # Active subscriptions for this group
    subscriptions = Subscription.objects.filter(
        user__in=allowed_users, active=True
    ).select_related("plan", "user")

    # Map plan_id → subscription object
    subscription_map = {sub.plan.id: sub for sub in subscriptions if sub.plan}

    # Annotate plans
    for plan in plans:
        sub = subscription_map.get(plan.id)
        plan.is_subscribed_by_group = bool(sub)
        plan.subscription = sub
        plan.can_change_subscription = user.is_superuser and not plan.is_subscribed_by_group

    return render(request, "billing/plan_list.html", {
        "plans": plans,
        "active_subscription": next((sub for sub in subscriptions if sub.user == user), None),
    })





# @login_required
# def plan_list(request):
#     plans = Plan.objects.all()
#     subscriptions = Subscription.objects.filter(user=request.user, active=True).select_related('plan')

#     subscribed_plan_ids = set()
#     subscription_map = {}

#     for sub in subscriptions:
#         if sub.plan:
#             subscribed_plan_ids.add(sub.plan.id)
#             subscription_map[sub.plan.id] = sub

#     for plan in plans:
#         plan.is_subscribed = plan.id in subscribed_plan_ids
#         plan.subscription = subscription_map.get(plan.id)

#     return render(request, 'billing/plan_list.html', {
#         'plans': plans,
#         'has_active_subscription': subscriptions.exists(),
#         'current_subscription': subscriptions.first() if subscriptions else None,
#     })



    
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Plan


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Plan




@login_required
@user_passes_test(is_accountant_or_superuser)
def delete_plan(request, plan_id):
    if request.method == 'POST':
        plan = get_object_or_404(Plan, id=plan_id)
        plan.delete()
    return redirect('plan_list') 

    


# views.py
from django.shortcuts import render, redirect
from .forms import PlanForm
from django.contrib.auth.decorators import user_passes_test

# @user_passes_test(lambda u: u.is_superuser)  # Optional: restrict to admin

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import PlanForm
from .models import Plan


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import PlanForm
from .models import Plan


@login_required
@user_passes_test(lambda u: u.is_superuser or getattr(u, "role", None) == "Accountant")
def add_plan(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    if request.method == "POST":
        form = PlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.created_by = user
            if not plan.owner or plan.owner not in allowed_users:
                plan.owner = user
            plan.save()
            return redirect('plan_list')
    else:
        form = PlanForm()
        if "owner" in form.fields:
            form.fields['owner'].queryset = allowed_users

    return render(request, "billing/add_plan.html", {"form": form})


from .models import Subscription, Plan
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required


from django.utils.timezone import now
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Plan, Subscription
from django.contrib.auth import get_user_model
from datetime import timedelta

from django.utils.timezone import now
from datetime import timedelta
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Plan, Subscription


from django.utils.timezone import now
from datetime import timedelta
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from .models import Plan, Subscription, SubscriptionInvoice


User = get_user_model()

@login_required
@user_passes_test(lambda u: u.is_superuser)
def subscribe(request, plan_id):
    user = request.user
    allowed_users = get_allowed_users(user)  # superuser + their accountants

    # Only allow plans owned by current superuser group
    plan = get_object_or_404(Plan, id=plan_id, owner__in=allowed_users)

    # Prevent duplicate group subscription
    existing_sub = Subscription.objects.filter(user__in=allowed_users, plan=plan, active=True).first()
    if existing_sub:
        messages.error(request, f"Your group is already subscribed to {plan.name}.")
        return redirect("plan_list")

    # Determine target user (superuser or an accountant)
    user_id = request.GET.get("user_id")
    target_user = get_object_or_404(User, id=user_id, id__in=[u.id for u in allowed_users]) if user_id else user

    # Deactivate any current active subscription for this user
    Subscription.objects.filter(user=target_user, active=True).update(active=False)

    # Calculate start and billing dates
    today = now().date()
    trial_end = today + timedelta(days=plan.trial_days) if plan.trial_days else None
    next_billing = trial_end if trial_end else today + plan.get_interval_delta()

    # Create the new subscription
    sub = Subscription.objects.create(
        user=target_user,
        plan=plan,
        active=True,
        start_date=today,
        next_billing_date=next_billing,
    )

    # Create invoice immediately (respecting trial days)
    invoice_amount = 0 if plan.trial_days else plan.price
    SubscriptionInvoice.objects.create(
        user=target_user,
        subscription=sub,
        amount=invoice_amount,
        description=f"Subscription for {plan.name}"
    )

    messages.success(
        request,
        f"{'Successfully subscribed to' if target_user == user else target_user.email + ' subscribed to'} {plan.name}"
    )
    return redirect("plan_list")





@login_required
@user_passes_test(is_accountant_or_superuser)
def subscription_success(request):
    return render(request, 'billing/success.html')


# 🔁 Recurring Invoice Generation
# @staff_member_required
# def generate_recurring_invoices_view(request):
#     today = now().date()
#     recurring_invoices = Invoice.objects.filter(is_recurring=True)
#     created_count = 0
#     for invoice in recurring_invoices:
#         interval = invoice.recurring_interval
#         due_date = None
#         if interval == 'monthly':
#             due_date = invoice.date + timedelta(days=30)
#         elif interval == 'quarterly':
#             due_date = invoice.date + timedelta(days=90)
#         elif interval == 'yearly':
#             due_date = invoice.date + timedelta(days=365)
#         if due_date and due_date <= today:
#             exists = Invoice.objects.filter(client=invoice.client, date=due_date, is_recurring=False).exists()
#             if not exists:
#                 new_invoice = Invoice.objects.create(
#                     client=invoice.client,
#                     date=due_date,
#                     due_date=due_date + timedelta(days=10),
#                     currency=invoice.currency,
#                     exchange_rate=invoice.exchange_rate,
#                     gst_percent=invoice.gst_percent,
#                     is_recurring=False,
#                     notes=invoice.notes,
#                     template_style=invoice.template_style
#                 )
#                 for item in invoice.items.all():
#                     new_invoice.items.create(
#                         description=item.description,
#                         quantity=item.quantity,
#                         unit_price=item.unit_price
#                     )
#                 for entry in invoice.time_entries.all():
#                     TimeEntry.objects.create(
#                         invoice=new_invoice,
#                         description=entry.description,
#                         hours=entry.hours,
#                         rate_per_hour=entry.rate_per_hour
#                     )
#                 created_count += 1
#     messages.success(request, f"{created_count} recurring invoices generated.")
#     return redirect('invoice_list')

from django.db.models import Sum
from django.shortcuts import render
from .models import Project, InvoiceItem, TimeEntry, JournalItem, Account

from decimal import Decimal
from django.db.models import Sum
from .models import Project, InvoiceItem, TimeEntry, JournalItem, Account

from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import render
from .models import Project, InvoiceItem, TimeEntry, JournalItem, Account

from django.core.paginator import Paginator
from django.shortcuts import render
from decimal import Decimal
from django.db.models import Sum
from accounting_app.models import Project, JournalItem, InvoiceItem, TimeEntry, Account
from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.core.paginator import Paginator
from django.shortcuts import render

from django.db.models import Sum, F
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from .models import Project, JournalItem

def is_accountant(user):
    return user.is_superuser or getattr(user, "role", "") == "Accountant"

from decimal import Decimal
from collections import defaultdict

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Sum, F, Q
from django.db.models.functions import Coalesce
from django.shortcuts import render

# assumes: Project has fields: name, client (FK), budget (Decimal)
# JournalItem: fields: project (FK), stage (FK), account (FK with account_type), debit, credit

from decimal import Decimal
from collections import defaultdict

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce
from django.db.models import DecimalField  # ✅ for typed Value/Coalesce

from decimal import Decimal
from collections import defaultdict

from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce
from django.db.models import DecimalField
from django.shortcuts import render

from .models import Project, TimeEntry, JournalItem, Invoice  # ✅ import Invoice

from decimal import Decimal
from collections import defaultdict
from django.db.models import Sum, F, DecimalField, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F, DecimalField, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render

from .models import Project
from .models import JournalItem
from .models import Invoice
from .models import TimeEntry


def get_allowed_projects_qs(user):
    """Return the queryset of projects visible to the given user."""
    projects = Project.objects.select_related("client").prefetch_related("stages")

    if user.is_superuser:
        # superuser sees:
        # - projects they own
        # - projects created by their accountants
        accountants = user.created_users.all()
        return projects.filter(
            Q(owner=user) | Q(created_by__in=accountants)
        )

    else:
        # accountant sees:
        # - projects they created
        # - projects owned by their superuser
        superuser_creator = getattr(user, "created_by", None)
        return projects.filter(
            Q(created_by=user) | Q(owner=superuser_creator)
        )

from decimal import Decimal
from django.db.models import F, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Project, ProjectStage, JournalItem, Invoice, TimeEntry
  # Assuming you have this helper

from django.db.models import Sum, F
from django.db.models.functions import Coalesce
from decimal import Decimal
@login_required
@user_passes_test(lambda u: u.is_superuser or getattr(u, "is_accountant", False))
def project_costing_report(request):
    projects = get_allowed_projects_qs(request.user)
    D0 = Decimal("0.00")
    DECIMAL0 = Value(D0, output_field=DecimalField())

    # --- SEARCH/FILTER ---
    project_filter = request.GET.get("project", "").strip()
    client_filter = request.GET.get("client", "").strip()
    not_found = False
    if project_filter:
        projects = projects.filter(name__icontains=project_filter)
    if client_filter:
        projects = projects.filter(client__name__icontains=client_filter)

    aggregated_rows = {}

    for project in projects:
        key = (project.name, project.client.id)

        # Expenses (project-wide)
        expense_total = (
            JournalItem.objects.filter(project=project, account__account_type="Expense")
            .aggregate(total=Coalesce(Sum(F("debit") - F("credit"), output_field=DecimalField()), DECIMAL0))
            ["total"] or D0
        )

        # Stage-wise expenses
        stage_expenses_qs = (
            JournalItem.objects.filter(project=project, account__account_type="Expense")
            .values("stage__id", "stage__name")
            .annotate(total=Coalesce(Sum(F("debit") - F("credit"), output_field=DecimalField()), DECIMAL0))
            .order_by("stage__order")
        )

        # Income (paid invoices)
        income_total = D0
        paid_invoices_qs = Invoice.objects.filter(project=project, status__iexact="paid").prefetch_related("items", "time_entries")
        for inv in paid_invoices_qs:
            twt = getattr(inv, "total_with_tax", None)
            amt = twt() if callable(twt) else twt
            income_total += D0 if amt is None else (amt if isinstance(amt, Decimal) else Decimal(str(amt)))

        # Time entry hours
        time_hours = TimeEntry.objects.filter(project=project).aggregate(
            total=Coalesce(Sum("hours", output_field=DecimalField()), DECIMAL0)
        )["total"] or D0

        # Budget / variance / profit
        budget = project.budget or D0
        budget_variance = budget - expense_total
        net_profit = income_total - expense_total

        if key not in aggregated_rows:
            aggregated_rows[key] = {
                "project_name": project.name,
                "client": project.client,
                "project_id": project.id,
                "budget": D0,
                "income": D0,
                "expense": D0,
                "budget_variance": D0,
                "net_profit": D0,
                "time_hours": D0,
                "start_date": project.start_date,
                "end_date": project.end_date,
                "trello_board_id": project.trello_board_id,
                "created": getattr(project, "created_at", None),
                "modified": getattr(project, "modified_at", None),
                "stages": {},
                "stage_expenses": stage_expenses_qs,
            }

        row = aggregated_rows[key]

        # Aggregate numbers
        row["budget"] += budget
        row["income"] += income_total
        row["expense"] += expense_total
        row["budget_variance"] += budget_variance
        row["net_profit"] += net_profit
        row["time_hours"] += time_hours

        # Merge dates
        if not row["start_date"] or (project.start_date and project.start_date < row["start_date"]):
            row["start_date"] = project.start_date
        if not row["end_date"] or (project.end_date and project.end_date > row["end_date"]):
            row["end_date"] = project.end_date

        # Fill missing trello / created / modified
        if not row["trello_board_id"] and project.trello_board_id:
            row["trello_board_id"] = project.trello_board_id
        if not row["created"] and hasattr(project, "created_at"):
            row["created"] = project.created_at
        if not row["modified"] and hasattr(project, "modified_at"):
            row["modified"] = project.modified_at

        # Deduplicate stages
        for stg in project.stages.all():
            key_stage = (stg.name, stg.order)
            if key_stage not in row["stages"]:
                row["stages"][key_stage] = {"id": stg.id, "name": stg.name, "order": stg.order}

    # Convert dict back to list and sort stages
    aggregated_list = []
    for row in aggregated_rows.values():
        row["stages"] = sorted(row["stages"].values(), key=lambda x: x["order"])
        aggregated_list.append(row)

    # --- Handle not found ---
    not_found = False
    if project_filter or client_filter:
        if len(aggregated_list) == 0:
            not_found = True

    # Paginate
    paginator = Paginator(aggregated_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Totals for current page
    totals = {
        "budget": sum(r["budget"] for r in page_obj.object_list) if page_obj.object_list else D0,
        "income": sum(r["income"] for r in page_obj.object_list) if page_obj.object_list else D0,
        "expense": sum(r["expense"] for r in page_obj.object_list) if page_obj.object_list else D0,
        "budget_variance": sum(r["budget_variance"] for r in page_obj.object_list) if page_obj.object_list else D0,
        "net_profit": sum(r["net_profit"] for r in page_obj.object_list) if page_obj.object_list else D0,
        "time_hours": sum(r["time_hours"] for r in page_obj.object_list) if page_obj.object_list else D0,
    }

    return render(request, "projects/project_costing_report.html", {
        "page_obj": page_obj,
        "rows": page_obj.object_list,
        "totals": totals,
        "project_filter": project_filter,
        "client_filter": client_filter,
        "not_found": not_found,  # flag for template
    })



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Project, ProjectStage
from .forms import ProjectEditForm
from django.forms import inlineformset_factory








@login_required
@user_passes_test(is_accountant)
def print_project_summary(request, client_id, project_name):
    # filter all projects with same client & name
    projects = Project.objects.filter(client_id=client_id, name=project_name)
    # recompute same grouped totals as in report
    # ...
    return render(request, "projects/print_summary.html", {"projects": projects})

# @login_required
# @user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='Accountant').exists())
# def project_costing_report(request):
#     projects = Project.objects.all()
#     report = []

#     for project in projects:
#         # Income from invoices and time entries
#         invoice_items = InvoiceItem.objects.filter(invoice__project=project)
#         time_entries = TimeEntry.objects.filter(project=project)

#         income_from_items = sum(item.total() for item in invoice_items)
#         income_from_time = sum(te.total() for te in time_entries)
#         total_income = income_from_items + income_from_time

#         # Expenses from journal items linked to this project and marked as Expense accounts
#         expense_journals = JournalItem.objects.filter(
#             project=project,
#             account__account_type='Expense'
#         )
#         total_expenses = sum(j.debit for j in expense_journals)

#         profit = total_income - total_expenses
#         budget = project.budget or 0

#         report.append({
#             'project': project,
#             'client': project.client.name,
#             'budget': budget,
#             'income': total_income,
#             'expenses': total_expenses,
#             'profit': profit
#         })

#     return render(request, 'projects/project_costing_report.html', {'report': report})
from datetime import date
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
# from .models import Project  # make sure this import exists

def is_accountant_or_superuser(user):
    return user.is_superuser or getattr(user, "role", "") == "Accountant"

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Project
from datetime import date

# Helper function to check if user is an accountant
def is_accountant(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

@login_required
@user_passes_test(is_accountant_or_superuser)
def project_list(request):
    q = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "-id")

    # Allow only these sort fields (prevents invalid field errors)
    allowed_sorts = {
        "name", "-name", "start_date", "-start_date", "end_date", "-end_date",
        "budget", "-budget", "id", "-id"
    }
    if sort not in allowed_sorts:
        sort = "-id"

    # Filtering projects based on user role
    if request.user.is_superuser:
        # Superusers can see all projects
        projects = Project.objects.select_related("client").order_by(sort)
    else:
        # Regular users see only their own projects or projects created by the superuser who created them
        projects = Project.objects.filter(
            Q(owner=request.user) | Q(owner__created_by=request.user)
        ).select_related("client").order_by(sort)

    # Filter by search query if provided
    if q:
        projects = projects.filter(
            Q(name__icontains=q) |
            Q(client__name__icontains=q) |
            Q(trello_board_id__icontains=q)
        )

    paginator = Paginator(projects, 20)  # 20 per page
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "projects/project_list.html",
        {
            "page_obj": page_obj,
            "q": q,
            "sort": sort,
            "today": date.today(),
        },
    )

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import ProjectForm, ProjectStageFormSet
from .models import Client

# Helper function to check if the user is an accountant or superuser
def is_accountant(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.shortcuts import render, redirect
from django.db.models import Q

from .forms import ProjectForm, ProjectStageFormSet
from .models import Project

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_accountant)
@transaction.atomic
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, user=request.user)
        formset = ProjectStageFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            project = form.save(commit=False)

            # 🔑 Ownership logic
            if request.user.is_superuser:
                project.created_by = request.user
                project.owner = request.user
            else:
                project.created_by = request.user
                project.owner = request.user.created_by  # their superuser

            project.save()

            # Save stages with ownership
            stages = formset.save(commit=False)
            for stage in stages:
                stage.project = project
                if request.user.is_superuser:
                    stage.created_by = request.user
                    stage.owner = request.user
                else:
                    stage.created_by = request.user
                    stage.owner = request.user.created_by
                stage.save()

            # Handle deleted stages
            for stage in formset.deleted_objects:
                stage.delete()

            # Save many-to-many if used
            formset.save_m2m()

            return redirect('project_costing_report')

    else:
        form = ProjectForm(user=request.user)
        formset = ProjectStageFormSet()

    return render(request, 'create_project.html', {
        'form': form,
        'formset': formset
    })



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from .models import Project
from .forms import ProjectForm, ProjectStageFormSet

@login_required
@user_passes_test(lambda u: u.is_superuser or getattr(u, "is_accountant", False))
@transaction.atomic
def project_create_edit(request, project_id=None):
    if project_id:
        project = get_object_or_404(Project, id=project_id)
        form_title = f"✏️ Edit Project: {project.name}"
    else:
        project = None
        form_title = "📁 Create New Project"

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project, user=request.user)
        formset = ProjectStageFormSet(request.POST, instance=project)

        if form.is_valid() and formset.is_valid():
            project_instance = form.save(commit=False)

            if not project_instance.pk:  # For new projects
                project_instance.created_by = request.user if request.user.is_superuser else request.user
                project_instance.owner = request.user if request.user.is_superuser else request.user.created_by

            project_instance.save()

            stages = formset.save(commit=False)
            for stage in stages:
                stage.project = project_instance
                if not stage.pk:
                    stage.created_by = request.user if request.user.is_superuser else request.user
                    stage.owner = request.user if request.user.is_superuser else request.user.created_by
                stage.save()

            for stage in formset.deleted_objects:
                stage.delete()

            formset.save_m2m()
            return redirect('project_costing_report')
    else:
        form = ProjectForm(instance=project, user=request.user)
        formset = ProjectStageFormSet(instance=project)

    return render(request, 'projects/create_edit_project.html', {
        "form": form,
        "formset": formset,
        "form_title": form_title,
    })



from django.shortcuts import render, redirect, get_object_or_404
from .models import Payroll, ContractorPayment, Employee
from .forms import PayrollForm, ContractorPaymentForm
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from decimal import Decimal

def is_hr_or_superuser(user):
    return user.is_superuser or user.groups.filter(name='HR').exists()

# @user_passes_test(is_hr_or_superuser)
from decimal import Decimal
from .models import Payroll, ContractorPayment
from .forms import PayrollForm
from django.shortcuts import render, redirect

from decimal import Decimal
from .models import Payroll, ContractorPayment
from .forms import PayrollForm
from django.shortcuts import render, redirect

from decimal import Decimal
from django.shortcuts import render, redirect
from .forms import PayrollForm
from .models import Payroll, ContractorPayment

from decimal import Decimal
from django.shortcuts import render, redirect
from .forms import PayrollForm
from .models import Payroll, ContractorPayment

from decimal import Decimal
from .forms import PayrollForm
from .models import Payroll, ContractorPayment
from .models import TDSRecord  # ✅ import this
from decimal import Decimal
from django.shortcuts import redirect, render
from .forms import PayrollForm
from .models import ContractorPayment, TDSRecord

from django.shortcuts import render, redirect
from .forms import PayrollForm
from .models import Payroll, ContractorPayment, TDSRecord





# views.py
from decimal import Decimal
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import PayrollForm
from .models import ContractorPayment, TDSRecord
from .payroll_math import contractor_breakup

@login_required
@user_passes_test(lambda u: u.is_accountant or u.is_superuser)
def create_payroll(request):
    user = request.user

    if request.method == 'POST':
        form = PayrollForm(request.POST, user=user)
        if form.is_valid():
            payroll_type = form.cleaned_data['payroll_type']
            employee = form.cleaned_data['name']
            month = form.cleaned_data['month']
            basic = form.cleaned_data['basic_salary'] or Decimal('0')
            other_allowances = form.cleaned_data.get('other_allowances', Decimal('0')) or Decimal('0')
            ot_hours = form.cleaned_data.get('overtime_hours', Decimal('0')) or Decimal('0')
            ot_rate = form.cleaned_data.get('overtime_rate', Decimal('0')) or Decimal('0')

            if payroll_type == 'contractor':
                br = contractor_breakup(basic, other_allowances, ot_hours, ot_rate)  

                # Save gross in ContractorPayment
                payment = ContractorPayment.objects.create(
                    name=employee,
                    date=month,
                    amount=br["gross"],   # ✅ gross amount
                    description=f"Contractor payment for {month.strftime('%B %Y')}",
                    is_paid=False,
                    created_by=user,
                    owner=user if user.is_superuser else user.owner
                )

                # Create TDS record from gross
                TDSRecord.create_from_contractor_payment(payment, gross_amount=br["gross"])

                return redirect('contractor_payment_list')

            else:
                payroll = form.save(commit=False)
                payroll.created_by = user
                payroll.owner = user if user.is_superuser else user.owner
                payroll.calculate()
                payroll.save()
                TDSRecord.create_from_payroll(payroll)
                return redirect('payroll_list')
    else:
        form = PayrollForm(user=user)

    return render(request, 'payroll/create_payroll.html', {'form': form})






# @user_passes_test(is_hr_or_superuser)
from decimal import Decimal
from django.db.models import Sum
from .models import Payroll, TDSRecord
from decimal import Decimal
from django.db.models import Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import Payroll, TDSRecord

def is_accountant_or_superuser(user):
    return user.is_superuser or getattr(user, "is_accountant", False)
from decimal import Decimal
from django.db.models import Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import Payroll, TDSRecord

from decimal import Decimal
from django.db.models import Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from .models import Payroll, TDSRecord

@login_required
@user_passes_test(lambda u: u.is_accountant or u.is_superuser)
def payroll_list(request):
    user = request.user

    # 🔑 Ownership-based filtering (same as before)
    if user.is_superuser:
        payrolls = Payroll.objects.filter(name__owner=user)
        # If you added owner to TDSRecord, keep this for scoping:
        tenant_owner = user
    else:
        tenant_owner = getattr(user, 'created_by', None)
        payrolls = Payroll.objects.filter(name__owner=tenant_owner)

    # 🔹 Show FILED TDS (from TDSRecord) + Net based on FILED TDS
    for p in payrolls:
        # IMPORTANT: reference_id is stored as string; also ensure we only fetch "Payroll" TDS
        filed = (
            TDSRecord.objects
            .filter(source="Payroll", reference_id=str(p.id))
            # If your TDSRecord has owner, also add: .filter(owner=tenant_owner)
            .aggregate(total=Sum('tds_amount'))['total']
            or Decimal('0.00')
        )
        p.tds_dynamic = filed

        # include overtime in earnings to match your model logic
        ot_pay = (p.overtime_hours or 0) * (p.overtime_rate or 0)
        total_earnings = (p.basic_salary or 0) + (p.hra or 0) + (p.other_allowances or 0) + ot_pay
        total_deductions = (p.pf or 0) + (p.esi or 0) + p.tds_dynamic
        p.net_salary_dynamic = total_earnings - total_deductions
    return render(request, "payroll/payroll_list.html", {"payrolls": payrolls})





# @user_passes_test(is_hr_or_superuser)
# def create_contractor_payment(request):
#     form = ContractorPaymentForm(request.POST or None)
#     if form.is_valid():
#         form.save()
#         messages.success(request, "Contractor payment recorded.")
#         return redirect('contractor_payment_list')
#     return render(request, 'payroll/contractor_payment.html', {'form': form})

# @user_passes_test(is_hr_or_superuser)
from django.shortcuts import render
from .models import ContractorPayment

from decimal import Decimal
from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.shortcuts import render
from .models import ContractorPayment, ContractorFilingRecord


def is_accountant_or_superuser(user):
    return user.is_superuser or getattr(user, "is_accountant", False)
from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import render
from .models import ContractorPayment, ContractorFilingRecord
from .utils import get_employee_queryset_for_user

# views.py (contractor_payment_list)
from decimal import Decimal
from django.db.models import Q
from .models import ContractorPayment, ContractorFilingRecord

from decimal import Decimal
from django.db.models import Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import ContractorPayment, ContractorFilingRecord, TDSRecord

from decimal import Decimal
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import ContractorPayment, ContractorFilingRecord, TDSRecord
from decimal import Decimal
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import ContractorPayment, ContractorFilingRecord, TDSRecord

def is_accountant_or_superuser(u):
    return u.is_superuser or getattr(u, "is_accountant", False)

@login_required
@user_passes_test(is_accountant_or_superuser)
def contractor_payment_list(request):
    user = request.user

    if user.is_superuser:
        # 🧭 Show rows created by THIS superuser OR by any user whose created_by == THIS superuser
        payments = (
            ContractorPayment.objects
            .filter(Q(created_by=user) | Q(created_by__created_by=user))
            .select_related("name", "owner", "created_by")
            .order_by("-date", "-id")
        )
    else:
        # 📎 Accountant sees their own rows or rows owned by their superuser (tenant)
        payments = (
            ContractorPayment.objects
            .filter(Q(created_by=user) | Q(owner=user.created_by))
            .select_related("name", "owner", "created_by")
            .order_by("-date", "-id")
        )

    # 🔢 Filed TDS from TDSRecord + Net Paid
    for p in payments:
        gross = p.amount or Decimal('0.00')

        # Sum TDS records filed for this contractor payment (kept tenant-agnostic; add owner filter if you store it)
        tds_filed = (
            TDSRecord.objects
            .filter(source="Contractor", reference_id=str(p.id))
            .aggregate(total=Sum('tds_amount'))['total'] or Decimal('0.00')
        )
        p.tds_dynamic = tds_filed

        filing = ContractorFilingRecord.objects.filter(contractor_payment=p).first()
        filing_amt = filing.amount_filed if filing else Decimal('0.00')

        p.net_paid_dynamic = (gross - (p.tds_dynamic + filing_amt)).quantize(Decimal('0.01'))

    return render(request, "payroll/contractor_payment_list.html", {"payments": payments})











# @user_passes_test(is_hr_or_superuser)
# def salary_slip(request, pk):
#     payroll = get_object_or_404(Payroll, pk=pk)
#     return render(request, 'payroll/salary_slip.html', {'payroll': payroll})
from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from .models import Payroll
from .models import TDSRecord  # <- update to your actual app/model
from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from .models import Payroll, TDSRecord

from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Payroll, TDSRecord

def is_accountant_or_superuser(u):
    return u.is_superuser or getattr(u, "is_accountant", False)

@login_required
@user_passes_test(is_accountant_or_superuser)
def salary_slip(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk)

    # 🔒 If you added owner to TDSRecord, use it to avoid cross-tenant mixing:
    # tenant_owner = payroll.owner
    # tds_qs = TDSRecord.objects.filter(owner=tenant_owner, source="Payroll", reference_id=str(payroll.id))

    # Show only FILED/GENERATED TDS for this payroll
    tds_qs = TDSRecord.objects.filter(source="Payroll", reference_id=str(payroll.id))
    tds_dynamic = tds_qs.aggregate(total=Sum('tds_amount'))['total'] or Decimal('0.00')

    # Include overtime in earnings
    overtime_pay = (payroll.overtime_hours or 0) * (payroll.overtime_rate or 0)

    total_earnings = (
        (payroll.basic_salary or 0)
        + (payroll.hra or 0)
        + (payroll.other_allowances or 0)
        + overtime_pay
    )
    total_deductions = (payroll.pf or 0) + (payroll.esi or 0) + tds_dynamic
    net_salary_dynamic = total_earnings - total_deductions

    context = {
        'payroll': payroll,
        'overtime_pay': overtime_pay,
        'tds_dynamic': tds_dynamic,
        'total_earnings_dynamic': total_earnings,
        'total_deductions_dynamic': total_deductions,
        'net_salary_dynamic': net_salary_dynamic,
        'tds_records': tds_qs.order_by('-filing_date', '-id'),
    }
    return render(request, 'payroll/salary_slip.html', context)







# views.py

from .forms import EmployeeForm

# @user_passes_test(is_hr_or_superuser)
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import EmployeeForm

from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import EmployeeForm

# def create_employee(request):
#     if request.method == 'POST':
#         form = EmployeeForm(request.POST)
#         if form.is_valid():
#             employee = form.save()
#             if employee.is_contractor:
#                 messages.success(request, "Contractor added.")
#                 return redirect('contractor_list')
#             else:
#                 messages.success(request, "Employee added.")
#                 return redirect('employee_list')
#     else:
#         form = EmployeeForm()

#     return render(request, 'payroll/create_employee.html', {'form': form})




from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required


from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_accountant)
def employee_list(request):
    user = request.user

    base_qs = Employee.objects.filter(is_contractor=False).exclude(user__is_superuser=True)

    if user.is_superuser:
        # Superuser domain: self + accountants created by them
        accountants = list(user.created_users.all())
        allowed_users = [user] + accountants
    else:
        # Accountant: only themselves + their superuser
        superuser_creator = getattr(user, "created_by", None)
        allowed_users = [user]
        if superuser_creator:
            allowed_users.append(superuser_creator)

    # Employees must belong to this superuser "domain"
    employees = base_qs.filter(
        Q(created_by__in=allowed_users) |
        Q(owner__in=allowed_users)
    ).distinct().order_by("name")

    paginator = Paginator(employees, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "payroll/employee_list.html", {"page_obj": page_obj})








from django.views.decorators.http import require_POST

# @user_passes_test(is_hr_or_superuser)
# @require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Payroll 
from django.http import HttpResponse, HttpResponseNotAllowed



from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponseNotAllowed
from django.contrib import messages
from .models import Payroll

@login_required
@user_passes_test(is_accountant)
def mark_regular_payroll_paid(request, pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    payroll = get_object_or_404(Payroll, pk=pk)

    if payroll.name.is_contractor:
        messages.error(request, "This payroll belongs to a contractor.")
        return redirect('payroll_list')

    payroll.is_paid = True
    payroll.save()

    messages.success(request, f"Payroll for {payroll.name} marked as paid.")
    return redirect('payroll_list')


@login_required
@user_passes_test(is_accountant)
def mark_contractor_payroll_paid(request, pk):
    payment = get_object_or_404(ContractorPayment, pk=pk)
    if request.method == 'POST':
        payment.is_paid = True
        payment.save()
        messages.success(request, "Marked as paid.")
    return redirect('contractor_payment_list')






from django.shortcuts import render, get_object_or_404, redirect
from .models import Payroll
from .forms import FilingForm
from django.contrib import messages


@login_required
@user_passes_test(is_accountant)
def update_filing_status(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk)

    try:
        filing = FilingRecord.objects.get(payroll=payroll)
    except FilingRecord.DoesNotExist:
        filing = None

    if request.method == 'POST':
        form = FilingRecordForm(request.POST, request.FILES, instance=filing)
        if form.is_valid():
            filing_record = form.save(commit=False)
            filing_record.payroll = payroll
            filing_record.save()
            messages.success(request, 'Filing record updated successfully.')
            return redirect('payroll_list')
    else:
        form = FilingRecordForm(instance=filing)

    return render(request, 'payroll/update_filing_status.html', {'form': form, 'payroll': payroll})



# views.py
# views.py

@login_required
@user_passes_test(is_accountant_or_superuser)
def filing_record_list(request, payroll_id):
    payroll = get_object_or_404(Payroll, id=payroll_id)
    filings = payroll.filingrecord_set.all()  # or use related_name if defined
    return render(request, 'payroll/filing_list.html', {
        'payroll': payroll,
        'filings': filings
    })









# from django.template.loader import render_to_string
# from weasyprint import HTML
# from django.http import HttpResponse

# # @user_passes_test(is_hr_or_superuser)
# def download_salary_slip(request, pk):
#     payroll = get_object_or_404(Payroll, pk=pk)
#     html_string = render_to_string('payroll/salary_slip.html', {'payroll': payroll})
#     pdf = HTML(string=html_string).write_pdf()

#     response = HttpResponse(pdf, content_type='application/pdf')
#     response['Content-Disposition'] = f'filename=SalarySlip_{payroll.employee.name}_{payroll.month.strftime("%Y_%m")}.pdf'
#     return response


from django.shortcuts import render, get_object_or_404
from .models import Payroll
from django.contrib.auth.decorators import user_passes_test

# @user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='HR').exists())
# def salary_slip(request, pk):
#     payroll = get_object_or_404(Payroll, pk=pk)
#     return render(request, 'payroll/salary_slip.html', {'payroll': payroll})




from django.http import JsonResponse
from .models import Employee

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_accountant)
def get_employees_by_type(request):
    emp_type = request.GET.get("type")
    user = request.user

    # Ownership filtering
    if user.is_superuser:
        base_qs = Employee.objects.filter(owner=user)
    else:
        base_qs = Employee.objects.filter(owner=user.created_by)

    # Filter by type
    if emp_type == "contractor":
        employees = base_qs.filter(is_contractor=True)
    elif emp_type == "employee":
        employees = base_qs.filter(is_contractor=False)
    else:
        employees = base_qs.none()

    return JsonResponse(list(employees.values("id", "name")), safe=False)



from django.db.models import Sum
from .models import Payroll, Employee

@login_required
@user_passes_test(is_accountant_or_superuser)
def get_total_net_salary(employee_id):
    total = Payroll.objects.filter(name_id=employee_id).aggregate(
        total_net=Sum('net_salary')
    )['total_net'] or 0
    return total

from django.shortcuts import render
from .models import Employee
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required


@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_accountant)
def contractor_list(request):
    user = request.user

    base_qs = Employee.objects.filter(is_contractor=True).exclude(user__is_superuser=True)

    if user.is_superuser:
        # Superuser domain: self + accountants created by them
        accountants = list(user.created_users.all())
        allowed_users = [user] + accountants
    else:
        # Accountant: themselves + their superuser
        superuser_creator = getattr(user, "created_by", None)
        allowed_users = [user]
        if superuser_creator:
            allowed_users.append(superuser_creator)

    contractors = base_qs.filter(
        Q(created_by__in=allowed_users) |
        Q(owner__in=allowed_users)
    ).distinct().order_by("name")

    paginator = Paginator(contractors, 10)  # Show 10 contractors per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "payroll/contractor_list.html", {"page_obj": page_obj})



from django.shortcuts import get_object_or_404, render
from .models import Payroll  # or ContractorPayment if you separate models

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Payroll
from .models import ContractorPayment

from decimal import Decimal
from django.shortcuts import get_object_or_404, render

# views.py
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from .models import ContractorPayment, ContractorFilingRecord

@login_required
@user_passes_test(is_accountant_or_superuser)
def contractor_salary_slip(request, pk):
    contractor_payment = get_object_or_404(ContractorPayment, pk=pk)

    amount = contractor_payment.amount or Decimal('0.00')
    tds = round(amount * Decimal('0.10'), 2)

    # Get amount_filed from ContractorFilingRecord if exists
    filing_record = ContractorFilingRecord.objects.filter(contractor_payment=contractor_payment).first()
    amount_filed = filing_record.amount_filed if filing_record else Decimal('0.00')

    total_deductions = tds + amount_filed
    net_paid = round(amount - total_deductions, 2)

    # Attach computed values for the template
    contractor_payment.tds = tds
    contractor_payment.amount_filed = amount_filed
    contractor_payment.total_deductions = total_deductions
    contractor_payment.net_paid = net_paid
    contractor_payment.filing_record = filing_record  # so we can also show filing date, etc.

    return render(request, 'payroll/contractor_salary_slip.html', {
        'payment': contractor_payment
    })



# views.py
from django.shortcuts import render, redirect
from .forms import TaxDeclarationForm
from .models import Payroll, Employee, EmployeeTaxSummary
from django.db.models import Sum
from datetime import date

@login_required
@user_passes_test(is_accountant_or_superuser)
def tax_declaration_view(request):
    if request.method == 'POST':
        form = TaxDeclarationForm(request.POST, user=request.user)
        if form.is_valid():
            declaration = form.save(commit=False)
            # (optional) set owner/created_by if these fields exist on your model
            if hasattr(declaration, "owner"):
                declaration.owner = request.user if request.user.is_superuser else request.user.created_by
            if hasattr(declaration, "created_by"):
                declaration.created_by = request.user
            declaration.save()
            return redirect('generate_tax_summary', employee_id=declaration.name.id)
    else:
        form = TaxDeclarationForm(user=request.user)
    return render(request, 'tax/declare_tax.html', {'form': form})




from django.db.models import Sum


# views.py
from django.shortcuts import get_object_or_404

from datetime import date
from decimal import Decimal
from django.shortcuts import get_object_or_404, render
from django.db.models import Sum

@login_required
@user_passes_test(is_accountant_or_superuser)
def generate_tax_summary(request, employee_id):
    employee = get_object_or_404(Employee, id=employee_id)
    current_year = date.today().year

    payrolls = Payroll.objects.filter(name=employee)

    total_income = payrolls.aggregate(total=Sum('basic_salary'))['total'] or Decimal('0.00')

    # ✅ TDS from TDSRecord (generated/“filed” TDS), not from Payroll.tds
    payroll_ids = list(payrolls.values_list('id', flat=True))
    total_tds = (
        TDSRecord.objects
        .filter(source="Payroll", reference_id__in=[str(pid) for pid in payroll_ids])
        .aggregate(total=Sum('tds_amount'))['total']
        or Decimal('0.00')
    )

    declaration = TaxDeclaration.objects.filter(name=employee).order_by('-submitted_on').first()
    if declaration:
        year = declaration.financial_year
        approved_deduction = declaration.approved_amount or Decimal('0.00')
    else:
        year = f"{current_year - 1}-{current_year}"
        approved_deduction = Decimal('0.00')

    taxable_income = total_income - approved_deduction

    summary, created = EmployeeTaxSummary.objects.update_or_create(
        name=employee,
        year=year,
        defaults={
            'total_income': total_income,
            'approved_deductions': approved_deduction,
            'approved_amount': approved_deduction,
            'taxable_income': taxable_income,
            'total_tds': total_tds,
        }
    )
    return render(request, 'tax/tax_summary.html', {'summary': summary})




# views.py
from django.shortcuts import render, get_object_or_404, redirect
from .models import ContractorPayment, ContractorFilingRecord
from .forms import ContractorFilingForm

@login_required
@user_passes_test(is_accountant)
def update_contractor_filing(request, pk):
    payment = get_object_or_404(ContractorPayment, pk=pk)
    try:
        filing = ContractorFilingRecord.objects.get(contractor_payment=payment)
    except ContractorFilingRecord.DoesNotExist:
        filing = None

    if request.method == 'POST':
        form = ContractorFilingForm(request.POST, request.FILES, instance=filing)
        if form.is_valid():
            filing_record = form.save(commit=False)
            filing_record.contractor_payment = payment
            filing_record.save()
            return redirect('contractor_payment_list')
    else:
        form = ContractorFilingForm(instance=filing)

    return render(request, 'payroll/update_contractor_filing.html', {
        'form': form,
        'payment': payment
    })



from django.shortcuts import render, get_object_or_404
from .models import ContractorPayment, ContractorFilingRecord

@login_required
@user_passes_test(is_accountant_or_superuser)
def contractor_filing_record_list(request, contractor_payment_id):
    contractor_payment = get_object_or_404(ContractorPayment, id=contractor_payment_id)
    filings = ContractorFilingRecord.objects.filter(contractor_payment=contractor_payment)

    return render(request, 'payroll/contractor_filing_record_list.html', {
        'contractor_payment': contractor_payment,
        'filings': filings
    })


    

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.contrib import messages
from .models import TaxRecord
from .forms import TaxRecordForm

from django.core.paginator import Paginator

@login_required
@user_passes_test(is_accountant_or_superuser)
def tax_record_list(request):
    user = request.user

    # Restrict records depending on role
    if user.is_superuser:
        records = TaxRecord.objects.filter(owner=user)
    else:
        records = TaxRecord.objects.filter(created_by=user)

    records = records.order_by('-date')

    # Pagination
    paginator = Paginator(records, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ Correct: totals per tax_type (aggregated once, not per record)
    totals = (
        records.values('tax_type')
        .annotate(total=Sum('tax_amount'))
        .order_by('tax_type')
    )

    # ✅ Grand total
    grand_total = records.aggregate(total=Sum('tax_amount'))['total'] or 0

    return render(request, 'tax/tax_record_list.html', {
        'page_obj': page_obj,
        'totals': totals,
        'grand_total': grand_total,
    })


from django.db import IntegrityError, transaction


@login_required
@user_passes_test(is_accountant_or_superuser)
def create_tax_record(request):
    if request.method == 'POST':
        form = TaxRecordForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    record = form.save(commit=False)

                    # Set creator and owner
                    if hasattr(record, "created_by"):
                        record.created_by = request.user
                    if hasattr(record, "owner"):
                        record.owner = request.user if request.user.is_superuser else request.user.created_by

                    record.calculate_tax()
                    record.save()  # raises IntegrityError on duplicate

                messages.success(request, "✅ Tax record created.")
                return redirect('tax_record_list')
            except IntegrityError:
                form.add_error('invoice_number', "Invoice number already exists.")
    else:
        form = TaxRecordForm()
    return render(request, 'tax/tax_record_form.html', {'form': form})



@login_required
@user_passes_test(is_accountant_or_superuser)
def mark_tax_filed(request, pk):
    record = get_object_or_404(TaxRecord, pk=pk)
    record.filed = True
    record.filing_date = record.filing_date or record.date
    record.save()
    messages.success(request, "✅ Tax marked as filed.")
    return redirect('tax_record_list')


from django.db.models import Sum
from django.shortcuts import render
from .models import TaxRecord
from datetime import date
from calendar import month_name

@login_required
@user_passes_test(is_accountant_or_superuser)
def tax_filing_report(request):
    user = request.user
    year = request.GET.get('year', date.today().year)
    month = request.GET.get('month')
    month_list = [(i, month_name[i]) for i in range(1, 13)]

    # Restrict records to current user’s scope
    if user.is_superuser:
        records = TaxRecord.objects.filter(owner=user, date__year=year)
    else:
        records = TaxRecord.objects.filter(created_by=user, date__year=year)

    if month:
        records = records.filter(date__month=month)

    # Totals by tax type (only visible records)
    totals = records.values('tax_type').annotate(
        total_tax=Sum('tax_amount'),
        total_base=Sum('taxable_amount'),
    )

    # Summary stats
    summary = {
        'total_tax_amount': records.aggregate(Sum('tax_amount'))['tax_amount__sum'] or 0,
        'total_records': records.count(),
        'filed': records.filter(filed=True).count(),
        'unfiled': records.filter(filed=False).count(),
    }

    return render(request, 'tax/filing_report.html', {
        'records': records,
        'totals': totals,
        'summary': summary,
        'year': year,
        'month': month,
        'month_list': month_list,
    })

    
    
    
from django.shortcuts import render, get_object_or_404, redirect
from .models import TDSRecord
from .forms import TDSRecordForm
from django.contrib import messages
from django.db.models import Sum
from .models import Payroll, ContractorPayment

from django.core.paginator import Paginator

from decimal import Decimal
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from .models import TDSRecord, Payroll, ContractorPayment
 # or your existing checker
@login_required
@user_passes_test(is_accountant_or_superuser)
def tds_record_list(request):
    user = request.user
    # Determine the tenant owner: superuser sees their own records; regular users see their creator's
    tenant_owner = user if user.is_superuser else getattr(user, "created_by", None)

    # Get Payroll IDs for this tenant
    payroll_ids = Payroll.objects.filter(name__owner=tenant_owner).values_list("id", flat=True)

    # Get ContractorPayment IDs for this tenant
    contractor_ids = ContractorPayment.objects.filter(owner=tenant_owner).values_list("id", flat=True)

    # Fetch TDS records for Payroll and Contractors belonging to this tenant
    tds_qs = TDSRecord.objects.filter(
        Q(source="Payroll", reference_id__in=map(str, payroll_ids)) |
        Q(source="Contractor", reference_id__in=map(str, contractor_ids))
    ).order_by("-payment_date")

    # Pagination
    paginator = Paginator(tds_qs, 5)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Total TDS calculation
    total_tds = tds_qs.aggregate(total=Sum("tds_amount"))["total"] or Decimal("0.00")

    return render(request, "tds/tds_record_list.html", {
        "records": page_obj,
        "total_tds": total_tds,
        "page_obj": page_obj,
    })

# def add_tds_record(request):
#     if request.method == 'POST':
#         form = TDSRecordForm(request.POST)
#         if form.is_valid():
#             record = form.save(commit=False)
#             record.calculate_tds()
#             record.save()
#             messages.success(request, "✅ TDS record added.")
#             return redirect('tds_record_list')
#     else:
#         form = TDSRecordForm()
#     return render(request, 'tds/tds_record_form.html', {'form': form})

@login_required
@user_passes_test(is_accountant_or_superuser)
def mark_tds_filed(request, pk):
    record = get_object_or_404(TDSRecord, pk=pk)
    record.filed = True
    record.filing_date = record.filing_date or record.payment_date
    record.save()
    messages.success(request, "✅ TDS marked as filed.")
    return redirect('tds_record_list')



# views.py
from django.shortcuts import render, get_object_or_404, redirect
from .forms import TDSRecordForm
from .models import Payroll

from django.contrib import messages
from .forms import TDSRecordForm  # keep your form path

def is_accountant_or_superuser(u):  # if you don't already have this
    return u.is_superuser or getattr(u, "is_accountant", False)

@login_required
@user_passes_test(is_accountant_or_superuser)
def create_tds_from_payroll(request, payroll_id):
    payroll = get_object_or_404(Payroll, pk=payroll_id)

    # ✅ One-click generate path from the list (POST)
    if request.method == 'POST' and request.POST.get('quick_generate') == '1':
        # Uses your factory (make sure it doesn't overwrite with 10% if you use slabs)
        TDSRecord.create_from_payroll(payroll)
        payroll.tds_filed = True
        payroll.save(update_fields=["tds_filed"])
        messages.success(request, f"TDS generated for {payroll.name.name} ({payroll.month:%B %Y}).")
        return redirect('payroll_list')

    # Existing manual form flow (unchanged)
    if request.method == 'POST':
        form = TDSRecordForm(request.POST, payroll=payroll)
        if form.is_valid():
            rec = form.save(commit=False)
            rec.source = "Payroll"
            rec.reference_id = str(payroll.id)
            # If TDSRecord has owner, set: rec.owner = payroll.owner
            rec.save()
            messages.success(request, "TDS record saved.")
            return redirect('tds_record_list')
    else:
        form = TDSRecordForm(payroll=payroll)

    return render(request, 'tds/tds_record_form.html', {'form': form})



from .models import ContractorPayment

@login_required
@user_passes_test(is_accountant_or_superuser)
def create_tds_from_contractor(request, contractor_id):
    contractor = get_object_or_404(ContractorPayment, pk=contractor_id)

    if request.method == 'POST':
        form = TDSRecordForm(request.POST, contractor=contractor)
        if form.is_valid():
            form.save()
            return redirect('tds_record_list')
    else:
        form = TDSRecordForm(contractor=contractor)

    return render(request, 'tds/tds_record_form.html', {'form': form})


from django.db.models import Sum, Q
from django.utils.timezone import now
from .models import JournalItem

# utils.py or same views.py
from django.db.models import Sum
from decimal import Decimal
from .models import Payroll, ContractorPayment, ContractorFilingRecord, JournalItem, Account
from decimal import Decimal
from django.db.models import Sum
from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import JournalItem, Account, Payroll, ContractorPayment, ContractorFilingRecord, TDSRecord
# your custom role check


from decimal import Decimal
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import JournalItem, Account, Payroll, ContractorPayment, TDSRecord, ContractorFilingRecord


from decimal import Decimal
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import JournalItem, Account, Payroll, ContractorPayment, TDSRecord, ContractorFilingRecord



from decimal import Decimal
from django.db.models import Sum, Q
from .models import Payroll, TDSRecord, ContractorPayment, ContractorFilingRecord, Account

def get_cash_flow_context(user, tenant_user_ids, entries):
    # ----------------- Operating inflows/outflows -----------------
    operating_inflows = entries.filter(
        account__account_type='Revenue'
    ).aggregate(Sum('credit'))['credit__sum'] or Decimal('0.00')

    operating_outflows = entries.filter(
        account__account_type='Expense'
    ).aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')

    # ----------------- Payroll outflows (Paid, scoped to tenant) -----------------
    payroll_out = Decimal('0.00')
    payroll_qs = Payroll.objects.filter(
        is_paid=True
    ).filter(
        Q(owner__id__in=tenant_user_ids) | Q(created_by__id__in=tenant_user_ids)
    )

    for p in payroll_qs:
        # Use filed TDS only, matching payroll_list logic
        tds_total = TDSRecord.objects.filter(
            source="Payroll", reference_id=str(p.id)
        ).aggregate(total=Sum('tds_amount'))['total'] or Decimal('0.00')

        # Include overtime in earnings
        overtime_pay = (p.overtime_hours or 0) * (p.overtime_rate or 0)
        total_earnings = (p.basic_salary or 0) + (p.hra or 0) + (p.other_allowances or 0) + overtime_pay
        total_deductions = (p.pf or 0) + (p.esi or 0) + tds_total

        net_salary = total_earnings - total_deductions
        payroll_out += net_salary

    # ----------------- Contractor outflows (Paid, scoped to tenant) -----------------
    contractor_out = Decimal('0.00')
    contractor_qs = ContractorPayment.objects.filter(
        is_paid=True
    ).filter(
        Q(owner__id__in=tenant_user_ids) | Q(created_by__id__in=tenant_user_ids)
    )

    for c in contractor_qs:
        tds = round(c.amount * Decimal('0.10'), 2)
        filing_record = ContractorFilingRecord.objects.filter(contractor_payment=c).first()
        filing_amt = filing_record.amount_filed if filing_record else Decimal('0.00')
        contractor_out += c.amount - (tds + filing_amt)

    # ----------------- Investing and Financing -----------------
    investing_out = entries.filter(
        account__account_type='Asset'
    ).aggregate(Sum('debit'))['debit__sum'] or Decimal('0.00')

    financing_in = entries.filter(
        account__account_type='Equity'
    ).aggregate(Sum('credit'))['credit__sum'] or Decimal('0.00')

    # ----------------- Net calculations -----------------
    net_operating = operating_inflows - operating_outflows - payroll_out - contractor_out
    net_investing = -investing_out
    net_financing = financing_in
    net_cash_flow = net_operating + net_investing + net_financing

    # ----------------- Opening & Closing Balances (Bank accounts scoped to tenant) -----------------
    bank_accounts = Account.objects.filter(
        is_bank=True
    ).filter(
        Q(owner__id__in=tenant_user_ids) | Q(created_by__id__in=tenant_user_ids)
    )
    opening_balance = sum(acc.opening_balance for acc in bank_accounts)
    closing_balance = opening_balance + net_cash_flow

    return {
        'operating_inflows': operating_inflows,
        'operating_outflows': operating_outflows,
        'payroll_out': payroll_out,
        'contractor_out': contractor_out,
        'net_operating': net_operating,
        'investing_out': investing_out,
        'net_investing': net_investing,
        'financing_in': financing_in,
        'net_financing': net_financing,
        'net_cash_flow': net_cash_flow,
        'opening_balance': opening_balance,
        'closing_balance': closing_balance,
    }


@login_required
@user_passes_test(is_accountant_or_superuser)
def cash_flow_statement(request):
    user = request.user

    # ----------------- Determine tenant users for scoping -----------------
    if user.is_superuser:
        # Superuser sees self + accountants they created
        tenant_user_ids = list(user.created_users.filter(role='Accountant').values_list('id', flat=True))
        tenant_user_ids.append(user.id)
    elif user.is_accountant:
        # Accountant sees self + their superuser
        tenant_user_ids = [user.id]
        if user.created_by:
            tenant_user_ids.append(user.created_by.id)
    else:
        tenant_user_ids = [user.id]

    # ----------------- Restrict journal entries -----------------
    if user.is_superuser or user.is_accountant:
        entries = JournalItem.objects.filter(
            Q(created_by__id__in=tenant_user_ids) | Q(account__created_by__id__in=tenant_user_ids)
        ).select_related('account', 'entry').order_by('-entry__date')
    else:
        entries = JournalItem.objects.filter(
            created_by=user
        ).select_related('account', 'entry').order_by('-entry__date')

    # ----------------- Paginate journal entries -----------------
    paginator = Paginator(entries, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ----------------- Build cash flow context -----------------
    context = get_cash_flow_context(user, tenant_user_ids, entries)
    context['page_obj'] = page_obj

    return render(request, 'reports/cash_flow_statement.html', context)




@login_required
@user_passes_test(is_accountant_or_superuser)
def download_cash_flow_pdf(request):
    context = get_cash_flow_context()
    template = get_template('reports/cash_flow_pdf.html')
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="detailed_cash_flow.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)
    return response

from decimal import Decimal
from django.shortcuts import render
from .models import Project
from django.db.models import Sum
from collections import defaultdict

from decimal import Decimal
from collections import defaultdict

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Q
from django.shortcuts import render

# import your models
# from accounting_app.models import Project, JournalItem   # adjust path/names as needed

from decimal import Decimal
from django.db.models import Sum, Q
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import Project, JournalItem

def is_accountant_or_superuser(user):
    return user.is_superuser or getattr(user, "is_accountant", False)

@login_required
@user_passes_test(is_accountant_or_superuser)
def budget_vs_actual_report(request):
    user = request.user

    # --- Determine tenant owner ---
    tenant_owner = user if user.is_superuser else getattr(user, "created_by", None)

    # --- Load projects scoped to this tenant ---
    projects = Project.objects.filter(
        Q(owner=tenant_owner) | Q(created_by=tenant_owner)
    ).select_related('client').order_by('name')

    D0 = Decimal('0.00')

    # --- Compute Actual Expense from journal (Expense accounts) ---
    exp_rows = (
        JournalItem.objects
        .filter(project__in=projects, account__account_type='Expense')
        .values('project')
        .annotate(deb=Sum('debit'), cre=Sum('credit'))
    )
    expense_by_project = {
        r['project']: (r['deb'] or D0) - (r['cre'] or D0) for r in exp_rows
    }

    # --- Build rows for template ---
    project_data = []
    total_budget = D0
    total_expense = D0
    total_variance = D0

    for p in projects:
        budget = Decimal(p.budget or 0)
        actual_expense = expense_by_project.get(p.id, D0)
        variance = budget - actual_expense

        total_budget += budget
        total_expense += actual_expense
        total_variance += variance

        project_data.append({
            'project': p,
            'budget': budget,
            'expense': actual_expense,       # Actual Expense
            'budget_variance': variance,     # Budget vs Actual variance
        })

    return render(request, 'reports/budget_vs_actual.html', {
        'project_data': project_data,
        'total_budget': total_budget,
        'total_expense': total_expense,
        'total_variance': total_variance,
    })



from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from .models import Project

from collections import defaultdict
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from .models import Project

@login_required
@user_passes_test(is_accountant_or_superuser)
def download_budget_vs_actual_pdf(request):
    projects = Project.objects.select_related('client')
    grouped = defaultdict(lambda: {'budget': 0, 'expense': 0, 'project': None})

    for project in projects:
        key = (project.name, project.client.name)
        grouped[key]['project'] = project
        grouped[key]['budget'] += project.budget or 0
        grouped[key]['expense'] += project.expenses or 0

    project_data = []
    total_budget = total_expense = total_variance = 0

    for data in grouped.values():
        variance = data['budget'] - data['expense']
        total_budget += data['budget']
        total_expense += data['expense']
        total_variance += variance
        project_data.append({
            'project': data['project'],
            'budget': data['budget'],
            'expense': data['expense'],
            'budget_variance': variance,
        })

    template = get_template('reports/budget_vs_actual_pdf.html')
    html = template.render({
        'project_data': project_data,
        'total_budget': total_budget,
        'total_expense': total_expense,
        'total_variance': total_variance,
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="budget_vs_actual_report.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('PDF generation failed', status=500)
    return response




# views.py
from django.shortcuts import render
from decimal import Decimal
from django.db.models import Sum
from .models import Project, InvoiceItem, TimeEntry, JournalItem, Account
from collections import defaultdict
from decimal import Decimal
from django.db.models import Sum
from .models import Project, InvoiceItem, TimeEntry, JournalItem, Account
from django.shortcuts import render

from collections import defaultdict
from decimal import Decimal
from django.db.models import Sum
from django.shortcuts import render
from .models import Project, InvoiceItem, TimeEntry, JournalItem, Account
from decimal import Decimal
from collections import defaultdict
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.db.models import Sum, Q
from .models import Project, InvoiceItem, TimeEntry, Account, JournalItem

def is_accountant_or_superuser(user):
    return user.is_superuser or getattr(user, "is_accountant", False)

from decimal import Decimal
from collections import defaultdict
from django.db.models import F, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import Project, Invoice, TimeEntry, JournalItem

@login_required
@user_passes_test(lambda u: u.is_superuser or getattr(u, "is_accountant", False))
def project_profitability_report(request):
    user = request.user

    # Get projects scoped to tenant (same as project_costing_report)
    projects = get_allowed_projects_qs(user)
    D0 = Decimal("0.00")
    DECIMAL0 = D0

    grouped_data = {}
    total_income = total_expense = total_profit = D0

    for project in projects:
        key = (project.name, project.client.id)

        # Expenses (project-wide)
        expense_total = (
            JournalItem.objects.filter(project=project, account__account_type="Expense")
            .aggregate(total=Coalesce(Sum(F("debit") - F("credit"), output_field=DecimalField()), DECIMAL0))
            ["total"] or D0
        )

        # Income (paid invoices)
        income_total = D0
        paid_invoices = Invoice.objects.filter(project=project, status__iexact="paid").prefetch_related("items")
        for inv in paid_invoices:
            twt = getattr(inv, "total_with_tax", None)
            amt = twt() if callable(twt) else twt
            income_total += D0 if amt is None else (amt if isinstance(amt, Decimal) else Decimal(str(amt)))

        # Profit
        net_profit = income_total - expense_total

        # Build grouped row
        grouped_data[key] = {
            "project_name": project.name,
            "client": project.client.name,
            "income": income_total,
            "expense": expense_total,
            "profit": net_profit,
            "margin": (net_profit / income_total * 100) if income_total > 0 else 0,
        }

        total_income += income_total
        total_expense += expense_total
        total_profit += net_profit

    # Convert to list for template
    report_data = []
    for row in grouped_data.values():
        row["margin"] = round(row["margin"], 2)
        report_data.append(row)

    total_margin = (total_profit / total_income * 100) if total_income > 0 else 0

    return render(request, "reports/project_profitability_report.html", {
        "report_data": report_data,
        "total_income": total_income,
        "total_expense": total_expense,
        "total_profit": total_profit,
        "total_margin": round(total_margin, 2),
    })


from collections import defaultdict
from decimal import Decimal
from django.db.models import Sum
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import Project, InvoiceItem, TimeEntry, JournalItem, Account

@login_required
@user_passes_test(is_accountant_or_superuser)
def download_project_profitability_pdf(request):
    projects = Project.objects.select_related('client')
    grouped_data = defaultdict(lambda: {
        'income': Decimal('0.00'),
        'expenses': Decimal('0.00'),
        'profit': Decimal('0.00'),
    })

    for project in projects:
        key = (project.name, project.client.name)

        invoice_items = InvoiceItem.objects.filter(invoice__project=project)
        item_income = sum(
            item.total() if callable(getattr(item, 'total', None)) else item.quantity * item.unit_price
            for item in invoice_items
        )

        time_entries = TimeEntry.objects.filter(project=project)
        time_income = sum(
            te.total() if callable(getattr(te, 'total', None)) else te.hours * te.rate_per_hour
            for te in time_entries
        )

        income = Decimal(item_income) + Decimal(time_income)

        expense_accounts = Account.objects.filter(account_type='Expense')
        expenses = JournalItem.objects.filter(project=project, account__in=expense_accounts)
        expense = expenses.aggregate(total=Sum('debit'))['total'] or Decimal('0.00')

        profit = income - expense

        grouped_data[key]['income'] += income
        grouped_data[key]['expenses'] += expense
        grouped_data[key]['profit'] += profit

    report_data = []
    total_income = total_expense = total_profit = Decimal('0.00')

    for (project_name, client_name), values in grouped_data.items():
        income = values['income']
        expense = values['expenses']
        profit = values['profit']
        margin = (profit / income * 100) if income > 0 else 0

        report_data.append({
            'project': project_name,
            'client': client_name,
            'income': income,
            'expenses': expense,
            'profit': profit,
            'margin': round(margin, 2),
        })

        total_income += income
        total_expense += expense
        total_profit += profit

    context = {
        'report_data': report_data,
        'total_income': total_income,
        'total_expense': total_expense,
        'total_profit': total_profit,
        'total_margin': round((total_profit / total_income * 100), 2) if total_income > 0 else 0,
    }

    template = get_template('reports/project_profitability_pdf.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="project_profitability_report.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('PDF generation failed', status=500)
    return response



from django.shortcuts import render
from django.db.models import Sum
from .models import TaxRecord

from django.db.models import Sum
from django.db.models.functions import Upper, Trim

from django.db.models import Sum
from django.db.models.functions import Upper, Trim
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import TaxRecord

def is_accountant_or_superuser(user):
    return user.is_superuser or getattr(user, "is_accountant", False)

@login_required
@user_passes_test(is_accountant_or_superuser)
def tax_summary_report(request):
    user = request.user

    # Determine tenant owner
    tenant_owner = user if user.is_superuser else getattr(user, "created_by", None)

    # Scope TaxRecords to tenant (owner or created_by)
    records = TaxRecord.objects.filter(
        Q(owner=tenant_owner) | Q(created_by=tenant_owner)
    ).order_by('-date')

    # Aggregate by tax type
    qs = (
        records
        .annotate(_tax_type=Upper(Trim('tax_type')))
        .values('_tax_type')
        .annotate(
            taxable_total=Sum('taxable_amount'),
            total_tax=Sum('tax_amount'),
        )
        .order_by('_tax_type')
    )

    # Convert to list and rename key for template
    summary = []
    for row in qs:
        row['tax_type'] = row.pop('_tax_type')
        summary.append(row)

    # Grand totals scoped to tenant
    grand_totals = records.aggregate(
        taxable_total=Sum('taxable_amount'),
        total_tax=Sum('tax_amount')
    )

    return render(request, 'tax/tax_summary_report.html', {
        'records': records,
        'summary': summary,
        'grand_totals': grand_totals
    })


from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from .models import TaxRecord
from django.db.models import Sum

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.db.models.functions import Upper, Trim
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

@login_required
@user_passes_test(is_accountant_or_superuser)
def download_tax_summary_pdf(request):
    records = TaxRecord.objects.all().order_by('-date')

    # ✅ Grouped summary (same as HTML view)
    qs = (
        records
        .annotate(_tax_type=Upper(Trim('tax_type')))
        .values('_tax_type')
        .annotate(
            taxable_total=Sum('taxable_amount'),
            total_tax=Sum('tax_amount'),
        )
        .order_by('_tax_type')
    )

    summary = []
    for row in qs:
        row['tax_type'] = row.pop('_tax_type')
        summary.append(row)

    grand_totals = records.aggregate(
        taxable_total=Sum('taxable_amount'),
        total_tax=Sum('tax_amount')
    )

    # ✅ Build PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="tax_summary_report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("📊 Tax Summary Report", styles['Title']))
    elements.append(Spacer(1, 0.2 * inch))

    # ---- Detailed Tax Records ----
    elements.append(Paragraph("🗓️ Detailed Tax Records", styles['Heading3']))
    data_records = [["Date", "Tax Type", "Taxable Amount (₹)", "Tax Amount (₹)", "Filed?"]]

    for r in records:
        data_records.append([
            r.date.strftime("%d-%m-%Y"),
            r.tax_type,
            f"₹{r.taxable_amount:.2f}",
            f"₹{r.tax_amount:.2f}",
            "Yes" if r.filed else "No"
        ])

    if len(data_records) == 1:  # No rows added
        data_records.append(["-", "-", "0.00", "0.00", "-"])

    table_records = Table(data_records, colWidths=[1.2*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1*inch])
    table_records.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (2, 1), (3, -1), "RIGHT"),
        ("ALIGN", (4, 1), (4, -1), "CENTER"),
    ]))
    elements.append(table_records)
    elements.append(Spacer(1, 0.3 * inch))

    # ---- Summary Table ----
    elements.append(Paragraph("🧾 Summary by Tax Type", styles['Heading3']))
    data_summary = [["Tax Type", "Total Taxable (₹)", "Total Tax (₹)"]]

    for row in summary:
        data_summary.append([
            row['tax_type'],
            f"₹{row['taxable_total']:.2f}",
            f"₹{row['total_tax']:.2f}"
        ])

    # Add grand totals
    data_summary.append([
        "Grand Total",
        f"₹{grand_totals['taxable_total']:.2f}" if grand_totals['taxable_total'] else "₹0.00",
        f"₹{grand_totals['total_tax']:.2f}" if grand_totals['total_tax'] else "₹0.00"
    ])

    table_summary = Table(data_summary, colWidths=[2.5*inch, 2*inch, 2*inch])
    table_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    elements.append(table_summary)

    # ✅ Build PDF
    doc.build(elements)
    return response




from django.shortcuts import render
from django.db.models import Sum
from .models import Invoice, JournalItem, TaxRecord, TDSRecord, Account

from django.db.models import Sum, F, FloatField, ExpressionWrapper
from .models import Invoice, InvoiceItem, TimeEntry, JournalItem, TaxRecord, TDSRecord
from decimal import Decimal
from django.db.models import Sum, F, Q
from django.db.models.functions import Coalesce

from decimal import Decimal
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from .models import (
    JournalItem, Invoice, InvoiceItem, TimeEntry,
    TaxRecord, TDSRecord
)



from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import (
    Sum, F, Q, Value, DecimalField, ExpressionWrapper
)
from django.db.models.functions import Coalesce
from django.shortcuts import render

from .models import Invoice, JournalItem, TaxRecord, TDSRecord
# from .utils import is_accountant_or_superuser  # if defined elsewhere

# Safe Decimal constants to avoid mixed-type errors
D0 = Value(Decimal('0.00'), output_field=DecimalField(max_digits=18, decimal_places=2))
HUNDRED = Value(Decimal('100.00'), output_field=DecimalField(max_digits=6, decimal_places=2))
from django.db.models import Sum, Q, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from accounting_app.models import JournalItem, Invoice, TaxRecord, TDSRecord, Payroll, ContractorPayment

D0 = Decimal('0.00')
HUNDRED = Decimal('100.00')
from decimal import Decimal
from django.db.models import Sum, F, Q, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from .models import JournalItem, Invoice, TaxRecord, TDSRecord, Payroll, ContractorPayment

D0 = Decimal("0.00")
HUNDRED = Decimal("100.00")


def is_accountant_or_superuser(user):
    return user.is_superuser or getattr(user, "is_accountant", False)


from django.db.models import Sum, Q, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from .models import (
    User, JournalItem, Invoice, TaxRecord, TDSRecord, Payroll, ContractorPayment
)

D0 = 0
HUNDRED = 100


def is_accountant_or_superuser(user):
    return user.is_superuser or getattr(user, "is_accountant", False)


@login_required
@user_passes_test(is_accountant_or_superuser)
def financial_dashboard(request):
    user = request.user

    # -----------------------------
    # Tenant scoping
    # -----------------------------
    if user.is_superadmin:
        # Platform-wide superadmin → see everything
        tenant_users = User.objects.all()

    elif user.is_normal_superuser:
        # Tenant superuser → themselves + their accountants
        tenant_users = list(user.created_users.all()) + [user]

    elif user.is_accountant:
        # Accountant → themselves + their owning superuser
        tenant_owner = user.created_by
        tenant_users = [user, tenant_owner] if tenant_owner else [user]

    else:
        # Default fallback
        tenant_users = [user]

    # -----------------------------
    # Journal Items (Revenue & Expenses)
    # -----------------------------
    journalitems = JournalItem.objects.filter(
        Q(owner__in=tenant_users) | Q(created_by__in=tenant_users) |
        Q(account__owner__in=tenant_users) | Q(account__created_by__in=tenant_users)
    )

    revenue = journalitems.filter(account__account_type="Revenue") \
                          .aggregate(total=Coalesce(Sum("credit"), D0))["total"]
    expenses = journalitems.filter(account__account_type="Expense") \
                           .aggregate(total=Coalesce(Sum("debit"), D0))["total"]
    net_profit = revenue - expenses

    # -----------------------------
    # Invoices
    # -----------------------------
    inv_qs = Invoice.objects.filter(
        Q(owner__in=tenant_users) | Q(created_by__in=tenant_users) |
        Q(project__owner__in=tenant_users) | Q(project__created_by__in=tenant_users)
    )

    inclusive_total_expr = ExpressionWrapper(
        F("total_amount") + (F("total_amount") * Coalesce(F("gst_percent"), D0) / HUNDRED),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )

    amount_due_inclusive_expr = ExpressionWrapper(
        inclusive_total_expr - Coalesce(F("payment__amount"), D0),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )

    inv_qs = inv_qs.annotate(
        inclusive_total=inclusive_total_expr,
        amount_due_inclusive=amount_due_inclusive_expr,
    )

    outstanding_with_tax = inv_qs.filter(
        Q(status__iexact="unpaid") | Q(status__iexact="partial")
    ).aggregate(total_with_tax=Coalesce(Sum("amount_due_inclusive"), D0))["total_with_tax"]

    top_clients = (
        inv_qs.values(client_name=F("client__name"))
              .annotate(total_with_tax=Coalesce(Sum("inclusive_total"), D0))
              .order_by("-total_with_tax")[:5]
    )

    # -----------------------------
    # Tax Records
    # -----------------------------
    tax_summary = (
        TaxRecord.objects.filter(
            Q(owner__in=tenant_users) | Q(created_by__in=tenant_users)
        ).values("tax_type")
         .annotate(total=Coalesce(Sum("tax_amount"), D0))
         .order_by("tax_type")
    )

    # -----------------------------
    # TDS Records
    # -----------------------------
    payroll_ids = Payroll.objects.filter(
        Q(owner__in=tenant_users) | Q(created_by__in=tenant_users)
    ).values_list("id", flat=True)

    contractor_ids = ContractorPayment.objects.filter(
        Q(owner__in=tenant_users) | Q(created_by__in=tenant_users)
    ).values_list("id", flat=True)

    tds_qs = TDSRecord.objects.filter(
        Q(owner__in=tenant_users) | Q(created_by__in=tenant_users) |
        Q(source="Payroll", reference_id__in=payroll_ids) |
        Q(source="Contractor", reference_id__in=contractor_ids)
    )

    tds_total = tds_qs.aggregate(total=Coalesce(Sum("tds_amount"), D0))["total"]

    # -----------------------------
    # Render
    # -----------------------------
    context = {
        "revenue": revenue,
        "expenses": expenses,
        "net_profit": net_profit,
        "outstanding_with_tax": outstanding_with_tax,
        "top_clients": top_clients,
        "tax_summary": tax_summary,
        "tds_total": tds_total,
    }

    return render(request, "dashboard/financial_dashboard.html", context)





from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from .models import JournalItem, InvoiceItem, TimeEntry, TaxRecord, TDSRecord
from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, F, Q, Value, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

from .models import Invoice, InvoiceItem, TimeEntry, JournalItem, TaxRecord, TDSRecord
# from .utils import is_accountant_or_superuser  # if defined elsewhere

# Safe Decimal constants for Coalesce and math
D0 = Value(Decimal('0.00'), output_field=DecimalField(max_digits=18, decimal_places=2))
HUNDRED = Value(Decimal('100.00'), output_field=DecimalField(max_digits=6, decimal_places=2))


@login_required
@user_passes_test(is_accountant_or_superuser)
def download_financial_dashboard_pdf(request):
    # --------- Revenue & Expenses (NET) ----------
    total_revenue = (JournalItem.objects
        .filter(account__account_type='Revenue')
        .aggregate(total=Coalesce(Sum('credit'), D0))['total'])

    total_expenses = (JournalItem.objects
        .filter(account__account_type='Expense')
        .aggregate(total=Coalesce(Sum('debit'), D0))['total'])

    net_profit = total_revenue - total_expenses

    # --------- Tax-INCLUSIVE invoice math ----------
    # Your create_invoice saves pre-tax in Invoice.total_amount.
    # inclusive_total = total_amount + (total_amount * gst_percent / 100)
    inclusive_total_expr = ExpressionWrapper(
        F('total_amount') + (F('total_amount') * Coalesce(F('gst_percent'), D0) / HUNDRED),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )

    # If you track a single payment relation: payment__amount.
    # (If you don't track payments, see the fallback below.)
    amount_due_inclusive_expr = ExpressionWrapper(
        inclusive_total_expr - Coalesce(F('payment__amount'), D0),
        output_field=DecimalField(max_digits=18, decimal_places=2),
    )

    inv_qs = (Invoice.objects
        .annotate(
            inclusive_total=inclusive_total_expr,
            amount_due_inclusive=amount_due_inclusive_expr
        ))

    # Outstanding invoices (WITH tax) = sum of amount_due_inclusive for unpaid/partial
    outstanding_with_tax = (inv_qs
        .filter(Q(status__iexact='unpaid') | Q(status__iexact='partial'))
        .aggregate(total_with_tax=Coalesce(Sum('amount_due_inclusive'), D0))
    )['total_with_tax']

    # ---- Fallback if you DO NOT have payments on invoice ----
    # outstanding_with_tax = (inv_qs
    #     .filter(Q(status__iexact='unpaid') | Q(status__iexact='partial'))
    #     .aggregate(total_with_tax=Coalesce(Sum('inclusive_total'), D0))
    # )['total_with_tax']

    # Top clients (WITH tax)
    top_clients = (inv_qs
        .values(client_name=F('client__name'))
        .annotate(total_with_tax=Coalesce(Sum('inclusive_total'), D0))
        .order_by('-total_with_tax')[:5])

    # Tax summary (unchanged)
    tax_summary = (TaxRecord.objects
        .values('tax_type')
        .annotate(total=Coalesce(Sum('tax_amount'), D0)))

    # TDS (Decimal safe)
    tds_total = TDSRecord.objects.aggregate(total=Coalesce(Sum('tds_amount'), D0))['total']

    # --------- Render PDF ----------
    context = {
        'revenue': total_revenue,
        'expenses': total_expenses,
        'net_profit': net_profit,
        'outstanding_with_tax': outstanding_with_tax,   # <-- use this in template
        'top_clients': top_clients,                     # <-- has client_name & total_with_tax
        'tax_summary': tax_summary,
        'tds_total': tds_total,
    }

    template = get_template('dashboard/financial_dashboard_pdf.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="financial_dashboard.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("PDF generation failed", status=500)

    return response


from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from .models import AuditLog

# @staff_member_required

@login_required
@user_passes_test(is_accountant_or_superuser)
def audit_log_view(request):
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:100]
    return render(request, 'compliance/audit_log.html', {'logs': logs})


from django.shortcuts import render
from .versioning import VersionHistory
from django.contrib.contenttypes.models import ContentType

# def version_history_view(request, model_name, object_id):
#     content_type = ContentType.objects.get(model=model_name)
#     history = VersionHistory.objects.filter(content_type=content_type, object_id=object_id).order_by('-version_number')
#     return render(request, 'version_history.html', {'history': history})

@login_required
@user_passes_test(is_accountant_or_superuser)
def version_history_all_view(request):
    history = VersionHistory.objects.select_related('content_type').order_by('-created_at')
    return render(request, 'version_history.html', {'history': history})


from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.db.models import Sum
from .models import Account
from django.contrib.auth.decorators import login_required, user_passes_test

@login_required
@user_passes_test(is_accountant_or_superuser)
def trial_balance_pdf(request):
    accounts = Account.objects.annotate(
        total_debit=Sum('journalitem__debit'),
        total_credit=Sum('journalitem__credit'),
    )

    rows = []
    for acc in accounts:
        debit = acc.total_debit or 0
        credit = acc.total_credit or 0
        balance = credit - debit
        rows.append((acc.name, debit, credit, balance))

    template = get_template('reports/trial_balance_pdf.html')
    html = template.render({'rows': rows})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="trial_balance.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)
    return response


from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Account



# @login_required
# @user_passes_test(is_accountant_or_superuser)

@login_required
@user_passes_test(is_accountant_or_superuser)
def balance_sheet_pdf(request):
    accounts = Account.objects.all()

    def get_balance(acc):
        debits = sum(i.debit for i in acc.journalitem_set.all())
        credits = sum(i.credit for i in acc.journalitem_set.all())
        return debits - credits

    context = {
        'assets': [(a.name, get_balance(a)) for a in accounts.filter(account_type='Asset')],
        'liabilities': [(l.name, get_balance(l)) for l in accounts.filter(account_type='Liability')],
        'equity': [(e.name, get_balance(e)) for e in accounts.filter(account_type='Equity')],
        'readonly': request.user.is_superuser
    }

    template = get_template('reports/balance_sheet_pdf.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="balance_sheet.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('PDF generation failed', status=500)
    return response


from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Account
# from .utils import is_accountant_or_superuser


# @login_required
# @user_passes_test(is_accountant_or_superuser)

@login_required
@user_passes_test(is_accountant_or_superuser)
def profit_loss_pdf(request):
    def get_balance(acc):
        debits = sum(i.debit for i in acc.journalitem_set.all())
        credits = sum(i.credit for i in acc.journalitem_set.all())
        return credits - debits if acc.account_type == 'Revenue' else debits - credits

    revenue_data = [(r.name, get_balance(r)) for r in Account.objects.filter(account_type='Revenue')]
    expense_data = [(e.name, get_balance(e)) for e in Account.objects.filter(account_type='Expense')]
    net_profit = sum(r[1] for r in revenue_data) - sum(e[1] for e in expense_data)

    context = {
        'revenues': revenue_data,
        'expenses': expense_data,
        'net_profit': net_profit,
    }

    template = get_template('reports/profit_loss_pdf.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="profit_loss_report.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('PDF generation failed', status=500)
    return response


from django.shortcuts import render, get_object_or_404, redirect
from .models import Currency, ExchangeRate, CostCenter, InterCompanyTransaction, DeferredRevenue
from .forms import ExchangeRateForm, CostCenterForm, InterCompanyTransactionForm, DeferredRevenueForm
from django.shortcuts import render, redirect
from .forms import CurrencyForm
from django.contrib.auth.decorators import login_required, user_passes_test

# # Optional: Restrict to staff/admin users
# def is_finance_staff(user):
#     return user.is_superuser or user.groups.filter(name='Finance').exists()

# @login_required
# @user_passes_test(is_finance_staff)

@login_required
@user_passes_test(is_accountant_or_superuser)
def create_currency(request):
    if request.method == 'POST':
        form = CurrencyForm(request.POST)
        if form.is_valid():
            currency = form.save(commit=False)
            currency.created_by = request.user   # 👈 set owner
            currency.save()
            return redirect('currency_list')
    else:
        form = CurrencyForm()

    return render(request, 'finance/currency_form.html', {'form': form})


from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import Currency

  # reuse the helper

from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Currency
 # 👈 same helper you use elsewhere

@login_required
@user_passes_test(is_accountant_or_superuser)
def currency_list(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    currencies = (
        Currency.objects
        .filter(created_by__in=allowed_users)   # 👈 filter by allowed users
        .order_by("code")
    )

    return render(request, 'finance/currency_list.html', {'currencies': currencies})


# your helper function

@login_required
@user_passes_test(is_accountant_or_superuser)
def exchange_rate_list(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    rates = (
        ExchangeRate.objects
        .filter(
            from_currency__created_by__in=allowed_users,
            to_currency__created_by__in=allowed_users
        )
        .select_related("from_currency", "to_currency")
        .order_by("from_currency__code", "to_currency__code")
    )
    return render(request, 'finance/exchange_rate_list.html', {'rates': rates})


@login_required
@user_passes_test(is_accountant_or_superuser)
def add_exchange_rate(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    form = ExchangeRateForm(request.POST or None)

    # ✅ Restrict currency dropdowns using correct field names
    form.fields["from_currency"].queryset = Currency.objects.filter(created_by__in=allowed_users)
    form.fields["to_currency"].queryset = Currency.objects.filter(created_by__in=allowed_users)

    if form.is_valid():
        exchange_rate = form.save(commit=False)
        exchange_rate.created_by = user  # track ownership
        exchange_rate.save()
        return redirect('exchange_rate_list')

    return render(request, 'finance/exchange_rate_form.html', {'form': form})


from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from .models import CostCenter, Currency
from .forms import CostCenterForm
 # helper for allowed users

@login_required
@user_passes_test(is_accountant_or_superuser)
def cost_center_list(request):
    user = request.user
    allowed_users = get_allowed_users(user)
    
    centers = CostCenter.objects.filter(created_by__in=allowed_users).order_by("name")
    return render(request, 'finance/cost_center_list.html', {'centers': centers})


@login_required
@user_passes_test(is_accountant_or_superuser)
def add_cost_center(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    form = CostCenterForm(request.POST or None)
    
    # Optional: restrict any foreign key fields in the form by owner if needed
    # e.g., if the CostCenter has a currency field
    if 'currency' in form.fields:
        form.fields['currency'].queryset = Currency.objects.filter(created_by__in=allowed_users)

    if form.is_valid():
        center = form.save(commit=False)
        center.created_by = user  # assign ownership
        center.save()
        return redirect('cost_center_list')
    
    return render(request, 'finance/cost_center_form.html', {'form': form})


from django.shortcuts import render, redirect
from .models import InterCompanyTransaction
from .forms import InterCompanyTransactionForm

@login_required
@user_passes_test(is_accountant_or_superuser)
def inter_company_list(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    records = InterCompanyTransaction.objects.filter(created_by__in=allowed_users).order_by("-date")
    return render(request, 'finance/inter_company_list.html', {'records': records})


@login_required
@user_passes_test(is_accountant_or_superuser)
def add_inter_company(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    if request.method == 'POST':
        form = InterCompanyTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.created_by = user  # assign ownership
            transaction.save()
            return redirect('inter_company_list')
    else:
        form = InterCompanyTransactionForm()
    
    # Optional: restrict related foreign key fields (e.g., currency)
    if 'currency' in form.fields:
        form.fields['currency'].queryset = Currency.objects.filter(created_by__in=allowed_users)

    return render(request, 'finance/inter_company_form.html', {'form': form})



@login_required
@user_passes_test(is_accountant_or_superuser)
def deferred_revenue_list(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    # Filter records based on allowed users
    records = DeferredRevenue.objects.filter(created_by__in=allowed_users).order_by("-start_date")
    return render(request, 'finance/deferred_revenue_list.html', {'records': records})


@login_required
@user_passes_test(is_accountant_or_superuser)
def add_deferred_revenue(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    if request.method == 'POST':
        form = DeferredRevenueForm(request.POST)
        if form.is_valid():
            revenue = form.save(commit=False)
            revenue.created_by = user
            revenue.owner = user  # optional, depending on your ownership rules
            revenue.save()
            return redirect('deferred_revenue_list')
    else:
        form = DeferredRevenueForm()

    # Optional: restrict foreign key choices
    form.fields['customer'].queryset = Client.objects.filter(created_by__in=allowed_users)

    return render(request, 'finance/deferred_revenue_form.html', {'form': form})




from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from .models import SubscriptionInvoice
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import razorpay

# @login_required

@login_required
@user_passes_test(is_accountant_or_superuser)
def pay_invoice(request, invoice_id):
    invoice = get_object_or_404(SubscriptionInvoice, id=invoice_id, user=request.user, paid=False)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    razorpay_order = client.order.create({
        'amount': int(invoice.amount * 100),  # amount in paise
        'currency': 'INR',
        'payment_capture': 1
    })

    invoice.razorpay_order_id = razorpay_order['id']
    invoice.save()

    context = {
        'invoice': invoice,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'order_id': razorpay_order['id'],
        'amount': invoice.amount,
        'user': request.user,
    }
    return render(request, 'billing/razorpay_checkout.html', context)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt

@login_required
@user_passes_test(is_accountant_or_superuser)
def payment_success(request):
    payment_id = request.GET.get('payment_id')
    order_id = request.GET.get('order_id')
    invoice_id = request.GET.get('invoice_id')

    invoice = get_object_or_404(SubscriptionInvoice, id=invoice_id, razorpay_order_id=order_id)

    invoice.razorpay_payment_id = payment_id
    invoice.paid = True
    invoice.save()

    messages.success(request, "🎉 Payment successful! Invoice marked as paid.")
    return redirect('invoices_list')




# views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, F

from datetime import date

# ----------------------
# 📊 Budget Overview View
# ----------------------
from itertools import chain
from django.core.paginator import Paginator
from datetime import date

from datetime import date
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import F

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.core.paginator import Paginator
from decimal import Decimal
from datetime import date
from .models import Budget, Project
 # helper function

@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='Accountant').exists())
def budget_overview(request):
    user = request.user
    allowed_users = get_allowed_users(user)  # only budgets created by these users
    current_year = date.today().year

    # --- Filter budgets by allowed users ---
    budgets_qs = (
        Budget.objects
        .select_related('project', 'project__client', 'account')
        .filter(year=current_year, created_by__in=allowed_users)
    )

    if budgets_qs.exists():
        items = budgets_qs
        is_budget = True
    else:
        # --- Fallback to projects owned by allowed users ---
        projects = Project.objects.filter(start_date__year__lte=current_year, owner__in=allowed_users)
        items = [
            type("FallbackBudget", (), {
                "id": f"proj-{p.id}",
                "project": p,
                "amount": p.budget or Decimal("0.00"),
                "year": current_year,
                "month": None,
                "account": None,
            }) for p in projects if p.budget > 0
        ]
        is_budget = False

    # --- Pagination ---
    paginator = Paginator(items, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "finance/budget_overview.html", {
        "page_obj": page_obj,
        "is_budget": is_budget,
    })


# views.py
@login_required
@user_passes_test(is_accountant_or_superuser)
def add_budget(request):
    from .forms import BudgetForm

    form = BudgetForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect("budget_overview")

    return render(request, "finance/add_budget.html", {"form": form})


# ----------------------
# 🔁 Forecast Dashboard



# ----------------------
# 🔮 What-If Analysis View
# ----------------------

from decimal import Decimal
from .forms import WhatIfScenarioForm

from decimal import Decimal
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

# @login_required
# @user_passes_test(is_accountant_or_superuser)
# def what_if_scenarios(request):
#     from .models import WhatIfScenario, Forecast, Budget
#     scenarios = WhatIfScenario.objects.all()
#     context = []

#     for s in scenarios:
#         forecast_qs = Forecast.objects.filter(
#             project=s.project,
#             account=s.account
#         ).order_by('-year', '-month')

#         if forecast_qs.exists():
#             base = forecast_qs.first().forecast_amount
#         else:
#             budget_qs = Budget.objects.filter(
#                 project=s.project,
#                 account=s.account,
#                 year=date.today().year
#             )
#             base = budget_qs.first().amount if budget_qs.exists() else Decimal('0.00')

#         impact = Decimal(str(s.apply_scenario(base))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
#         context.append({'scenario': s, 'base': base, 'impact': impact})

#     return render(request, 'finance/what_if.html', {'scenarios': context})



# --- WHAT-IF + FvA (Forecast vs Actual) ---
from datetime import date
from decimal import Decimal
from collections import defaultdict

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, F, DecimalField, Value, Q
from django.db.models.functions import Coalesce
from django.shortcuts import render

from .models import (
    Forecast, Budget, Project, Account,
    Invoice, JournalItem, WhatIfScenario
)

D0 = Decimal("0.00")
DEC0 = Value(D0, output_field=DecimalField())


def _sum_decimal(qs, field):
    return qs.aggregate(total=Coalesce(Sum(field, output_field=DecimalField()), DEC0))["total"] or D0


def _month_name(m):
    # simple helper for templates
    return ["—","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m]


# views.py
from datetime import date
from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, DecimalField, Q
from django.db.models.functions import Coalesce
from django.shortcuts import render

from .models import Project, Account, Forecast, Budget, WhatIfScenario

D0 = Decimal("0.00")

def is_accountant_or_superuser(user):
    return user.is_superuser or getattr(user, "role", "") == "Accountant"

def _sum_decimal(qs, field_name: str) -> Decimal:
    return qs.aggregate(total=Coalesce(Sum(field_name, output_field=DecimalField()), D0))["total"] or D0


from decimal import Decimal
from django.db.models import Q, Sum
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from datetime import date
from .models import WhatIfScenario, Forecast, Budget, Project, Account

D0 = Decimal("0.00")

def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name="Accountant").exists()

from datetime import date
from decimal import Decimal
from django.db.models import Sum, Q
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import WhatIfScenario, Forecast, Budget, Project, Account

D0 = Decimal("0.00")


def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name="Accountant").exists()


@login_required
@user_passes_test(is_accountant_or_superuser)
def what_if_scenarios(request):
    year = int(request.GET.get("year", date.today().year))
    project_id = request.GET.get("project") or None
    account_id = request.GET.get("account") or None
    user = request.user

    # Allowed users based on tenant (superuser + their accountants)
    allowed_users = get_allowed_users(user)

    # Restrict scenarios by allowed users
    scenarios = WhatIfScenario.objects.select_related("project", "account").order_by("name")
    scenarios = scenarios.filter(Q(owner__in=allowed_users) | Q(owner__isnull=True))

    # Apply filters from request
    if project_id:
        scenarios = scenarios.filter(project_id=project_id)
    if account_id:
        scenarios = scenarios.filter(account_id=account_id)

    # Restrict projects/accounts to allowed users
    projects = Project.objects.filter(owner__in=allowed_users).order_by("name")
    accounts = Account.objects.filter(owner__in=allowed_users).order_by("name")

    rows = []

    for s in scenarios.distinct():
        proj = s.project
        acct = s.account

        # --- Forecast baseline ---
        f_qs = Forecast.objects.filter(year=year)
        if proj:
            f_qs = f_qs.filter(project=proj)
        if acct:
            # include forecasts for this account OR no account
            f_qs = f_qs.filter(Q(account=acct) | Q(account__isnull=True))

        baseline = f_qs.aggregate(total=Sum("forecast_amount"))["total"] or D0
        baseline_source = "Forecast"
        # --- Fallback to Budget if no forecast exists ---
        if baseline == D0:
            b_qs = Budget.objects.filter(year=year)
            if proj:
                b_qs = b_qs.filter(project=proj)
            if acct:
                b_qs = b_qs.filter(Q(account=acct) | Q(account__isnull=True))

            baseline = b_qs.aggregate(total=Sum("amount"))["total"] or D0
            baseline_source = "Budget" if baseline != D0 else "None"

        # --- Apply scenario safely ---
        try:
            after_val = s.apply_scenario(baseline)
            after = D0 if after_val is None else Decimal(after_val)
        except Exception:
            after = baseline

        delta = after - baseline
        pct = (delta / baseline * Decimal("100")) if baseline else D0

        rows.append({
            "scenario": s,
            "project": proj,
            "account": acct,
            "year": year,
            "baseline": baseline,
            "baseline_source": baseline_source, 
            "after": after,
            "delta": delta,
            "pct": pct,
        })

    # Years (from Forecasts + Budgets)
    f_years = set(Forecast.objects.values_list("year", flat=True))
    b_years = set(Budget.objects.values_list("year", flat=True))
    years = sorted(f_years | b_years | {year}, reverse=True)

    return render(request, "finance/what_if.html", {
        "rows": rows,
        "year": year,
        "years": years,
        "projects": projects,
        "accounts": accounts,
        "selected_project_id": project_id,
        "selected_account_id": account_id,
    })


from collections import defaultdict
from decimal import Decimal
from datetime import date

from django.db.models import Sum, DecimalField, F, Value as V
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from .models import Forecast, Invoice, JournalItem, Project

D0 = Decimal("0.00")
DEC0 = V(D0, output_field=DecimalField())


@login_required
@user_passes_test(is_accountant_or_superuser)
def forecast_vs_actual(request):
    """
    Monthly comparison for a year:
      - Forecast Income  = sum(Forecast for accounts with account_type='Income')
      - Forecast Expense = sum(Forecast for accounts with account_type='Expense')
      - Actual Expense   = sum(JournalItem (Expense) debit-credit) by entry.date month
    Optional filter by project.
    Only shows data for allowed users.
    """
    user = request.user
    allowed_users = get_allowed_users(user)

    # --- Inputs ---
    year = int(request.GET.get("year", date.today().year))
    project_id = request.GET.get("project") or None
    project = Project.objects.filter(id=project_id).first() if project_id else None

    # --- Forecasts ---
    f_qs = Forecast.objects.filter(year=year, created_by__in=allowed_users).select_related("account", "project")
    if project:
        f_qs = f_qs.filter(project=project)

    f_income = f_qs.filter(account__account_type="Income").values("month").annotate(
        amt=Coalesce(Sum("forecast_amount", output_field=DecimalField()), DEC0)
    )
    f_expense = f_qs.filter(account__account_type="Expense").values("month").annotate(
        amt=Coalesce(Sum("forecast_amount", output_field=DecimalField()), DEC0)
    )

    f_income_map = {row["month"]: row["amt"] or D0 for row in f_income}
    f_exp_map    = {row["month"]: row["amt"] or D0 for row in f_expense}

    # --- Actual Income (paid invoices) ---
    inv_qs = Invoice.objects.filter(status="paid", date__year=year, created_by__in=allowed_users)
    if project:
        inv_qs = inv_qs.filter(project=project)

    actual_income_by_month = defaultdict(lambda: D0)
    for inv in inv_qs.select_related("project").prefetch_related("items", "time_entries"):
        month = inv.date.month
        twt_attr = getattr(inv, "total_with_tax", None)
        twt = inv.total_with_tax() if callable(twt_attr) else twt_attr
        amt = D0 if twt is None else (twt if isinstance(twt, Decimal) else Decimal(str(twt)))
        actual_income_by_month[month] += amt

    # --- Actual Expense ---
    ji = JournalItem.objects.filter(
        account__account_type="Expense",
        entry__date__year=year,
        created_by__in=allowed_users
    )
    if project:
        ji = ji.filter(project=project)

    exp_rows = (ji.values("entry__date__month")
                 .annotate(total=Coalesce(Sum(F("debit") - F("credit"), output_field=DecimalField()), DEC0)))

    actual_exp_by_month = defaultdict(lambda: D0)
    for r in exp_rows:
        actual_exp_by_month[r["entry__date__month"]] = r["total"] or D0

    # --- Build rows 1..12 ---
    rows = []
    totals = {
        "forecast_income": D0, "forecast_expense": D0,
        "actual_income": D0,   "actual_expense": D0,
        "income_var": D0,      "expense_var": D0,
        "net_forecast": D0,    "net_actual": D0, "net_var": D0
    }

    for m in range(1, 13):
        fi = f_income_map.get(m, D0)
        fe = f_exp_map.get(m, D0)
        ai = actual_income_by_month.get(m, D0)
        ae = actual_exp_by_month.get(m, D0)

        income_var = ai - fi
        expense_var = fe - ae
        net_forecast = fi - fe
        net_actual   = ai - ae
        net_var      = net_actual - net_forecast

        rows.append({
            "month": m,
            "month_name": _month_name(m),
            "forecast_income": fi,
            "forecast_expense": fe,
            "actual_income": ai,
            "actual_expense": ae,
            "income_var": income_var,
            "expense_var": expense_var,
            "net_forecast": net_forecast,
            "net_actual": net_actual,
            "net_var": net_var,
        })

        totals["forecast_income"] += fi
        totals["forecast_expense"] += fe
        totals["actual_income"] += ai
        totals["actual_expense"] += ae
        totals["income_var"] += income_var
        totals["expense_var"] += expense_var
        totals["net_forecast"] += net_forecast
        totals["net_actual"] += net_actual
        totals["net_var"] += net_var

    projects = Project.objects.filter(owner__in=allowed_users).order_by("name")
    years = Forecast.objects.filter(created_by__in=allowed_users).values_list("year", flat=True).distinct().order_by("-year")

    return render(request, "finance/forecast_vs_actual.html", {
        "year": year,
        "years": years,
        "project": project,
        "projects": projects,
        "selected_project_id": str(project_id) if project_id else "",
        "selected_year": str(year),
        "rows": rows,
        "totals": totals,
    })

from django.contrib import messages

@login_required
@user_passes_test(is_accountant_or_superuser)
def add_what_if_scenario(request):
    if request.method == "POST":
        form = WhatIfScenarioForm(request.POST, user=request.user)
        if form.is_valid():
            scenario = form.save(commit=False)
            scenario.owner = request.user        # always attach owner
            scenario.created_by = request.user   # track creator
            scenario.save()
            messages.success(request, f"Scenario '{scenario.name}' created successfully.")
            return redirect("what_if_scenarios")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = WhatIfScenarioForm(user=request.user)

    return render(request, "finance/add_what_if.html", {"form": form})




# ----------------------
# 💵 Cash Flow Projection
# ----------------------

# @login_required
# @user_passes_test(is_accountant_or_superuser)
# def cash_flow_view(request):
#     from .models import CashFlowProjection
#     inflows = CashFlowProjection.objects.filter(direction='inflow').order_by('date')
#     outflows = CashFlowProjection.objects.filter(direction='outflow').order_by('date')
#     return render(request, 'finance/cash_flow.html', {'inflows': inflows, 'outflows': outflows})
# views.py
from datetime import date
from decimal import Decimal
from collections import defaultdict

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, DecimalField, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render

from .models import CashFlowProjection, Project, Invoice

# If you already have this helper, keep using your version:
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, DecimalField, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render

def is_accountant_or_superuser(user):
    return getattr(user, "is_superuser", False) or getattr(user, "role", "") == "Accountant"

D0 = Decimal("0.00")
DEC0 = Value(D0, output_field=DecimalField())

def _month_name(m: int) -> str:
    return ["—","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m]

def _is_scenario_desc(desc: str) -> bool:
    """
    Detect scenario-generated rows by description text.
    Adjust if you use a different wording.
    """
    if not desc:
        return False
    t = desc.strip().lower()
    return t.startswith("auto from scenario") or "[scenario]" in t

# views.py  — Cash Flow

from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from .models import CashFlowProjection, Invoice, Project


# --- helpers ---------------------------------------------------------------

# views.py
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.db.models import Sum, Q, DecimalField, Value
from django.db.models.functions import Coalesce

from .models import (
    CashFlowProjection, Forecast, Budget,
    WhatIfScenario, Invoice, Project
)

D0 = Decimal("0.00")
DEC0 = Value(D0, output_field=DecimalField())


def is_accountant_or_superuser(user):
    return getattr(user, "is_superuser", False) or getattr(user, "role", "") == "Accountant"


def _month_name(m: int) -> str:
    return ["—", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m]


def _sum_decimal(qs, field_name: str):
    return qs.aggregate(total=Coalesce(Sum(field_name, output_field=DecimalField()), DEC0))["total"] or D0


def _is_scenario_desc(desc: str) -> bool:
    if not desc:
        return False
    t = desc.strip().lower()
    return (
        t.startswith("auto from scenario")
        or "[scenario]" in t
        or "generated from what-if" in t
    )



from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from .models import CashFlowProjection, Forecast, WhatIfScenario, Invoice, Project

D0 = Decimal("0.00")

def is_accountant_or_superuser(user):
    return getattr(user, "is_superuser", False) or getattr(user, "role", "") == "Accountant"


def get_allowed_users(user):
    """
    Returns allowed users for the current superuser:
    - The superuser itself
    - Users assigned to this superuser (accountants)
    """
    if user.is_superuser:
        # Adjust this based on your actual user hierarchy
        return User.objects.filter(profile__supervisor=user) | User.objects.filter(id=user.id)
    return User.objects.filter(id=user.id)


def _month_name(m: int) -> str:
    return ["—", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m]


def _is_scenario_desc(desc: str) -> bool:
    if not desc:
        return False
    t = desc.strip().lower()
    return t.startswith("auto from scenario") or "[scenario]" in t


@login_required
@user_passes_test(is_accountant_or_superuser)
def cash_flow_view(request):
    today = date.today()
    current_year = today.year
    years = [current_year - 2, current_year - 1, current_year,
             current_year + 1, current_year + 2]

    # --- filters ---
    try:
        year = int(request.GET.get("year", current_year))
    except (TypeError, ValueError):
        year = current_year

    project_id = request.GET.get("project") or ""
    include_ar = request.GET.get("include_ar", "1") == "1"

    # --- allowed users ---
    allowed_users = get_allowed_users(request.user)

    # Base queryset for CashFlowProjection
    cfp = CashFlowProjection.objects.filter(
        date__year=year,
        created_by__in=allowed_users
    ).select_related("project", "account")

    if project_id:
        cfp = cfp.filter(project_id=project_id)

    # --- Collapse baseline + scenario (scenario overrides baseline) ---
    baseline_map = defaultdict(lambda: D0)
    scenario_map = defaultdict(lambda: D0)

    for r in cfp.values("date__month", "project_id", "account_id", "direction", "amount", "description"):
        m = r["date__month"]
        if not m:
            continue
        key = (m, r["project_id"] or None, r["account_id"] or None, r["direction"])
        amt = D0 if r["amount"] is None else Decimal(r["amount"])
        if _is_scenario_desc(r.get("description") or ""):
            scenario_map[key] += amt
        else:
            baseline_map[key] += amt

    final_map = defaultdict(lambda: D0)
    final_map.update(baseline_map)
    for k, v in scenario_map.items():
        final_map[k] = v

    # Aggregate per month
    inflow_map = defaultdict(lambda: D0)
    outflow_map = defaultdict(lambda: D0)
    for (m, _pid, _aid, direction), amt in final_map.items():
        if direction == "inflow":
            inflow_map[m] += amt
        else:
            outflow_map[m] += amt

    # --- Optional AR ---
    ar_map = defaultdict(lambda: D0)
    if include_ar:
        ar_qs = Invoice.objects.filter(
            status="unpaid",
            due_date__year=year,
            created_by__in=allowed_users
        )
        if project_id:
            ar_qs = ar_qs.filter(project_id=project_id)

        for inv in ar_qs:
            amt = getattr(inv, "total_with_tax", D0)
            if callable(amt):
                amt = amt()
            if amt is None:
                amt = D0
            elif not isinstance(amt, Decimal):
                amt = Decimal(str(amt))
            if inv.due_date:
                ar_map[inv.due_date.month] += amt

    # --- Build monthly rows + totals ---
    rows = []
    totals = {"proj_inflow": D0, "ar_inflow": D0, "total_inflow": D0, "outflow": D0, "net": D0}
    cumulative = D0

    for m in range(1, 13):
        proj_in = inflow_map.get(m, D0)
        ar_in = ar_map.get(m, D0) if include_ar else D0
        out = outflow_map.get(m, D0)
        total_in = proj_in + ar_in
        net = total_in - out
        cumulative += net
        rows.append({
            "month": m,
            "month_name": _month_name(m),
            "proj_inflow": proj_in,
            "ar_inflow": ar_in,
            "total_inflow": total_in,
            "outflow": out,
            "net": net,
            "cumulative": cumulative,
        })
        totals["proj_inflow"] += proj_in
        totals["ar_inflow"] += ar_in
        totals["total_inflow"] += total_in
        totals["outflow"] += out
        totals["net"] += net

    # Detail lists
    inflow_lines = cfp.filter(direction="inflow").order_by("date")
    outflow_lines = cfp.filter(direction="outflow").order_by("date")

    projects = Project.objects.filter(owner__in=allowed_users).order_by("name")
    selected_project_id = str(project_id) if project_id else ""

    return render(request, "finance/cash_flow.html", {
        "today": today,
        "years": years,
        "year": year,
        "projects": projects,
        "selected_project_id": selected_project_id,
        "include_ar": include_ar,
        "rows": rows,
        "totals": totals,
        "inflow_lines": inflow_lines,
        "outflow_lines": outflow_lines,
    })




from datetime import date
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import CashFlowProjection, Forecast, WhatIfScenario
 # assuming you have this helper
from datetime import date
from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect

from .models import CashFlowProjection, Forecast, WhatIfScenario
# your helper

from datetime import date
from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from .models import CashFlowProjection, Forecast, WhatIfScenario

@login_required
@user_passes_test(is_accountant_or_superuser)
def generate_cash_flow(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    # --- Forecasts ---
    forecasts = Forecast.objects.filter(created_by__in=allowed_users)
    for f in forecasts:
        CashFlowProjection.objects.update_or_create(
            project=f.project,
            account=f.account,
            date=date(f.year, f.month, 1),
            direction="inflow",
           created_by=f.created_by or f.owner,
            defaults={
                "amount": f.forecast_amount,
                "description": "Generated from Forecast",
            }
        )

    # --- What-If Scenarios ---
    scenarios = WhatIfScenario.objects.filter(owner__in=allowed_users)
    for s in scenarios:
        # Use the same month/year as forecast if exists, else current month
        if hasattr(s, 'month') and hasattr(s, 'year'):
            proj_date = date(s.year, s.month, 1)
        else:
            # fallback: use forecast month if available
            f_qs = Forecast.objects.filter(project=s.project, account=s.account)
            if f_qs.exists():
                proj_date = date(f_qs.first().year, f_qs.first().month, 1)
            else:
                proj_date = date.today()

        CashFlowProjection.objects.update_or_create(
            project=s.project,
            account=s.account,
            date=proj_date,
            direction="inflow" if s.impact_amount > 0 else "outflow",
            created_by=s.owner,
            defaults={
                "amount": abs(s.impact_amount),
                "description": f"Generated from What-If: {s.name}",
            }
        )

    return redirect("cash_flow")




# ----------------------
# 📈 Forecast vs Actual View
# ----------------------

# @login_required
# @user_passes_test(is_accountant_or_superuser)
# def forecast_vs_actual(request):
#     from .models import ForecastVariance
#     variances = ForecastVariance.objects.all()
#     return render(request, 'finance/forecast_vs_actual.html', {'variances': variances})
# from django.shortcuts import redirect
# from accounting_app.utils import generate_forecast_variance

@login_required
@user_passes_test(is_accountant_or_superuser)
def refresh_variance_view(request):
    generate_forecast_variance()
    return redirect('forecast_vs_actual')  # Update with your actual URL name


# ----------------------
# 📦 Monthly Actuals Aggregator (Utility)
# ----------------------

# from django.db.models import Sum, F
# from decimal import Decimal

# def get_actuals_for_month(project, month, year):
#     expenses = JournalItem.objects.filter(
#         project=project,
#         entry__date__year=year,
#         entry__date__month=month
#     ).aggregate(total=Sum('debit'))['total'] or Decimal('0')

#     income = InvoiceItem.objects.filter(
#         invoice__project=project,
#         invoice__date__year=year,
#         invoice__date__month=month
#     ).aggregate(total=Sum(F('quantity') * F('unit_price')))['total'] or Decimal('0')

#     return income - expenses  # Net actuals





@login_required
@user_passes_test(is_accountant_or_superuser)
def delete_budget(request, budget_id):
    from .models import Budget
    budget = get_object_or_404(Budget, id=budget_id)
    budget.delete()
    return redirect('budget_overview')
# from .utils import generate_forecast_variance
# def trigger_variance_update(request):
#     generate_forecast_variance()
#     return redirect('forecast_vs_actual')





from django.shortcuts import render, redirect
from .forms import RollingForecastForm


@login_required
@user_passes_test(is_accountant_or_superuser)
def forecast_form_view(request):
    
    form = RollingForecastForm(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('forecast_table')  # name of the table view URL

    return render(request, 'finance/forecast_form.html', {'form': form})

from datetime import date
from decimal import Decimal
from django.core.paginator import Paginator
from django.db import models
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect

from .models import Forecast, Project
from .forecast_from_invoices import rebuild_cash_forecast_from_unpaid_invoices


def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name="Accountant").exists()


@login_required
@user_passes_test(is_accountant_or_superuser)
def forecast_table_view(request):
    user = request.user
    allowed_users = get_allowed_users(user)  # includes superuser + their accountants
    current_year = date.today().year

    # --- Projects that belong to this superuser group ---
    allowed_projects = Project.objects.filter(owner__in=allowed_users)

    # --- Forecasts (auto + manual), but restricted to allowed projects ---
    forecasts_qs = (
        Forecast.objects.select_related("project", "project__client", "account")
        .filter(year=current_year, project__in=allowed_projects)
        .filter(
            models.Q(created_by__in=allowed_users)
            | models.Q(notes__startswith="[AUTO-INVOICE]")
        )
        .order_by("-year", "-month")
    )

    if forecasts_qs.exists():
        items = forecasts_qs
        is_forecast = True
    else:
        # --- Fallback to projects owned by allowed users ---
        projects = allowed_projects.filter(start_date__year__lte=current_year)
        items = [
            type("FallbackForecast", (), {
                "id": f"proj-{p.id}",
                "project": p,
                "forecast_amount": p.budget or Decimal("0.00"),
                "year": current_year,
                "month": None,
                "account": None,
                "notes": "Fallback from project budget",
                "month_name": "",   # to keep template happy
            }) for p in projects if p.budget > 0
        ]
        is_forecast = False

    # --- Pagination ---
    paginator = Paginator(items, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "finance/forecast_table.html",
        {
            "page_obj": page_obj,
            "is_forecast": is_forecast,
        },
    )


@login_required
@user_passes_test(is_accountant_or_superuser)
def forecast_rebuild_from_invoices(request):
    rebuild_cash_forecast_from_unpaid_invoices()
    return redirect("forecast_table")



from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect
from .forecast_from_invoices import rebuild_cash_forecast_from_unpaid_invoices

def is_accountant_or_superuser(user):
    return user.is_superuser or getattr(user, "role", "") == "Accountant"



# accounting_app/views_audit.py
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils.dateparse import parse_date

from .models import AuditLog

# audit/views.py
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.contrib.auth import get_user_model
from .models import AuditLog  # path to your model

@login_required
def audit_log_list(request):
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')
    model_name = request.GET.get('model') or ''
    action     = request.GET.get('action') or ''
    user_id    = request.GET.get('user') or ''
    date_from  = request.GET.get('from') or ''
    date_to    = request.GET.get('to') or ''
    q          = request.GET.get('q') or ''

    if model_name: logs = logs.filter(model_name__iexact=model_name)
    if action:     logs = logs.filter(action__iexact=action)
    if user_id:    logs = logs.filter(user_id=user_id)
    if date_from:  logs = logs.filter(timestamp__date__gte=parse_date(date_from))
    if date_to:    logs = logs.filter(timestamp__date__lte=parse_date(date_to))
    if q:
        logs = logs.filter(
            Q(change_message__icontains=q) |
            Q(object_id__icontains=q) |
            Q(model_name__icontains=q)
        )

    page_obj = Paginator(logs, 25).get_page(request.GET.get('page'))

    model_names = (AuditLog.objects.order_by()
                   .values_list('model_name', flat=True).distinct())
    actions = (AuditLog.objects.order_by()
               .values_list('action', flat=True).distinct())
    users = get_user_model().objects.order_by('email')  # or username

    return render(request, 'audit/audit_log_list.html', {
        'page_obj': page_obj,
        'model_names': model_names,
        'actions': actions,
        'users': users,
        'selected': {'model': model_name, 'action': action, 'user': user_id,
                     'from': date_from, 'to': date_to, 'q': q}
    })

@login_required
def audit_log_for_object(request, model_name, object_id):
    logs = (AuditLog.objects.select_related('user')
            .filter(model_name=model_name, object_id=str(object_id))
            .order_by('-timestamp'))
    page_obj = Paginator(logs, 25).get_page(request.GET.get('page'))
    return render(request, 'audit/audit_log_object.html',
                  {'page_obj': page_obj, 'model_name': model_name, 'object_id': object_id})


# accounting_app/views_controls.py
from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import ControlTask, ControlTaskInstance

from datetime import date
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import ControlTask, ControlTaskInstance

from django.contrib.auth import get_user_model

User = get_user_model()

def get_allowed_users(user):
    """Return the list of users visible to the given user."""
    if getattr(user, "is_superadmin", False):
        # Superadmin sees everything
        return User.objects.all()

    elif user.is_superuser:
        # Superuser sees themselves + their accountants
        return [user] + list(user.created_users.all())

    else:
        # Accountant sees themselves + their superuser (created_by)
        superuser = getattr(user, "created_by", None)
        allowed = [user]
        if superuser:
            allowed.append(superuser)
        return allowed
from datetime import date
from django.shortcuts import render
from .models import ControlTask, ControlTaskInstance

def controls_dashboard(request):
    user = request.user
    y, m = date.today().year, date.today().month
    instances = []

    allowed_users = get_allowed_users(user)

    qs = (
        ControlTask.objects
        .filter(active=True, owner__in=allowed_users)
        .select_related("area", "owner")
    )

    for task in qs:
        month = m if task.cadence in ("MONTHLY", "QUARTERLY") else None
        inst, _ = ControlTaskInstance.objects.get_or_create(
            task=task, period_year=y, period_month=month
        )
        instances.append(inst)

    return render(
        request,
        "controls/dashboard.html",
        {"instances": instances, "year": y, "month": m},
    )

@login_required
@user_passes_test(is_accountant_or_superuser)
# @permission_required("accounting_app.complete_controltaskinstance", raise_exception=True)
def controls_mark_complete(request, pk):
    inst = get_object_or_404(ControlTaskInstance, pk=pk)
    if request.method == "POST":
        inst.completed = True
        inst.completed_by = request.user
        from django.utils.timezone import now
        inst.completed_on = now()
        inst.save(update_fields=["completed", "completed_by", "completed_on"])
        messages.success(request, "Control task marked complete.")
        return redirect("controls_dashboard")
    return render(request, "controls/confirm_complete.html", {"instance": inst})


from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.contenttypes.models import ContentType
from .models import ApprovalRequest

# def is_reviewer(user): return user.groups.filter(name__in=["Reviewer", "Approver"]).exists()
# def is_approver(user): return user.groups.filter(name="Approver").exists()


@login_required
@user_passes_test(is_accountant_or_superuser)
def approvals_for_object(request, app_label, model_name, object_id):
    ct = get_content_type(app_label, model_name)
    approvals = (
        ApprovalRequest.objects
        .filter(target_ct=ct, target_id=str(object_id))
        .order_by("-created_on")
    )
    return render(
        request,
        "approvals/object_approvals.html",
        {
            "approvals": approvals,
            "app_label": app_label,
            "model": model_name,
            "object_id": object_id,
        },
    )



@login_required
@user_passes_test(is_accountant_or_superuser)
def approval_request_create(request, app_label, model, object_id):
    ct = get_content_type(app_label, model)
    if request.method == "POST":
        title = request.POST.get("title") or f"Approval for {model} #{object_id}"
        ApprovalRequest.objects.create(
            target_ct=ct, target_id=str(object_id), title=title, requested_by=request.user
        )
        return redirect("approvals_for_object", app_label=app_label, model=model, object_id=object_id)

    # 👇 add app_label here so the template can reverse URLs
    return render(
        request,
        "approvals/create.html",
        {"app_label": app_label, "model": model, "object_id": object_id},
    )


@login_required
@user_passes_test(is_accountant_or_superuser)
def approval_review(request, pk):
    appr = get_object_or_404(ApprovalRequest, pk=pk)
    if request.method == "POST":
        appr.status = "REVIEWED"
        appr.assigned_to = request.user
        appr.comment = request.POST.get("comment", "")
        appr.save()
        return redirect("approvals_for_object", app_label=appr.target_ct.app_label, model=appr.target_ct.model, object_id=appr.target_id)
    return render(request, "approvals/review.html", {"approval": appr})


@login_required
@user_passes_test(is_accountant_or_superuser)
def approval_approve(request, pk):
    appr = get_object_or_404(ApprovalRequest, pk=pk)
    if request.method == "POST":
        appr.status = "APPROVED"
        appr.assigned_to = request.user
        appr.comment = request.POST.get("comment", "")
        appr.save()
        return redirect("approvals_for_object", app_label=appr.target_ct.app_label, model=appr.target_ct.model, object_id=appr.target_id)
    return render(request, "approvals/approve.html", {"approval": appr})

@login_required
@user_passes_test(is_accountant_or_superuser)
def approval_reject(request, pk):
    appr = get_object_or_404(ApprovalRequest, pk=pk)
    if request.method == "POST":
        appr.status = "REJECTED"
        appr.assigned_to = request.user
        appr.comment = request.POST.get("comment", "")
        appr.save()
        return redirect("approvals_for_object", app_label=appr.target_ct.app_label, model=appr.target_ct.model, object_id=appr.target_id)
    return render(request, "approvals/reject.html", {"approval": appr})

@login_required
@user_passes_test(is_accountant_or_superuser)
def get_content_type(app_label, model):
    model = model.lower()
    return ContentType.objects.get(app_label=app_label, model=model)

# accounting_app/views_journal_workflow.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.contenttypes.models import ContentType

from accounting_app.models import JournalEntry
from accounting_app.models import ApprovalRequest

# def can_review(user):  # customize as you wish (groups/permissions)
#     return user.is_superuser or user.groups.filter(name__in=["Reviewer", "Approver"]).exists()

# def can_approve(user):
#     return user.is_superuser or user.groups.filter(name="Approver").exists()



@user_passes_test(is_accountant_or_superuser)
def request_je_approval(request, pk):
    je = get_object_or_404(JournalEntry, pk=pk)
    ct = ContentType.objects.get_for_model(JournalEntry)

    # Check if the current user already requested approval for this JE
    existing_request = ApprovalRequest.objects.filter(
        target_ct=ct,
        target_id=str(je.pk),
        requested_by=request.user,
        status__in=["PENDING", "REVIEWED"]  # optional: only active requests
    ).first()

    if request.method == "POST":
        if existing_request:
            messages.warning(request, "You have already requested approval for this Journal Entry.")
        else:
            title = request.POST.get("title") or f"Approval for JournalEntry #{je.pk}"
            ApprovalRequest.objects.create(
                target_ct=ct,
                target_id=str(je.pk),
                title=title,
                requested_by=request.user,
            )
            messages.success(request, "Approval request created.")
        return redirect("journal_entry_detail", pk=je.pk)

    return render(request, "journal/request_approval.html", {"je": je})



@login_required
@user_passes_test(is_accountant_or_superuser)
def review_je(request, approval_pk):
    appr = get_object_or_404(ApprovalRequest, pk=approval_pk)
    if request.method == "POST":
        appr.status = "REVIEWED"
        appr.assigned_to = request.user
        appr.comment = request.POST.get("comment", "")
        appr.save()
        messages.success(request, "Journal entry reviewed.")
        return redirect("journal_entry_detail", pk=appr.target_id)
    return render(request, "journal/review.html", {"approval": appr})


@login_required
@user_passes_test(is_accountant_or_superuser)
def approve_je(request, approval_pk):
    appr = get_object_or_404(ApprovalRequest, pk=approval_pk)
    if request.method == "POST":
        appr.status = "APPROVED"
        appr.assigned_to = request.user
        appr.comment = request.POST.get("comment", "")
        appr.save()
        messages.success(request, "Journal entry approved.")
        return redirect("journal_entry_detail", pk=appr.target_id)
    return render(request, "journal/approve.html", {"approval": appr})

import logging, traceback
logger = logging.getLogger(__name__)


@login_required
@user_passes_test(is_accountant_or_superuser)
def post_je(request, pk):
    je = get_object_or_404(JournalEntry, pk=pk)
    if request.method == "POST":
        try:
            je.mark_posted(user=request.user)
            messages.success(request, "Journal entry posted.")
        except Exception as e:
            logger.error("Post failed for JE %s: %s\n%s", je.pk, e, traceback.format_exc())
            messages.error(request, f"Cannot post: {e}")
        return redirect("journal_entry_detail", pk=je.pk)
    return render(request, "journal/confirm_post.html", {"je": je})




from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render

from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from accounting_app.models import ControlTask, ControlTaskInstance

# --------------------
# Existing dashboard & complete
# --------------------

from datetime import date
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import ControlTask, ControlTaskInstance




@login_required
@user_passes_test(is_accountant_or_superuser)
def controls_mark_complete(request, pk):
    inst = get_object_or_404(ControlTaskInstance, pk=pk)
    if request.method == "POST":
        from django.utils.timezone import now
        inst.completed = True
        inst.completed_by = request.user
        inst.completed_on = now()
        inst.save(update_fields=["completed", "completed_by", "completed_on"])
        messages.success(request, "Control task marked complete.")
        return redirect("controls_dashboard")
    return render(request, "controls/confirm_complete.html", {"instance": inst})

# --------------------
# Helper: ensure instance for current period
# --------------------

@login_required
@user_passes_test(is_accountant_or_superuser)
def ensure_current_instance(task: ControlTask) -> None:
    """Create current period instance for a task if cadence is month/quarter and active."""
    if not task.active:
        return
    y, m = date.today().year, date.today().month
    period_month = m if task.cadence in ("MONTHLY", "QUARTERLY") else None
    ControlTaskInstance.objects.get_or_create(task=task, period_year=y, period_month=period_month)




from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import FixedAsset
from .forms import FixedAssetForm



@login_required
@user_passes_test(is_accountant_or_superuser)
def asset_list(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    assets = FixedAsset.objects.filter(owner__in=allowed_users).order_by("-id")
    return render(request, "assets/asset_list.html", {"assets": assets})


@login_required
@user_passes_test(is_accountant_or_superuser)
def asset_create(request):
    user = request.user
    owner = user if user.is_superuser else getattr(user, "created_by", user)

    if request.method == "POST":
        form = FixedAssetForm(request.POST, user=user)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.created_by = user
            asset.owner = owner
            asset.save()
            messages.success(request, "Asset registered successfully.")
            return redirect("asset_list")
    else:
        form = FixedAssetForm(user=user)

    return render(request, "assets/asset_form.html", {"form": form})


@login_required
@user_passes_test(is_accountant_or_superuser)
def asset_detail(request, pk):
    user = request.user
    allowed_users = get_allowed_users(user)

    asset = get_object_or_404(FixedAsset, pk=pk, owner__in=allowed_users)
    return render(request, "assets/asset_detail.html", {"asset": asset})


# utils/depreciation.py (you can also include this in views or services)

from .models import FixedAsset, DepreciationEntry
from django.utils.timezone import now

@login_required
@user_passes_test(is_accountant_or_superuser)
def post_depreciation_for_asset(asset):
    amount = asset.calculate_depreciation()

    if amount > 0:
        DepreciationEntry.objects.create(
            asset=asset,
            amount=amount,
            date=now().date().replace(day=1)
        )
        asset.accumulated_depreciation += amount
        asset.last_depreciation_date = now().date().replace(day=1)
        asset.save()

# fixedassets/views.py

from django.shortcuts import render, get_object_or_404
from .models import FixedAsset
from datetime import date

# def asset_depreciation_detail(request, pk):
#     asset = get_object_or_404(FixedAsset, pk=pk)

#     monthly_depreciation = 0
#     total_months = asset.useful_life * 12
#     if asset.purchase_price and asset.useful_life:
#         monthly_depreciation = asset.purchase_price / total_months

#     # Calculate depreciation history (simple display, not persisted unless you have a table)
#     start_date = asset.purchase_date
#     depreciation_schedule = []

#     for month in range(total_months):
#         dep_date = (start_date.replace(day=1) + timedelta(days=month * 30)).replace(day=1)
#         if dep_date > date.today():
#             break

#         depreciation_value = round(monthly_depreciation, 2)
#         accumulated = round(min((month + 1) * monthly_depreciation, asset.purchase_price), 2)
#         nbv = round(max(asset.purchase_price - accumulated, 0), 2)

#         depreciation_schedule.append({
#             "month": dep_date.strftime("%b %Y"),
#             "value": depreciation_value,
#             "accumulated": accumulated,
#             "net_book_value": nbv
#         })

#     context = {
#         "asset": asset,
#         "schedule": depreciation_schedule,
#     }

#     return render(request, "assets/asset_depreciation_detail.html", context)
from .models import FixedAsset, DepreciationEntry
from datetime import date
from dateutil.relativedelta import relativedelta  # install python-dateutil if not present

@login_required
@user_passes_test(is_accountant_or_superuser)
def asset_depreciation_detail(request, pk):
    asset = get_object_or_404(FixedAsset, pk=pk)

    if asset.disposed:
        entries = asset.depreciation_entries.all()
    else:
        start_date = asset.last_depreciation_date or asset.purchase_date
        today = date.today()
        current = start_date.replace(day=1)

        total_months = asset.useful_life * 12
        monthly_amount = round(asset.purchase_price / total_months, 2)
        accumulated = asset.accumulated_depreciation

        while current <= today.replace(day=1):
            if not DepreciationEntry.objects.filter(asset=asset, date=current).exists():
                accumulated += monthly_amount
                DepreciationEntry.objects.create(
                    asset=asset,
                    date=current,
                    amount=monthly_amount,
                    accumulated=accumulated
                )
                asset.accumulated_depreciation = accumulated
                asset.last_depreciation_date = current
                asset.save()
            current += relativedelta(months=1)

        entries = asset.depreciation_entries.all()

    # ➕ Add net book value to each entry
    entry_data = []
    for e in entries:
        net_value = max(asset.purchase_price - e.accumulated, 0)
        entry_data.append({
            "date": e.date,
            "amount": e.amount,
            "accumulated": e.accumulated,
            "net_book_value": round(net_value, 2)
        })

    return render(request, "assets/asset_depreciation_detail.html", {
        "asset": asset,
        "entries": entry_data
    })
    
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Employee

@login_required
@user_passes_test(is_accountant_or_superuser)
def delete_contractor(request, pk):
    contractor = get_object_or_404(Employee, pk=pk, is_contractor=True)
    if request.method == "POST":
        contractor.delete()
        messages.success(request, "Contractor deleted successfully.")
    return redirect("contractor_list")  # Change to your actual list view name


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from .models import EmployeeExpense
from .forms import EmployeeExpenseForm
from accounting_app.models import Employee
# make sure you have this helper

# ✅ Submit expense (for employees only)
@login_required
@user_passes_test(lambda u: getattr(u, 'role', '') == 'Employee')
def submit_expense(request):
    if request.method == 'POST':
        form = EmployeeExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)

            # Ensure Employee profile exists and assign
            allowed_users = get_allowed_users(request.user)
            employee, created = Employee.objects.get_or_create(
                user__in=allowed_users,
                defaults={
                    'user': request.user,
                    'name': request.user.email.split('@')[0].title(),
                    'email': request.user.email,
                }
            )
            expense.employee = employee
            expense.save()
            return redirect('my_expenses')
    else:
        form = EmployeeExpenseForm()
    return render(request, 'expenses/submit_expense.html', {'form': form})


# ✅ My expenses (for logged-in employee)
@login_required
def my_expenses(request):
    allowed_users = get_allowed_users(request.user)
    expenses = EmployeeExpense.objects.filter(employee__user__in=allowed_users).select_related(
        'employee', 'employee__user'
    ).order_by('-submitted_at')
    return render(request, 'expenses/my_expenses.html', {'expenses': expenses})


# ✅ Expense list (accountants / superusers see all; employees see their allowed)
@login_required
@user_passes_test(lambda u: getattr(u, 'role', '') in ['Accountant', 'Superuser', 'SuperAdmin'])
def expense_list(request):
    allowed_users = get_allowed_users(request.user)
    expenses = EmployeeExpense.objects.filter(employee__user__in=allowed_users).select_related(
        'employee', 'employee__user'
    ).order_by('-submitted_at')
    return render(request, "expenses/expense_list.html", {"expenses": expenses})


# ✅ Review expenses (pending only, accountants / superusers)
@login_required
@user_passes_test(lambda u: getattr(u, 'role', '') in ['Accountant', 'Superuser', 'SuperAdmin'])
def review_expenses(request):
    allowed_users = get_allowed_users(request.user)
    expenses = EmployeeExpense.objects.filter(
        status='PENDING',
        employee__user__in=allowed_users
    ).select_related('employee', 'employee__user').order_by('submitted_at')
    return render(request, 'expenses/review_expenses.html', {'expenses': expenses})


@login_required
@user_passes_test(is_accountant_or_superuser)
def approve_expense(request, pk):
    expense = get_object_or_404(EmployeeExpense, pk=pk)
    expense.status = 'APPROVED'
    expense.reviewed_by = request.user
    expense.reviewed_at = timezone.now()
    expense.save()
    return redirect('review_expenses')


@login_required
@user_passes_test(is_accountant_or_superuser)
def reject_expense(request, pk):
    expense = get_object_or_404(EmployeeExpense, pk=pk)
    expense.status = 'REJECTED'
    expense.reviewed_by = request.user
    expense.reviewed_at = timezone.now()
    expense.save()
    return redirect('review_expenses')



# @login_required
# def expense_list(request):
#     if request.user.is_staff:
#         expenses = EmployeeExpense.objects.all().order_by('-submitted_at')
#     else:
#         expenses = EmployeeExpense.objects.filter(employee=request.user).order_by('-submitted_at')
#     return render(request, "expenses/expense_list.html", {"expenses": expenses})


# payroll/views.py

from .models import Payroll

@login_required
@user_passes_test(is_accountant_or_superuser)
def finalize_payroll(request, payroll_id):
    payroll = Payroll.objects.get(id=payroll_id)
    payroll.calculate()
    payroll.save()
    payroll.mark_expenses_as_paid()
    messages.success(request, "Payroll finalized and expenses reimbursed.")
    return redirect('payroll_list')

# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import ClientContract, Retainer, BillingMilestone, Phase,Deal, Commission
from .forms import ClientContractForm, RetainerForm, MilestoneForm,PhaseForm,DealForm,CommissionForm
from accounting_app.models import Invoice
from django.utils.timezone import now

from django.contrib.auth.decorators import login_required, user_passes_test
from .models import ClientContract
 # adjust import if in another app
from django.shortcuts import render
@login_required
@user_passes_test(is_accountant_or_superuser)
def contract_list(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    contracts = (
        ClientContract.objects.filter(owner__in=allowed_users)  # ✅ only owned contracts
        .order_by("-start_date", "-id")
    )

    return render(
        request,
        "contracts/list.html",
        {"contracts": contracts}
    )

@login_required
@user_passes_test(is_accountant_or_superuser)
def contract_create(request):
    if request.method == "POST":
        form = ClientContractForm(request.POST, request=request)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.owner = request.user  # ✅ ensure owner set
            contract.created_by = request.user
            contract.save()
            return redirect('contract_list')
    else:
        form = ClientContractForm(request=request)

    return render(request, 'contracts/form.html', {'form': form})



from .forms import DealForm

def contract_detail(request, contract_id):
    contract = get_object_or_404(ClientContract, id=contract_id)
    deals = Deal.objects.filter(contract=contract).select_related('client', 'owner')
    phases = Phase.objects.filter(contract=contract)
    milestones = BillingMilestone.objects.filter(contract=contract)
    retainers = Retainer.objects.filter(contract=contract)

    # Pass empty DealForm for the modal
    form = DealForm(request=request)

    return render(request, 'contracts/contract_detail.html', {
        'deals': deals,
        'contract': contract,
        'phases': phases,
        'milestones': milestones,
        'retainers': retainers,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'form': form,  # <-- for modal
    })





@login_required
@user_passes_test(is_accountant_or_superuser)
def retainer_create(request, contract_id):
    contract = get_object_or_404(ClientContract, id=contract_id)
    form = RetainerForm(request.POST or None)
    if form.is_valid():
        retainer = form.save(commit=False)
        retainer.contract = contract
        retainer.save()
        return redirect('contract_list')
    return render(request, 'contracts/form.html', {'form': form})

@login_required
@user_passes_test(is_accountant_or_superuser)
def milestone_create(request, contract_id):
    contract = get_object_or_404(ClientContract, id=contract_id)
    form = MilestoneForm(request.POST or None)
    if form.is_valid():
        milestone = form.save(commit=False)
        milestone.contract = contract
        milestone.save()
        return redirect('contract_list')
    return render(request, 'contracts/form.html', {
        'form': form,
        'form_title': f"Add Milestone to {contract.name}",
        'return_url': 'contract_detail',
        'contract': contract
    })
from django.utils.timezone import now

@login_required
@user_passes_test(is_accountant_or_superuser)
def mark_milestone_billed(request, milestone_id):
    milestone = get_object_or_404(BillingMilestone, id=milestone_id)
    milestone.is_billed = True
    milestone.billed_date = now().date()
    milestone.save()
    return redirect('contract_detail', contract_id=milestone.contract.id)



@login_required
@user_passes_test(is_accountant_or_superuser)
def generate_invoice_for_milestone(request, milestone_id):
    milestone = get_object_or_404(BillingMilestone, id=milestone_id)
    if not milestone.is_billed:
        invoice = Invoice.objects.create(
            client=milestone.contract.client,
            date=now().date(),
            due_date=now().date(),
            total_amount=milestone.amount,
            project=None
        )
        milestone.is_billed = True
        milestone.save()
        messages.success(request, f"Invoice #{invoice.pk} generated for milestone '{milestone.name}'")
    return redirect('contract_list')

@login_required
@user_passes_test(is_accountant_or_superuser)
def revenue_dashboard(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    # ✅ Only include contracts owned by allowed users
    phases = (
        Phase.objects
        .select_related("contract")
        .filter(contract__owner__in=allowed_users)
        .order_by("-id")
    )

    total_revenue = sum(phase.revenue for phase in phases)

    return render(
        request,
        "dashboard/revenue.html",
        {
            "phases": phases,
            "total_revenue": total_revenue,
        }
    )



@login_required
@user_passes_test(is_accountant_or_superuser)
def phase_create(request, contract_id):
    contract = get_object_or_404(ClientContract, id=contract_id)
    form = PhaseForm(request.POST or None)
    if form.is_valid():
        phase = form.save(commit=False)
        phase.contract = contract
        phase.save()
        return redirect('contract_list')
    return render(request, 'contracts/form.html', {
        'form': form,
        'form_title': f"Add Phase to {contract.name}",
        'return_url': 'contract_list'
    })

from .models import Client, ClientContract, Deal, Invoice, Commission
from integrations.models import CRMClient
from django.utils import timezone
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from .forms import DealForm

from decimal import Decimal  # Make sure it's imported

# views.py
# views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import ClientContract, Deal
from .forms import DealForm

from django.http import JsonResponse

@login_required
@user_passes_test(is_accountant_or_superuser)
def deal_create(request, contract_id=None):
    contract = None
    if contract_id:
        contract = get_object_or_404(ClientContract, id=contract_id)

    if request.method == "POST":
        form = DealForm(request.POST, request=request)
        if form.is_valid():
            deal = form.save(commit=False)
            deal.owner = request.user.owner if request.user.role == "Accountant" else request.user
            deal.created_by = request.user

            if contract:
                deal.contract = contract
                deal.client = contract.client

            if not deal.client:
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": "Client must be selected."})
                messages.error(request, "Client must be selected.")
                return render(request, 'deals/form.html', {'form': form, 'contract': contract})

            deal.save()

            # Auto-create related models
            Invoice.objects.get_or_create(
                deal=deal,
                defaults={
                    'client': deal.client,
                    'total_amount': deal.amount or 0,
                    'date': timezone.now().date(),
                    'due_date': timezone.now().date(),
                }
            )
            Commission.objects.get_or_create(
                deal=deal,
                defaults={
                    'percentage': Decimal('10.0'),
                    'amount': (deal.amount or 0) * Decimal('0.10'),
                    'paid': False
                }
            )
            Quote.objects.get_or_create(
                deal=deal,
                defaults={
                    'title': f'Quote for {deal.title}',
                    'amount': deal.amount or 0,
                    'status': 'Draft',
                    'paid': False,
                }
            )

            # If AJAX, return deal info as JSON
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "success": True,
                    "deal": {
                        "id": deal.id,
                        "title": deal.title,
                        "amount": str(deal.amount or "0.00"),
                        "expected_close": deal.expected_close.strftime("%Y-%m-%d") if deal.expected_close else "",
                    }
                })

            # Otherwise normal redirect
            if contract:
                return redirect('contract_detail', contract_id=contract.id)
            return redirect('deals_list')

    else:
        form = DealForm(request=request)

    # If GET or invalid form, return HTML
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": False, "error": "Invalid data."})
    return render(request, 'deals/form.html', {'form': form, 'contract': contract})

    
    
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import Deal, ClientContract


@login_required
@user_passes_test(is_accountant_or_superuser)
def deals_list(request, contract_id=None):
    """
    List all deals. Optionally filter by contract.
    """
    contract = None
    deals = Deal.objects.all().select_related('contract', 'owner')

    if contract_id:
        contract = ClientContract.objects.filter(id=contract_id).first()
        if contract:
            deals = deals.filter(contract=contract)

    context = {
        'deals': deals,
        'contract': contract,
    }
    return render(request, 'deals/list.html', context)


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from .models import Deal, Invoice



from decimal import Decimal
from django.utils import timezone
from django.contrib import messages


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone

from .models import Deal, Invoice
from django.conf import settings

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone

from django.conf import settings

MAX_RZP_AMOUNT = 100000000  # ₹10L in paise

@login_required
@user_passes_test(is_accountant_or_superuser)
def invoice_create_for_deal(request, deal_id):
    deal = get_object_or_404(Deal, id=deal_id)

    if not deal.contract or not deal.contract.client:
        messages.error(request, "❌ Cannot create invoice: Deal is missing contract or client.")
        return redirect('deal_detail', deal_id=deal.id)

    client_obj = deal.contract.client
    today = timezone.now().date()
    due_date = today

    invoice, created = Invoice.objects.get_or_create(
        deal=deal,
        defaults={
            'client': client_obj,
            'date': today,
            'due_date': due_date,
            'total_amount': deal.amount,
            'project': None
        }
    )

    if created:
        rzp_amount = int(invoice.total_amount * 100)

        if rzp_amount > MAX_RZP_AMOUNT:
            messages.error(request, "❌ Amount exceeds Razorpay's ₹10,00,000 limit. Please contact admin.")
            invoice.delete()
            return redirect('deal_detail', deal_id=deal.id)

        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            order_data = {
                "amount": rzp_amount,
                "currency": "INR",
                "payment_capture": "1",
                "notes": {
                    "deal_id": str(deal.id),
                    "client": str(getattr(client_obj, "name", client_obj.id)),
                    "due_date": due_date.isoformat(),
                    "date": today.isoformat(),
                }
            }

            order = client.order.create(data=order_data)

            # Safety check
            if 'id' not in order:
                raise ValueError("Invalid Razorpay order response: Missing order ID")

            invoice.razorpay_order_id = order['id']
            invoice.save()
            messages.success(request, "✅ Invoice created and Razorpay order generated.")

        except Exception as e:
            invoice.delete()
            messages.error(request, f"❌ Razorpay error: {e}")
            return redirect('deal_detail', deal_id=deal.id)

    else:
        if not invoice.pk:
            messages.error(request, "❌ Invoice exists but is not valid. Please contact admin.")
            return redirect('deal_detail', deal_id=deal.id)

        messages.info(request, "ℹ️ Invoice already exists for this deal.")

    # ✅ Final redirect — only if invoice.pk is valid
    if invoice.pk:
        return redirect('invoice_details', pk=invoice.pk)
    else:
        messages.error(request, "❌ Invoice creation failed. Please try again.")
        return redirect('deal_detail', deal_id=deal.id)

@login_required
@user_passes_test(is_accountant_or_superuser)
def invoice_details(request, pk):
    user = request.user

    if user.is_superuser:
        invoice = get_object_or_404(Invoice, pk=pk, owner=user)
    else:
        allowed_users = get_allowed_users(user)  # all users tied to their superuser
        invoice = get_object_or_404(Invoice, pk=pk, owner__in=allowed_users)

    return render(request, "invoice/detail.html", {
        "invoice": invoice,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
    })




@login_required
@user_passes_test(is_accountant_or_superuser)
def commission_create_for_deal(request, deal_id):
    deal = get_object_or_404(Deal, id=deal_id)
    commission_pct = Decimal('10.00')
    amount = deal.amount * (commission_pct / Decimal('100.00'))

    commission, created = Commission.objects.get_or_create(
        deal=deal,
        defaults={
            'percentage': commission_pct,
            'amount': amount,
        }
    )

    if created:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        order_data = {
            "amount": int(amount * 100),
            "currency": "INR",
            "payment_capture": "1"
        }
        order = client.order.create(data=order_data)
        commission.razorpay_order_id = order['id']
        commission.save()
        messages.success(request, f"✅ Commission created and Razorpay order generated.")
    else:
        messages.info(request, "ℹ️ Commission already exists for this deal.")

    return redirect('deal_detail', deal_id=deal.id)



# def mark_invoice_paid(request, invoice_id):
#     invoice = get_object_or_404(Invoice, id=invoice_id)
#     invoice.is_paid = True
#     invoice.save()
#     messages.success(request, "✅ Invoice marked as paid.")
#     return redirect('contract_detail', contract_id=invoice.deal.contract.id)

@login_required
@user_passes_test(is_accountant)
def pay_commission(request, commission_id):
    commission = get_object_or_404(Commission, id=commission_id)
    commission.paid = True
    commission.save()
    messages.success(request, f"✅ Commission #{commission.id} marked as paid.")
    return redirect('contract_detail', contract_id=commission.deal.contract.id)


@login_required
@user_passes_test(is_accountant_or_superuser)
def deal_detail(request, deal_id):
    deal = get_object_or_404(Deal, id=deal_id)
    invoice = Invoice.objects.filter(deal=deal).first()
    commission = Commission.objects.filter(deal=deal).first()
    quote = Quote.objects.filter(deal=deal).first()  # ✅ FIXED

    return render(request, 'deals/detail.html', {
        'deal': deal,
        'invoice': invoice,
        'commission': commission,
        'quote': quote,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    })


from django.shortcuts import render, redirect, get_object_or_404
from .models import Quote, Deal
from .forms import QuoteForm
from django.contrib import messages

@login_required
@user_passes_test(is_accountant_or_superuser)
def quote_list(request):
    user = request.user

    # --- Determine allowed users ---
    if user.is_superuser:
        allowed_users = [user] + list(user.created_users.all())
    else:
        superuser_creator = getattr(user, "created_by", None)
        allowed_users = [user]
        if superuser_creator:
            allowed_users.append(superuser_creator)

    # --- Filter quotes ---
    quotes = (
        Quote.objects
        .select_related('deal', 'client')
        .filter(deal__owner__in=allowed_users)   # 🔒 restrict by ownership
        .order_by('-id')
    )

    return render(request, 'quotes/quote_list.html', {'quotes': quotes})

@login_required
@user_passes_test(is_accountant_or_superuser)
def quote_create(request, deal_id):
    user = request.user

    # 🔒 Restrict deal lookup
    if user.is_superuser:
        deal = get_object_or_404(Deal, id=deal_id, owner=user)
    else:
        allowed_users = get_allowed_users(user)
        deal = get_object_or_404(Deal, id=deal_id, owner__in=allowed_users)

    quote = None

    if request.method == 'POST':
        form = QuoteForm(request.POST, request.FILES)
        if form.is_valid():
            quote = form.save(commit=False)
            quote.deal = deal

            # ✅ If Deal has client, link it
            if hasattr(deal, "client"):
                quote.client = deal.client

            # ✅ Track ownership
            quote.owner = deal.owner   # superuser who owns the deal
            quote.created_by = user    # whoever actually created the quote (superuser or accountant)

            quote.save()

            # 🔑 Create Razorpay order (only if < ₹10L)
            if quote.amount <= 1000000:
                try:
                    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                    order = client.order.create({
                        "amount": int(quote.amount * 100),
                        "currency": "INR",
                        "payment_capture": "1"
                    })
                    quote.razorpay_order_id = order['id']
                    quote.save()
                except Exception as e:
                    messages.error(request, f"❌ Razorpay order failed: {e}")

            messages.success(request, "✅ Quote created.")
            return redirect('quote_list')
        else:
            messages.error(request, "❌ Invalid form data.")
    else:
        form = QuoteForm(initial={'amount': deal.amount})

    return render(request, 'quotes/quote_form.html', {
        'form': form,
        'deal': deal,
        'quote': quote,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    })


@login_required
@user_passes_test(is_accountant_or_superuser)
def quote_detail(request, quote_id):
    user = request.user

    if user.is_superuser:
        # 🔒 Superuser only sees their own quotes
        quote = get_object_or_404(Quote, id=quote_id, deal__owner=user)
    else:
        # 🔒 Accountant only sees quotes belonging to their allowed superuser
        allowed_users = get_allowed_users(user)
        quote = get_object_or_404(Quote, id=quote_id, deal__owner__in=allowed_users)

    return render(request, 'quotes/quote_detail.html', {
        'quote': quote,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    })


@login_required
@user_passes_test(is_accountant_or_superuser)
def quote_approve(request, quote_id):
    quote = get_object_or_404(Quote, id=quote_id)
    quote.approved = True
    quote.status = 'approved'
    quote.save()
    messages.success(request, "✅ Quote approved.")
    return redirect('quote_detail', quote.id)

from django.shortcuts import render, get_object_or_404, redirect
from .models import Invoice, Payment
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
# import razorpay
from django.http import HttpResponseBadRequest
from django.utils.timezone import now

from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

@login_required
@user_passes_test(is_accountant_or_superuser)
def mark_invoice_paid(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)

    if request.method == "POST":
        Payment.objects.create(
            invoice=invoice,
            amount=invoice.total_amount,
            method='manual',
            confirmed=True
        )
        invoice.is_paid = True
        invoice.save()
        messages.success(request, "✅ Invoice marked as paid manually.")
        return redirect('invoice_details', pk=invoice.id)


    return render(request, 'invoice/mark_manual.html', {'invoice': invoice})


from django.http import HttpResponseBadRequest

@csrf_exempt
def razorpay_invoice_payment_callback(request):
    if request.method == "POST":
        invoice_id = request.POST.get("invoice_id")
        razorpay_payment_id = request.POST.get("razorpay_payment_id")

        invoice = get_object_or_404(Invoice, id=invoice_id)

        Payment.objects.create(
            invoice=invoice,
            amount=invoice.total_amount,
            method='razorpay',
            razorpay_payment_id=razorpay_payment_id,
            confirmed=True
        )
        invoice.is_paid = True
        invoice.save()

        return redirect('deal_detail', deal_id=invoice.deal.id)

    return HttpResponseBadRequest("Invalid request")



@csrf_exempt
def razorpay_commission_payment_callback(request):
    if request.method == "POST":
        commission_id = request.POST.get("commission_id")
        razorpay_payment_id = request.POST.get("razorpay_payment_id")

        commission = get_object_or_404(Commission, id=commission_id)
        commission.paid = True
        commission.save()
        # You can create a `CommissionPayment` model if needed
        return redirect('deal_detail', deal_id=commission.deal.id)
    return HttpResponseBadRequest("Invalid request")
@csrf_exempt
def razorpay_quote_payment_callback(request):
    if request.method == "POST":
        quote_id = request.POST.get("quote_id")
        razorpay_payment_id = request.POST.get("razorpay_payment_id")

        quote = get_object_or_404(Quote, id=quote_id)
        quote.paid = True
        quote.save()
        # Create payment record if needed
        return redirect('deal_detail', deal_id=quote.deal.id)
    return HttpResponseBadRequest("Invalid request")


from django.http import JsonResponse
from .models import Invoice
from .serializers import InvoiceSerializer

@login_required
@user_passes_test(is_accountant_or_superuser)
def invoice_json_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    serializer = InvoiceSerializer(invoice)
    return JsonResponse(serializer.data, safe=False)


from rest_framework.views import APIView
from rest_framework.response import Response

class InvoiceDetailAPIView(APIView):
    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        serializer = InvoiceSerializer(invoice)
        return Response(serializer.data)


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Quote  # or your actual model name

@login_required
@user_passes_test(is_accountant)
def mark_quote_paid(request, quote_id):
    quote = get_object_or_404(Quote, id=quote_id)
    quote.paid = True
    quote.save()
    messages.success(request, f"✅ Quote #{quote.id} marked as paid.")
    return redirect('contract_detail', contract_id=quote.deal.contract.id)  # or redirect wherever makes sense

# reports/views.py
from django.shortcuts import render
from django.db.models import Sum, Avg, Count, F, Q
from django.http import JsonResponse, HttpResponse
from datetime import date, timedelta
from .models import *  # Import all required models
import csv

# -----------------------------
# 📊 1. Real-time KPI Dashboard
# -----------------------------

@login_required
@user_passes_test(is_accountant_or_superuser)
def kpi_dashboard(request):
    user = request.user

    # 🔑 Allowed users (superuser + accountants of that superuser)
    if user.is_superuser:
        allowed_users = [user] + list(user.created_users.all())
    else:
        superuser_creator = getattr(user, "created_by", None)
        allowed_users = [user]
        if superuser_creator:
            allowed_users.append(superuser_creator)

    today = date.today()

    # --- Invoices restricted ---
    total_invoices = Invoice.objects.filter(created_by__in=allowed_users).count()
    paid_invoices = Invoice.objects.filter(created_by__in=allowed_users, is_paid=True).count()

    # --- Revenue restricted ---
    total_revenue = (
        Payment.objects.filter(confirmed=True, created_by__in=allowed_users)
        .aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    # --- Expenses restricted ---
    expense_summary = (
        EmployeeExpense.objects.filter(status="APPROVED", created_by__in=allowed_users)
        .aggregate(total=Sum("amount"), average=Avg("amount"))
    )

    # --- Assets restricted ---
    upcoming_maintenance = (
        FixedAsset.objects.filter(
            next_maintenance_date__lte=today + timedelta(days=30),
            created_by__in=allowed_users
        ).count()
    )

    context = {
        "total_invoices": total_invoices,
        "paid_invoices": paid_invoices,
        "total_revenue": total_revenue,
        "total_expense": expense_summary["total"] or 0,
        "avg_expense": expense_summary["average"] or 0,
        "maintenance_due": upcoming_maintenance,
    }
    return render(request, "reports/kpi_dashboard.html", context)

# @login_required
# @user_passes_test(is_accountant_or_superuser)
# def invoice_report(request):
#     invoices = Invoice.objects.select_related('client', 'deal').all()
#     if client_id := request.GET.get('client'):
#         invoices = invoices.filter(client_id=client_id)

#     return render(request, 'reports/invoice_report.html', {'invoices': invoices})

from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.db.models import (
    F, Sum, OuterRef, Subquery, DecimalField, Value, ExpressionWrapper
)
from django.db.models.functions import Coalesce

# adjust imports to your app structure
from .models import Invoice
from .models import Payroll, TDSRecord, ContractorPayment, ContractorFilingRecord
 # or wherever your checker lives

from decimal import Decimal
from django.db.models import F, Sum, Value, OuterRef, Subquery, DecimalField
from django.db.models.functions import Coalesce
from django.db.models.expressions import ExpressionWrapper
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

@login_required
@user_passes_test(lambda u: u.is_accountant or u.is_superuser)
def invoice_report(request):
    """
    Combined report:
      1) Customer Invoices (restricted by deal__owner)
      2) Salary 'invoices' from Payroll (restricted by created_by)
      3) Contractor 'invoices' from ContractorPayment (restricted by created_by) 
    """
    user = request.user

    # --- Determine allowed users ---
    if user.is_superuser:
        allowed_users = [user] + list(user.created_users.all())
    else:
        superuser_creator = getattr(user, "created_by", None)
        allowed_users = [user]
        if superuser_creator:
            allowed_users.append(superuser_creator)

    # 1) Customer invoices (belongs to a deal → filter by deal__owner)
    invoices = (
        Invoice.objects
        .select_related('client', 'deal')
        .filter(deal__owner__in=allowed_users)
        .order_by('-date')
    )
    client_id = request.GET.get('client')
    if client_id:
        invoices = invoices.filter(client_id=client_id)

    # optional payroll/contractor period filter
    period = request.GET.get('period')

    # 2) Salary "invoices" from Payroll (correct calculation with FILED TDS)
    payroll_qs = Payroll.objects.select_related('name').filter(created_by__in=allowed_users)
    if period:
        payroll_qs = payroll_qs.filter(month=period)

    salary_rows = list(payroll_qs)  # force evaluation so we can loop and enrich
    for p in salary_rows:
        # FILED TDS only for Payroll
        filed = (
            TDSRecord.objects
            .filter(source="Payroll", reference_id=str(p.id))
            .aggregate(total=Sum('tds_amount'))['total']
            or Decimal('0.00')
        )
        p.tds_dynamic = filed

        # include overtime in earnings
        ot_pay = (p.overtime_hours or 0) * (p.overtime_rate or 0)
        total_earnings = (p.basic_salary or 0) + (p.hra or 0) + (p.other_allowances or 0) + ot_pay
        total_deductions = (p.pf or 0) + (p.esi or 0) + p.tds_dynamic
        net_salary = total_earnings - total_deductions

        # attach values for template
        p.total_earnings_dynamic = total_earnings
        p.total_deductions_dynamic = total_deductions
        p.net_salary_dynamic = net_salary

    # 3) Contractor "invoices"
    filed_sum_for_payment = (
        ContractorFilingRecord.objects
        .filter(contractor_payment_id=OuterRef('pk'))
        .values('contractor_payment_id')
        .annotate(total=Coalesce(Sum('amount_filed'), Value(Decimal('0.00'))))
        .values('total')[:1]
    )

    default_rate = Decimal('0.10')  # 10% TDS default

    contractor_rows = (
        ContractorPayment.objects
        .select_related('name')
        .filter(created_by__in=allowed_users)
        .annotate(
            tds_rate=Value(default_rate, output_field=DecimalField(max_digits=5, decimal_places=2)),
            amount_val=Coalesce(F('amount'), Value(Decimal('0.00'))),
        )
        .annotate(
            tds_dynamic=ExpressionWrapper(
                F('amount_val') * F('tds_rate'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            filed_total=Coalesce(Subquery(filed_sum_for_payment), Value(Decimal('0.00'))),
        )
        .annotate(
            total_deductions_dynamic=ExpressionWrapper(
                F('tds_dynamic') + F('filed_total'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            net_paid_dynamic=ExpressionWrapper(
                F('amount_val') - F('total_deductions_dynamic'),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
        )
        .order_by('-date', '-id')
    )

    return render(request, 'reports/invoice_report.html', {
        'invoices': invoices,
        'salary_rows': salary_rows,
        'contractor_rows': contractor_rows,
        'selected_client': client_id or '',
        'selected_period': period or '',
    })

@login_required
@user_passes_test(is_accountant_or_superuser)
def export_invoices_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="invoices.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Client', 'Deal', 'Amount', 'Status', 'Date'])

    invoices = Invoice.objects.select_related('client', 'deal').all()
    for invoice in invoices:
        writer.writerow([
            invoice.id,
            invoice.client.name if invoice.client else '',
            invoice.deal.title if invoice.deal else '',
            invoice.total_amount,
            'Paid' if invoice.is_paid else 'Unpaid',
            invoice.date
        ])

    return response


from django.utils.timezone import now
from accounting_app.models import Invoice, Payment, EmployeeExpense

@login_required
@user_passes_test(is_accountant_or_superuser)
def send_monthly_summary(request):
    user = request.user
    today = now().date()
    year, month = today.year, today.month

    # --- Determine allowed users ---
    if user.is_superuser:
        allowed_users = [user] + list(user.created_users.all())
    else:
        superuser_creator = getattr(user, "created_by", None)
        allowed_users = [user]
        if superuser_creator:
            allowed_users.append(superuser_creator)

    # --- Invoice count ---
    invoice_count = Invoice.objects.filter(
        date__year=year,
        date__month=month
    ).filter(
        Q(created_by__in=allowed_users) | Q(created_by__isnull=True)
    ).count()

    # --- Payment count ---
    payment_count = Payment.objects.filter(
        date__year=year,
        date__month=month
    ).filter(
        Q(created_by__in=allowed_users) | Q(created_by__isnull=True)
    ).count()

    # --- Employee Expense count ---
    expense_count = EmployeeExpense.objects.filter(
        date__year=year,
        date__month=month
    ).filter(
        Q(created_by__in=allowed_users) | Q(created_by__isnull=True)
    ).count()

    return render(request, 'reports/monthly_summary.html', {
        'invoice_count': invoice_count,
        'payment_count': payment_count,
        'expense_count': expense_count,
        'selected_month': today.strftime("%B %Y"),
    })
    
    
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from accounting_app.models import Invoice, Payment, EmployeeExpense
from django.utils.timezone import now
from django.core.mail import EmailMessage
from io import BytesIO
from django.contrib.admin.views.decorators import staff_member_required

@login_required
@user_passes_test(is_accountant_or_superuser)

def monthly_summary_pdf(request):
    today = now().date()
    month = today.strftime('%B')
    year = today.year

    invoice_count = Invoice.objects.filter(date__year=year, date__month=today.month).count()
    payment_count = Payment.objects.filter(date__year=year, date__month=today.month).count()
    expense_count = EmployeeExpense.objects.filter(date__year=year, date__month=today.month).count()

    context = {
        'month': month,
        'year': year,
        'invoice_count': invoice_count,
        'payment_count': payment_count,
        'expense_count': expense_count,
    }

    template = get_template('reports/monthly_summary_pdf.html')
    html = template.render(context)
    pdf_file = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_file)

    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)

    pdf_file.seek(0)

    # Option 1: Return as HTTP response
    if request.GET.get('download') == 'true':
        response = HttpResponse(pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Monthly_Report_{month}_{year}.pdf"'
        return response

    # Option 2: Email as attachment
    email = EmailMessage(
        subject="📈 Monthly Summary Report",
        body="Please find attached the monthly summary report.",
        from_email="snehasuresh98723@gmail.com",
        to=["snehasureshinventuratech@gmail.com"]
    )
    email.attach(f'Monthly_Report_{month}_{year}.pdf', pdf_file.read(), 'application/pdf')
    email.send()

    return HttpResponse("✅ Monthly summary PDF sent via email.")

from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from io import BytesIO
from django.utils.timezone import now
from accounting_app.models import Invoice, Payment, EmployeeExpense


from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from io import BytesIO
from django.utils.timezone import now
from .models import Invoice, Payment, EmployeeExpense


@login_required
@user_passes_test(is_accountant_or_superuser)
def download_monthly_summary_pdf(request):
    today = now().date()

    invoice_count = Invoice.objects.filter(date__year=today.year, date__month=today.month).count()
    payment_count = Payment.objects.filter(date__year=today.year, date__month=today.month).count()
    expense_count = EmployeeExpense.objects.filter(date__year=today.year, date__month=today.month).count()

    template = get_template('reports/monthly_summary_pdf.html')  # use a PDF-friendly template
    html = template.render({
        'invoice_count': invoice_count,
        'payment_count': payment_count,
        'expense_count': expense_count,
        'month': today.strftime('%B'),
        'year': today.year,
    })

    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer)

    if pisa_status.err:
        return HttpResponse("❌ Failed to generate PDF", status=500)

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="monthly_summary.pdf"'
    return response

# views.py
from django.shortcuts import render, redirect
from accounting_app.models import Invoice, Payment, EmployeeExpense
from django.utils.timezone import now
from django.core.mail import EmailMessage
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

@login_required
@user_passes_test(is_accountant_or_superuser)
def send_monthly_pdf_report(request):
    if request.method == 'POST':
        from_email = request.POST.get('from_email')
        to_email = request.POST.get('to_email')

        today = now().date()
        month = today.strftime('%B')
        year = today.year

        invoice_count = Invoice.objects.filter(date__year=year, date__month=today.month).count()
        payment_count = Payment.objects.filter(date__year=year, date__month=today.month).count()
        expense_count = EmployeeExpense.objects.filter(date__year=year, date__month=today.month).count()

        template = get_template('reports/monthly_summary_pdf.html')
        html = template.render({
            'month': month,
            'year': year,
            'invoice_count': invoice_count,
            'payment_count': payment_count,
            'expense_count': expense_count,
        })

        pdf_file = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_file)
        if pisa_status.err:
            return render(request, 'reports/send_pdf.html', {'error': 'Failed to generate PDF.'})

        pdf_file.seek(0)

        email = EmailMessage(
            subject=f"📈 Monthly Summary Report – {month} {year}",
            body="Please find attached the monthly summary report in PDF format.",
            from_email=from_email,
            to=[to_email]
        )
        email.attach(f"Monthly_Report_{month}_{year}.pdf", pdf_file.read(), "application/pdf")
        email.send()

        return render(request, 'reports/send_pdf.html', {'success': 'Email sent successfully!'})

    return render(request, 'reports/send_pdf.html')


from django.shortcuts import render
from django.http import JsonResponse
from .models import GSTR1, GSTR3B, GSTR9, EInvoice, TDSReport, EWayBill
from datetime import date
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from .models import GSTR1, GSTR3B, GSTR9, EInvoice, TDSReport, EWayBill, Client, Invoice

@login_required
@user_passes_test(is_accountant_or_superuser)
def compliances_dashboard(request):
    clients = Client.objects.all()
    return render(request, 'compliance/dashboard.html', {'clients': clients})

@login_required
@user_passes_test(is_accountant_or_superuser)
def generate_gstr1(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    gstr1 = GSTR1.objects.filter(client=client).order_by('-year', '-month')
    return render(request, 'compliance/gstr1.html', {'gstr1': gstr1, 'client': client})

@login_required
@user_passes_test(is_accountant_or_superuser)
def generate_gstr3b(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    gstr3b = GSTR3B.objects.filter(client=client).order_by('-year', '-month')
    return render(request, 'compliance/gstr3b.html', {'gstr3b': gstr3b, 'client': client})

@login_required
@user_passes_test(is_accountant_or_superuser)
def generate_gstr9(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    gstr9 = GSTR9.objects.filter(client=client).order_by('-year')
    return render(request, 'compliance/gstr9.html', {'gstr9': gstr9, 'client': client})

@login_required
@user_passes_test(is_accountant_or_superuser)
def generate_tds_report(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    tds = TDSReport.objects.filter(client=client)
    return render(request, 'compliance/tds_report.html', {'tds': tds, 'client': client})

@login_required
@user_passes_test(is_accountant_or_superuser)
def generate_einvoice(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    invoices = Invoice.objects.filter(client=client)
    einvoices = EInvoice.objects.filter(invoice__in=invoices)
    return render(request, 'compliance/einvoice.html', {'einvoices': einvoices, 'client': client})

@login_required
@user_passes_test(is_accountant_or_superuser)
def generate_ewaybill(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    invoices = Invoice.objects.filter(client=client)
    eway_bills = EWayBill.objects.filter(invoice__in=invoices)
    return render(request, 'compliance/ewaybill.html', {'eway_bills': eway_bills, 'client': client})

# signals.py


from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import UserActivityLog

def is_superuser(user):
    return user.is_superuser

# @login_required
# @user_passes_test(is_superuser)
# def activity_logs_view(request):
#     logs = UserActivityLog.objects.all().order_by('-timestamp')[:100]
#     return render(request, 'activity_logs.html', {'logs': logs})
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import UserActivityLog

@login_required
@user_passes_test(lambda u: u.is_superuser)  # Only superusers can view logs
@never_cache
def activity_logs_view(request):
    qs = UserActivityLog.objects.order_by('-timestamp')

    # optional quick filters: ?action=login|logout|failed_login, ?user=<id>
    action = request.GET.get('action')
    user_id = request.GET.get('user')
    if action:
        qs = qs.filter(action=action)
    if user_id:
        qs = qs.filter(user_id=user_id)

    page_obj = Paginator(qs, 50).get_page(request.GET.get('page'))

    # keep your original 'logs' context key so your template continues to work
    return render(request, 'activity_logs.html', {
        'logs': page_obj.object_list,
        'page_obj': page_obj,
        'selected_action': action or '',
        'selected_user': user_id or '',
    })




from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import GdprRequest, UserActivityLog
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def gdpr_request_view(request):
    if request.method == 'POST':
        req_type = request.POST.get('request_type')
        GdprRequest.objects.create(user=request.user, request_type=req_type)
        # Send email to user
        send_mail(
            subject="GDPR Request Received",
            message=f"Hi {request.user.email},\n\nWe've received your GDPR request for '{req_type}'. We'll notify you once it's processed.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
        )
        return render(request, 'gdpr/request_submitted.html')
    return render(request, 'gdpr/request_form.html')

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render
from .models import GdprRequest

@user_passes_test(lambda u: u.is_superuser)
def gdpr_admin_dashboard(request):
    requests = GdprRequest.objects.select_related('user').order_by('-timestamp')
    return render(request, 'gdpr/admin_dashboard.html', {'requests': requests})


@user_passes_test(lambda u: u.is_superuser)
def gdpr_export_data(request, user_id):
    """Export GDPR user data & mark request completed."""
    user = get_object_or_404(User, id=user_id)
    try:
        logs = list(UserActivityLog.objects.filter(user=user).values())

        # Mark request as completed
        GdprRequest.objects.filter(user=user, request_type='export').update(status='completed')

        messages.success(request, f"✅ Data export for {user.email} completed successfully.")
    except Exception as e:
        messages.error(request, f"❌ Failed to export data for {user.email}. Error: {str(e)}")

    return redirect('gdpr_admin_dashboard')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def gdpr_delete_user(request, user_id):
    """Delete/Anonymize a user and notify them via email."""
    user = get_object_or_404(User, id=user_id)
    original_email = user.email  # store before anonymizing

    try:
        # Anonymize + deactivate
        user.email = f"{user.email}"
        user.is_active = False
        user.first_name = ""
        user.last_name = ""
        user.save()

        # Mark request as completed
        GdprRequest.objects.filter(user=user, request_type='delete').update(status='completed')

        # Send notification email
        send_mail(
            subject="✅ Your GDPR Deletion Request Has Been Processed",
            message="Your account has been deleted/anonymized per your request.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[original_email],
            fail_silently=False,
        )

        messages.success(request, f"🗑️ User {original_email} deleted")
    except Exception as e:
        messages.error(request, f"❌ Failed to delete user {original_email}. Error: {str(e)}")

    return redirect('gdpr_admin_dashboard')

from django.shortcuts import render, redirect
from .forms import BrandingForm
from .models import BrandingSettings
from django.contrib.auth.decorators import login_required, user_passes_test

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import BrandingSettings
from .forms import BrandingForm

@login_required
@user_passes_test(is_superuser)
def branding_settings(request):
    user = request.user

    # Each superuser has their own branding row
    branding, created = BrandingSettings.objects.get_or_create(admin_user=user)

    if user.is_superuser:
        # Superuser can edit their branding
        form = BrandingForm(request.POST or None, request.FILES or None, instance=branding)
        if form.is_valid():
            branding = form.save(commit=False)
            branding.admin_user = user  # ensure linked to this superuser
            branding.owner = user       # optional: track ownership
            if not branding.created_by:
                branding.created_by = user
            branding.save()
            return redirect('dashboard')

        return render(request, 'settings/branding_settings.html', {
            'form': form,
            'can_edit': True,
            'branding': branding,
        })

    # Fallback: normal user (shouldn’t happen due to decorator)
    return render(request, 'settings/branding_settings.html', {
        'branding': branding,
        'can_edit': False,
    })




# views.py
from django.shortcuts import render
from django.db.models import Q, CharField
from django.db.models.functions import Cast

from .models import (
    Invoice, InvoiceItem, TimeEntry, Client, EmployeeExpense, TDSRecord, CashFlowProjection,
    FixedAsset, Currency, ExchangeRate, CostCenter, InterCompanyTransaction, DeferredRevenue,
    Plan, Subscription, SubscriptionInvoice, Payment as SubscriptionPayment, Budget, Forecast,
    WhatIfScenario, ForecastVariance, DepreciationEntry, GSTR1, GSTR3B, GSTR9, EInvoice, TDSReport,
    EWayBill, UserActivityLog, GdprRequest, BrandingSettings, VersionedModel  # VersionedModel not directly queried
)
from .models_procurement import (
    Vendor, Product, PurchaseRequisition, PurchaseRequisitionLine, PurchaseOrder, PurchaseOrderLine,
    GoodsReceipt, GoodsReceiptLine, VendorBill, VendorBillLine, VendorPayment
)
from .versioning import VersionHistory
from .models import AccountingPeriod, Approval, ApprovalRequest
from .models import ControlArea, ControlTask, ControlTaskInstance
from integrations.models import CRMClient
from .models import Deal, Quote, Payment as ARPayment, ClientContract, Retainer, BillingMilestone, Phase, JournalEntry, JournalItem

SEARCH_LIMIT = 20

def global_search(request):
    q = (request.GET.get('q') or '').strip()
    ctx = {'q': q, 'sections': []}
    if not q:
        return render(request, 'search/results.html', ctx)

    # --- Sales / AR ---
    invoices = Invoice.objects.filter(
        Q(id__icontains=q) | Q(client__name__icontains=q) | Q(notes__icontains=q)
    ).select_related('client')[:SEARCH_LIMIT]
    invoice_items = InvoiceItem.objects.filter(
        Q(description__icontains=q) | Q(invoice__client__name__icontains=q)
    ).select_related('invoice','invoice__client')[:SEARCH_LIMIT]
    time_entries = TimeEntry.objects.filter(
        Q(description__icontains=q) | Q(project__name__icontains=q) | Q(invoice__client__name__icontains=q)
    ).select_related('invoice','project')[:SEARCH_LIMIT]
    ar_payments = ARPayment.objects.filter(
        Q(invoice__id__icontains=q) | Q(razorpay_payment_id__icontains=q)
        | Q(method__icontains=q)
    ).select_related('invoice')[:SEARCH_LIMIT]
    clients = Client.objects.filter(
        Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q) | Q(company__icontains=q) | Q(gstin__icontains=q)
    )[:SEARCH_LIMIT]

    # --- Expenses / Payroll extras already in your model ---
    employee_expenses = EmployeeExpense.objects.filter(
        Q(description__icontains=q) | Q(employee__name__icontains=q) | Q(category__icontains=q) | Q(status__icontains=q)
    ).select_related('employee')[:SEARCH_LIMIT]
    tds_records = TDSRecord.objects.filter(
        Q(source__icontains=q) | Q(payee_name__icontains=q) | Q(reference_id__icontains=q)
    )[:SEARCH_LIMIT]

    # --- Cashflow / Assets ---
    cashflows = CashFlowProjection.objects.filter(
        Q(notes__icontains=q) | Q(description__icontains=q) | Q(direction__icontains=q)
    )[:SEARCH_LIMIT]
    assets = FixedAsset.objects.filter(
        Q(asset_tag__icontains=q) | Q(name__icontains=q) | Q(category__icontains=q)
    )[:SEARCH_LIMIT]
    depreciation_entries = DepreciationEntry.objects.filter(
        Q(asset__name__icontains=q)
    ).select_related('asset')[:SEARCH_LIMIT]

    # --- Procurement (AP) ---
    vendors = Vendor.objects.filter(
        Q(name__icontains=q) | Q(email__icontains=q) | Q(gstin__icontains=q)
    )[:SEARCH_LIMIT]
    products = Product.objects.filter(
        Q(sku__icontains=q) | Q(name__icontains=q)
    )[:SEARCH_LIMIT]
    prs = PurchaseRequisition.objects.filter(
        Q(number__icontains=q) | Q(notes__icontains=q) | Q(status__icontains=q)
    ).select_related('requester')[:SEARCH_LIMIT]
    pos = PurchaseOrder.objects.filter(
        Q(number__icontains=q) | Q(notes__icontains=q) | Q(status__icontains=q) | Q(vendor__name__icontains=q)
    ).select_related('vendor')[:SEARCH_LIMIT]
    grns = GoodsReceipt.objects.filter(
        Q(number__icontains=q) | Q(notes__icontains=q) | Q(po__number__icontains=q)
    ).select_related('po')[:SEARCH_LIMIT]
    bills = VendorBill.objects.filter(
        Q(number__icontains=q) | Q(vendor__name__icontains=q) | Q(notes__icontains=q)
        | Q(irn__icontains=q) | Q(ack_no__icontains=q) | Q(eway_bill_no__icontains=q)
    ).select_related('vendor')[:SEARCH_LIMIT]
    vpayments = VendorPayment.objects.filter(
        Q(vendor__name__icontains=q) | Q(description__icontains=q) | Q(remarks__icontains=q)
    ).select_related('vendor')[:SEARCH_LIMIT]

    # --- CRM / Deals / Quotes / Contracts ---
    crm_clients = CRMClient.objects.filter(
        Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q) | Q(company__icontains=q) | Q(notes__icontains=q)
    )[:SEARCH_LIMIT]
    deals = Deal.objects.filter(
        Q(title__icontains=q) | Q(stage__icontains=q) | Q(amount__icontains=q) | Q(crm_client__name__icontains=q)
    ).select_related('crm_client')[:SEARCH_LIMIT]
    quotes = Quote.objects.filter(
        Q(title__icontains=q) | Q(status__icontains=q) | Q(deal__title__icontains=q)
    ).select_related('deal','client')[:SEARCH_LIMIT]
    contracts = ClientContract.objects.filter(
        Q(name__icontains=q) | Q(client__name__icontains=q)
    ).select_related('client')[:SEARCH_LIMIT]
    milestones = BillingMilestone.objects.filter(
        Q(name__icontains=q) | Q(contract__name__icontains=q) | Q(is_billed__icontains=q)
    ).select_related('contract')[:SEARCH_LIMIT]
    retainers = Retainer.objects.filter(
        Q(contract__name__icontains=q)
    ).select_related('contract')[:SEARCH_LIMIT]
    phases = Phase.objects.filter(
        Q(name__icontains=q) | Q(contract__name__icontains=q)
    ).select_related('contract')[:SEARCH_LIMIT]

    # --- Budgets / Forecasts / What-if ---
    budgets = Budget.objects.filter(
        Q(name__icontains=q) | Q(project__name__icontains=q) | Q(account__name__icontains=q) | Q(cost_center__name__icontains=q)
    ).select_related('project','account','cost_center')[:SEARCH_LIMIT]
    forecasts = Forecast.objects.filter(
        Q(notes__icontains=q) | Q(project__name__icontains=q) | Q(account__name__icontains=q)
    ).select_related('project','account')[:SEARCH_LIMIT]
    scenarios = WhatIfScenario.objects.filter(
        Q(name__icontains=q) | Q(notes__icontains=q) | Q(scenario_type__icontains=q)
    )[:SEARCH_LIMIT]
    variances = ForecastVariance.objects.filter(
        Q(project__name__icontains=q) | Q(account__name__icontains=q)
    ).select_related('project','account','forecast')[:SEARCH_LIMIT]

    # --- GST / TDS filings & docs ---
    gstr1 = GSTR1.objects.filter(Q(month__icontains=q) | Q(year__icontains=q) | Q(client__name__icontains=q))[:SEARCH_LIMIT]
    gstr3b = GSTR3B.objects.filter(Q(month__icontains=q) | Q(year__icontains=q) | Q(client__name__icontains=q))[:SEARCH_LIMIT]
    gstr9 = GSTR9.objects.filter(Q(year__icontains=q) | Q(client__name__icontains=q))[:SEARCH_LIMIT]
    einvoices = EInvoice.objects.filter(Q(irn__icontains=q) | Q(ack_no__icontains=q) | Q(status__icontains=q) | Q(invoice__id__icontains=q)).select_related('invoice')[:SEARCH_LIMIT]
    eway = EWayBill.objects.filter(Q(eway_bill_no__icontains=q) | Q(status__icontains=q) | Q(invoice__id__icontains=q)).select_related('invoice')[:SEARCH_LIMIT]

    # --- Subscriptions / Plans (your SaaS) ---
    plans = Plan.objects.filter(Q(name__icontains=q) | Q(description__icontains=q))[:SEARCH_LIMIT]
    subs = Subscription.objects.filter(Q(user__email__icontains=q) | Q(plan__name__icontains=q)).select_related('user','plan')[:SEARCH_LIMIT]
    sub_invoices = SubscriptionInvoice.objects.filter(Q(description__icontains=q) | Q(subscription__user__email__icontains=q) | Q(name__name__icontains=q)).select_related('subscription','user','name')[:SEARCH_LIMIT]
    sub_payments = SubscriptionPayment.objects.filter(Q(payment_gateway__icontains=q)).select_related('invoice')[:SEARCH_LIMIT]

    # --- Master / FX / ICC / DR ---
    currencies = Currency.objects.filter(Q(code__icontains=q) | Q(name__icontains=q))[:SEARCH_LIMIT]
    xrates = ExchangeRate.objects.filter(Q(from_currency__code__icontains=q) | Q(to_currency__code__icontains=q)).select_related('from_currency','to_currency')[:SEARCH_LIMIT]
    ccs = CostCenter.objects.filter(Q(code__icontains=q) | Q(name__icontains=q))[:SEARCH_LIMIT]
    icc = InterCompanyTransaction.objects.filter(Q(from_company__icontains=q) | Q(to_company__icontains=q))[:SEARCH_LIMIT]
    dr = DeferredRevenue.objects.filter(Q(customer__name__icontains=q) | Q(description__icontains=q)).select_related('customer')[:SEARCH_LIMIT]

    # --- Ledger snippets (JE/JI) ---
    jes = JournalEntry.objects.filter(Q(description__icontains=q)).select_related('currency','project')[:SEARCH_LIMIT]
    jis = JournalItem.objects.filter(Q(description__icontains=q) | Q(account__name__icontains=q)).select_related('entry','account','project')[:SEARCH_LIMIT]

    # Build sections (order matters for UI)
    sections = [
        ("Invoices", invoices),
        ("Invoice Items", invoice_items),
        ("Time Entries", time_entries),
        ("AR Payments", ar_payments),
        ("Clients", clients),

        ("Employee Expenses", employee_expenses),
        ("TDS Records", tds_records),

        ("Cash Flow Projections", cashflows),
        ("Fixed Assets", assets),
        ("Depreciation Entries", depreciation_entries),

        ("Vendors", vendors),
        ("Products", products),
        ("Purchase Requisitions", prs),
        ("Purchase Orders", pos),
        ("Goods Receipts", grns),
        ("Vendor Bills", bills),
        ("Vendor Payments", vpayments),

        ("CRM Clients", crm_clients),
        ("Deals", deals),
        ("Quotes", quotes),
        ("Client Contracts", contracts),
        ("Billing Milestones", milestones),
        ("Retainers", retainers),
        ("Phases", phases),

        ("Budgets", budgets),
        ("Forecasts", forecasts),
        ("What-If Scenarios", scenarios),
        ("Forecast Variances", variances),

        ("GSTR-1", gstr1),
        ("GSTR-3B", gstr3b),
        ("GSTR-9", gstr9),
        ("E-Invoices", einvoices),
        ("E-Way Bills", eway),

        ("Plans", plans),
        ("Subscriptions", subs),
        ("Subscription Invoices", sub_invoices),
        ("Subscription Payments", sub_payments),

        ("Currencies", currencies),
        ("Exchange Rates", xrates),
        ("Cost Centers", ccs),
        ("Inter-Company Transactions", icc),
        ("Deferred Revenue", dr),

        ("Journal Entries", jes),
        ("Journal Items", jis),
    ]

    # Admin-only extras
    if request.user.is_superuser:
        try:
            vhist = VersionHistory.objects.annotate(data_text=Cast('data', CharField())).filter(Q(data_text__icontains=q))[:SEARCH_LIMIT]
        except Exception:
            vhist = VersionHistory.objects.none()
        periods = AccountingPeriod.objects.filter(Q(status__icontains=q) | Q(year__icontains=q))[:SEARCH_LIMIT]
        approvals = ApprovalRequest.objects.filter(Q(title__icontains=q) | Q(status__icontains=q))[:SEARCH_LIMIT]
        sections.extend([
            ("Version History", vhist),
            ("Accounting Periods", periods),
            ("Approval Requests", approvals),
        ])

    ctx['sections'] = sections
    return render(request, 'search/results.html', ctx)

# core/views.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from .models import ErrorLog, ModelMessage

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.messages import get_messages
from django.contrib import messages as dj_messages

@login_required

def messages_inbox(request):
    only = request.GET.get('only')  # 'errors' | 'messages' | None

    # Optional: clear snapshot
    if request.GET.get('clear') == '1':
        request.session.pop('_flash_snapshot', None)

    # Capture flash messages ONCE and requeue once
    snapshot = request.session.get('_flash_snapshot')
    if snapshot is None:
        storage = get_messages(request)           # consumes current flash
        captured = list(storage)
        snapshot = [{'level': m.level, 'text': m.message, 'tags': m.tags or ''} for m in captured]
        # re-add once so they still exist for the rest of the site
        for m in captured:
            dj_messages.add_message(request, m.level, m.message, extra_tags=m.tags)
        request.session['_flash_snapshot'] = snapshot

    errors_qs = ErrorLog.objects.select_related('user')
    msgs_qs   = ModelMessage.objects.select_related('created_by', 'content_type')

    context = {
        'flash_messages': snapshot,                               # render from snapshot
        'errors_all':   [] if only == 'messages' else errors_qs[:500],
        'messages_all': [] if only == 'errors'   else msgs_qs[:500],
        'only': only,
        'suppress_global_messages': True,  # avoid double-render in base
    }
    return render(request, "core/messages_inbox.html", context)


from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST

@login_required

@require_POST
def delete_message(request, message_id):
    msg = get_object_or_404(ModelMessage, id=message_id)
    msg.delete()
    return redirect('messages_inbox')  # your inbox view name

@login_required

@require_POST
def delete_error(request, error_id):
    err = get_object_or_404(ErrorLog, id=error_id)
    err.delete()
    return redirect('messages_inbox')

@login_required

@require_POST
def delete_all_messages(request):
    ModelMessage.objects.all().delete()
    return redirect('messages_inbox')

@login_required

@require_POST
def delete_all_errors(request):
    ErrorLog.objects.all().delete()
    return redirect('messages_inbox')

# views.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.messages import get_messages
from django.shortcuts import render, redirect
from django.http import HttpResponseNotAllowed
from django.contrib import messages as dj_messages  # only for clearing

# @login_required
# @user_passes_test(lambda u: u.is_staff or u.is_superuser)
# def messages_inbox(request):
#     only = request.GET.get('only')  # 'errors' | 'messages' | None

#     # Create snapshot once; do NOT re-add to storage
#     snap = request.session.get('_flash_snapshot')
#     if snap is None:
#         captured = list(get_messages(request))  # consume storage
#         snap = [{'level': m.level, 'tags': m.tags or '', 'text': m.message} for m in captured]
#         request.session['_flash_snapshot'] = snap

#     errors_qs = ErrorLog.objects.select_related('user')
#     msgs_qs   = ModelMessage.objects.select_related('created_by', 'content_type')

#     return render(request, "core/messages_inbox.html", {
#         'flash_messages': snap,
#         'errors_all':   [] if only == 'messages' else errors_qs[:500],
#         'messages_all': [] if only == 'errors'   else msgs_qs[:500],
#         'only': only,
#         'suppress_global_messages': True,  # avoid base.html rendering them again
#     })

@login_required

def delete_flash_message(request, idx: int):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    snap = request.session.get('_flash_snapshot', [])
    if 0 <= idx < len(snap):
        snap.pop(idx)
        request.session['_flash_snapshot'] = snap
    # also consume storage so removed items don't reappear accidentally
    list(get_messages(request))
    return redirect('messages_inbox')

@login_required

def clear_flash_messages(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    request.session.pop('_flash_snapshot', None)
    # clear any remaining storage
    list(get_messages(request))
    return redirect('messages_inbox')



# from django.shortcuts import render
# from .models import Message

# def messages_inbox(request):
#     return render(request, "messages_inbox.html", {
#         "messages_all": Message.objects.all(),  # ordered by model Meta
#     })

# profiles/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Profile
from .forms import ProfileForm


@login_required
def settings_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('settings_view')
    else:
        form = ProfileForm(instance=profile)

    contacts = User.objects.exclude(id=request.user.id)

    return render(request, 'profiles/settings.html', {
        'form': form,
        'contacts': contacts
    })

# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Profile
from .forms import ProfileForm

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Profile


@login_required
def profile_view(request):
    # Get or create profile
    profile, created = Profile.objects.get_or_create(user=request.user)

    # Get allowed users
    allowed_users = get_allowed_users(request.user)
    allowed_profiles = Profile.objects.filter(user__in=allowed_users)

    context = {
        'profile': profile,
        'allowed_users': allowed_users,
        'allowed_profiles': allowed_profiles,
    }
    return render(request, 'profile.html', context)


@login_required
def profile_edit(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile_view')  # Redirect to profile page
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'profile_edit.html', {'form': form})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.mail import send_mail
from django.utils.timezone import now
from .models import PasswordResetToken
from .forms import ForgotPasswordForm, ResetPasswordForm

User = get_user_model()

def forgot_password_view(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email=email).first()
            if user:
                # Create token
                token_obj = PasswordResetToken.objects.create(user=user)
                reset_url = request.build_absolute_uri(
                    reverse('reset_password', kwargs={'token': str(token_obj.token)})
                )
                # Send email (customize subject & message)
                send_mail(
                    'Password Reset Request',
                    f'Click the link below to reset your password:\n\n{reset_url}',
                    'noreply@yourdomain.com',
                    [email],
                )
            # Show success message anyway (avoid email enumeration)
            return render(request, 'forgot_password_done.html')
    else:
        form = ForgotPasswordForm()
    return render(request, 'forgot_password.html', {'form': form})

def reset_password_view(request, token):
    token_obj = get_object_or_404(PasswordResetToken, token=token)
    if token_obj.is_expired():
        return render(request, 'reset_password_expired.html')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user = token_obj.user
            user.set_password(new_password)
            user.save()
            token_obj.delete()  # invalidate token after use
            return render(request, 'reset_password_complete.html')
    else:
        form = ResetPasswordForm()

    return render(request, 'reset_password.html', {'form': form})
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import (
    TDSRecord,
    FilingRecord,
    ContractorFilingRecord,
    TaxDeclaration
)

def is_accountant_or_superuser(user):
    return user.is_superuser or user.groups.filter(name='Accountant').exists()

@login_required
@user_passes_test(is_accountant_or_superuser)
def combined_tax_and_tds_list(request):
    # Get all TDSRecords from Payroll and Contractors
    all_tds_records = TDSRecord.objects.all().order_by('-filing_date', '-payment_date')

    # Get all filing records from employees and contractors, merged in Python
    employee_filings = FilingRecord.objects.all()
    contractor_filings = ContractorFilingRecord.objects.all()

    # Merge filing querysets using itertools.chain (or convert to list and sort)
    import itertools
    filings = list(itertools.chain(employee_filings, contractor_filings))
    # Sort by filed_on date descending
    filings.sort(key=lambda x: x.filed_on, reverse=True)

    # Get all employee tax declarations
    tax_declarations = TaxDeclaration.objects.all().order_by('-submitted_on')

    context = {
        'tds_records': all_tds_records,
        'filing_records': filings,
        'tax_declarations': tax_declarations,
    }

    return render(request, 'payroll/combined_tax_and_tds_list.html', context)

from django.shortcuts import render
from .models import Client

from .models import Account

@login_required
def client_list(request):
    user = request.user

    # --- Determine allowed users ---
    if user.is_superuser:
        allowed_users = [user] + list(user.created_users.all())
    else:
        superuser_creator = getattr(user, "created_by", None)
        allowed_users = [user]
        if superuser_creator:
            allowed_users.append(superuser_creator)

    # --- Filter clients ---
    account_names = Account.objects.values_list("name", flat=True)
    clients = (
        Client.objects
        .filter(created_by__in=allowed_users)
        .exclude(name__startswith="Receivable – ")
        .order_by("name")
        .distinct()
    )

    return render(request, "users/client_list.html", {"clients": clients})




# views.py
from django.shortcuts import render, get_object_or_404
from .models import Project



from decimal import Decimal
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from .models import Project, Invoice, Account, JournalItem, TimeEntry
 # adjust import if needed


from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, F
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render

from decimal import Decimal
from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce
from django.db.models import DecimalField   # ✅ add this
# ... other imports ...

from decimal import Decimal
from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce
from django.db.models import DecimalField
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Project, TimeEntry, JournalItem, Invoice

from decimal import Decimal
from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce
from django.db.models import DecimalField
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Project, TimeEntry, JournalItem, Invoice

@login_required
@user_passes_test(is_accountant_or_superuser)
def print_project(request, project_id):
    D0 = Decimal("0.00")
    DECIMAL0 = Value(D0, output_field=DecimalField())

    project = get_object_or_404(
        Project.objects.select_related("client").prefetch_related("stages"),
        pk=project_id
    )

    # Expense (ledger)
    expense_total = (
        JournalItem.objects.filter(project=project, account__account_type="Expense")
        .aggregate(total=Coalesce(
            Sum(F("debit") - F("credit"), output_field=DecimalField()),
            DECIMAL0
        ))["total"] or D0
    )

    # ✅ Income (PAID only, incl. tax)
    income_total = D0
    paid_invoices_qs = (
        Invoice.objects
        .filter(project=project, status__iexact="paid")   # <-- only paid
        .prefetch_related("items", "time_entries")
    )
    for inv in paid_invoices_qs:
        twt = getattr(inv, "total_with_tax", None)
        amt = twt() if callable(twt) else twt
        try:
            income_total += D0 if amt is None else (amt if isinstance(amt, Decimal) else Decimal(str(amt)))
        except Exception:
            income_total += D0

    # Stage-wise expenses for display
    stage_expenses = (
        JournalItem.objects.filter(project=project, account__account_type="Expense")
        .values("stage__id", "stage__name")
        .annotate(total=Coalesce(
            Sum(F("debit") - F("credit"), output_field=DecimalField()),
            DECIMAL0
        ))
        .order_by("stage__name")
    )

    # Hours
    time_hours = (
        TimeEntry.objects.filter(project=project)
        .aggregate(total=Coalesce(Sum("hours", output_field=DecimalField()), DECIMAL0))
    )["total"] or D0

    budget = project.budget or D0
    budget_variance = budget - expense_total
    net_profit = income_total - expense_total

    context = {
        "project": project,
        "client": project.client,
        "budget": budget,
        "income": income_total,      # ✅ paid-only income
        "expense": expense_total,
        "budget_variance": budget_variance,
        "net_profit": net_profit,
        "time_hours": time_hours,
        "stage_expenses": stage_expenses,
    }
    return render(request, "print_project.html", context)





from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ClientForm
@login_required
@user_passes_test(is_accountant_or_superuser)
 # Account is your existing model

@login_required
@user_passes_test(is_accountant_or_superuser)
def add_client(request):
    user = request.user

    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.created_by = user
            client.owner = user
            client.save()

            # Create Receivable account automatically and link to client
            Account.objects.create(
                name=f"Receivable – {client.name}",
                account_type="Asset",   # or "Receivable" depending on your choices
                is_receivable=True,
                client=client
            )

            messages.success(request, "Client and Receivable account added successfully!")
            return redirect("client_list")
    else:
        form = ClientForm()

    return render(request, "clients/add_client.html", {"form": form})



@login_required
@user_passes_test(is_accountant_or_superuser)
def edit_client(request, pk):
    client = get_object_or_404(Client, pk=pk)

    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            try:
                with transaction.atomic():
                    client = form.save()

                    # Keep the receivable account in sync with the client's name
                    desired_name = f"Receivable – {client.name}".strip()

                    # Case A: client already linked to an account
                    acc = client.receivable_account

                    if acc:
                        # If the name changed, try to rename; if conflict, reuse the existing with desired name
                        if acc.name != desired_name:
                            existing = Account.objects.filter(name=desired_name).exclude(pk=acc.pk).first()
                            if existing:
                                acc = existing  # reuse the existing one with desired name
                            else:
                                acc.name = desired_name
                                # Ensure required fields are correct
                                if hasattr(acc, "is_receivable"):
                                    acc.is_receivable = True
                                if hasattr(acc, "account_type"):
                                    acc.account_type = "Receivable"
                                acc.save(update_fields=["name"] + (["is_receivable"] if hasattr(acc, "is_receivable") else []) + (["account_type"] if hasattr(acc, "account_type") else []))
                    else:
                        # Case B: no linked account yet — create or reuse by name
                        acc, _ = Account.objects.get_or_create(
                            name=desired_name,
                            defaults={
                                "account_type": "Receivable",
                                "is_receivable": True,
                            },
                        )

                    # Link both directions
                    if hasattr(Account, "client"):
                        if getattr(acc, "client_id", None) != client.id:
                            acc.client = client
                            acc.save(update_fields=["client"])

                    if client.receivable_account_id != acc.id:
                        client.receivable_account = acc
                        client.save(update_fields=["receivable_account"])

                messages.success(request, "Client updated successfully.")
                return redirect("client_list")

            except Exception as e:
                messages.error(request, f"Something went wrong: {e}")
    else:
        form = ClientForm(instance=client)

    return render(request, "clients/edit_client.html", {"form": form, "client": client})

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

@login_required
@user_passes_test(is_accountant_or_superuser)
def delete_client(request, pk):
    """
    Deletes the Client and its linked Receivable Account (if any).
    """
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("client_list")

    client = get_object_or_404(Client, pk=pk)
    name = client.name

    try:
        with transaction.atomic():
            # Try to get the linked Account safely
            try:
                acc = client.receivable_account
            except ObjectDoesNotExist:
                acc = None

            # Delete the receivable account first
            if acc:
                acc.delete()

            # Delete the client
            client.delete()

        messages.success(request, f"Client '{name}' and its receivable account were deleted.")
    except Exception as e:
        messages.error(request, f"Could not delete client: {e}")

    return redirect("client_list")




@login_required
def quote_reject(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    quote.status = "Rejected"
    quote.save(update_fields=["status"])
    messages.error(request, f"❌ Quote {quote.title} rejected.")
    return redirect("quote_detail", quote_id=pk)


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import ClientContract
from .forms import ClientContractForm
from django.forms import inlineformset_factory
from .models import ClientContract, Retainer, BillingMilestone, Phase
from .forms import RetainerForm, MilestoneForm, PhaseForm,RetainerFormSet, MilestoneFormSet, PhaseFormSet

@login_required
def contract_edit(request, pk):
    contract = get_object_or_404(ClientContract, pk=pk)

    if request.method == "POST":
        form = ClientContractForm(request.POST, instance=contract)
        retainer_formset = RetainerFormSet(request.POST, instance=contract)
        milestone_formset = MilestoneFormSet(request.POST, instance=contract)
        phase_formset = PhaseFormSet(request.POST, instance=contract)

        # DEBUGGING: print validation errors
        if not form.is_valid():
            print("Contract errors:", form.errors)
        if not retainer_formset.is_valid():
            print("Retainer errors:", retainer_formset.errors)
        if not milestone_formset.is_valid():
            print("Milestone errors:", milestone_formset.errors)
        if not phase_formset.is_valid():
            print("Phase errors:", phase_formset.errors)

        if form.is_valid() and retainer_formset.is_valid() and milestone_formset.is_valid() and phase_formset.is_valid():
            form.save()
            retainer_formset.save()
            milestone_formset.save()
            phase_formset.save()
            messages.success(request, "Contract and related items updated successfully ✅")
            return redirect("contract_list")

    else:
        form = ClientContractForm(instance=contract)
        retainer_formset = RetainerFormSet(instance=contract)
        milestone_formset = MilestoneFormSet(instance=contract)
        phase_formset = PhaseFormSet(instance=contract)

    context = {
        "form": form,
        "retainer_formset": retainer_formset,
        "milestone_formset": milestone_formset,
        "phase_formset": phase_formset,
        "contract": contract,
    }
    return render(request, "contracts/contract_form.html", context)


@login_required
def contract_delete(request, pk):
    contract = get_object_or_404(ClientContract, pk=pk)
    if request.method == "POST":
        contract.delete()
        messages.success(request, "Contract deleted successfully 🗑")
        return redirect("contract_list")
    return render(request, "contracts/contract_confirm_delete.html", {"contract": contract})

@login_required
@user_passes_test(is_accountant_or_superuser)
def reject_je(request, approval_pk):
    appr = get_object_or_404(ApprovalRequest, pk=approval_pk)
    if request.method == "POST":
        appr.status = "REJECTED"
        appr.assigned_to = request.user
        appr.comment = request.POST.get("comment", "")
        appr.save()
        messages.success(request, "Journal entry rejected.")
        return redirect("journalentry_approvals", pk=appr.target_id)
    return render(request, "approvals/reject.html", {"approval": appr})




# views.py
from collections import defaultdict
from decimal import Decimal
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils import timezone

from .models import Invoice, Client


D0 = Decimal("0.00")


def _call_or_value(obj, attr, default=None):
    """
    If attr is a callable (e.g., model method), call it; otherwise read the value.
    Return `default` if missing/None.
    """
    val = getattr(obj, attr, None)
    if callable(val):
        val = val()
    return default if val is None else val


def _bucket_for(days_overdue: int) -> str:
    """
    Map integer days into bucket keys that match the template context.
    <= 0 => current; 1–30 => d1_30; 31–60 => d31_60; 61–90 => d61_90; >90 => d90_plus
    """
    if days_overdue <= 0:
        return "current"
    if days_overdue <= 30:
        return "d1_30"
    if days_overdue <= 60:
        return "d31_60"
    if days_overdue <= 90:
        return "d61_90"
    return "d90_plus"


@login_required
@user_passes_test(is_accountant_or_superuser)
def ar_aging_report(request):
    """
    Accounts Receivable aging report
    Shows only invoices belonging to clients/projects the current user owns.
    """
    today = timezone.localdate()
    user = request.user

    # Filters
    client_id = request.GET.get("client")
    show = request.GET.get("show", "unpaid")  # unpaid (default) or all
    age_by = request.GET.get("age_by", "due")  # due (default) or date

    invoices_qs = (
        Invoice.objects
        .select_related("client", "project")
        .prefetch_related("items", "time_entries")
        .order_by("client__name", "date", "id")
    )

    # --- Restrict invoices by role ---
    if user.is_superadmin:
        # SuperAdmin sees everything
        pass
    elif user.is_normal_superuser:
        # Superuser sees their own + their accountants' clients
        invoices_qs = invoices_qs.filter(
            Q(client__created_by=user) |
            Q(client__created_by__created_by=user)
        )
    elif user.is_accountant:
        # Accountant sees only their own clients
        invoices_qs = invoices_qs.filter(client__created_by=user)

    # --- Apply unpaid filter ---
    if show != "all":
        invoices_qs = invoices_qs.exclude(status__iexact="paid")

    # --- Apply client filter if provided ---
    if client_id:
        invoices_qs = invoices_qs.filter(client_id=client_id)

    # Initialize grouping
    groups = defaultdict(lambda: {
        "client_id": None,
        "client_name": None,
        "current": D0,
        "d1_30": D0,
        "d31_60": D0,
        "d61_90": D0,
        "d90_plus": D0,
        "total": D0,
        "rows": [],
    })

    for inv in invoices_qs:
        amount = _call_or_value(inv, "total_with_tax", D0)
        if amount is None or amount <= 0:
            continue

        if age_by == "date":
            anchor = getattr(inv, "date", None)
        else:
            anchor = getattr(inv, "due_date", None) or getattr(inv, "date", None)

        days_overdue = max(0, (today - anchor).days) if anchor else 0
        bucket = _bucket_for(days_overdue)

        g = groups[inv.client_id]
        g["client_id"] = inv.client_id
        g["client_name"] = getattr(inv.client, "name", str(inv.client))
        g[bucket] += amount
        g["total"] += amount

        g["rows"].append({
            "invoice_id": inv.id,
            "project_name": getattr(getattr(inv, "project", None), "name", None),
            "date": inv.date,
            "due_date": getattr(inv, "due_date", None),
            "days_overdue": days_overdue,
            "status": inv.status,
            "amount": amount,
        })

    # Flatten & totals
    client_summaries = []
    grand = {k: D0 for k in ["current", "d1_30", "d31_60", "d61_90", "d90_plus", "total"]}

    for g in groups.values():
        client_summaries.append(g)
        for k in grand.keys():
            grand[k] += g[k]

    client_summaries.sort(key=lambda r: (r["client_name"] or "").lower())

    # --- Dropdown clients (restricted) ---
    if user.is_superadmin:
        clients = Client.objects.order_by("name").only("id", "name")
    elif user.is_normal_superuser:
        clients = Client.objects.filter(
            Q(created_by=user) | Q(created_by__created_by=user)
        ).order_by("name").only("id", "name")
    else:
        clients = Client.objects.filter(created_by=user).order_by("name").only("id", "name")

    bucket_order = [
        ("current", "Current"),
        ("d1_30", "1–30"),
        ("d31_60", "31–60"),
        ("d61_90", "61–90"),
        ("d90_plus", "90+"),
        ("total", "Total"),
    ]

    ctx = {
        "today": today,
        "client_summaries": client_summaries,
        "grand": grand,
        "clients": clients,
        "selected_client_id": client_id or "",
        "show": show,
        "age_by": age_by,
        "bucket_order": bucket_order,
    }
    return render(request, "reports/ar_aging_report.html", ctx)
