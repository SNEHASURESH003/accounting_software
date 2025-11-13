# utils/payroll_math.py
from decimal import Decimal, ROUND_HALF_UP

def q(n):  # safe Decimal
    return (n if isinstance(n, Decimal) else Decimal(str(n or 0)))

def contractor_breakup(basic, other_allowances, ot_hours, ot_rate, tds_rate=Decimal('0.10')):
    basic = q(basic)
    other_allowances = q(other_allowances)
    ot_hours = q(ot_hours)
    ot_rate = q(ot_rate)
    tds_rate = q(tds_rate)

    overtime = (ot_hours * ot_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    gross = (basic + other_allowances + overtime).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    tds = (gross * tds_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    net = (gross - tds).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        "overtime": overtime,
        "gross": gross,         # use this as ContractorPayment.amount
        "tds": tds,
        "net": net
    }
