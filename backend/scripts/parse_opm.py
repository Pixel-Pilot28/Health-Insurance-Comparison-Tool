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
try:
    from .parse_helpers import (
        parse_money_percent,
        detect_flags,
        parse_deductible,
        parse_coinsurance,
        parse_specialist_split,
        safe_float,
        normalize_column_name,
        is_ambiguous_cell
    )
    from .opm_fuzzy_map import fuzzy_map_columns, apply_manual_overrides, suggest_mappings
    from .opm_nlp_parser import ExtendedNLPParser
except ImportError:
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
def determine_enrollment_type(enrollment_code):
    """Map the trailing enrollment code digit to an enrollment type."""
    if not enrollment_code:
        return None

    code = str(enrollment_code).strip()
    if not code:
        return None

    last_char = code[-1]
    if last_char in {"1", "4"}:
        return "Self"
    if last_char in {"2", "5"}:
        return "Self + Family"
    if last_char in {"3", "6"}:
        return "Self + One"
    return None


def determine_option_slot(plan_option_counts, plan_code, enrollment_code):
    """Infer which option slot (0/1) an enrollment code belongs to for a plan."""
    if not plan_code or not enrollment_code:
        return None

    option_count = plan_option_counts.get(plan_code, 1)
    if option_count <= 1:
        return 0

    last_char = str(enrollment_code).strip()[-1]
    if last_char in {"1", "2", "3"}:
        return 0
    if last_char in {"4", "5", "6"}:
        return 1
    return None


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
        # Preserve critical identity columns to avoid collisions
        identity_overrides = {
            'Plan Option Name': 'Plan Option Name',
            'Plan Name': 'Plan Name',
            'Plan Option Type': 'Plan Option Type',
            'Plan Code': 'Plan Code',
            'In-network/out-of-network': 'In-network/out-of-network',
            'Brochure Number': 'Brochure Number'
        }
        for original, target in identity_overrides.items():
            if original in benefits_df.columns:
                column_mapping[original] = target

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

    # focus on in-network benefits which drive member costs
    if 'In-network/out-of-network' in benefits_df.columns:
        in_network_mask = benefits_df['In-network/out-of-network'].astype(str).str.contains('in-network', case=False, na=False)
        filtered = benefits_df[in_network_mask].copy()
        if not filtered.empty:
            benefits_df = filtered

    # Build ordered list of identity columns present in the sheet
    identity_candidates = [
        'Plan',
        'Plan Name',
        'Plan Option Name',
        'Plan Option Type',
        'Short Name',
        'Option',
        'Plan Code',
        'Brochure Number',
        'In-network/out-of-network',
        'Enrollment Code',
        'Enrollment Type'
    ]
    id_cols = []
    for candidate in identity_candidates:
        if candidate in benefits_df.columns and candidate not in id_cols:
            id_cols.append(candidate)

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
            if isinstance(raw_val, pd.Series):
                non_null = raw_val.dropna()
                raw_val = non_null.iloc[0] if not non_null.empty else None
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

    # Remove empty enrollment identity columns before merge to avoid suffix duplication
    for empty_col in ['Enrollment_Code', 'Enrollment_Type']:
        if empty_col in parsed_df.columns and parsed_df[empty_col].notna().sum() == 0:
            parsed_df.drop(columns=[empty_col], inplace=True)

    plan_code_col = 'Plan_Code' if 'Plan_Code' in parsed_df.columns else None
    plan_option_col = 'Plan_Option_Name' if 'Plan_Option_Name' in parsed_df.columns else None

    # Build option index mapping for each plan code
    if plan_code_col and plan_option_col:
        seen = {}
        option_indices = []
        for _, r in parsed_df[[plan_code_col, plan_option_col]].iterrows():
            plan_code = r.get(plan_code_col)
            option_name = r.get(plan_option_col)
            if plan_code not in seen:
                seen[plan_code] = []
            if option_name not in seen[plan_code]:
                seen[plan_code].append(option_name)
            option_indices.append(seen[plan_code].index(option_name))
        parsed_df['Option_Index'] = option_indices

    # Count options per plan code for payroll alignment
    if plan_code_col and 'Option_Index' in parsed_df.columns:
        plan_option_counts = (
            parsed_df[[plan_code_col, 'Option_Index']]
            .drop_duplicates()
            .groupby(plan_code_col)['Option_Index']
            .nunique()
            .to_dict()
        )
    else:
        plan_option_counts = {}

    # Prepare payroll table with enrollment metadata
    payroll_enrl_col = next((c for c in payroll_df.columns if 'Enrl' in c or 'Enrol' in c or 'Enrollment' in c), None)
    if payroll_enrl_col:
        payroll_df['Enrollment_Code'] = payroll_df[payroll_enrl_col].astype(str).str.strip()
        payroll_df['Plan_Code'] = payroll_df['Enrollment_Code'].str[:2]
        payroll_df['Enrollment_Type'] = payroll_df['Enrollment_Code'].apply(determine_enrollment_type)
        if plan_option_counts:
            payroll_df['Option_Index'] = payroll_df.apply(
                lambda r: determine_option_slot(plan_option_counts, r.get('Plan_Code'), r.get('Enrollment_Code')),
                axis=1
            )
        else:
            payroll_df['Option_Index'] = 0
    else:
        payroll_df['Enrollment_Code'] = None
        payroll_df['Plan_Code'] = None
        payroll_df['Enrollment_Type'] = None
        payroll_df['Option_Index'] = None

    merge_keys_left = []
    merge_keys_right = []
    if plan_code_col:
        merge_keys_left.append(plan_code_col)
        merge_keys_right.append('Plan_Code')
    if 'Option_Index' in parsed_df.columns and 'Option_Index' in payroll_df.columns:
        merge_keys_left.append('Option_Index')
        merge_keys_right.append('Option_Index')

    if merge_keys_left and payroll_enrl_col:
        merged = parsed_df.merge(
            payroll_df,
            left_on=merge_keys_left,
            right_on=merge_keys_right,
            how='left',
            suffixes=('', '_payroll')
        )
    else:
        merged = parsed_df.copy()

    # Clean duplicate metadata columns from merge
    if plan_code_col == 'Plan_Code' and 'Plan_Code_payroll' in merged.columns:
        merged.drop(columns=['Plan_Code_payroll'], inplace=True)
    if 'Option_Index_payroll' in merged.columns:
        merged.drop(columns=['Option_Index_payroll'], inplace=True)

    # Derive premium columns from payroll data
    for src, dest in [
        ('Gov_Pays', 'Biweekly_Govt'),
        ('Emp_Pays', 'Biweekly_Emp'),
        ('SE_Pays', 'Biweekly_Total_Self'),
        ('TCC_Pays', 'Biweekly_TCC'),
        ('MGov_Pays', 'Monthly_Govt'),
        ('MEmp_Pays', 'Monthly_Emp'),
        ('MSE_Pays', 'Monthly_Total_Self'),
        ('MTCC_Pays', 'Monthly_TCC')
    ]:
        if src in merged.columns:
            merged[dest] = merged[src]

    if 'Biweekly_Govt' in merged.columns or 'Biweekly_Emp' in merged.columns:
        merged['Biweekly_Total'] = merged[['Biweekly_Govt', 'Biweekly_Emp']].sum(axis=1, min_count=1)
    if 'Monthly_Govt' in merged.columns or 'Monthly_Emp' in merged.columns:
        merged['Monthly_Total'] = merged[['Monthly_Govt', 'Monthly_Emp']].sum(axis=1, min_count=1)

    if 'Monthly_Govt' in merged.columns:
        merged['Annual_Govt'] = merged['Monthly_Govt'] * 12
    if 'Monthly_Emp' in merged.columns:
        merged['Annual_Emp'] = merged['Monthly_Emp'] * 12

    # Fallback to biweekly calculations if monthly missing
    if 'Annual_Govt' in merged.columns and 'Biweekly_Govt' in merged.columns:
        merged.loc[merged['Annual_Govt'].isna(), 'Annual_Govt'] = merged['Biweekly_Govt'] * 26
    if 'Annual_Emp' in merged.columns and 'Biweekly_Emp' in merged.columns:
        merged.loc[merged['Annual_Emp'].isna(), 'Annual_Emp'] = merged['Biweekly_Emp'] * 26

    if 'Annual_Govt' in merged.columns and 'Annual_Emp' in merged.columns:
        merged['Annual_Total'] = merged[['Annual_Govt', 'Annual_Emp']].sum(axis=1, min_count=1)

    # Coverage split percentages
    if 'Biweekly_Total' in merged.columns:
        total = merged['Biweekly_Total']
        if 'Biweekly_Govt' in merged.columns:
            merged['Govt_pct'] = (merged['Biweekly_Govt'] / total * 100).where(total.notna() & (total != 0))
        if 'Biweekly_Emp' in merged.columns:
            merged['Emp_pct'] = (merged['Biweekly_Emp'] / total * 100).where(total.notna() & (total != 0))

    # Ensure enrollment metadata is populated
    if 'Enrollment_Code' in merged.columns and 'Enrollment_Code_payroll' in merged.columns:
        merged['Enrollment_Code'] = merged['Enrollment_Code'].fillna(merged['Enrollment_Code_payroll'])
        merged.drop(columns=['Enrollment_Code_payroll'], inplace=True)
    elif 'Enrollment_Code_payroll' in merged.columns:
        merged.rename(columns={'Enrollment_Code_payroll': 'Enrollment_Code'}, inplace=True)

    if 'Enrollment_Type' not in merged.columns and 'Enrollment_Type_payroll' in merged.columns:
        merged.rename(columns={'Enrollment_Type_payroll': 'Enrollment_Type'}, inplace=True)
    elif 'Enrollment_Type' in merged.columns and 'Enrollment_Type_payroll' in merged.columns:
        merged['Enrollment_Type'] = merged['Enrollment_Type'].fillna(merged['Enrollment_Type_payroll'])
        merged.drop(columns=['Enrollment_Type_payroll'], inplace=True)

    if 'Enrollment_Type' in merged.columns:
        merged['Enrollment_Type'] = merged['Enrollment_Type'].fillna(
            merged['Enrollment_Code'].apply(determine_enrollment_type)
        )
    if 'Enrollment_Code' in merged.columns:
        enrollment_codes = merged['Enrollment_Code'].astype(str).str.strip()
        valid_mask = enrollment_codes.str.len() > 0
        valid_mask &= enrollment_codes.str.lower() != 'nan'
        merged = merged[valid_mask].copy()
        merged['Enrollment_Code'] = enrollment_codes[valid_mask]

    # If payroll band was requested, pick corresponding columns (agent must provide exact column-to-use)
    if payroll_band and payroll_band in merged.columns:
        merged['Selected_Payroll_Band'] = merged[payroll_band]
    elif payroll_band:
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
