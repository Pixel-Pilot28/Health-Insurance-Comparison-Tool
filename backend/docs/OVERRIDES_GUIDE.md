# OPM Parser Overrides Guide

## Overview

The OPM parser supports manual overrides to correct fuzzy mapping errors and fix specific parsing issues. Overrides are stored in `data/overrides.json` and are applied during the parsing process.

## Overrides File Structure

### Location
- Default: `backend/data/overrides.json`
- Custom: Specify with `--overrides /path/to/overrides.json`

### Schema

```json
{
  "version": "1.0",
  "last_updated": "2025-10-13T00:00:00Z",
  "description": "Manual overrides for OPM parser",
  
  "column_map": {
    "OPM_Column_Name": "Canonical_Internal_Name"
  },
  
  "plan_overrides": {
    "Plan_Key": {
      "Field_Name": value
    }
  },
  
  "ignore_columns": [
    "Column_To_Skip"
  ]
}
```

## Column Mapping Overrides

### Purpose
Manually map OPM column names that fuzzy mapping failed to match or matched incorrectly.

### How It Works
1. Parser first attempts fuzzy matching with configurable threshold (default 0.6)
2. If column unmapped or low confidence, check `column_map` for manual mapping
3. Manual mappings always override fuzzy matches

### Example

```json
"column_map": {
  "Biweekly - Ttl Premium 2025": "2025 Biweekly - Total Premium",
  "Annual deductible (Self)": "Annual Deductible Self",
  "PCP Visit": "Primary Care Office Visit",
  "Spec Visit": "Specialist Office Visit",
  "Ded. Self+1": "Annual Deductible Self Plus One"
}
```

### When to Use
- Fuzzy matching failed (column in unmapped list)
- Fuzzy matching chose wrong target
- Column name format changed between years
- Abbreviations that fuzzy matching doesn't recognize

## Plan-Specific Overrides

### Purpose
Correct parsing errors for specific plans. Applied AFTER automatic parsing completes.

### Plan Keys
Overrides are keyed by unique plan identifier:
- **Format 1**: `EnrollmentCode_<code>` (preferred)
  - Example: `"EnrollmentCode_474"`
- **Format 2**: `<Plan>__<Option>`
  - Example: `"Kaiser Permanente__Standard"`

### Field Names
Override keys must match normalized column names with suffixes:

**Available Suffixes**:
- `_raw` - Original text value
- `_money` - Copay amount
- `_percent` - Coinsurance percentage
- `_cap` - Maximum amount
- `_min_value` - Range minimum
- `_max_value` - Range maximum
- `_applies_after_deductible` - Boolean flag
- `_prior_authorization` - Boolean flag
- `_network_only` - Boolean flag
- `_first_visit_only` - Boolean flag
- `_visits_limit` - Integer visit count
- `_secondary_copay` - Second step copay
- `_secondary_coinsurance` - Second step coinsurance
- `_is_covered` - Boolean (true/false/null)

### Examples

#### Multi-Step Rule Correction
```json
"EnrollmentCode_474": {
  "Primary_Care_Office_Visit_raw": "$25 then 20% up to $500",
  "Primary_Care_Office_Visit_money": 25.0,
  "Primary_Care_Office_Visit_secondary_coinsurance": 20.0,
  "Primary_Care_Office_Visit_cap": 500.0,
  "Primary_Care_Office_Visit_applies_after_deductible": false,
  "_note": "Parser didn't capture 'then' correctly"
}
```

#### Coverage Status Fix
```json
"Kaiser Permanente__Standard": {
  "Emergency_Care_raw": "$150 copay, waived if admitted",
  "Emergency_Care_money": 150.0,
  "Emergency_Care_is_covered": true,
  "_note": "Waived clause not captured"
}
```

#### Flag Correction
```json
"BCBS Basic__High": {
  "Specialist_Office_Visit_money": 50.0,
  "Specialist_Office_Visit_prior_authorization": true,
  "Specialist_Office_Visit_network_only": false,
  "_note": "Manual flag update"
}
```

### Special Keys
- Keys starting with `_` (underscore) are ignored by parser
- Use `_note` to document why override was needed
- Use `_source` to track who made the change

## Ignore Columns

### Purpose
Skip columns entirely during parsing. Useful for:
- Internal/temporary columns in Excel file
- Columns with irrelevant data
- Columns that cause parsing errors

### Example
```json
"ignore_columns": [
  "Internal ID",
  "Temp Column",
  "Legacy Field XYZ",
  "Debug Info"
]
```

## Workflow

### 1. Initial Parse (No Overrides)
```bash
python scripts/parse_opm.py \
  --benefits inputs/2026-fehb-plan-benefits.xlsx \
  --payroll inputs/2026-fehb-payroll-rates.xlsx \
  --out data/health_plan_info_parsed.csv
```

This generates:
- `health_plan_info_parsed.csv` - Parsed data
- `parse_report.json` - Ambiguous cells and unmapped columns
- `column_map.json` - Column mapping results with suggestions

### 2. Review Parse Report

Check `parse_report.json`:
```json
{
  "ambiguous_cells": [
    {
      "plan": "GEHA Standard",
      "enrollment_code": "474",
      "column": "Primary Care Office Visit",
      "raw": "$25 then 20% up to $500"
    }
  ],
  "unmapped_columns": [
    "Ded. (Self)",
    "Spec Copay"
  ],
  "column_suggestions": {
    "Ded. (Self)": [
      ["Annual Deductible Self", 0.75],
      ["Annual Deductible Family", 0.45]
    ]
  }
}
```

### 3. Create overrides.json

Create `data/overrides.json`:
```json
{
  "version": "1.0",
  "last_updated": "2025-10-13T12:00:00Z",
  
  "column_map": {
    "Ded. (Self)": "Annual Deductible Self",
    "Spec Copay": "Specialist Office Visit"
  },
  
  "plan_overrides": {
    "EnrollmentCode_474": {
      "Primary_Care_Office_Visit_money": 25.0,
      "Primary_Care_Office_Visit_secondary_coinsurance": 20.0,
      "Primary_Care_Office_Visit_cap": 500.0,
      "_note": "Multi-step rule correction"
    }
  }
}
```

### 4. Reparse with Overrides
```bash
python scripts/parse_opm.py \
  --benefits inputs/2026-fehb-plan-benefits.xlsx \
  --payroll inputs/2026-fehb-payroll-rates.xlsx \
  --out data/health_plan_info_parsed.csv \
  --overrides data/overrides.json
```

Parser will:
1. Apply fuzzy column mapping
2. Apply manual column mappings from overrides
3. Parse all rows with NLP parser
4. Apply plan-specific overrides to correct parsing errors

### 5. Verify Results

Check updated `parse_report.json`:
- Unmapped columns should be reduced
- Ambiguous cells should be fewer
- Review any remaining issues

## CLI Options

```bash
python scripts/parse_opm.py \
  --benefits <path>           # Required: Benefits Excel file
  --payroll <path>            # Required: Payroll Excel file
  --out <path>                # Required: Output CSV path
  --overrides <path>          # Optional: Overrides JSON (default: data/overrides.json)
  --column-map-out <path>     # Optional: Save column map (default: data/column_map.json)
  --min-score <float>         # Optional: Fuzzy match threshold 0.0-1.0 (default: 0.6)
  --no-fuzzy                  # Optional: Disable fuzzy mapping
  --emit-legacy <path>        # Optional: Write legacy CSV
  --payroll-band <name>       # Optional: Select payroll band
```

## Best Practices

### 1. Start with Fuzzy Mapping
Don't create overrides immediately. Let fuzzy matching do its job first.

### 2. Review Suggestions
Check `column_suggestions` in `parse_report.json` before creating manual mappings.

### 3. Document Overrides
Use `_note` fields to explain why each override was needed. Future you will thank you.

### 4. Version Control
Commit `overrides.json` to git so changes are tracked.

### 5. Test Incrementally
Add one override at a time and reparse to verify it works as expected.

### 6. Use Enrollment Codes
Prefer `EnrollmentCode_<code>` over plan names because codes are more stable.

### 7. Be Specific
Only override the exact fields that are wrong. Don't override entire plans.

### 8. Validate Results
After applying overrides, spot-check a few plans to ensure parsing is correct.

## Troubleshooting

### Column Not Being Mapped
1. Check spelling in `column_map`
2. Verify column name appears in Excel file
3. Check if column is in `ignore_columns`
4. Try lowering `--min-score` threshold

### Plan Override Not Applied
1. Verify plan key format (`EnrollmentCode_<code>` or `<Plan>__<Option>`)
2. Check field names match normalized column names
3. Look for typos in field suffixes
4. Ensure JSON syntax is valid

### Parsing Still Wrong After Override
1. Check if field name includes proper suffix
2. Verify value types (string for raw, float for money, bool for flags)
3. Review parser output in CSV to see actual field names
4. Check parse_report.json for errors

### JSON Syntax Errors
- Use a JSON validator (jsonlint.com)
- Watch for trailing commas (not allowed in JSON)
- Ensure all strings use double quotes
- Check bracket/brace matching

## Integration with UI

The overrides system integrates with the OPM Reconciliation UI (future implementation):

1. **View Unmapped Columns**: UI displays unmapped columns with suggestions
2. **Accept Suggestion**: Click suggestion to add to `column_map`
3. **Edit Ambiguous Cell**: UI shows parsed fields, allows manual correction
4. **Save Override**: Manual edits saved to `plan_overrides`
5. **Reparse**: UI triggers reparse with updated overrides
6. **Export/Import**: Download/upload overrides.json for sharing

## Examples from Real Plans

### Example 1: GEHA Standard Multi-Step Copay
**Issue**: Parser didn't capture "then" step in "$25 then 20% up to $500"

**Solution**:
```json
"EnrollmentCode_474": {
  "Primary_Care_Office_Visit_money": 25.0,
  "Primary_Care_Office_Visit_secondary_coinsurance": 20.0,
  "Primary_Care_Office_Visit_cap": 500.0
}
```

### Example 2: BCBS Emergency Waiver
**Issue**: "Waived if admitted" not captured

**Solution**:
```json
"BCBS Basic__Standard": {
  "Emergency_Care_raw": "$150, waived if admitted",
  "Emergency_Care_money": 150.0,
  "_note": "Waiver clause needs manual review"
}
```

### Example 3: Kaiser Preventive Care
**Issue**: Parser marked as ambiguous instead of covered

**Solution**:
```json
"Kaiser Permanente__Standard": {
  "Preventive_Care_is_covered": true,
  "Preventive_Care_money": 0.0
}
```

### Example 4: Aetna Range
**Issue**: Parser didn't extract min/max from "$25-$50 per visit"

**Solution**:
```json
"EnrollmentCode_123": {
  "Specialist_Office_Visit_min_value": 25.0,
  "Specialist_Office_Visit_max_value": 50.0
}
```

## API Integration

When using the FastAPI endpoints:

### Get Current Overrides
```http
GET /api/opm/overrides
```

### Update Overrides
```http
POST /api/opm/overrides
Content-Type: application/json

{
  "version": "1.0",
  "column_map": {...},
  "plan_overrides": {...}
}
```

### Accept Column Suggestion
```http
POST /api/opm/accept-suggestion
Content-Type: application/json

{
  "column": "Ded. (Self)",
  "suggested_target": "Annual Deductible Self"
}
```

### Trigger Reparse
```http
POST /api/opm/reparse
```

## FAQ

**Q: Do overrides persist between parses?**
A: Yes, overrides.json is saved and reused unless you delete it.

**Q: Can I share overrides with colleagues?**
A: Yes, commit overrides.json to git and share the repository.

**Q: What happens if I override non-existent fields?**
A: Parser ignores them silently. Check field names carefully.

**Q: Can I undo an override?**
A: Yes, remove the entry from overrides.json and reparse.

**Q: Do overrides work without fuzzy mapping?**
A: Yes, use `--no-fuzzy` and provide complete column_map.

**Q: How do I know if my override worked?**
A: Check the output CSV and verify the field has your override value.

## See Also

- [Parser README](PARSER_README.md) - Main parser documentation
- [OPM Enhancement Plan](../OPM_ENHANCEMENT_PLAN.md) - Full feature specification
- [Fuzzy Mapping Guide](fuzzy_mapping.md) - Column mapping details
- [NLP Parser Guide](nlp_parser.md) - Benefit parsing rules
