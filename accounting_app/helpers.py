from django.db.models import Sum, F


def get_actuals_for_month(project, month, year):
    from accounting_app.models import JournalItem, InvoiceItem
    expenses = JournalItem.objects.filter(
        project=project,
        entry__date__year=year,
        entry__date__month=month
    ).aggregate(total=Sum('debit'))['total'] or 0

    income = InvoiceItem.objects.filter(
        invoice__project=project,
        invoice__date__year=year,
        invoice__date__month=month
    ).aggregate(total=Sum(F('quantity') * F('unit_price')))['total'] or 0

    return {'income': income, 'expenses': expenses}
