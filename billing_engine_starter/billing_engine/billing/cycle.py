"""
BillingCycle — finds due subscriptions, generates invoices, posts ledger DEBITs,
advances the subscription period. Must be IDEMPOTENT (safe to run twice).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional

from billing_engine.db import (
    Database,
    CustomerRepository, PlanRepository, SubscriptionRepository,
    UsageRecordRepository, InvoiceRepository, InvoiceLineItemRepository,
    LedgerRepository,
)
from billing_engine.models import Subscription


@dataclass
class BillingResult:
    invoices_created: int
    invoices_skipped_duplicate: int
    trials_activated: int


class BillingCycle:
    """Day-3 deliverable. Day-4 stretch: add `upgrade_subscription(...)`."""

    def __init__(
        self,
        db: Database,
        customer_repo: CustomerRepository,
        plan_repo: PlanRepository,
        subscription_repo: SubscriptionRepository,
        usage_repo: UsageRecordRepository,
        invoice_repo: InvoiceRepository,
        line_item_repo: InvoiceLineItemRepository,
        ledger_repo: LedgerRepository,
        strategy_factory: Callable,    # given a Plan, returns a PricingStrategy
        discount_factory: Callable,    # given a discount_id or None, returns a Discount or None
        tax_factory: Callable,         # given a Customer, returns (TaxCalculator, TaxContext)
    ) -> None:
        self.db = db
        self.customer_repo = customer_repo
        self.plan_repo = plan_repo
        self.subscription_repo = subscription_repo
        self.usage_repo = usage_repo
        self.invoice_repo = invoice_repo
        self.line_item_repo = line_item_repo
        self.ledger_repo = ledger_repo
        self.strategy_factory = strategy_factory
        self.discount_factory = discount_factory
        self.tax_factory = tax_factory

    # --------------------------------------------------------
    def run(self, as_of: date) -> BillingResult:
        """Bill all subscriptions whose current period ends on or before `as_of`."""
        # TODO Day 3
        with self.db.conn as conn:
            subscriptions = self.subscription_repo.find_due_subscriptions(conn, as_of)
            invoices_created = 0
            invoices_skipped_duplicate = 0
            trials_activated = 0

            for subscription in subscriptions:
                if subscription.status == "trialing":
                    # Activate trial
                    subscription.status = "active"
                    self.subscription_repo.update(conn, subscription)
                    trials_activated += 1
                else:
                    # Generate invoice
                    invoice = self.generate_invoice(conn, subscription)
                    if invoice:
                        invoices_created += 1
                    else:
                        invoices_skipped_duplicate += 1

            return BillingResult(
                invoices_created=invoices_created,
                invoices_skipped_duplicate=invoices_skipped_duplicate,
                trials_activated=trials_activated
            )

    # --------------------------------------------------------
    def upgrade_subscription(self, subscription_id: int, new_plan_id: int, switch_date: date) -> None:
        """Mid-cycle upgrade — Day 4 stretch."""
        # TODO Day 4
        with self.db.conn as conn:
            subscription = self.subscription_repo.get(conn, subscription_id)
            if not subscription:
                raise ValueError(f"Subscription with id {subscription_id} not found.")

            new_plan = self.plan_repo.get(conn, new_plan_id)
            if not new_plan:
                raise ValueError(f"Plan with id {new_plan_id} not found.")

            # Update the subscription to the new plan
            subscription.plan_id = new_plan_id
            self.subscription_repo.update(conn, subscription)

            # Generate a prorated invoice for the remaining period
            invoice = self.generate_invoice(conn, subscription, switch_date)
            if invoice:
                print(f"Generated prorated invoice: {invoice.id}")
            
