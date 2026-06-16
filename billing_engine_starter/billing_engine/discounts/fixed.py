"""
FixedAmountDiscount — e.g., flat ₹500 off.

CAPPING RULE: if the fixed amount exceeds the subtotal, return subtotal
(so the discounted total never goes below zero).
"""

from billing_engine.money import Money
from billing_engine.discounts.base import Discount, DiscountContext


class FixedAmountDiscount(Discount):
    def __init__(self, amount: Money) -> None:
        if not isinstance(amount, Money):
            raise TypeError("amount must be an instance of Money")
        if amount.is_negative():
            raise ValueError("amount must be non-negative")
        self.amount=amount

    def apply(self, subtotal: Money, context: DiscountContext) -> Money:
        # TODO Day 1
        if subtotal.is_negative():
            raise ValueError("subtotal cannot be negative")
        discount_amount = min(self.amount, subtotal)
        return discount_amount
