"""
parse_helpers.py

Parsing helper functions for OPM health plan data.
These functions extract money values, percentages, and special flags from raw cell data.
"""
import re
import pandas as pd


def parse_money_percent(s):
    """
    Parse a cell value to extract money amounts and percentages.
    
    Args:
        s: Raw cell value (string or any type)
    
    Returns:
        dict with keys:
            - 'money': float or None (extracted dollar amount)
            - 'percent': float or None (extracted percentage)
            - 'raw': str or None (original value)
    
    Examples:
        >>> parse_money_percent("$25 copay")
        {'money': 25.0, 'percent': None, 'raw': '$25 copay'}
        
        >>> parse_money_percent("20% after deductible")
        {'money': None, 'percent': 20.0, 'raw': '20% after deductible'}
        
        >>> parse_money_percent("Covered")
        {'money': 0.0, 'percent': 0.0, 'raw': 'Covered'}
    """
    if pd.isna(s):
        return {'money': None, 'percent': None, 'raw': None}
    
    orig = str(s).strip()
    lowered = orig.lower()
    
    # Simple canonical answers
    if lowered in ('covered', 'yes', 'included', 'in-network', 'in network'):
        return {'money': 0.0, 'percent': 0.0, 'raw': orig}
    if lowered in ('not covered', 'no', 'n/a', 'na', 'excluded', 'not applicable'):
        return {'money': None, 'percent': None, 'raw': orig}
    
    # Extract numbers with currency and percentage symbols
    money_matches = re.findall(r'\$[\d,]+(?:\.\d+)?', orig)
    percent_matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', orig)
    
    money = None
    percent = None
    
    if money_matches:
        val = money_matches[0].replace('$', '').replace(',', '')
        try:
            money = float(val)
        except:
            money = None
    
    if percent_matches:
        try:
            percent = float(percent_matches[0])
        except:
            percent = None
    
    # Fallback: plain numbers with context words (copay, per visit, dollars)
    if money is None:
        if re.search(r'\b(copay|copayment|dollar|per visit|per day|first visit)\b', lowered):
            num = re.findall(r'(?<!%)\b(\d+(?:\.\d+)?)\b', orig)
            if num:
                try:
                    money = float(num[0])
                except:
                    money = None
    
    return {'money': money, 'percent': percent, 'raw': orig}


def detect_flags(raw):
    """
    Detect special condition flags from raw text.
    
    Args:
        raw: Raw cell value (string or None)
    
    Returns:
        dict with boolean flags:
            - applies_after_deductible
            - first_visit_only
            - network_only
            - prior_authorization
    
    Examples:
        >>> detect_flags("$25 copay after deductible")
        {'applies_after_deductible': True, 'first_visit_only': False, ...}
    """
    if raw is None:
        return {}
    
    r = raw.lower()
    return {
        'applies_after_deductible': bool(re.search(r'after deductible', r)),
        'first_visit_only': bool(re.search(r'first visit', r)),
        'network_only': bool(re.search(r'network only|in-network only|in network only', r)),
        'prior_authorization': bool(re.search(r'prior authori|prior approval|pre-authorization|preauthorization', r)),
    }


def parse_deductible(raw):
    """
    Extract deductible amounts and family/individual markers.
    
    Args:
        raw: Raw cell value containing deductible information
    
    Returns:
        dict with keys:
            - ded_money: float or None (primary deductible amount)
            - ded_money_max: float or None (maximum/family deductible if present)
            - ded_per_person: bool (whether it's per person)
            - ded_family: bool (whether it's family maximum)
            - ded_raw: str (original value)
    
    Examples:
        >>> parse_deductible("$500 per person / $1,000 family")
        {'ded_money': 500.0, 'ded_money_max': 1000.0, 'ded_per_person': True, ...}
    """
    if raw is None:
        return {}
    
    result = {'ded_money': None, 'ded_money_max': None, 'ded_raw': raw}
    
    # Find dollar amounts
    nums = re.findall(r'\$[\d,]+(?:\.\d+)?', raw)
    if nums:
        vals = [float(n.replace('$', '').replace(',', '')) for n in nums]
        if len(vals) == 1:
            result['ded_money'] = vals[0]
        elif len(vals) >= 2:
            result['ded_money'] = vals[0]
            result['ded_money_max'] = vals[1]
    
    # Capture "per person" or "family" markers
    result['ded_per_person'] = bool(re.search(r'per person|per individual|self', raw.lower()))
    result['ded_family'] = bool(re.search(r'family|max', raw.lower()))
    
    return result


def parse_coinsurance(raw):
    """
    Extract coinsurance percentage.
    
    Args:
        raw: Raw cell value containing coinsurance information
    
    Returns:
        dict with keys:
            - coinsurance_pct: float or None (percentage)
            - coinsurance_raw: str or None (original value)
    
    Examples:
        >>> parse_coinsurance("20% after deductible")
        {'coinsurance_pct': 20.0, 'coinsurance_raw': '20% after deductible'}
    """
    p = parse_money_percent(raw)
    info = {'coinsurance_pct': p['percent'], 'coinsurance_raw': p['raw']}
    return info


def parse_specialist_split(raw):
    """
    Try to detect PCP vs Specialist copays from a cell with multiple values.
    
    Args:
        raw: Raw cell value that may contain both PCP and specialist information
    
    Returns:
        dict with keys:
            - pcp_copay: float or None
            - specialist_copay: float or None
            - specialist_coinsurance_pct: float or None
            - specialist_raw: str or None
    
    Examples:
        >>> parse_specialist_split("$20 PCP / $35 Specialist")
        {'pcp_copay': 20.0, 'specialist_copay': 35.0, 'specialist_raw': ...}
    """
    if raw is None:
        return {}
    
    low = raw.lower()
    nums = re.findall(r'\$[\d,]+(?:\.\d+)?', raw)
    
    # If we have two dollar amounts, assume first is PCP, second is specialist
    if len(nums) >= 2:
        try:
            vals = [float(n.replace('$', '').replace(',', '')) for n in nums]
            return {
                'pcp_copay': vals[0],
                'specialist_copay': vals[1],
                'specialist_raw': raw
            }
        except:
            pass
    
    # Sometimes the specialist cost is expressed as a percentage
    pct = re.findall(r'(\d+(?:\.\d+)?)\s*%', raw)
    if pct and 'specialist' in low:
        return {
            'specialist_copay': None,
            'specialist_coinsurance_pct': float(pct[0]),
            'specialist_raw': raw
        }
    
    return {}


def safe_float(x):
    """
    Safely convert a value to float, handling currency symbols and NaN.
    
    Args:
        x: Value to convert (can be string, float, or pandas NaN)
    
    Returns:
        float or None
    
    Examples:
        >>> safe_float("$1,234.56")
        1234.56
        >>> safe_float(pd.NA)
        None
    """
    if pd.isna(x):
        return None
    
    s = str(x).replace('$', '').replace(',', '').strip()
    try:
        return float(s)
    except:
        try:
            return float(x)
        except:
            return None


def normalize_column_name(col_name):
    """
    Normalize a column name to a valid Python identifier.
    
    Args:
        col_name: Original column name
    
    Returns:
        Normalized column name (replaces spaces, slashes, colons, hyphens with underscores)
    
    Examples:
        >>> normalize_column_name("PCP/Specialist Copay")
        "PCP_Specialist_Copay"
    """
    return col_name.strip().replace('/', '_').replace(' ', '_').replace(':', '').replace('-', '_')


def is_ambiguous_cell(parsed, raw):
    """
    Check if a parsed cell contains ambiguous text that couldn't be parsed to numbers.
    
    Args:
        parsed: Result from parse_money_percent
        raw: Original raw value
    
    Returns:
        bool: True if the cell contains ambiguous language
    
    Examples:
        >>> is_ambiguous_cell({'money': None, 'percent': None, 'raw': 'May be covered'}, 'May be covered')
        True
    """
    if parsed['money'] is None and parsed['percent'] is None and raw is not None:
        if re.search(r'after|or|may|visit|subject to|up to|not covered|pending', raw.lower()):
            return True
    return False
