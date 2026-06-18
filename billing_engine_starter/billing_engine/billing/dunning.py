"""
DunningProcess — finite state machine for failed-payment retries.

States:
    PENDING       (initial)  →  RETRYING  on first failure
    RETRYING      ──→ SUCCEEDED    when a retry succeeds
                  ──→ FAILED_FINAL after 3 total failures
    SUCCEEDED     (terminal)
    FAILED_FINAL  (terminal — also flips subscription to PAST_DUE)

Retry schedule:
    attempt 2 scheduled at  now + 1 day
    attempt 3 scheduled at  now + 3 days
    (no attempt 4 — after the 3rd failure we mark FAILED_FINAL)

After the subscription has been PAST_DUE for 7 days with no recovery,
the BillingCycle.run (Day 2 work) may flip it to CANCELLED — that
transition does NOT live in this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

from billing_engine.db import (
    InvoiceRepository, LedgerRepository, SubscriptionRepository,
    PaymentAttemptRepository,
)
from billing_engine.models import Invoice, LedgerEntry, LedgerDirection, SubscriptionStatus
from billing_engine.payments.gateway import PaymentGateway, PaymentResult


class DunningState(str, Enum):
    PENDING = "PENDING"
    RETRYING = "RETRYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED_FINAL = "FAILED_FINAL"


@dataclass(frozen=True)
class DunningOutcome:
    state: DunningState
    attempt_no: int
    next_retry_at: Optional[datetime]


# Retry intervals (in days) after each failure, indexed by attempt_no JUST COMPLETED.
# After failure of attempt 1, schedule attempt 2 at +1 day.
# After failure of attempt 2, schedule attempt 3 at +3 days.
# After failure of attempt 3, no more retries → FAILED_FINAL.
RETRY_DELAYS_DAYS = {1: 1, 2: 3}
MAX_ATTEMPTS = 3


class DunningProcess:
    def __init__(
        self,
        gateway: PaymentGateway,
        invoice_repo: InvoiceRepository,
        ledger_repo: LedgerRepository,
        subscription_repo: SubscriptionRepository,
        attempt_repo: PaymentAttemptRepository,
    ) -> None:
        self.gateway = gateway
        self.invoice_repo = invoice_repo
        self.ledger_repo = ledger_repo
        self.subscription_repo = subscription_repo
        self.attempt_repo = attempt_repo

    def attempt(self, invoice: Invoice, customer_id: int, now: datetime) -> DunningOutcome:
        """Try once. Record the attempt. Return the resulting outcome."""
        # TODO Day 4
        with self.invoice_repo.db.conn as conn:
            # 1. Check if invoice is already SUCCEEDED or FAILED_FINAL
            if invoice.status in [DunningState.SUCCEEDED, DunningState.FAILED_FINAL]:
                raise ValueError(f"Invoice {invoice.id} is already in terminal state {invoice.status}")

            # 2. Determine the attempt number
            attempt_no = self.attempt_repo.count_attempts(conn, invoice.id) + 1

            # 3. Attempt payment via gateway
            payment_result = self.gateway.charge(invoice, customer_id)

            # 4. Record the attempt in the database
            self.attempt_repo.record_attempt(conn, invoice.id, now, payment_result)

            # 5. Update invoice status based on payment result
            if payment_result.success:
                new_state = DunningState.SUCCEEDED
                next_retry_at = None
                self.invoice_repo.update_status(conn, invoice.id, new_state)
                self.subscription_repo.update_status(conn, invoice.subscription_id, SubscriptionStatus.ACTIVE)
            else:
                if attempt_no >= MAX_ATTEMPTS:
                    new_state = DunningState.FAILED_FINAL
                    next_retry_at = None
                    self.invoice_repo.update_status(conn, invoice.id, new_state)
                    self.subscription_repo.update_status(conn, invoice.subscription_id, SubscriptionStatus.PAST_DUE)
                else:
                    new_state = DunningState.RETRYING
                    next_retry_at = now + timedelta(days=RETRY_DELAYS_DAYS[attempt_no])
                    self.invoice_repo.update_status(conn, invoice.id, new_state)

            return DunningOutcome(state=new_state, attempt_no=attempt_no, next_retry_at=next_retry_at)
    
    # --------------------------------------------------------
    @staticmethod
    def should_cancel(past_due_since: date, today: date, grace_days: int = 7) -> bool:
        """Helper used by BillingCycle to decide PAST_DUE → CANCELLED."""
        # TODO Day 4
        with self.invoice_repo.db.conn as conn:
            # Calculate the number of days past due
            days_past_due = (today - past_due_since).days
            return days_past_due >= grace_days
