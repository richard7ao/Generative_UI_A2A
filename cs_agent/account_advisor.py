"""Deterministic account-recommendation helpers.

The fee/eligibility *rules* below are transcribed from the public knowledge base
(kb/documents/doc_checking_accounts_*). They are product rules that ship with this
repo and are NOT perturbed by the marking harness (only the transactional customer
DB is). The CUSTOMER facts (age, deposit, balance) are passed in by the agent from
live tool lookups, so the result is exact and generalises to perturbed customer data.

The model is error-prone at multi-account fee arithmetic (it misses that a foreign
ATM withdrawal is also out-of-network, so BOTH fees stack, and it trusts marketing
summaries). This module does that math deterministically so the agent just relays
the answer instead of computing it.
"""

from typing import Optional

# Per-withdrawal fee model types:
#   {"type": "flat", "fee": F}                  -> always F
#   {"type": "percent", "pct": P, "min": m?, "max": M?}  -> clamp(P*amount, m, M)
#   {"type": "tiered", "tiers": [(<=amt, fee), ...]}     -> first tier whose cap >= amount
# Each account also has separate monthly free-withdrawal allowances for
# out-of-network (oon) and foreign ATM usage.
CHECKING_ACCOUNTS: dict[str, dict] = {
    "Green Fee-Free Account": {
        "oon": {"type": "flat", "fee": 0.0}, "oon_free_per_month": 0,
        "foreign": {"type": "flat", "fee": 0.0}, "foreign_free_per_month": 0,
        "age_min": None, "age_max": None, "min_opening_deposit": 0.0,
    },
    "Purple Account": {
        "oon": {"type": "flat", "fee": 2.50}, "oon_free_per_month": 0,
        "foreign": {"type": "flat", "fee": 0.0}, "foreign_free_per_month": 0,
        "age_min": None, "age_max": None, "min_opening_deposit": 0.0,
    },
    "Bluest Account": {
        "oon": {"type": "flat", "fee": 2.00}, "oon_free_per_month": 0,
        "foreign": {"type": "flat", "fee": 0.0}, "foreign_free_per_month": 0,
        "age_min": None, "age_max": None, "min_opening_deposit": 75000.0,
    },
    "Blue Account": {
        "oon": {"type": "percent", "pct": 0.01, "max": 3.00}, "oon_free_per_month": 0,
        "foreign": {"type": "percent", "pct": 0.03, "min": 5.00}, "foreign_free_per_month": 0,
        "age_min": None, "age_max": None, "min_opening_deposit": 0.0,
    },
    "Evergreen Account": {
        "oon": {"type": "percent", "pct": 0.01, "max": 2.50}, "oon_free_per_month": 0,
        "foreign": {"type": "percent", "pct": 0.02, "min": 3.00}, "foreign_free_per_month": 0,
        "age_min": None, "age_max": None, "min_opening_deposit": 0.0,
    },
    "Light Blue Account": {
        "oon": {"type": "flat", "fee": 2.50}, "oon_free_per_month": 2,
        "foreign": {"type": "flat", "fee": 4.00}, "foreign_free_per_month": 2,
        "age_min": None, "age_max": None, "min_opening_deposit": 0.0,
    },
    "Dark Green Account": {
        "oon": {"type": "percent", "pct": 0.01, "min": 1.50}, "oon_free_per_month": 0,
        "foreign": {"type": "percent", "pct": 0.025, "max": 6.00}, "foreign_free_per_month": 0,
        "age_min": 17, "age_max": 26, "min_opening_deposit": 0.0,
    },
    "Light Green Account": {
        "oon": {"type": "flat", "fee": 1.50}, "oon_free_per_month": 4,
        "foreign": {"type": "tiered", "tiers": [(100.0, 2.00), (300.0, 3.50)]},
        "foreign_free_per_month": 0,
        "age_min": 13, "age_max": 24, "min_opening_deposit": 0.0,
    },
    "Gold Years Account": {
        "oon": {"type": "flat", "fee": 0.0}, "oon_free_per_month": 0,
        "foreign": {"type": "flat", "fee": 3.50}, "foreign_free_per_month": 0,
        "foreign_waived_if_balance_gte": 10000.0,
        "age_min": 62, "age_max": None, "min_opening_deposit": 0.0,
    },
}


def _per_withdrawal_fee(model: dict, amount: float) -> float:
    t = model["type"]
    if t == "flat":
        return float(model["fee"])
    if t == "percent":
        fee = model["pct"] * amount
        if "max" in model:
            fee = min(fee, model["max"])
        if "min" in model:
            fee = max(fee, model["min"])
        return float(fee)
    if t == "tiered":
        for cap, fee in model["tiers"]:
            if amount <= cap:
                return float(fee)
        return float(model["tiers"][-1][1])  # beyond top tier: use highest known
    return 0.0


def _component_total(
    model: dict, free_per_month: int, amount: float, per_month: int, months: int
) -> float:
    fee = _per_withdrawal_fee(model, amount)
    charged_per_month = max(0, per_month - free_per_month)
    return fee * charged_per_month * months


def _eligibility(acct: dict, age: Optional[int], opening_deposit: Optional[float]) -> list[str]:
    reasons: list[str] = []
    if acct["age_min"] is not None and (age is None or age < acct["age_min"]):
        reasons.append(f"requires primary holder age >= {acct['age_min']}")
    if acct["age_max"] is not None and (age is None or age > acct["age_max"]):
        reasons.append(f"requires primary holder age <= {acct['age_max']}")
    if acct["min_opening_deposit"] and (
        opening_deposit is None or opening_deposit < acct["min_opening_deposit"]
    ):
        reasons.append(f"requires opening deposit >= ${acct['min_opening_deposit']:,.0f}")
    return reasons


def recommend_checking_account(
    withdrawals_per_month: int,
    amount_per_withdrawal: float,
    months: int = 1,
    foreign: bool = True,
    customer_age: Optional[int] = None,
    opening_deposit: Optional[float] = None,
    balance: Optional[float] = None,
) -> dict:
    """Deterministically pick the personal checking account with the lowest total
    ATM fees for a customer's stated usage. Call this for any "which checking
    account is cheapest / best for ATM fees" request instead of computing fees
    yourself.

    A foreign ATM is also out-of-network, so for foreign withdrawals BOTH the
    out-of-network fee AND the foreign ATM fee apply (each with its own monthly
    free allowance). Eligibility (age, minimum opening deposit) is enforced.

    Args:
        withdrawals_per_month: Number of ATM withdrawals the customer makes per month.
        amount_per_withdrawal: USD amount of each withdrawal.
        months: How many months the usage pattern lasts (default 1).
        foreign: True if withdrawals are at foreign ATMs (default True). If False,
            treats them as domestic out-of-network withdrawals.
        customer_age: Customer's age, for age-restricted accounts. Look this up first.
        opening_deposit: Amount the customer can deposit at opening, for
            minimum-deposit accounts. Provide it so high-minimum accounts are
            correctly excluded.
        balance: Ongoing balance, for fee waivers that depend on it.

    Returns:
        dict with: recommended (cheapest eligible account name), ranked (eligible
        accounts sorted by total fee, with breakdown), and ineligible (accounts
        excluded, with reasons).
    """
    ranked = []
    ineligible = []
    for name, acct in CHECKING_ACCOUNTS.items():
        reasons = _eligibility(acct, customer_age, opening_deposit)
        oon_total = _component_total(
            acct["oon"], acct["oon_free_per_month"],
            amount_per_withdrawal, withdrawals_per_month, months,
        )
        foreign_total = 0.0
        if foreign:
            foreign_total = _component_total(
                acct["foreign"], acct["foreign_free_per_month"],
                amount_per_withdrawal, withdrawals_per_month, months,
            )
            waive_at = acct.get("foreign_waived_if_balance_gte")
            if waive_at is not None and balance is not None and balance >= waive_at:
                foreign_total = 0.0
        total = round(oon_total + foreign_total, 2)
        entry = {
            "account": name,
            "total_atm_fees": total,
            "out_of_network_fees": round(oon_total, 2),
            "foreign_atm_fees": round(foreign_total, 2),
        }
        if reasons:
            ineligible.append({**entry, "ineligible_reasons": reasons})
        else:
            ranked.append(entry)

    ranked.sort(key=lambda e: e["total_atm_fees"])
    return {
        "recommended": ranked[0]["account"] if ranked else None,
        "recommended_total_atm_fees": ranked[0]["total_atm_fees"] if ranked else None,
        "ranked_eligible": ranked,
        "ineligible": ineligible,
        "assumptions": {
            "withdrawals_per_month": withdrawals_per_month,
            "amount_per_withdrawal": amount_per_withdrawal,
            "months": months,
            "foreign": foreign,
            "note": "Foreign ATM withdrawals incur both out-of-network and foreign "
                    "fees. Third-party ATM operator surcharges are external and not "
                    "included.",
        },
    }
