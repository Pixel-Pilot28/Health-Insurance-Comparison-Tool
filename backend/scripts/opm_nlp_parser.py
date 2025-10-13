"""
Extended NLP Parser for Complex OPM Benefit Strings

Handles multi-step benefit rules like:
- "$25 then 20% up to $500"
- "$25 or 15%"
- "50% after deductible up to $1500"
- "$100-$200 range"
- "First 3 visits $25, then $50"
- "No charge" / "Not covered" / "All charges"

Uses regex patterns and a rule engine to extract structured data.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class BenefitRule:
    """Structured representation of a parsed benefit rule."""
    copay: Optional[float] = None
    coinsurance: Optional[float] = None
    cap: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    applies_after_deductible: bool = False
    first_visit_only: bool = False
    network_only: bool = False
    prior_authorization: bool = False
    visits_limit: Optional[int] = None
    secondary_copay: Optional[float] = None
    secondary_coinsurance: Optional[float] = None
    is_covered: Optional[bool] = None
    raw: str = ""


class ExtendedNLPParser:
    """
    Parser for complex benefit strings with multi-step rules.
    """
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self.money_pattern = re.compile(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)')
        self.percent_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*%')
        self.range_pattern = re.compile(r'\$\s*(\d+(?:,\d{3})*)\s*[-–—]\s*\$\s*(\d+(?:,\d{3})*)')
        self.visits_pattern = re.compile(r'(?:first|initial)\s+(\d+)\s+visits?', re.IGNORECASE)
        
        # Flag patterns
        self.flag_patterns = {
            'after_deductible': re.compile(
                r'after\s+(?:meeting\s+)?(?:the\s+)?deductible|'
                r'deductible\s+applies|'
                r'subject\s+to\s+deductible', 
                re.IGNORECASE
            ),
            'first_visit': re.compile(
                r'first\s+visit\s+only|'
                r'initial\s+visit\s+only',
                re.IGNORECASE
            ),
            'network_only': re.compile(
                r'network\s+only|'
                r'in[-\s]network\s+only|'
                r'preferred\s+provider\s+only',
                re.IGNORECASE
            ),
            'prior_auth': re.compile(
                r'prior\s+authorization|'
                r'preauthorization|'
                r'pre[-\s]auth',
                re.IGNORECASE
            ),
        }
        
        # Coverage status patterns
        self.covered_pattern = re.compile(
            r'\b(?:covered|no\s+charge|no\s+cost|paid\s+in\s+full|100%)\b',
            re.IGNORECASE
        )
        self.not_covered_pattern = re.compile(
            r'\bnot\s+covered\b|'
            r'\bno\s+coverage\b|'
            r'\ball\s+charges\b',
            re.IGNORECASE
        )
        
        # Multi-step patterns
        self.then_pattern = re.compile(r'\bthen\b', re.IGNORECASE)
        self.or_pattern = re.compile(r'\bor\b', re.IGNORECASE)
        self.up_to_pattern = re.compile(r'up\s+to\s+\$\s*(\d+(?:,\d{3})*)', re.IGNORECASE)
    
    def parse(self, text: str) -> BenefitRule:
        """
        Parse a benefit string into structured rule.
        
        Args:
            text: Benefit description string
            
        Returns:
            BenefitRule object with extracted information
        """
        if not text or not isinstance(text, str):
            return BenefitRule(raw=str(text))
        
        rule = BenefitRule(raw=text)
        text_lower = text.lower().strip()
        
        # Check coverage status first
        if self._check_not_covered(text):
            rule.is_covered = False
            return rule
        
        if self._check_covered(text):
            rule.is_covered = True
            rule.copay = 0.0
            return rule
        
        # Extract flags
        rule.applies_after_deductible = bool(self.flag_patterns['after_deductible'].search(text))
        rule.first_visit_only = bool(self.flag_patterns['first_visit'].search(text))
        rule.network_only = bool(self.flag_patterns['network_only'].search(text))
        rule.prior_authorization = bool(self.flag_patterns['prior_auth'].search(text))
        
        # Extract visit limits
        visits_match = self.visits_pattern.search(text)
        if visits_match:
            rule.visits_limit = int(visits_match.group(1))
        
        # Check for multi-step rules
        if self.then_pattern.search(text):
            self._parse_then_rule(text, rule)
        elif self.or_pattern.search(text):
            self._parse_or_rule(text, rule)
        elif self.up_to_pattern.search(text):
            self._parse_up_to_rule(text, rule)
        else:
            # Simple single-value rule
            self._parse_simple_rule(text, rule)
        
        return rule
    
    def _check_covered(self, text: str) -> bool:
        """Check if service is fully covered."""
        return bool(self.covered_pattern.search(text))
    
    def _check_not_covered(self, text: str) -> bool:
        """Check if service is not covered."""
        # Check "not covered" BEFORE "covered"
        return bool(self.not_covered_pattern.search(text))
    
    def _parse_simple_rule(self, text: str, rule: BenefitRule) -> None:
        """Parse simple copay or coinsurance."""
        # Look for range first
        range_match = self.range_pattern.search(text)
        if range_match:
            rule.min_value = self._clean_money(range_match.group(1))
            rule.max_value = self._clean_money(range_match.group(2))
            return
        
        # Extract money values
        money_matches = self.money_pattern.findall(text)
        if money_matches:
            rule.copay = self._clean_money(money_matches[0])
            if len(money_matches) > 1:
                rule.cap = self._clean_money(money_matches[1])
        
        # Extract percentages
        percent_matches = self.percent_pattern.findall(text)
        if percent_matches:
            rule.coinsurance = float(percent_matches[0])
    
    def _parse_then_rule(self, text: str, rule: BenefitRule) -> None:
        """
        Parse multi-step 'then' rule.
        Example: "$25 then 20% up to $500"
        """
        parts = self.then_pattern.split(text, maxsplit=1)
        
        if len(parts) == 2:
            first_part, second_part = parts
            
            # Parse first step
            money_first = self.money_pattern.findall(first_part)
            percent_first = self.percent_pattern.findall(first_part)
            
            if money_first:
                rule.copay = self._clean_money(money_first[0])
            elif percent_first:
                rule.coinsurance = float(percent_first[0])
            
            # Parse second step
            money_second = self.money_pattern.findall(second_part)
            percent_second = self.percent_pattern.findall(second_part)
            
            if money_second:
                rule.secondary_copay = self._clean_money(money_second[0])
                if len(money_second) > 1:
                    rule.cap = self._clean_money(money_second[1])
            elif percent_second:
                rule.secondary_coinsurance = float(percent_second[0])
            
            # Check for cap in second part
            cap_match = self.up_to_pattern.search(second_part)
            if cap_match:
                rule.cap = self._clean_money(cap_match.group(1))
    
    def _parse_or_rule(self, text: str, rule: BenefitRule) -> None:
        """
        Parse 'or' rule (alternative payment methods).
        Example: "$25 or 15%"
        Takes the first option as primary.
        """
        parts = self.or_pattern.split(text, maxsplit=1)
        
        if len(parts) == 2:
            first_part, second_part = parts
            
            # Primary: first option
            money_first = self.money_pattern.findall(first_part)
            percent_first = self.percent_pattern.findall(first_part)
            
            if money_first:
                rule.copay = self._clean_money(money_first[0])
            elif percent_first:
                rule.coinsurance = float(percent_first[0])
            
            # Secondary: alternative option
            money_second = self.money_pattern.findall(second_part)
            percent_second = self.percent_pattern.findall(second_part)
            
            if money_second:
                rule.secondary_copay = self._clean_money(money_second[0])
            elif percent_second:
                rule.secondary_coinsurance = float(percent_second[0])
    
    def _parse_up_to_rule(self, text: str, rule: BenefitRule) -> None:
        """
        Parse 'up to' rule (benefit with cap).
        Example: "50% after deductible up to $1500"
        """
        # Extract cap
        cap_match = self.up_to_pattern.search(text)
        if cap_match:
            rule.cap = self._clean_money(cap_match.group(1))
        
        # Extract primary values before "up to"
        before_cap = self.up_to_pattern.split(text)[0]
        
        money_matches = self.money_pattern.findall(before_cap)
        percent_matches = self.percent_pattern.findall(before_cap)
        
        if money_matches:
            rule.copay = self._clean_money(money_matches[0])
        if percent_matches:
            rule.coinsurance = float(percent_matches[0])
    
    def _clean_money(self, value: str) -> float:
        """Convert money string to float, removing commas."""
        return float(value.replace(',', ''))
    
    def to_dict(self, rule: BenefitRule) -> Dict[str, Any]:
        """Convert BenefitRule to dictionary for JSON serialization."""
        return {
            'copay': rule.copay,
            'coinsurance': rule.coinsurance,
            'cap': rule.cap,
            'min_value': rule.min_value,
            'max_value': rule.max_value,
            'applies_after_deductible': rule.applies_after_deductible,
            'first_visit_only': rule.first_visit_only,
            'network_only': rule.network_only,
            'prior_authorization': rule.prior_authorization,
            'visits_limit': rule.visits_limit,
            'secondary_copay': rule.secondary_copay,
            'secondary_coinsurance': rule.secondary_coinsurance,
            'is_covered': rule.is_covered,
            'raw': rule.raw,
        }


def parse_benefit_string(text: str) -> Dict[str, Any]:
    """
    Convenience function to parse a benefit string.
    
    Args:
        text: Benefit description string
        
    Returns:
        Dictionary with parsed benefit information
    """
    parser = ExtendedNLPParser()
    rule = parser.parse(text)
    return parser.to_dict(rule)
