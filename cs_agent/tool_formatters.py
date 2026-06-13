"""Tool result formatters for cleaner agent responses.

Converts raw tool results into human-readable formats.
Based on pattern: Tool Result Synthesis Templates from model example.
"""

from typing import Any, Callable, Dict


class ToolFormatter:
    """Format tool results for better readability."""
    
    # Registry of formatters by tool name
    _formatters: Dict[str, Callable[[Any], str]] = {}
    
    @classmethod
    def register(cls, tool_name: str):
        """Decorator to register a formatter for a tool."""
        def decorator(func: Callable[[Any], str]):
            cls._formatters[tool_name] = func
            return func
        return decorator
    
    @classmethod
    def format(cls, tool_name: str, result: Any) -> str:
        """Format a tool result.
        
        Args:
            tool_name: Name of the tool
            result: Raw tool result
            
        Returns:
            Formatted string representation
        """
        if tool_name in cls._formatters:
            try:
                return cls._formatters[tool_name](result)
            except Exception as e:
                return f"[{tool_name} result formatting error: {e}. Raw: {str(result)[:200]}]"
        
        # Default: return as-is
        return str(result)


# ============================================================================
# Banking Tool Formatters
# ============================================================================

@ToolFormatter.register("get_account_balance")
def format_account_balance(result: Any) -> str:
    """Format account balance result."""
    if isinstance(result, dict):
        if result.get("error"):
            return f"Error retrieving balance: {result.get('content', 'Unknown error')}"
        
        data = result.get("content", {})
        if isinstance(data, dict):
            balance = data.get("balance", "N/A")
            account_type = data.get("account_type", "Unknown")
            return f"{account_type} Account Balance: ${balance}"
    return str(result)


@ToolFormatter.register("get_transaction_history")
def format_transaction_history(result: Any) -> str:
    """Format transaction history result."""
    if isinstance(result, dict):
        if result.get("error"):
            return f"Error retrieving transactions: {result.get('content', 'Unknown error')}"
        
        transactions = result.get("content", [])
        if not transactions:
            return "No transactions found for this period."
        
        lines = [f"Recent Transactions ({len(transactions)} total):"]
        for tx in transactions[:5]:  # Show first 5
            if isinstance(tx, dict):
                date = tx.get("date", "N/A")
                desc = tx.get("description", tx.get("merchant", "Unknown"))
                amount = tx.get("amount", "N/A")
                lines.append(f"  • {date}: {desc} - ${amount}")
        
        if len(transactions) > 5:
            lines.append(f"  ... and {len(transactions) - 5} more")
        
        return "\n".join(lines)
    return str(result)


@ToolFormatter.register("submit_referral")
def format_referral_result(result: Any) -> str:
    """Format referral submission result."""
    if isinstance(result, dict):
        if result.get("error"):
            return f"Referral submission failed: {result.get('content', 'Unknown error')}"
        
        data = result.get("content", {})
        if isinstance(data, dict):
            status = data.get("status", "Submitted")
            code = data.get("confirmation_code", data.get("referral_id", "N/A"))
            return f"Referral {status}! Confirmation code: {code}"
    return str(result)


@ToolFormatter.register("apply_for_card")
def format_card_application(result: Any) -> str:
    """Format card application result."""
    if isinstance(result, dict):
        if result.get("error"):
            return f"Application error: {result.get('content', 'Unknown error')}"
        
        data = result.get("content", {})
        if isinstance(data, dict):
            status = data.get("status", "Submitted")
            card_type = data.get("card_type", "Card")
            ref = data.get("application_reference", data.get("reference", "N/A"))
            return f"{card_type} application {status}. Reference: {ref}"
    return str(result)


@ToolFormatter.register("verify_identity")
def format_identity_verification(result: Any) -> str:
    """Format identity verification result."""
    if isinstance(result, dict):
        if result.get("error"):
            return f"Verification failed: {result.get('content', 'Unknown error')}"
        
        data = result.get("content", {})
        if isinstance(data, dict):
            verified = data.get("verified", False)
            if verified:
                return "✓ Identity verified successfully."
            else:
                remaining = data.get("attempts_remaining", "N/A")
                return f"✗ Identity verification failed. Attempts remaining: {remaining}"
    return str(result)


@ToolFormatter.register("transfer_funds")
def format_transfer_result(result: Any) -> str:
    """Format fund transfer result."""
    if isinstance(result, dict):
        if result.get("error"):
            return f"Transfer failed: {result.get('content', 'Unknown error')}"
        
        data = result.get("content", {})
        if isinstance(data, dict):
            status = data.get("status", "Completed")
            amount = data.get("amount", "N/A")
            from_acct = data.get("from_account", "Unknown")
            to_acct = data.get("to_account", "Unknown")
            tx_id = data.get("transaction_id", data.get("confirmation", "N/A"))
            return f"Transfer {status}: ${amount} from {from_acct} to {to_acct}. TX ID: {tx_id}"
    return str(result)


# ============================================================================
# KB Search Formatters
# ============================================================================

@ToolFormatter.register("kb_search_bm25")
def format_bm25_results(result: Any) -> str:
    """Format BM25 search results."""
    if isinstance(result, list):
        if not result:
            return "No documents found matching your query."
        
        lines = [f"Found {len(result)} relevant documents:"]
        for doc in result[:3]:  # Top 3
            if isinstance(doc, dict):
                title = doc.get("title", "Untitled")
                content = doc.get("content", "")[:150]  # Truncate
                lines.append(f"\n📄 {title}")
                lines.append(f"   {content}...")
        return "\n".join(lines)
    return str(result)


@ToolFormatter.register("kb_search_vector")
def format_vector_results(result: Any) -> str:
    """Format vector search results."""
    if isinstance(result, list):
        if not result:
            return "No semantically relevant documents found. Try rephrasing your question."
        
        lines = [f"Found {len(result)} semantically similar documents:"]
        for doc in result[:3]:
            if isinstance(doc, dict):
                title = doc.get("title", "Untitled")
                content = doc.get("content", "")[:150]
                lines.append(f"\n📄 {title}")
                lines.append(f"   {content}...")
        return "\n".join(lines)
    return str(result)


# ============================================================================
# Generic Fallback
# ============================================================================

def format_generic_result(tool_name: str, result: Any) -> str:
    """Generic formatter for any tool result."""
    if isinstance(result, dict):
        if result.get("error"):
            return f"[{tool_name} error: {result.get('content', 'Unknown error')}"
        return f"[{tool_name} result: {result.get('content', str(result))}"
    return f"[{tool_name} result: {str(result)}"


def format_tool_result(tool_name: str, result: Any) -> str:
    """Main entry point for formatting tool results.
    
    Args:
        tool_name: Name of the tool that produced the result
        result: Raw result from the tool
        
    Returns:
        Human-readable formatted string
    """
    return ToolFormatter.format(tool_name, result)
