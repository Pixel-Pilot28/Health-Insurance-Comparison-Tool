#!/usr/bin/env python3
"""
scripts/parse_opm.py

Usage:
  python scripts/parse_opm.py \
    --benefits /path/to/2026-fehb-plan-benefits_100525.xlsx \
    --payroll /path/to/2026-fehb-payroll-rates_100525.xlsx \
    --out /path/to/health_plan_info_parsed.csv \
    [--emit-legacy /path/to/health_plan_info.csv] \
    [--payroll-band BAND_NAME]

Produces:
  - health_plan_info_parsed.csv
  - parse_report.json
  - (optional) health_plan_info.csv -- mapped to legacy schema for backward compatibility
"""
import argparse
import json
import sys
from pathlib import Path
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

# -----------------------
# Main transformation
# -----------------------
def transform(benefits_path, payroll_path, out_csv, legacy_out=None, payroll_band=None):
    benefits_df = pd.read_excel(benefits_path, sheet_name=0, engine='openpyxl')
    payroll_df = pd.read_excel(payroll_path, sheet_name=0, engine='openpyxl')
    # normalize column names to simple str
    benefits_df.columns = [str(c).strip() for c in benefits_df.columns]
    payroll_df.columns = [str(c).strip() for c in payroll_df.columns]

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
            parsed = parse_money_percent(raw_val)
            key_base = normalize_column_name(c)
            out[f"{key_base}_raw"] = parsed['raw']
            out[f"{key_base}_money"] = parsed['money']
            out[f"{key_base}_percent"] = parsed['percent']
            # flags
            flags = detect_flags(parsed['raw'])
            for fk, fv in flags.items():
                out[f"{key_base}_{fk}"] = fv
            # column-specific parsing examples
            # adjust these keys to the actual column names in your sheet for better accuracy
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

            # record ambiguous cells (no numeric parsed but raw contains words like 'after', 'may', 'or') 
            if is_ambiguous_cell(parsed, parsed['raw']):
                report['ambiguous_cells'].append({
                    'plan': out.get('Plan'),
                    'enrollment_code': out.get('Enrollment_Code'),
                    'column': c,
                    'raw': parsed['raw']
                })
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

    # Save parse report
    report_path = Path(out_path.parent) / 'parse_report.json'
    with open(report_path, 'w') as fh:
        json.dump(report, fh, indent=2)

    print(f"Saved parsed CSV to {out_path}")
    print(f"Saved parse report to {report_path}")
    if legacy_out:
        print(f"Saved legacy CSV to {legacy_out}")

# -----------------------
# CLI
# -----------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--benefits', required=True)
    parser.add_argument('--payroll', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--emit-legacy', dest='legacy', help='Write legacy health_plan_info.csv', default=None)
    parser.add_argument('--payroll-band', default=None, help='Choose payroll column/band to use from payroll file')
    args = parser.parse_args()
    transform(args.benefits, args.payroll, args.out, legacy_out=args.legacy, payroll_band=args.payroll_band)

if __name__ == '__main__':
    main()
