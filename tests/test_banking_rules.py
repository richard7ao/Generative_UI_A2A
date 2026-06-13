"""Unit tests for the deterministic banking-rule checkers.

Rules are grounded in kb/documents; scenarios mirror the documented task traps.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cs_agent.banking_rules import (
    check_dispute_eligibility,
    check_card_closure_eligibility,
    check_savings_eligibility,
    check_business_checking_eligibility,
    plan_operation_order,
)


class TestDisputeEligibility:
    def test_clean_fraud_dispute_eligible(self):
        r = check_dispute_eligibility(
            "unauthorized_fraudulent_charge", 500.0, "Silver Rewards Card",
            account_open_days=200, disputes_last_12_months=0,
        )
        assert r["eligible"] is True
        assert r["tier"] == "Mid" and r["tier_max"] == 5000.0

    def test_amount_over_tier_max_rejected(self):
        r = check_dispute_eligibility(
            "duplicate_charge", 3000.0, "Bronze Rewards Card",  # Entry max $2500
            account_open_days=200, disputes_last_12_months=0,
        )
        assert r["eligible"] is False
        assert any("tier max" in x for x in r["reasons"])

    def test_account_too_new_rejected(self):
        r = check_dispute_eligibility(
            "unauthorized_fraudulent_charge", 100.0, "Gold Rewards Card",
            account_open_days=30, disputes_last_12_months=0,
        )
        assert r["eligible"] is False
        assert any("60 days" in x for x in r["reasons"])

    def test_too_many_prior_disputes_rejected(self):
        r = check_dispute_eligibility(
            "duplicate_charge", 100.0, "Silver Rewards Card",
            account_open_days=200, disputes_last_12_months=3, contacted_merchant=True,
        )
        assert r["eligible"] is False
        assert any("more than 2 disputes" in x for x in r["reasons"])

    def test_nonfraud_requires_merchant_contact(self):
        r = check_dispute_eligibility(
            "duplicate_charge", 100.0, "Silver Rewards Card",
            account_open_days=200, disputes_last_12_months=0, contacted_merchant=False,
        )
        assert r["eligible"] is False
        assert any("merchant" in x for x in r["reasons"])

    def test_ineligible_reason_category(self):
        r = check_dispute_eligibility(
            "incorrect_amount", 100.0, "Silver Rewards Card",
            account_open_days=200, disputes_last_12_months=0, contacted_merchant=True,
        )
        assert r["eligible"] is False

    def test_gsr_requires_over_30_days(self):
        r = check_dispute_eligibility(
            "goods_services_not_received", 100.0, "Silver Rewards Card",
            account_open_days=200, disputes_last_12_months=0, contacted_merchant=True,
            purchase_age_days=10,
        )
        assert r["eligible"] is False


class TestCardClosure:
    def test_clean_closure_eligible(self):
        r = check_card_closure_eligibility(0.0, False, 200)
        assert r["eligible"] is True

    def test_outstanding_balance_blocks(self):
        r = check_card_closure_eligibility(125.0, False, 200)
        assert r["eligible"] is False  # task_007: $125 balance must be paid first

    def test_pending_dispute_blocks(self):
        r = check_card_closure_eligibility(0.0, True, 200)
        assert r["eligible"] is False  # task_014: user lies "no disputes"; system says otherwise


class TestSavingsEligibility:
    def test_personal_needs_14_day_checking(self):
        r = check_savings_eligibility("personal", has_open_checking=True,
                                      checking_tenure_days=10, existing_savings_count=0,
                                      has_negative_or_collections=False)
        assert r["eligible"] is False  # task_043: Blue checking only 10 days old

    def test_personal_ok_at_14_days(self):
        r = check_savings_eligibility("personal", has_open_checking=True,
                                      checking_tenure_days=120, existing_savings_count=1,
                                      has_negative_or_collections=False)
        assert r["eligible"] is True

    def test_business_needs_balance_and_tenure(self):
        r = check_savings_eligibility("business", has_open_checking=True,
                                      checking_tenure_days=40, existing_savings_count=0,
                                      has_negative_or_collections=False, checking_balance=1000.0)
        assert r["eligible"] is False  # balance < $2,500


class TestBusinessCheckingEligibility:
    def test_closed_account_blocks(self):
        r = check_business_checking_eligibility(has_open_personal_checking=True,
                                                has_any_closed_account=True,
                                                existing_business_checking_count=0,
                                                personal_checking_balance=1000.0)
        assert r["eligible"] is False  # task_070: must open BEFORE any closures
        assert any("CLOSED" in x for x in r["reasons"])

    def test_clean_eligible(self):
        r = check_business_checking_eligibility(True, False, 0, 1000.0)
        assert r["eligible"] is True


class TestSequencing:
    def test_cli_before_dispute(self):  # task_040
        r = plan_operation_order(["file_dispute", "credit_limit_increase"])
        assert r["execution_order"] == ["credit_limit_increase", "file_dispute"]
        assert r["reordered"] is True

    def test_open_savings_before_close(self):  # task_043
        r = plan_operation_order(["close_account", "open_personal_savings"])
        assert r["execution_order"] == ["open_personal_savings", "close_account"]

    def test_business_checking_before_closures(self):  # task_070
        r = plan_operation_order([
            "close_account", "open_business_checking", "close_account", "open_personal_savings",
        ])
        # all opens precede all closes
        order = r["execution_order"]
        assert order.index("open_business_checking") < order.index("close_account")
        assert order.index("open_personal_savings") < order.index("close_account")
