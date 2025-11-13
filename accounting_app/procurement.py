# accounting_app/views/procurement.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.db import transaction
from django.core.exceptions import ValidationError


from accounting_app.models_procurement import (
    Vendor, Product,
    PurchaseRequisition, PurchaseOrder, GoodsReceipt,PurchaseOrderLine,
    VendorBill, post_vendor_bill
)
from accounting_app.forms_procurement import (
    PurchaseRequisitionForm, PRLineFormSet,
    PurchaseOrderForm, POLineFormSet,
    GoodsReceiptForm, GRNLineFormSet,
    VendorBillForm, VendorBillLineFormSet,ProductForm
)
from accounting_app.models import ApprovalRequest
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.contrib.auth import get_user_model

def get_allowed_users(user):
    """
    Returns a list of users the current user is allowed to see:
    - Superuser: themselves + all users they created
    - Accountant: themselves + their superuser creator
    """
    allowed = [user]

    if user.is_superuser:
        if hasattr(user, "created_users"):
            allowed.extend(user.created_users.all())
    else:
        if getattr(user, "created_by", None):
            allowed.append(user.created_by)

    return allowed


# ---- Purchase Requisition ----
from django.contrib.auth.decorators import login_required, user_passes_test

from .models_procurement import PurchaseRequisition
def is_accountant_or_superuser(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, "is_accountant", False))

from collections import defaultdict
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseNotAllowed

from .forms_procurement import PurchaseRequisitionForm, PRLineFormSet
from .models_procurement import PurchaseRequisition, ApprovalRequest,  Product
from .models import Project, CostCenter, Account




# --- LIST ---
@login_required
@user_passes_test(is_accountant_or_superuser)
def pr_list(request):
    allowed_users = get_allowed_users(request.user)

    prs = (
        PurchaseRequisition.objects
        .filter(requester__in=allowed_users)   # restrict by allowed users
        .select_related("project", "cost_center", "requester")
        .prefetch_related("lines")
        .order_by("-created_on")
    )

    return render(request, "procurement/pr_list.html", {"objects": prs})


@login_required
@user_passes_test(is_accountant_or_superuser)
def pr_create(request):
    user = request.user
    owner = user if user.is_superuser else  user.created_by 

    if request.method == "POST":
        form = PurchaseRequisitionForm(request.POST, user=user)
        formset = PRLineFormSet(request.POST, user=user)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                pr = form.save(commit=False)
                pr.requester = user
                pr.owner = owner
                pr.save()
                formset.instance = pr
                formset.save()
                pr.recalc_total()
            messages.success(request, "Requisition created.")
            return redirect("pr_detail", pk=pr.pk)
    else:
        form = PurchaseRequisitionForm(user=user)
        formset = PRLineFormSet(user=user)

    # ✅ Always reach here with form & formset defined
    return render(
        request,
        "procurement/pr_form.html",
        {"form": form, "formset": formset},
    )


# --- DETAIL ---
@login_required
@user_passes_test(is_accountant_or_superuser)
def pr_detail(request, pk):
    allowed_users = get_allowed_users(request.user)

    pr = get_object_or_404(
        PurchaseRequisition.objects.filter(requester__in=allowed_users),
        pk=pk
    )

    # compute line totals for template
    for li in pr.lines.all():
        li.line_total = (li.qty or 0) * (li.unit_price or 0)

    return render(request, "procurement/pr_detail.html", {"object": pr})


# --- SUBMIT ---
@login_required
@user_passes_test(is_accountant_or_superuser)
def pr_submit(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    allowed_users = get_allowed_users(request.user)

    pr = get_object_or_404(
        PurchaseRequisition.objects.filter(requester__in=allowed_users),
        pk=pk
    )

    try:
        pr.send_for_approval()

        # Create approval request if not exists
        ct = ContentType.objects.get_for_model(PurchaseRequisition)
        ApprovalRequest.objects.get_or_create(
            target_ct=ct,
            target_id=str(pr.pk),
            defaults={
                "title": f"Approve PR {pr.number}",
                "requested_by": request.user,
            },
        )

        messages.success(request, "PR submitted for approval.")
    except ValidationError as e:
        messages.error(request, e.message)

    return redirect("pr_detail", pk=pr.pk)


# ---- Purchase Order ----
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q

from .forms_procurement import PurchaseOrderForm, POLineFormSet
from .models_procurement import PurchaseOrder
  # ✅ reuse helpers
from .models import ApprovalRequest


@login_required
@user_passes_test(is_accountant_or_superuser)
def po_list(request):
    allowed_users = get_allowed_users(request.user)

    pos = (
        PurchaseOrder.objects
        .filter(created_by__in=allowed_users)   # 🔑 restrict by allowed users
        .select_related("vendor", "created_by")
        .prefetch_related("lines")
        .order_by("-created_on")
    )

    return render(request, "procurement/po_list.html", {"objects": pos})


@login_required
@user_passes_test(is_accountant_or_superuser)
def po_create(request):
    user = request.user
    owner = user if user.is_superuser else  user.created_by  

    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, user=user)  # ✅ pass user
        formset = POLineFormSet(request.POST, user=user)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                po = form.save(commit=False)
                po.created_by = user
                po.owner = owner 
                po.save()
                formset.instance = po
                formset.save()
                po.recalc_total()
            messages.success(request, "PO created.")
            return redirect("po_detail", pk=po.pk)
    else:
        form = PurchaseOrderForm(user=user)
        formset = POLineFormSet(user=user)

    return render(
        request,
        "procurement/po_form.html",
        {"form": form, "formset": formset},
    )


@login_required
@user_passes_test(is_accountant_or_superuser)
def po_detail(request, pk):
    allowed_users = get_allowed_users(request.user)

    po = get_object_or_404(PurchaseOrder, pk=pk, created_by__in=allowed_users)
    return render(request, "procurement/po_detail.html", {"object": po})


@login_required
@user_passes_test(is_accountant_or_superuser)
def po_submit_for_approval(request, pk):
    allowed_users = get_allowed_users(request.user)

    po = get_object_or_404(PurchaseOrder, pk=pk, created_by__in=allowed_users)

    try:
        ct = ContentType.objects.get_for_model(PurchaseOrder)
        ApprovalRequest.objects.get_or_create(
            target_ct=ct,
            target_id=str(po.pk),
            defaults={
                "title": f"Approve PO {po.number}",
                "requested_by": request.user,
            },
        )
        messages.success(request, "PO submitted for approval.")
    except ValidationError as e:
        messages.error(request, e.message)

    return redirect("po_detail", pk=po.pk)



# ---- Goods Receipt ----
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db import transaction
from django.contrib.contenttypes.models import ContentType


from .forms_procurement import (
    GoodsReceiptForm, GRNLineFormSet,
    VendorBillForm, VendorBillLineFormSet,
)
from .models_procurement import GoodsReceipt, VendorBill



# ---- Goods Receipt (GRN) ----
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from accounting_app.forms_procurement import GoodsReceiptForm, GRNLineFormSet

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.contrib import messages
from accounting_app.models_procurement import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderLine
from accounting_app.forms_procurement import GoodsReceiptForm, GRNLineFormSet


@login_required
def grn_create(request):
    user = request.user

    if request.method == "POST":
        form = GoodsReceiptForm(request.POST, user=user)
        if form.is_valid():
            # 👇 Extract selected PO before validating formset
            selected_po = form.cleaned_data.get("po")
        else:
            selected_po = None

        formset = GRNLineFormSet(request.POST, user=user)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                grn = form.save(commit=False)
                grn.owner = user
                grn.save()
                formset.instance = grn
                formset.save()

                # ✅ Update PO lines qty_received
                for li in grn.lines.select_related("po_line"):
                    pol = li.po_line
                    pol.qty_received = (pol.qty_received or 0) + (li.qty_received or 0)
                    pol.save(update_fields=["qty_received"])

                # ✅ Update PO status
                po = grn.po
                rec_qty = sum(li.qty_received for li in po.lines.all())
                total_qty = sum(li.qty for li in po.lines.all())
                if rec_qty >= total_qty:
                    po.status = "RECEIVED"
                elif rec_qty > 0:
                    po.status = "PARTIALLY_RECEIVED"
                po.save(update_fields=["status"])

            messages.success(request, "Goods Receipt recorded successfully.")
            return redirect("grn_list")

    else:
        
        form = GoodsReceiptForm(user=user)
        selected_po = None
        formset = GRNLineFormSet(user=user)

    return render(
        request,
        "procurement/grn_form.html",
        {
            "form": form,
            "formset": formset,
            "selected_po": selected_po,  # 👈 pass PO to template if needed
        },
    )


# ---- Vendor Bill ----
@login_required
@user_passes_test(is_accountant_or_superuser)
def bill_create(request):
    user = request.user
    owner = user if user.is_superuser else getattr(user, "created_by", user)

    if request.method == "POST":
        form = VendorBillForm(request.POST, user=user)
        formset = VendorBillLineFormSet(request.POST, user=user)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                bill = form.save(commit=False)
                bill.created_by = user
                bill.owner = owner
                bill.save()
                
                formset.instance = bill
                formset.save()
                bill.recalc()
            messages.success(request, "Vendor bill created.")
            return redirect("bill_detail", pk=bill.pk)
    else:
        form = VendorBillForm(user=user)
        formset = VendorBillLineFormSet(user=user)

    return render(
        request,
        "procurement/bill_form.html",
        {"form": form, "formset": formset},
    )


@login_required
@user_passes_test(is_accountant_or_superuser)
def bill_detail(request, pk):
    allowed_users = get_allowed_users(request.user)
    bill = get_object_or_404(
        VendorBill.objects.filter(owner__in=allowed_users),
        pk=pk
    )
    return render(request, "procurement/bill_detail.html", {"object": bill})



@login_required
@user_passes_test(is_accountant_or_superuser)
def bill_submit_for_approval(request, pk):
    bill = get_object_or_404(VendorBill, pk=pk)
    ct = ContentType.objects.get_for_model(VendorBill)
    ApprovalRequest.objects.get_or_create(
        target_ct=ct, target_id=str(bill.pk),
        defaults={"title": f"Approve Bill {bill.number}", "requested_by": request.user}
    )
    messages.success(request, "Bill submitted for approval.")
    return redirect("bill_detail", pk=bill.pk)


@login_required
@user_passes_test(is_accountant_or_superuser)
def bill_post(request, pk):
    bill = get_object_or_404(VendorBill, pk=pk)
    if request.method == "POST":
        try:
            je = post_vendor_bill(bill, user=request.user)
            messages.success(request, f"Bill posted. JE #{je.pk} created.")
        except Exception as e:
            messages.error(request, f"Post failed: {e}")
        return redirect("bill_detail", pk=bill.pk)
    return render(request, "procurement/bill_confirm_post.html", {"object": bill})


# Vendors CRUD
from django.contrib.auth.decorators import login_required
from accounting_app.forms_procurement import VendorForm
from accounting_app.models_procurement import Vendor,VendorPayment,VendorBill
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.decorators import user_passes_test


import razorpay
def is_accountant_or_superuser(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, "is_accountant", False))
@login_required
@user_passes_test(is_accountant_or_superuser)
def vendor_list(request):
    allowed_users = get_allowed_users(request.user)
    vendors = Vendor.objects.filter(owner__in=allowed_users).prefetch_related('vendorpayment_set')
    return render(request, "procurement/vendor_list.html", {"objects": vendors})


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
# ✅ Mark as paid manually
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import razorpay



def vendor_mark_as_paid(request, pk):
    bill = get_object_or_404(VendorBill, pk=pk)
    if request.method == 'POST':
        if bill.status != 'PAID':
            bill.status = 'PAID'
            bill.is_paid = True
            bill.paid_on = timezone.now()
            bill.save()
            messages.success(request, f"✅ Bill {bill.number} marked as paid.")
        else:
            messages.info(request, f"ℹ️ Bill {bill.number} is already marked as paid.")
    return redirect('bill_list')  # Or your actual bill list view name

from django.views.decorators.csrf import csrf_exempt
import razorpay
from decimal import Decimal

def vendor_razorpay_pay(request, pk):
    from django.conf import settings
    bill = get_object_or_404(VendorBill, pk=pk)

    if bill.is_paid:
        messages.info(request, "✅ Bill already paid.")
        return redirect('bill_list')

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    amount = int(bill.total * 100)  # Amount in paisa

    # Create Razorpay order
    order_data = {
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1,
        "notes": {
            "vendor": bill.vendor.name,
            "bill_number": bill.number
        }
    }

    order = client.order.create(data=order_data)

    # Save order ID to bill
    bill.razorpay_order_id = order['id']
    bill.save()

    context = {
        'bill': bill,
        'order_id': order['id'],
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'amount': amount
    }

    return render(request, 'procurement/vendor_razorpay_checkout.html', context)

def vendor_payment_success(request, pk):
    bill = get_object_or_404(VendorBill, pk=pk)
    bill.is_paid = True
    bill.status = "PAID"
    bill.save()
    messages.success(request, f"✅ Payment received for Bill {bill.number}.")
    return redirect('bill_list')



@login_required
@user_passes_test(is_accountant_or_superuser)
def vendor_create(request):
    if request.method == "POST":
        form = VendorForm(request.POST, user=request.user)
        if form.is_valid():
            vendor = form.save(commit=False)
            
            # Set owner: superuser owns their vendors; accountant’s vendors owned by themselves
            if request.user.is_superuser:
                vendor.owner = request.user
            elif getattr(request.user, "role", "") == "Accountant":
                # If you want the accountant's vendor to be linked to their superuser creator
                superuser_creator = getattr(request.user, "created_by", None)
                vendor.owner = superuser_creator if superuser_creator else request.user
            else:
                vendor.owner = request.user  # fallback

            vendor.created_by = request.user
            vendor.save()
            messages.success(request, "Vendor created.")
            return redirect("vendor_list")
    else:
        form = VendorForm(user=request.user)
    return render(request, "procurement/vendor_form.html", {"form": form, "title": "New Vendor"})


@login_required
@user_passes_test(is_accountant_or_superuser)
def vendor_update(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    if request.method == "POST":
        form = VendorForm(request.POST, instance=vendor, user=request.user)
        if form.is_valid():
            vendor = form.save(commit=False)
            # Owner should not change on update
            vendor.save()
            messages.success(request, "Vendor updated.")
            return redirect("vendor_list")
    else:
        form = VendorForm(instance=vendor, user=request.user)
    return render(request, "procurement/vendor_form.html", {"form": form, "title": f"Edit Vendor — {vendor.name}"})


from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .models_procurement import Vendor  # adjust import if needed

@login_required
def vendor_delete(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)

    if request.method == "POST":
        try:
            vendor.delete()
            messages.success(request, "Vendor deleted.")
        except ProtectedError:
            messages.error(
                request,
                "⚠️ Cannot delete this vendor because it is linked to existing Purchase Orders or Bills."
            )
        return redirect("vendor_list")

    return render(request, "procurement/vendor_confirm_delete.html", {"object": vendor})


@login_required
@user_passes_test(is_accountant_or_superuser)
def bill_list(request):
    allowed_users = get_allowed_users(request.user)
    bills = (
        VendorBill.objects
        .filter(owner__in=allowed_users)
        .select_related("vendor", "po")
        .order_by("-bill_date", "-id")
    )
    return render(request, "procurement/bill_list.html", {"objects": bills})


@login_required
def grn_list(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    grns = (
        GoodsReceipt.objects
        .select_related("po")
        .filter(owner__in=allowed_users)   # ✅ restrict to allowed users
        .order_by("-date", "-id")
    )

    return render(
        request,
        "procurement/grn_list.html",
        {"objects": grns}
    )





from django.shortcuts import render, redirect

from django.contrib import messages

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms_procurement import ProductForm
from .models_procurement import Product

@login_required
@user_passes_test(is_accountant_or_superuser)
def product_create(request):
    user = request.user

    if request.method == "POST":
        form = ProductForm(request.POST, user=user)
        if form.is_valid():
            product = form.save(commit=False)
            product.owner = user        # assign owner
            product.created_by = user   # assign created_by
            product.save()
            messages.success(request, "Product created.")
            return redirect("product_list")
    else:
        form = ProductForm(user=user)

    return render(request, "products/product_form.html", {"form": form})


def get_allowed_users(user):
    """
    Returns users the current user can see:
    - Superuser: themselves + all users they created
    - Accountant: themselves + their superuser creator
    """
    allowed = [user]

    if user.is_superuser:
        # now works with related_name='created_users'
        allowed.extend(user.created_users.all())
    else:
        if user.created_by:
            allowed.append(user.created_by)

    return allowed

from django.db.models import Q

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from .models_procurement import Product
 # your helper
 # assuming you have this

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from .models_procurement import Product
 # your helper function

def is_accountant_or_superuser(user):
    return user.is_superuser or getattr(user, "role", "") == "Accountant"

@login_required
@user_passes_test(is_accountant_or_superuser)
def product_list(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    # Fetch products owned or created by allowed users
    products = Product.objects.filter(
        Q(owner__in=allowed_users) | Q(created_by__in=allowed_users)
    ).order_by("name")

    return render(request, "products/product_list.html", {"products": products})








@login_required
def three_way_match_report(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    report_data = []

    po_lines = (
        PurchaseOrderLine.objects.select_related("po", "po__vendor", "product")
        .prefetch_related("grn_lines", "bill_lines")
        .filter(po__owner__in=allowed_users)   # ✅ restrict to allowed users
    )

    for line in po_lines:
        received_qty = sum(gl.qty_received or 0 for gl in line.grn_lines.all())
        invoiced_qty = sum(bl.qty or 0 for bl in line.bill_lines.all())
        match_status = "✅ Match" if (line.qty == received_qty == invoiced_qty) else "❌ Mismatch"

        report_data.append({
            "po_number": line.po.number,
            "vendor": line.po.vendor.name,
            "product": line.product.name if line.product else "(no product)",
            "ordered_qty": line.qty,
            "received_qty": received_qty,
            "invoiced_qty": invoiced_qty,
            "status": match_status,
        })

    return render(request, "reports/three_way_match.html", {"rows": report_data})





from django.db.models import Sum, F, FloatField, ExpressionWrapper


@login_required
def spend_by_account_report(request):
    user = request.user
    allowed_users = get_allowed_users(user)

    lines = (
        PurchaseOrderLine.objects.filter(po__owner__in=allowed_users)  # ✅ restrict
        .values("account__name")
        .annotate(
            total_spent=Sum(
                ExpressionWrapper(
                    F("qty") * F("unit_price"),
                    output_field=FloatField()
                )
            )
        )
        .order_by("-total_spent")
    )

    return render(request, "procurement/spend_by_account.html", {"lines": lines})





# accounting_app/views/approvals.py (or inside views/procurement.py if you prefer)

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from django.shortcuts import get_object_or_404, render

from .models import ApprovalRequest

@login_required
def approvals_for_object(request, app_label, model_name, object_id):
    model = apps.get_model(app_label, model_name)
    obj = get_object_or_404(model, pk=object_id)

    approvals = ApprovalRequest.objects.filter(
        target_ct=ContentType.objects.get_for_model(model),
        target_id=str(object_id),
    ).select_related("requested_by")

    return render(request, "procurement/approval_list.html", {
        "object": obj,
        "approvals": approvals,
    })
