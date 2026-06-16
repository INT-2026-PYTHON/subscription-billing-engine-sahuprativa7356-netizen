"""
UsageBased — pay per unit consumed.

Example: ₹0.50 per API call. Customer makes 1200 calls => charge = ₹600.
"""

from billing_engine.money import Money
from billing_engine.pricing.base import PricingStrategy


class UsageBased(PricingStrategy):
    """Charges `unit_price * quantity`."""

    def __init__(self, unit_price: Money) -> None:
       if unit_price.is_negative():
            raise ValueError("unit price must be non-negative")
        
    def calculate(self, quantity: int) -> Money:
        
        if quantity < 0:
            raise ValueError("quantity must be non-negative")
        return self.unit_price * quantity

