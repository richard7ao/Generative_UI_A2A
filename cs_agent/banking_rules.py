"""Deterministic banking-rule checkers (council-driven v1).

These encode STABLE product/policy rules from the public knowledge base so the
model stops deciding eligibility/sequencing in free-form reasoning (where
gemini-3.5-flash drops gates and trusts customers). The model supplies live
customer facts (read from env tools); these functions return the deterministic
verdict. Rules are transcribed from kb/documents and are NOT perturbed by the
marking harness (only customer data is), so the verdicts generalise.

Scope (v1): the highest-frequency trap classes — dispute provisional-credit
eligibility + per-tier limits, credit-card closure eligibility, personal/business
savings eligibility (incl. checking-tenure), business-checking eligibility, and
operation sequencing for the documented cross-action dependencies. This is not
the entire KB; unknown rules should still be looked up in the KB.
"""

from typing import Optional

# --- Credit-card tiers (kb: provisional-credit + replacement-shipping docs) ---
CARD_TIERS: dict[str, str] = {
    "Bronze Rewards Card": "Entry",
    "EcoCard": "Entry",
    "Business Bronze Rewards Card": "Entry",
    "Crypto-Cash Back Card": "Entry",
    "Silver Rewards Card": "Mid",
    "Business Silver Rewards Card": "Mid",
    "Green Rewards Card": "Mid",
    "Silver Zoom Card": "Mid",
    "Gold Rewards Card": "Premium",
    "Business Gold Rewards Card": "Premium",
    "Platinum Rewards Card": "Elite",
    "Business Platinum Rewards Card": "Elite",
    "Diamond Elite Card": "Invitation",
}

# kb: "Maximum Provisional Credit Limits by Card Tier"
DISPUTE_TIER_MAX: dict[str, float] = {
    "Entry": 2500.0,
    "Mid": 5000.0,
    "Premium": 10000.0,
    "Elite": 15000.0,
    "Invitation": 25000.0,
}

# kb: provisional-credit "Eligibility Criteria" — reason categories
_FRAUD_REASON = "unauthorized_fraudulent_charge"
DISPUTE_ELIGIBLE_REASONS = {
    _FRAUD_REASON,
    "duplicate_charge",
    "goods_services_not_received",  # only if purchase > 30 days ago
}


def _tier_of(card_tier_or_name: str) -> Optional[str]:
    if card_tier_or_name in DISPUTE_TIER_MAX:
        return card_tier_or_name
    return CARD_TIERS.get(card_tier_or_name)


def check_dispute_eligibility(
    dispute_reason: str,
    amount: float,
    card_tier_or_name: str,
    account_open_days: int,
    disputes_last_12_months: int,
    contacted_merchant: bool = False,
    purchase_age_days: Optional[int] = None,
) -> dict:
    """Decide if a credit-card transaction dispute qualifies for provisional credit.

    Use this before filing a dispute / promising a provisional credit. All criteria
    must hold (kb provisional-credit policy). Returns {eligible, reasons, tier,
    tier_max}.

    Args:
        dispute_reason: e.g. 'unauthorized_fraudulent_charge', 'duplicate_charge',
            'goods_services_not_received', 'incorrect_amount', etc.
        amount: disputed transaction amount in USD.
        card_tier_or_name: the card's tier ('Entry'...) or exact card name.
        account_open_days: how long the credit-card account has been open.
        disputes_last_12_months: number of disputes filed in the past 12 months.
        contacted_merchant: whether the customer tried the merchant first
            (required for all non-fraud reasons).
        purchase_age_days: age of the purchase (required for
            'goods_services_not_received', which needs > 30 days).
    """
    reasons: list[str] = []
    tier = _tier_of(card_tier_or_name)
    tier_max = DISPUTE_TIER_MAX.get(tier) if tier else None

    if account_open_days < 60:
        reasons.append("account must be open at least 60 days")
    if dispute_reason not in DISPUTE_ELIGIBLE_REASONS:
        reasons.append(f"reason '{dispute_reason}' is not eligible for provisional credit")
    elif dispute_reason == "goods_services_not_received" and (
        purchase_age_days is None or purchase_age_days <= 30
    ):
        reasons.append("goods_services_not_received requires the purchase be > 30 days old")
    if amount < 25.0:
        reasons.append("amount must be at least $25.00")
    if tier_max is None:
        reasons.append(f"unknown card tier for '{card_tier_or_name}'")
    elif amount > tier_max:
        reasons.append(f"amount exceeds {tier} tier max of ${tier_max:,.0f}")
    if disputes_last_12_months > 2:
        reasons.append("customer has already filed more than 2 disputes in the past 12 months")
    if dispute_reason != _FRAUD_REASON and not contacted_merchant:
        reasons.append("non-fraud disputes require the customer to contact the merchant first")

    return {"eligible": not reasons, "reasons": reasons, "tier": tier, "tier_max": tier_max}


def check_card_closure_eligibility(
    outstanding_balance: float,
    has_pending_dispute: bool,
    account_open_days: int,
    has_pending_replacement_card: bool = False,
) -> dict:
    """Decide if a credit-card account can be closed (kb closure policy).

    Verify the SYSTEM state with tools first — do not trust the customer's claim
    of "no disputes"/"zero balance".
    """
    reasons: list[str] = []
    if outstanding_balance != 0:
        reasons.append(f"outstanding balance must be $0.00 (currently ${outstanding_balance:,.2f})")
    if has_pending_dispute:
        reasons.append("account has a pending/active dispute (must resolve first)")
    if account_open_days < 60:
        reasons.append("account must be at least 60 days old")
    if has_pending_replacement_card:
        reasons.append("a pending replacement card must arrive/settle first")
    return {"eligible": not reasons, "reasons": reasons}


def check_savings_eligibility(
    kind: str,
    has_open_checking: bool,
    checking_tenure_days: int,
    existing_savings_count: int,
    has_negative_or_collections: bool,
    checking_balance: Optional[float] = None,
) -> dict:
    """Decide if a savings account can be opened (kb savings-opening procedures).

    Args:
        kind: 'personal' or 'business'.
        has_open_checking: customer has >= 1 OPEN checking of the matching type.
        checking_tenure_days: age of the qualifying checking account.
        existing_savings_count: how many savings accounts (of that type) exist.
        has_negative_or_collections: any account negative / in collections.
        checking_balance: balance of the qualifying checking (business needs >= $2,500).
    """
    reasons: list[str] = []
    kind = kind.lower()
    if not has_open_checking:
        reasons.append(f"needs at least one OPEN {kind} checking account")
    if has_negative_or_collections:
        reasons.append("no accounts may be negative or in collections")
    if kind == "personal":
        if checking_tenure_days < 14:
            reasons.append("checking account must have been open at least 14 days")
        if existing_savings_count >= 5:
            reasons.append("already at the max of 5 personal savings accounts")
    elif kind == "business":
        if checking_tenure_days < 30:
            reasons.append("business checking must have been open at least 30 days")
        if existing_savings_count >= 4:
            reasons.append("already at the max of 4 business savings accounts")
        if checking_balance is not None and checking_balance < 2500:
            reasons.append("business checking balance must be at least $2,500")
    else:
        reasons.append(f"unknown savings kind '{kind}'")
    return {"eligible": not reasons, "reasons": reasons}


def check_business_checking_eligibility(
    has_open_personal_checking: bool,
    has_any_closed_account: bool,
    existing_business_checking_count: int,
    personal_checking_balance: Optional[float] = None,
) -> dict:
    """Decide if a business checking account can be opened (kb business-checking
    procedure). Note the trap: it requires NO accounts with status CLOSED, so any
    closure must happen AFTER opening it.
    """
    reasons: list[str] = []
    if not has_open_personal_checking:
        reasons.append("needs at least one OPEN personal checking account")
    if has_any_closed_account:
        reasons.append("customer must have NO accounts with status CLOSED (open business checking before any closures)")
    if existing_business_checking_count > 6:
        reasons.append("cannot exceed 6 business checking accounts")
    if personal_checking_balance is not None and personal_checking_balance < 500:
        reasons.append("existing checking balance must be at least $500")
    return {"eligible": not reasons, "reasons": reasons}


# Operation sequencing: ops that get BLOCKED by another op's side effect must run
# first. Lower priority = earlier. (kb dependencies: business checking needs no
# CLOSED accounts; personal savings needs an OPEN >=14d checking; CLI and card
# closure both need NO pending dispute, so they precede filing disputes.)
_OP_PRIORITY = {
    "open_business_checking": 0,   # needs no closed accounts -> before any close
    "open_personal_savings": 0,    # needs an open >=14d checking -> before closing it
    "open_business_savings": 0,
    "credit_limit_increase": 1,    # blocked by pending dispute -> before file_dispute
    "close_card": 1,               # blocked by pending dispute -> before file_dispute
    "open_account": 1,
    "close_account": 2,            # closures after opens that depend on no-closed/tenure
    "file_dispute": 3,             # disputes last (they block CLI/closure)
}


def plan_operation_order(operations: list[str]) -> dict:
    """Return a safe execution order for a multi-step request so no step makes a
    later step ineligible (kb cross-action dependencies). Pass the operation tags
    the customer asked for (any order); get back the order to execute them in.

    Recognised tags: open_business_checking, open_personal_savings,
    open_business_savings, open_account, credit_limit_increase, close_card,
    close_account, file_dispute.
    """
    indexed = list(enumerate(operations))
    ordered = sorted(indexed, key=lambda p: (_OP_PRIORITY.get(p[1], 1), p[0]))
    safe = [op for _, op in ordered]
    reordered = safe != list(operations)
    notes = []
    if reordered:
        notes.append("Reordered so dependent steps stay eligible (opens before closures; "
                     "credit-limit increase / card closure before filing disputes).")
    unknown = [op for op in operations if op not in _OP_PRIORITY]
    if unknown:
        notes.append(f"Unrecognised operations (kept in place, verify manually): {unknown}")
    return {"execution_order": safe, "reordered": reordered, "notes": notes}
