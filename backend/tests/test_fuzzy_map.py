"""
Unit tests for OPM Fuzzy Column Mapping

Tests the fuzzy matching functionality that maps OPM Excel column names
to canonical internal field names.
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from opm_fuzzy_map import (
    normalize,
    jaccard,
    seq_ratio,
    score_candidate,
    fuzzy_map_columns,
    apply_manual_overrides,
    suggest_mappings,
    CANONICAL_TARGETS,
)


class TestNormalize:
    """Tests for string normalization."""
    
    def test_lowercase_conversion(self):
        result = normalize("Primary Care Office Visit")
        assert all(t.islower() for t in result)
    
    def test_punctuation_removal(self):
        result = normalize("Annual Deductible (Self)")
        assert "(" not in " ".join(result)
        assert ")" not in " ".join(result)
    
    def test_stopword_removal(self):
        result = normalize("The Annual Deductible for the Self")
        assert "the" not in result
        assert "for" not in result
        assert "annual" in result
        assert "deductible" in result
        assert "self" in result
    
    def test_empty_string(self):
        result = normalize("")
        assert result == []
    
    def test_only_stopwords(self):
        result = normalize("the and of")
        assert result == []
    
    def test_numbers_preserved(self):
        result = normalize("Tier 1 Prescription")
        assert "tier" in result
        assert "1" in result
        assert "prescription" in result


class TestJaccard:
    """Tests for Jaccard similarity coefficient."""
    
    def test_identical_sets(self):
        a = ["annual", "deductible", "self"]
        b = ["annual", "deductible", "self"]
        assert jaccard(a, b) == 1.0
    
    def test_no_overlap(self):
        a = ["primary", "care"]
        b = ["specialist", "visit"]
        assert jaccard(a, b) == 0.0
    
    def test_partial_overlap(self):
        a = ["annual", "deductible", "self"]
        b = ["annual", "deductible", "family"]
        # Intersection: 2, Union: 4
        assert jaccard(a, b) == 0.5
    
    def test_empty_lists(self):
        assert jaccard([], []) == 0.0
        assert jaccard(["a"], []) == 0.0
        assert jaccard([], ["b"]) == 0.0
    
    def test_subset(self):
        a = ["annual", "deductible"]
        b = ["annual", "deductible", "self"]
        # Intersection: 2, Union: 3
        assert jaccard(a, b) == pytest.approx(0.6667, abs=0.01)


class TestSeqRatio:
    """Tests for sequence similarity ratio."""
    
    def test_identical_sequences(self):
        a = ["annual", "deductible", "self"]
        b = ["annual", "deductible", "self"]
        assert seq_ratio(a, b) == 1.0
    
    def test_completely_different(self):
        a = ["primary", "care"]
        b = ["specialist", "visit"]
        ratio = seq_ratio(a, b)
        assert 0.0 <= ratio < 0.3  # Should be very low
    
    def test_order_matters(self):
        a = ["annual", "deductible", "self"]
        b = ["self", "deductible", "annual"]
        ratio = seq_ratio(a, b)
        assert ratio < 1.0  # Not identical due to ordering
        assert ratio > 0.5  # But still similar tokens
    
    def test_partial_match(self):
        a = ["annual", "deductible"]
        b = ["annual", "deductible", "family"]
        ratio = seq_ratio(a, b)
        assert 0.7 < ratio < 1.0  # High but not perfect


class TestScoreCandidate:
    """Tests for candidate scoring."""
    
    def test_exact_match(self):
        score = score_candidate(
            "Primary Care Office Visit",
            "Primary Care Office Visit"
        )
        assert score == 1.0
    
    def test_case_insensitive(self):
        score1 = score_candidate(
            "PRIMARY CARE OFFICE VISIT",
            "Primary Care Office Visit"
        )
        score2 = score_candidate(
            "primary care office visit",
            "Primary Care Office Visit"
        )
        assert score1 == score2 == 1.0
    
    def test_punctuation_tolerant(self):
        score = score_candidate(
            "Annual Deductible (Self)",
            "Annual Deductible Self"
        )
        assert score > 0.95
    
    def test_stopword_handling(self):
        score = score_candidate(
            "The Annual Deductible for the Self",
            "Annual Deductible Self"
        )
        assert score > 0.95
    
    def test_completely_different(self):
        score = score_candidate(
            "Primary Care Visit",
            "Prescription Drug Tier 5"
        )
        assert score < 0.3
    
    def test_partial_match(self):
        score = score_candidate(
            "Annual Deductible Self",
            "Annual Deductible Family"
        )
        assert 0.6 < score < 0.9  # Similar but not identical


class TestFuzzyMapColumns:
    """Tests for automatic fuzzy column mapping."""
    
    def test_exact_matches(self):
        sheet_columns = [
            "Plan Name",
            "Enrollment Code",
            "Primary Care Office Visit",
        ]
        mapping, unmapped = fuzzy_map_columns(
            sheet_columns,
            canonical_targets=CANONICAL_TARGETS,
            min_score=0.6
        )
        
        assert len(mapping) == 3
        assert mapping["Plan Name"] == "Plan Name"
        assert mapping["Enrollment Code"] == "Enrollment Code"
        assert len(unmapped) == 0
    
    def test_fuzzy_matches(self):
        sheet_columns = [
            "Plan",  # Should match "Plan Name"
            "Enrl Code",  # Should match "Enrollment Code"
            "PCP Visit",  # Should match "Primary Care Office Visit"
        ]
        mapping, unmapped = fuzzy_map_columns(
            sheet_columns,
            canonical_targets=["Plan Name", "Enrollment Code", "Primary Care Office Visit"],
            min_score=0.5
        )
        
        # At least some should match
        assert len(mapping) > 0
    
    def test_unmapped_columns(self):
        sheet_columns = [
            "Random Column XYZ",
            "Completely Different Name",
        ]
        mapping, unmapped = fuzzy_map_columns(
            sheet_columns,
            canonical_targets=CANONICAL_TARGETS,
            min_score=0.6
        )
        
        assert len(unmapped) == 2
        assert "Random Column XYZ" in unmapped
    
    def test_min_score_threshold(self):
        sheet_columns = ["Annual Ded Self"]
        
        # With low threshold
        mapping_low, _ = fuzzy_map_columns(
            sheet_columns,
            canonical_targets=["Annual Deductible Self"],
            min_score=0.4
        )
        
        # With high threshold
        mapping_high, unmapped_high = fuzzy_map_columns(
            sheet_columns,
            canonical_targets=["Annual Deductible Self"],
            min_score=0.95
        )
        
        assert len(mapping_low) >= len(mapping_high)
        if len(mapping_high) == 0:
            assert len(unmapped_high) == 1
    
    def test_empty_input(self):
        mapping, unmapped = fuzzy_map_columns(
            [],
            canonical_targets=CANONICAL_TARGETS
        )
        assert mapping == {}
        assert unmapped == []


class TestApplyManualOverrides:
    """Tests for manual override application."""
    
    def test_apply_overrides(self):
        mapping = {
            "Col1": "Target1",
            "Col2": "Target2",
        }
        overrides = {
            "Col2": "DifferentTarget",
            "Col3": "Target3",
        }
        
        result = apply_manual_overrides(mapping, overrides)
        
        assert result["Col1"] == "Target1"  # Unchanged
        assert result["Col2"] == "DifferentTarget"  # Overridden
        assert result["Col3"] == "Target3"  # Added
    
    def test_empty_overrides(self):
        mapping = {"Col1": "Target1"}
        result = apply_manual_overrides(mapping, {})
        assert result == mapping
    
    def test_original_unchanged(self):
        mapping = {"Col1": "Target1"}
        overrides = {"Col1": "Target2"}
        
        result = apply_manual_overrides(mapping, overrides)
        
        # Original should not be modified
        assert mapping["Col1"] == "Target1"
        assert result["Col1"] == "Target2"


class TestSuggestMappings:
    """Tests for mapping suggestions."""
    
    def test_suggest_top_matches(self):
        unmapped = ["Annual Ded", "PCP"]
        canonical = [
            "Annual Deductible Self",
            "Annual Deductible Family",
            "Primary Care Office Visit",
            "Prescription Drug",
        ]
        
        suggestions = suggest_mappings(unmapped, canonical, top_n=2)
        
        assert len(suggestions) == 2
        assert "Annual Ded" in suggestions
        assert "PCP" in suggestions
        
        # Each should have 2 suggestions
        assert len(suggestions["Annual Ded"]) == 2
        assert len(suggestions["PCP"]) == 2
        
        # Check format: list of (target, score) tuples
        for target, score in suggestions["Annual Ded"]:
            assert isinstance(target, str)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0
    
    def test_suggestions_sorted(self):
        unmapped = ["Deductible"]
        canonical = [
            "Annual Deductible Self",
            "Primary Care Visit",
            "Prescription Drug",
        ]
        
        suggestions = suggest_mappings(unmapped, canonical, top_n=3)
        
        # Scores should be descending
        scores = [score for _, score in suggestions["Deductible"]]
        assert scores == sorted(scores, reverse=True)
        
        # Best match should include "Deductible"
        best_target = suggestions["Deductible"][0][0]
        assert "deductible" in best_target.lower()
    
    def test_empty_unmapped(self):
        suggestions = suggest_mappings([], CANONICAL_TARGETS)
        assert suggestions == {}


class TestIntegration:
    """Integration tests for the full fuzzy mapping workflow."""
    
    def test_full_workflow(self):
        # Simulate OPM column names (with variations)
        opm_columns = [
            "Plan Name",
            "Short Name",
            "Annual Ded. (Self)",  # Punctuation variation
            "Deductible Self+One",  # Different format
            "PCP Office Visit",  # Abbreviation
            "Random Extra Column",
        ]
        
        # Auto-map
        mapping, unmapped = fuzzy_map_columns(opm_columns, min_score=0.6)
        
        # Should map most columns
        assert len(mapping) > 0
        
        # Get suggestions for unmapped
        if unmapped:
            suggestions = suggest_mappings(unmapped, top_n=3)
            assert len(suggestions) == len(unmapped)
        
        # Apply manual overrides
        manual_fixes = {
            "Random Extra Column": "Custom Field"
        }
        final_mapping = apply_manual_overrides(mapping, manual_fixes)
        
        assert "Random Extra Column" in final_mapping
        assert final_mapping["Random Extra Column"] == "Custom Field"
