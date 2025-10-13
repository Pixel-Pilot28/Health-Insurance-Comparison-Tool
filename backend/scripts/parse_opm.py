#!/usr/bin/env python3
"""
scripts/parse_opm.py

Usage:
  python scripts/parse_opm.py \
    --benefits /path/to/2026-fehb-plan-benefits_100525.xlsx \
    --payroll /path/to/2026-fehb-payroll-rates_100525.xlsx \
    --out /path/to/health_plan_info_parsed.csv \
    [--emit-legacy /path/to/health_plan_info.csv] \
    [--payroll-band BAND_NAME] \
    [--overrides /path/to/overrides.json] \
    [--column-map-out /path/to/column_map.json] \
    [--min-score 0.6] \
    [--no-fuzzy]

Produces:
  - health_plan_info_parsed.csv
  - parse_report.json
  - column_map.json (if --column-map-out specified)
  - (optional) health_plan_info.csv -- mapped to legacy schema for backward compatibility
"""
import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd

# Import parsing helpers
from parse_helpers import (
    parse_money_percent,
    detect_flags,
    parse_deductible,
    parse_coinsurance,
    parse_specialist_split,
    safe_float,
    normalize_column_name,
    is_ambiguous_cell
)

# Import fuzzy mapping and NLP parser
try:
    from opm_fuzzy_map import (
        fuzzy_map_columns,
        apply_manual_overrides,
        suggest_mappings
    )
    from opm_nlp_parser import ExtendedNLPParser
    FUZZY_AVAILABLE = True
except ImportError:
    print("Warning: Fuzzy mapping or NLP parser not available. Run with --no-fuzzy or install modules.")
    FUZZY_AVAILABLE = False

# -----------------------
# Helper functions
# -----------------------
def load_overrides(overrides_path):
    """Load manual overrides from JSON file."""
    if not os.path.exists(overrides_path):
        return {'column_map': {}, 'plan_overrides': {}}
    
    try:
        with open(overrides_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load overrides from {overrides_path}: {e}")
        return {'column_map': {}, 'plan_overrides': {}}


def save_column_map(mapping, unmapped, suggestions, path):
    """Save column mapping results for UI and reproducibility."""
    data = {
        'timestamp': datetime.now().isoformat(),
        'mapping': mapping,
        'unmapped': unmapped,
        'suggestions': {k: [[t, s] for t, s in v] for k, v in suggestions.items()}
    }
    
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved column map to {path}")
    except Exception as e:
        print(f"Warning: Failed to save column map: {e}")


def should_use_nlp_parser(column_name):
    """Determine if column should use advanced NLP parser."""
    benefit_keywords = [
        'visit', 'care', 'copay', 'coinsurance', 'hospital', 'surgery',
        'diagnostic', 'tier', 'therapy', 'prescription', 'drug',
        'emergency', 'urgent', 'preventive', 'specialist', 'primary',
        'inpatient', 'outpatient', 'maternity', 'mental', 'physical'
    ]
    col_lower = column_name.lower()
    return any(kw in col_lower for kw in benefit_keywords)


def get_plan_key(row_data):
    """Generate unique plan key for overrides lookup."""
    # Try Enrollment_Code first
    if 'Enrollment_Code' in row_data and row_data['Enrollment_Code']:
        return f"EnrollmentCode_{row_data['Enrollment_Code']}"
    
    # Fall back to Plan__Option
    plan = row_data.get('Plan', '')
    option = row_data.get('Option', '')
    if plan and option:
        return f"{plan}__{option}"
    
    return None


def apply_plan_overrides(row_data, plan_overrides):
    """Apply plan-specific field overrides from overrides.json."""
    plan_key = get_plan_key(row_data)
    
    if not plan_key or plan_key not in plan_overrides:
        return row_data
    
    overrides = plan_overrides[plan_key]
    print(f"Applying overrides for {plan_key}: {len(overrides)} fields")
    
    # Apply each override
    for field, value in overrides.items():
        row_data[field] = value
    
    return row_data


# -----------------------
# Main transformation
# -----------------------
def transform(benefits_path, payroll_path, out_csv, legacy_out=None, payroll_band=None,
              overrides_path=None, column_map_out=None, min_fuzzy_score=0.6, use_fuzzy=True):
    
    # Load Excel files
    benefits_df = pd.read_excel(benefits_path, sheet_name=0, engine='openpyxl')
    payroll_df = pd.read_excel(payroll_path, sheet_name=0, engine='openpyxl')
    
    # Normalize column names to simple str
    benefits_df.columns = [str(c).strip() for c in benefits_df.columns]
    payroll_df.columns = [str(c).strip() for c in payroll_df.columns]
    
    # Load overrides if provided
    overrides = {}
    if overrides_path:
        overrides = load_overrides(overrides_path)
        print(f"Loaded overrides: {len(overrides.get('column_map', {}))} column mappings, "
              f"{len(overrides.get('plan_overrides', {}))} plan overrides")
    
    # Apply fuzzy column mapping if enabled
    column_mapping = {}
    unmapped_columns = []
    mapping_suggestions = {}
    
    if use_fuzzy and FUZZY_AVAILABLE:
        print("Running fuzzy column mapping...")
        sheet_columns = list(benefits_df.columns)
        
        # Auto-map columns
        column_mapping, unmapped_columns = fuzzy_map_columns(
            sheet_columns,
            min_score=min_fuzzy_score,
            verbose=True
        )
        
        # Apply manual overrides from overrides.json
        manual_column_map = overrides.get('column_map', {})
        if manual_column_map:
            print(f"Applying {len(manual_column_map)} manual column mappings...")
            column_mapping = apply_manual_overrides(column_mapping, manual_column_map)
            # Remove from unmapped if now mapped
            unmapped_columns = [c for c in unmapped_columns if c not in manual_column_map]
        
        # Generate suggestions for remaining unmapped columns
        if unmapped_columns:
            print(f"Generating suggestions for {len(unmapped_columns)} unmapped columns...")
            mapping_suggestions = suggest_mappings(unmapped_columns, top_n=3)
        
        # Save column map if requested
        if column_map_out:
            save_column_map(column_mapping, unmapped_columns, mapping_suggestions, column_map_out)
        
        # Rename columns using mapping (only successfully mapped ones)
        rename_dict = {k: v for k, v in column_mapping.items() if k in benefits_df.columns}
        if rename_dict:
            print(f"Renaming {len(rename_dict)} columns using fuzzy mapping...")
            benefits_df.rename(columns=rename_dict, inplace=True)
    else:
        print("Fuzzy mapping disabled or unavailable")
    
    # Initialize NLP parser if available
    nlp_parser = None
    if FUZZY_AVAILABLE:
        nlp_parser = ExtendedNLPParser()
        print("NLP parser initialized for complex benefit strings")

    # basic identity columns we expect; but be tolerant if missing
    id_cols = ['Plan','Short Name','Option','Enrollment Code','Enrollment Type']
    for c in id_cols:
        if c not in benefits_df.columns:
            # try alternate names
            alternatives = [x for x in benefits_df.columns if c.split()[0].lower() in x.lower()]
            if alternatives:
                id_cols[id_cols.index(c)] = alternatives[0]

    # find premium / gov/emp columns heuristically
    biweekly_total_col = next((c for c in benefits_df.columns if '2025 Biweekly - Total Premium' in c), None)
    gov_col = next((c for c in benefits_df.columns if "Gov't Pays" in c or "Gov_Pays" in c or "Gov" in c and 'Pays' in c), None)
    emp_col = next((c for c in benefits_df.columns if "Emp Pays" in c or "Emp_Pays" in c or "Emp" in c and 'Pays' in c), None)
    # fallback to common names if not found
    if biweekly_total_col is None:
        biweekly_total_col = next((c for c in benefits_df.columns if 'Biweekly' in c and 'Total' in c), None)

    rows = []
    report = {'ambiguous_cells': []}

    # list of benefit columns to parse (exclude ID/premium columns)
    exclude = set(id_cols + [biweekly_total_col, gov_col, emp_col])
    benefit_columns = [c for c in benefits_df.columns if c not in exclude]

    for _, row in benefits_df.iterrows():
        out = {}
        # identity
        for c in id_cols:
            out[c.replace(' ','_')] = row.get(c) if c in row.index else None
        # premium values (safe parse)
        out['Biweekly_Total'] = safe_float(row.get(biweekly_total_col)) if biweekly_total_col else None
        out['Biweekly_Govt'] = safe_float(row.get(gov_col)) if gov_col else None
        out['Biweekly_Emp'] = safe_float(row.get(emp_col)) if emp_col else None
        # annualize
        out['Annual_Total'] = out['Biweekly_Total'] * 26 if out['Biweekly_Total'] is not None else None
        out['Annual_Govt'] = out['Biweekly_Govt'] * 26 if out['Biweekly_Govt'] is not None else None
        out['Annual_Emp'] = out['Biweekly_Emp'] * 26 if out['Biweekly_Emp'] is not None else None
        # gov/emp pct
        if out['Biweekly_Total'] and out['Biweekly_Govt']:
            out['Govt_pct'] = round(100.0 * out['Biweekly_Govt'] / out['Biweekly_Total'],2)
        else:
            out['Govt_pct'] = None
        if out['Biweekly_Total'] and out['Biweekly_Emp']:
            out['Emp_pct'] = round(100.0 * out['Biweekly_Emp'] / out['Biweekly_Total'],2)
        else:
            out['Emp_pct'] = None

        # parse each benefit column
        for c in benefit_columns:
            raw_val = row.get(c)
            key_base = normalize_column_name(c)
            
            # Use NLP parser for benefit columns if available
            if nlp_parser and should_use_nlp_parser(c):
                nlp_rule = nlp_parser.parse(str(raw_val))
                
                # Store all parsed fields from NLP parser
                out[f"{key_base}_raw"] = nlp_rule.raw
                out[f"{key_base}_money"] = nlp_rule.copay
                out[f"{key_base}_percent"] = nlp_rule.coinsurance
                out[f"{key_base}_cap"] = nlp_rule.cap
                out[f"{key_base}_min_value"] = nlp_rule.min_value
                out[f"{key_base}_max_value"] = nlp_rule.max_value
                out[f"{key_base}_applies_after_deductible"] = nlp_rule.applies_after_deductible
                out[f"{key_base}_first_visit_only"] = nlp_rule.first_visit_only
                out[f"{key_base}_network_only"] = nlp_rule.network_only
                out[f"{key_base}_prior_authorization"] = nlp_rule.prior_authorization
                out[f"{key_base}_visits_limit"] = nlp_rule.visits_limit
                out[f"{key_base}_secondary_copay"] = nlp_rule.secondary_copay
                out[f"{key_base}_secondary_coinsurance"] = nlp_rule.secondary_coinsurance
                out[f"{key_base}_is_covered"] = nlp_rule.is_covered
                
                # Check if ambiguous (no clear parse)
                if (nlp_rule.copay is None and nlp_rule.coinsurance is None and 
                    nlp_rule.is_covered is None and nlp_rule.raw and len(nlp_rule.raw) > 0):
                    report['ambiguous_cells'].append({
                        'plan': out.get('Plan'),
                        'enrollment_code': out.get('Enrollment_Code'),
                        'column': c,
                        'raw': nlp_rule.raw
                    })
            else:
                # Fall back to legacy parsing
                parsed = parse_money_percent(raw_val)
                out[f"{key_base}_raw"] = parsed['raw']
                out[f"{key_base}_money"] = parsed['money']
                out[f"{key_base}_percent"] = parsed['percent']
                
                # flags
                flags = detect_flags(parsed['raw'])
                for fk, fv in flags.items():
                    out[f"{key_base}_{fk}"] = fv
                
                # column-specific parsing examples
                low_c = c.lower()
                if 'deductible' in low_c:
                    ded = parse_deductible(parsed['raw'])
                    out.update({f"{key_base}_{kk}": vv for kk,vv in ded.items()})
                if 'coinsurance' in low_c or 'coinsur' in low_c or '%' in str(c):
                    coin = parse_coinsurance(parsed['raw'])
                    out.update({f"{key_base}_{kk}": vv for kk,vv in coin.items()})
                if 'specialist' in low_c or 'pcp' in low_c:
                    split = parse_specialist_split(parsed['raw'])
                    out.update({f"{key_base}_{kk}": vv for kk,vv in split.items()})

                # record ambiguous cells
                if is_ambiguous_cell(parsed, parsed['raw']):
                    report['ambiguous_cells'].append({
                        'plan': out.get('Plan'),
                        'enrollment_code': out.get('Enrollment_Code'),
                        'column': c,
                        'raw': parsed['raw']
                    })
        
        # Apply plan-specific overrides AFTER parsing
        if overrides.get('plan_overrides'):
            out = apply_plan_overrides(out, overrides['plan_overrides'])
        
        rows.append(out)

    parsed_df = pd.DataFrame(rows)

    # Merge payroll by enrollment code
    # detect payroll enrollment column
    payroll_enrl_col = next((c for c in payroll_df.columns if 'Enrl' in c or 'Enrol' in c or 'Enrollment' in c), None)
    if payroll_enrl_col and 'Enrollment_Code' in parsed_df.columns:
        # small normalization to compare types (string vs numeric)
        parsed_df['Enrollment_Code_str'] = parsed_df['Enrollment_Code'].astype(str).str.strip()
        payroll_df['Enrl_Code_str'] = payroll_df[payroll_enrl_col].astype(str).str.strip()
        # join on these
        merged = parsed_df.merge(payroll_df, left_on='Enrollment_Code_str', right_on='Enrl_Code_str', how='left', suffixes=('','_payroll'))
    else:
        merged = parsed_df.copy()

    # If payroll band was requested, pick corresponding columns (agent must provide exact column-to-use)
    if payroll_band:
        if payroll_band in payroll_df.columns:
            merged['Selected_Payroll_Band'] = merged[payroll_band]
        else:
            print(f"Warning: payroll_band {payroll_band} not found in payroll sheet; skipping band selection.")

    # Save parsed CSV
    out_path = Path(out_csv)
    merged.to_csv(out_path, index=False)

    # Optionally emit a legacy CSV (map column names to the older health_plan_info.csv)
    if legacy_out:
        # This mapping is a placeholder — the agent should map fields precisely to existing health_plan_info.csv columns
        legacy_map = {
            # 'Plan' : 'Plan',
            # 'Short Name' : 'Short Name',
            # 'Option' : 'Option',
            # 'Biweekly_Total' : '2025 Biweekly - Total Premium',
            # ... (extend mapping)
        }
        # If the mapping is empty, export a subset with likely needed fields
        legacy_df = merged.copy()
        # keep only selected columns for legacy compatibility
        prefer_cols = ['Plan','Short Name','Option','Enrollment Code','Enrollment Type','Biweekly_Total','Biweekly_Govt','Biweekly_Emp']
        exist_cols = [c for c in prefer_cols if c in legacy_df.columns]
        legacy_df[exist_cols].to_csv(Path(legacy_out), index=False)

    # Enhance parse report with mapping information
    report.update({
        'total_plans': len(merged),
        'total_columns': len(merged.columns),
        'unmapped_columns': unmapped_columns,
        'column_suggestions': {k: [[t, s] for t, s in v] for k, v in mapping_suggestions.items()},
        'timestamp': datetime.now().isoformat()
    })
    
    # Save parse report
    report_path = Path(out_path.parent) / 'parse_report.json'
    with open(report_path, 'w') as fh:
        json.dump(report, fh, indent=2)

    print(f"Saved parsed CSV to {out_path}")
    print(f"Saved parse report to {report_path}")
    print(f"  - {len(report['ambiguous_cells'])} ambiguous cells")
    print(f"  - {len(unmapped_columns)} unmapped columns")
    if legacy_out:
        print(f"Saved legacy CSV to {legacy_out}")

# -----------------------
# CLI
# -----------------------
def main():
    parser = argparse.ArgumentParser(
        description='Parse OPM FEHB Excel files with fuzzy mapping and NLP parsing'
    )
    parser.add_argument('--benefits', required=True, help='Path to benefits Excel file')
    parser.add_argument('--payroll', required=True, help='Path to payroll Excel file')
    parser.add_argument('--out', required=True, help='Output CSV path')
    parser.add_argument('--emit-legacy', dest='legacy', 
                       help='Write legacy health_plan_info.csv', default=None)
    parser.add_argument('--payroll-band', default=None, 
                       help='Choose payroll column/band to use from payroll file')
    parser.add_argument('--overrides', default=None,
                       help='Path to overrides.json file (default: data/overrides.json)')
    parser.add_argument('--column-map-out', default=None,
                       help='Path to save column_map.json (default: data/column_map.json)')
    parser.add_argument('--min-score', type=float, default=0.6,
                       help='Minimum fuzzy match score 0.0-1.0 (default: 0.6)')
    parser.add_argument('--no-fuzzy', action='store_true',
                       help='Disable fuzzy column mapping')
    
    args = parser.parse_args()
    
    # Set default paths relative to data directory
    overrides_path = args.overrides
    if not overrides_path and not args.no_fuzzy:
        overrides_path = Path(args.out).parent / 'overrides.json'
    
    column_map_out = args.column_map_out
    if not column_map_out and not args.no_fuzzy:
        column_map_out = Path(args.out).parent / 'column_map.json'
    
    transform(
        args.benefits, 
        args.payroll, 
        args.out, 
        legacy_out=args.legacy, 
        payroll_band=args.payroll_band,
        overrides_path=overrides_path,
        column_map_out=column_map_out,
        min_fuzzy_score=args.min_score,
        use_fuzzy=not args.no_fuzzy
    )

if __name__ == '__main__':
    main()
