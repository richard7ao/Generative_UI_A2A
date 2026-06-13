"""Unit tests for the deterministic checking-account fee comparator.

The expected per-account totals are the oracle documented in task_001's notes:
18 foreign withdrawals of $350 (6/month for 3 months), customer age 31.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cs_agent.account_advisor import recommend_checking_account


def _all_totals(result):
    t = {e["account"]: e["total_atm_fees"] for e in result["ranked_eligible"]}
    t.update({e["account"]: e["total_atm_fees"] for e in result["ineligible"]})
    return t


class TestTask001Oracle:
    """Engine must reproduce task_001's documented per-account fee totals."""

    def setup_method(self):
        self.r = recommend_checking_account(
            withdrawals_per_month=6,
            amount_per_withdrawal=350.0,
            months=3,
            foreign=True,
            customer_age=31,
            opening_deposit=6300.0,
        )
        self.t = _all_totals(self.r)

    def test_recommends_green_fee_free_at_zero(self):
        assert self.r["recommended"] == "Green Fee-Free Account"
        assert self.r["recommended_total_atm_fees"] == 0.0

    def test_per_account_totals_match_oracle(self):
        assert self.t["Green Fee-Free Account"] == 0.0
        assert self.t["Purple Account"] == 45.0
        assert self.t["Bluest Account"] == 36.0
        assert self.t["Light Blue Account"] == 78.0
        assert self.t["Evergreen Account"] == 171.0
        assert self.t["Blue Account"] == 243.0

    def test_age_restricted_excluded_for_adult(self):
        inelig = {e["account"] for e in self.r["ineligible"]}
        assert "Gold Years Account" in inelig   # 62+
        assert "Light Green Account" in inelig   # 13-24
        assert "Dark Green Account" in inelig    # 17-26

    def test_bluest_excluded_by_min_deposit(self):
        inelig = {e["account"] for e in self.r["ineligible"]}
        assert "Bluest Account" in inelig  # requires $75k opening deposit

    def test_purple_is_not_recommended(self):
        # The whole point: Purple looks travel-friendly but loses to Green Fee-Free.
        assert self.r["recommended"] != "Purple Account"


class TestFeeModel:
    def test_free_allowance_zeroes_small_usage(self):
        # Light Blue: 2 free OON + 2 free foreign per month covers 2 withdrawals.
        r = recommend_checking_account(2, 100.0, months=1, foreign=True, customer_age=30, opening_deposit=1000)
        lb = next(e for e in r["ranked_eligible"] if e["account"] == "Light Blue Account")
        assert lb["total_atm_fees"] == 0.0

    def test_domestic_only_skips_foreign_fee(self):
        r = recommend_checking_account(10, 200.0, months=1, foreign=False, customer_age=30, opening_deposit=1000)
        purple = next(e for e in r["ranked_eligible"] if e["account"] == "Purple Account")
        assert purple["foreign_atm_fees"] == 0.0
        assert purple["out_of_network_fees"] == 25.0  # 10 x $2.50

    def test_percent_fee_caps_and_floors(self):
        # Evergreen OON: 1% of $600 = $6 capped at $2.50; foreign 2% of $600 = $12 (min $3 n/a).
        r = recommend_checking_account(1, 600.0, months=1, foreign=True, customer_age=40, opening_deposit=1000)
        ev = next(e for e in r["ranked_eligible"] if e["account"] == "Evergreen Account")
        assert ev["out_of_network_fees"] == 2.50
        assert ev["foreign_atm_fees"] == 12.0

    def test_gold_years_foreign_waiver_with_balance(self):
        r = recommend_checking_account(5, 200.0, months=1, foreign=True, customer_age=65, balance=15000)
        gy = next(e for e in r["ranked_eligible"] if e["account"] == "Gold Years Account")
        assert gy["foreign_atm_fees"] == 0.0  # waived at balance >= $10k
