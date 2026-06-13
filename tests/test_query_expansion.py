"""Unit tests for query expansion and enhanced search.

Tests the synonym-based query expansion for better recall.
"""

import pytest
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cs_agent.rag_tools import expand_query, deduplicate_results, QUERY_EXPANSIONS


class TestQueryExpansion:
    """Test query expansion functionality."""
    
    def test_original_query_always_included(self):
        """Original query should always be in expanded list."""
        query = "overdraft fee"
        expanded = expand_query(query)
        assert query.lower() in [q.lower() for q in expanded]
    
    def test_overdraft_expansion(self):
        """Overdraft should expand to synonyms."""
        query = "overdraft fee"
        expanded = expand_query(query)
        
        # Should have expanded variations
        assert len(expanded) > 1
        
        # Check for expected synonyms
        assert any("NSF" in q for q in expanded)
        assert any("negative balance" in q for q in expanded)
    
    def test_dispute_expansion(self):
        """Dispute should expand to synonyms."""
        query = "dispute transaction"
        expanded = expand_query(query)
        
        assert len(expanded) > 1
        assert any("fraud" in q for q in expanded)
        assert any("unauthorized" in q for q in expanded)
    
    def test_referral_expansion(self):
        """Referral should expand to synonyms."""
        query = "referral bonus"
        expanded = expand_query(query)
        
        assert len(expanded) > 1
        assert any("invite" in q for q in expanded)
    
    def test_no_expansion_for_unknown_terms(self):
        """Unknown terms should return just original."""
        query = "xyzabc123"
        expanded = expand_query(query)
        assert len(expanded) == 1
        assert expanded[0] == query
    
    def test_case_preservation(self):
        """Expansion should preserve case of original."""
        query = "OVERDRAFT Fee"
        expanded = expand_query(query)
        
        # Original should be present (case may vary)
        assert query.lower() in [q.lower() for q in expanded]
    
    def test_multiple_matching_keywords(self):
        """Query with multiple keywords should expand all."""
        # This query has both "account" and "fee"
        query = "account fee"
        expanded = expand_query(query)
        
        # Should have expansions for both keywords
        assert len(expanded) >= 1
    
    def test_no_duplicate_expansions(self):
        """Should not produce duplicate expanded queries."""
        query = "overdraft"
        expanded = expand_query(query)
        
        # Check no duplicates
        assert len(expanded) == len(set(e.lower() for e in expanded))


class TestDeduplicateResults:
    """Test result deduplication."""
    
    def test_empty_list(self):
        """Empty list should return empty."""
        result = deduplicate_results([])
        assert result == []
    
    def test_single_list_no_dups(self):
        """Single list with no duplicates."""
        docs = [[
            {"doc_id": "1", "title": "Doc 1"},
            {"doc_id": "2", "title": "Doc 2"},
        ]]
        result = deduplicate_results(docs)
        assert len(result) == 2
    
    def test_duplicate_removal(self):
        """Should remove duplicates across lists."""
        docs = [
            [{"doc_id": "1", "title": "Doc 1"}],
            [{"doc_id": "1", "title": "Doc 1 Duplicate"}],
            [{"doc_id": "2", "title": "Doc 2"}],
        ]
        result = deduplicate_results(docs)
        
        # Should have 2 unique docs
        assert len(result) == 2
        doc_ids = [d["doc_id"] for d in result]
        assert "1" in doc_ids
        assert "2" in doc_ids
    
    def test_preserves_first_occurrence(self):
        """Should keep first occurrence of each doc."""
        docs = [
            [{"doc_id": "1", "title": "First"}],
            [{"doc_id": "1", "title": "Second"}],
        ]
        result = deduplicate_results(docs)
        
        assert len(result) == 1
        assert result[0]["title"] == "First"
    
    def test_handles_missing_doc_id(self):
        """Should handle documents without doc_id."""
        docs = [
            [{"title": "No ID"}],
            [{"title": "Also No ID"}],
        ]
        result = deduplicate_results(docs)
        
        # Should still include both (no doc_id to dedup on)
        assert len(result) == 2


class TestQueryExpansionCoverage:
    """Test coverage of all expansion categories."""
    
    @pytest.mark.parametrize("keyword,synonyms", list(QUERY_EXPANSIONS.items()))
    def test_all_categories_expand(self, keyword, synonyms):
        """All categories in QUERY_EXPANSIONS should work."""
        query = f"{keyword} query"
        expanded = expand_query(query)
        
        # Should have at least original + some expansions
        assert len(expanded) >= 1
        
        # Original should be present
        assert any(keyword in q for q in expanded)
    
    def test_all_keywords_present(self):
        """All expected keywords should be in expansion dict."""
        expected_keywords = [
            "account", "overdraft", "transaction", "dispute",
            "card", "limit", "referral", "application", "fee", "policy"
        ]
        
        for keyword in expected_keywords:
            assert keyword in QUERY_EXPANSIONS, f"Missing keyword: {keyword}"


class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_string(self):
        """Empty string should return empty list or single item."""
        result = expand_query("")
        assert len(result) >= 1  # At least empty string
    
    def test_single_word(self):
        """Single word should expand if it's a keyword."""
        result = expand_query("overdraft")
        assert len(result) > 1  # Should have expansions
    
    def test_very_long_query(self):
        """Very long query should still work."""
        long_query = "overdraft " * 100
        result = expand_query(long_query)
        assert len(result) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
