"""Unit tests for intent classification system.

Tests the keyword-based intent classification for research escalation.
"""

import pytest
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cs_agent.research_client_tool import classify_research_intent, RESEARCH_KEYWORDS, SIMPLE_QUERY_PATTERNS


class TestIntentClassification:
    """Test intent classification accuracy."""
    
    def test_simple_balance_query(self):
        """Balance queries should NOT need research."""
        result = classify_research_intent("What's my account balance?")
        assert result["needs_research"] == False
        assert result["confidence"] == "high"
    
    def test_simple_status_query(self):
        """Status queries should NOT need research."""
        result = classify_research_intent("Is my card active?")
        assert result["needs_research"] == False
    
    def test_policy_conflict_query(self):
        """Policy conflict queries SHOULD need research."""
        result = classify_research_intent("What are all the exceptions to the overdraft policy?")
        assert result["needs_research"] == True
        assert result["confidence"] == "high"
    
    def test_comparison_query(self):
        """Comparison queries SHOULD need research."""
        result = classify_research_intent("Compare the Blue and Gold account benefits")
        assert result["needs_research"] == True
    
    def test_procedure_query(self):
        """Detailed procedure queries SHOULD need research."""
        result = classify_research_intent("What are the complete steps to dispute a transaction?")
        assert result["needs_research"] == True
    
    def test_cross_reference_query(self):
        """Cross-reference queries SHOULD need research."""
        result = classify_research_intent("Can you cross-reference this against multiple policies?")
        assert result["needs_research"] == True
    
    def test_multiple_keywords(self):
        """Multiple research keywords should increase confidence."""
        result = classify_research_intent("Compare and contrast the differences between all account types")
        assert result["needs_research"] == True
        assert result["confidence"] == "high"
    
    def test_complex_long_query(self):
        """Very long queries should trigger research."""
        long_query = "I have a question about my account and I want to know what are all the different scenarios where fees might apply and how they compare to other banks and what exceptions exist?"
        result = classify_research_intent(long_query)
        assert result["needs_research"] == True
    
    def test_multiple_questions(self):
        """Multiple questions should trigger research."""
        multi_query = "What's the fee? When is it charged? Are there exceptions?"
        result = classify_research_intent(multi_query)
        assert result["needs_research"] == True
    
    def test_case_insensitive(self):
        """Classification should be case insensitive."""
        result1 = classify_research_intent("What are the EXCEPTIONS?")
        result2 = classify_research_intent("what are the exceptions?")
        assert result1["needs_research"] == result2["needs_research"]
    
    def test_returns_classification_dict(self):
        """Should return properly structured dict."""
        result = classify_research_intent("Test query")
        assert "needs_research" in result
        assert "confidence" in result
        assert "reason" in result
        assert "suggested_approach" in result


class TestKeywordCoverage:
    """Test that all keywords are properly detected."""
    
    @pytest.mark.parametrize("keyword", RESEARCH_KEYWORDS)
    def test_research_keyword_detection(self, keyword):
        """Each research keyword should be detected."""
        query = f"Tell me about {keyword}"
        result = classify_research_intent(query)
        assert result["needs_research"] == True, f"Keyword '{keyword}' not detected"
    
    @pytest.mark.parametrize("pattern", SIMPLE_QUERY_PATTERNS)
    def test_simple_pattern_detection(self, pattern):
        """Each simple pattern should be detected."""
        query = f"{pattern} something"
        result = classify_research_intent(query)
        assert result["needs_research"] == False, f"Pattern '{pattern}' should not trigger research"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_query(self):
        """Empty query should not crash."""
        result = classify_research_intent("")
        assert "needs_research" in result
    
    def test_very_short_query(self):
        """Very short query should be simple."""
        result = classify_research_intent("Hi")
        assert result["needs_research"] == False
    
    def test_very_long_query_no_keywords(self):
        """Long query without keywords should be medium confidence."""
        long_no_kw = "I have a question about banking and accounts and transactions and would like to know more about how things work in general without any specific terms or technical language or complicated scenarios and I am just trying to understand the overall picture a little better before I decide what I personally want to do next with my money this coming year"
        result = classify_research_intent(long_no_kw)
        assert result["needs_research"] == True
        assert result["confidence"] == "medium"
    
    def test_exact_50_words(self):
        """Query at exactly 50 words boundary."""
        words_50 = "word " * 50
        result = classify_research_intent(words_50)
        assert "needs_research" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
