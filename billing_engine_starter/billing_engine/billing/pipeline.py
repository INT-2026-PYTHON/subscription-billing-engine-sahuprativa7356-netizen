"""
build_invoice — PURE function that turns inputs into an Invoice dataclass.

⚠️ NO database calls here. No `datetime.now()`. No PDF. Just math.

The order is FIXED:
    1. base       = strategy.calculate(usage)
    2. discount   = discount.apply(base) if discount else 0
    3. taxable    = base - discount
    4. tax        = tax_calc.apply(taxable)
    5. total      = taxable + tax.total
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from billing_engine.money import Money
from billing_engine.models import (
    Invoice, InvoiceStatus, InvoiceLineItem, LineItemKind, Subscription, Plan,
)
from billing_engine.pricing.base import PricingStrategy
from billing_engine.discounts.base import Discount, DiscountContext
from billing_engine.taxes.base import TaxCalculator, TaxContext


def build_invoice(
    subscription: Subscription,
    plan: Plan,
    strategy: PricingStrategy,
    discount: Optional[Discount],
    tax_calc: TaxCalculator,
    tax_context: TaxContext,
    usage_quantity: int,
    period_start: date,
    period_end: date,
    invoice_count_so_far: int,
) -> Invoice:
    """Pure function. Returns an Invoice (id=None, status=DRAFT) ready to be persisted."""
    # TODO Day 2
    base = strategy.calculate(usage_quantity)
    discount_amount = discount.apply(base, DiscountContext(invoice_count_so_far)) if discount else Money(0, base.currency)
    taxable = base - discount_amount
    tax = tax_calc.apply(taxable, tax_context)
    total = taxable + tax.total
    return Invoice(
        id=None,
        status=InvoiceStatus.DRAFT,
        subscription_id=subscription.id,
        plan_id=plan.id,
        base=base,
        discount=discount_amount,
        taxable=taxable,
        tax=tax.total,
        total=total,
        period_start=period_start,
        period_end=period_end
    )
