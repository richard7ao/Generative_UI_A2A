"""Mock LLM for testing without Google API.

This module provides a fallback when Google API is unavailable.
"""

import json
import random

# Pre-defined responses for common queries
MOCK_RESPONSES = {
    "hours": "Our business hours are:\n\nMonday-Friday: 9 AM - 5 PM EST\nSaturday: 10 AM - 2 PM EST\nSunday: Closed\n\nPhone support is available during these hours. Online banking is available 24/7.",
    
    "balance": "I can help you check your balance. To proceed, I'll need to verify your identity first. Could you please provide:\n\n1. Your account number\n2. Your date of birth\n3. The last 4 digits of your Social Security Number\n\nOnce verified, I can provide your current balance and recent transactions.",
    
    "overdraft": "Overdraft fees are $35 per transaction when your account balance goes negative. However, you may be eligible for overdraft protection.\n\nKey points:\n- $35 fee per overdraft\n- Maximum 4 fees per day\n- Overdraft protection available\n- You can opt out of overdraft coverage\n\nWould you like me to help you set up overdraft protection or review your options?",
    
    "dispute": "To dispute a transaction, follow these steps:\n\n1. **Contact the merchant first** - Many issues can be resolved directly\n2. **Gather documentation** - Receipts, emails, proof of return\n3. **File a dispute** - Call us at 1-800-555-BANK or visit a branch\n4. **Timeline** - Most disputes resolved within 10 business days\n\nImportant: Disputes must be filed within 60 days of the transaction date.",
    
    "referral": "Our referral program offers great rewards!\n\n**Current Offer:**\n- You earn: $50 per successful referral\n- Your friend gets: $25 welcome bonus\n- Maximum: 10 referrals per year ($500 total)\n\n**How it works:**\n1. Share your unique referral code\n2. Friend opens a qualifying account\n3. Both bonuses credited within 30 days\n\nWould you like me to look up your referral code?",
    
    "policy": "I can research our policies for you. What specific area are you interested in?\n\n- Account policies\n- Fee schedules\n- Overdraft policies\n- Security policies\n- Privacy policies\n- Dispute procedures\n\nPlease let me know which policy you'd like to review.",
    
    "default": "Thank you for your question. I'm here to help with:\n\n- Account inquiries\n- Transaction questions\n- Policy information\n- Technical support\n- General banking questions\n\nHow can I assist you today?"
}

def mock_generate_content(prompt: str, model: str = "gemini-3.5-flash") -> str:
    """Generate a mock response based on prompt keywords."""
    prompt_lower = prompt.lower()
    
    # Check for keywords
    if any(word in prompt_lower for word in ["hour", "open", "close", "time"]):
        return MOCK_RESPONSES["hours"]
    elif any(word in prompt_lower for word in ["balance", "how much", "money", "fund"]):
        return MOCK_RESPONSES["balance"]
    elif any(word in prompt_lower for word in ["overdraft", "nsf", "negative"]):
        return MOCK_RESPONSES["overdraft"]
    elif any(word in prompt_lower for word in ["dispute", "fraud", "unauthorized", "charge"]):
        return MOCK_RESPONSES["dispute"]
    elif any(word in prompt_lower for word in ["referral", "refer", "invite", "friend"]):
        return MOCK_RESPONSES["referral"]
    elif any(word in prompt_lower for word in ["policy", "rule", "regulation", "term"]):
        return MOCK_RESPONSES["policy"]
    else:
        return MOCK_RESPONSES["default"]

def is_mock_mode() -> bool:
    """Check if we should use mock mode (when Google API fails)."""
    import os
    return os.environ.get("MOCK_LLM", "false").lower() == "true"
