"""
OPM Column Fuzzy Mapping Module

Provides fuzzy string matching to automatically map OPM Excel column names
(which vary by year and format) to canonical internal field names.

Uses token-based similarity scoring with Jaccard index and sequence matching.
"""

import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Set

# Words to ignore when normalizing column names
STOPWORDS: Set[str] = {
    'the', 'a', 'an', 'per', 'of', 'and', 'to', 'for', 'in', 'on', 'with',
    'or', 'at', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'been', 'be'
}

# Canonical target field names that the parser expects
CANONICAL_TARGETS = [
    'Plan Name',
    'Short Name',
    'Plan Code',
    'Enrollment Code',
    'Enrollment Type',
    'Brochure Number',
    'In Network Out Of Network',
    'Plan Option Type',
    'Annual Deductible Self',
    'Annual Deductible Self Plus One',
    'Annual Deductible Self And Family',
    'Annual Out Of Pocket Maximum Self',
    'Annual Out Of Pocket Maximum Self Plus One',
    'Annual Out Of Pocket Maximum Self And Family',
    'Primary Care Office Visit',
    'Specialist Office Visit',
    'Emergency Care',
    'Urgent Care',
    'Preventive Care',
    'Hospital Inpatient Cost Per Admission',
    'Hospital Room Costs',
    'Doctor Costs For Inpatient Surgery',
    'Doctor Costs For Outpatient Surgery',
    'Other Outpatient Surgery Costs',
    'Diagnostic Tests Or Procedures Blood Tests X Rays Urinalysis Ultrasounds',
    'Diagnostic Tests Or Procedures CT Scans MRIs PET Scans',
    'Tier 0',
    'Tier 1',
    'Tier 2',
    'Tier 3',
    'Tier 4',
    'Tier 5',
    'Tier 6',
    'Applied Behavioral Analysis ABA',
    'Chiropractic',
    'Occupational Therapy',
    'Physical Therapy',
    'Speech Therapy',
    'Professional Services Mental Health And Substance Use Disorder',
    'Inpatient Hospital Mental Health And Substance Use Disorder Services',
    'Diagnosis And Treatment Infertility Services',
    'Hearing Services',
    'Prenatal Care Screening For Gestational Diabetes Delivery And Postpartum Care Maternity Care',
    'Biweekly Total',
    'Biweekly Govt',
    'Biweekly Emp',
    'Annual Total',
    'Annual Govt',
    'Annual Emp',
]


def normalize(s: str) -> List[str]:
    """
    Normalize a string for fuzzy matching.
    
    Steps:
    1. Convert to lowercase
    2. Remove punctuation (keep spaces)
    3. Split into tokens
    4. Remove stopwords
    
    Args:
        s: Input string to normalize
        
    Returns:
        List of normalized tokens
    """
    s = s.lower()
    # Replace punctuation with spaces, but keep alphanumeric
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    # Split and filter stopwords
    tokens = [t for t in s.split() if t and t not in STOPWORDS]
    return tokens


def jaccard(a: List[str], b: List[str]) -> float:
    """
    Calculate Jaccard similarity coefficient between two token lists.
    
    Jaccard = |A ∩ B| / |A ∪ B|
    
    Args:
        a: First token list
        b: Second token list
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    A, B = set(a), set(b)
    if not A and not B:
        return 0.0
    intersection = len(A & B)
    union = len(A | B)
    return intersection / union if union > 0 else 0.0


def seq_ratio(a: List[str], b: List[str]) -> float:
    """
    Calculate sequence similarity ratio between two token lists.
    
    Uses difflib.SequenceMatcher to account for token ordering.
    
    Args:
        a: First token list
        b: Second token list
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    str_a = " ".join(a)
    str_b = " ".join(b)
    return SequenceMatcher(None, str_a, str_b).ratio()


def score_candidate(candidate: str, target: str, 
                   jaccard_weight: float = 0.6,
                   seq_weight: float = 0.4) -> float:
    """
    Score how well a candidate column name matches a target field name.
    
    Uses weighted combination of:
    - Jaccard similarity (token overlap)
    - Sequence similarity (token ordering)
    
    Args:
        candidate: Column name from OPM file
        target: Canonical target field name
        jaccard_weight: Weight for Jaccard score (default 0.6)
        seq_weight: Weight for sequence score (default 0.4)
        
    Returns:
        Combined similarity score between 0.0 and 1.0
    """
    C = normalize(candidate)
    T = normalize(target)
    
    if not C or not T:
        return 0.0
    
    s1 = jaccard(C, T)
    s2 = seq_ratio(C, T)
    
    # Weighted combination favoring token overlap
    return jaccard_weight * s1 + seq_weight * s2


def fuzzy_map_columns(sheet_columns: List[str],
                     canonical_targets: List[str] = None,
                     min_score: float = 0.6,
                     verbose: bool = False) -> Tuple[Dict[str, str], List[str]]:
    """
    Automatically map OPM sheet columns to canonical field names using fuzzy matching.
    
    Args:
        sheet_columns: List of column names from OPM Excel file
        canonical_targets: List of target field names (uses CANONICAL_TARGETS if None)
        min_score: Minimum similarity score to auto-map (default 0.6)
        verbose: Print matching scores for debugging
        
    Returns:
        Tuple of (mapping_dict, unmapped_columns)
        - mapping_dict: {sheet_column -> canonical_field}
        - unmapped_columns: List of columns that couldn't be auto-mapped
    """
    if canonical_targets is None:
        canonical_targets = CANONICAL_TARGETS
    
    mapping = {}
    unmapped = []
    
    for col in sheet_columns:
        best = None
        best_score = 0.0
        
        for targ in canonical_targets:
            sc = score_candidate(col, targ)
            if sc > best_score:
                best_score = sc
                best = targ
        
        if verbose:
            print(f"Column '{col}' -> '{best}' (score: {best_score:.3f})")
        
        if best_score >= min_score:
            mapping[col] = best
        else:
            unmapped.append(col)
            if verbose:
                print(f"  -> UNMAPPED (score too low)")
    
    return mapping, unmapped


def apply_manual_overrides(mapping: Dict[str, str],
                          overrides: Dict[str, str]) -> Dict[str, str]:
    """
    Apply manual column mapping overrides.
    
    Args:
        mapping: Auto-generated column mapping
        overrides: Manual overrides {sheet_column -> canonical_field}
        
    Returns:
        Updated mapping with overrides applied
    """
    updated = mapping.copy()
    updated.update(overrides)
    return updated


def suggest_mappings(unmapped_columns: List[str],
                    canonical_targets: List[str] = None,
                    top_n: int = 3) -> Dict[str, List[Tuple[str, float]]]:
    """
    Suggest possible mappings for unmapped columns.
    
    Args:
        unmapped_columns: Columns that couldn't be auto-mapped
        canonical_targets: List of target field names
        top_n: Number of suggestions per column
        
    Returns:
        Dict mapping each unmapped column to list of (target, score) tuples
    """
    if canonical_targets is None:
        canonical_targets = CANONICAL_TARGETS
    
    suggestions = {}
    
    for col in unmapped_columns:
        scores = []
        for targ in canonical_targets:
            sc = score_candidate(col, targ)
            scores.append((targ, sc))
        
        # Sort by score descending and take top N
        scores.sort(key=lambda x: x[1], reverse=True)
        suggestions[col] = scores[:top_n]
    
    return suggestions
