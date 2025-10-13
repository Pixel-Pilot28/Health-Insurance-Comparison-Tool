# OPM Excel Parser

## Overview

The OPM Excel Parser is a Python tool that processes Federal Employee Health Benefits (FEHB) plan data from official OPM spreadsheets. It extracts benefit information, payroll rates, and parses complex cell values into machine-readable formats.

## Features

- **Automated Parsing**: Extracts money values, percentages, and special condition flags from raw text
- **Smart Column Detection**: Automatically identifies key columns (deductibles, copays, coinsurance, etc.)
- **Ambiguity Reporting**: Flags cells with unclear or complex language for manual review
- **Legacy Compatibility**: Can generate output in legacy format for backward compatibility
- **Payroll Merging**: Combines benefit and payroll data by enrollment code

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Key dependencies:
- `pandas` - Data manipulation
- `openpyxl` - Excel file reading
- `pytest` - Testing framework (dev)

## Usage

### Basic Usage

```bash
python scripts/parse_opm.py \
  --benefits inputs/2026-fehb-plan-benefits_100525.xlsx \
  --payroll inputs/2026-fehb-payroll-rates_100525.xlsx \
  --out data/health_plan_info_parsed.csv
```

### Options

| Option | Required | Description |
|--------|----------|-------------|
| `--benefits` | Yes | Path to the FEHB plan benefits Excel file |
| `--payroll` | Yes | Path to the FEHB payroll rates Excel file |
| `--out` | Yes | Path for the output parsed CSV file |
| `--emit-legacy` | No | Path to generate a legacy-format CSV |
| `--payroll-band` | No | Specific payroll band to use (if multiple bands exist) |

### Example with All Options

```bash
python scripts/parse_opm.py \
  --benefits inputs/2026-fehb-plan-benefits_100525.xlsx \
  --payroll inputs/2026-fehb-payroll-rates_100525.xlsx \
  --out data/health_plan_info_parsed.csv \
  --emit-legacy data/health_plan_info.csv \
  --payroll-band "Grade_1_4"
```

## Output Files

### 1. Parsed CSV (`health_plan_info_parsed.csv`)

The main output file with structured data. For each benefit column, the parser creates multiple fields:

- `<column_name>_raw` - Original text from the cell
- `<column_name>_money` - Extracted dollar amount (or None)
- `<column_name>_percent` - Extracted percentage (or None)
- `<column_name>_<flag>` - Boolean flags for special conditions

Example columns:
```
PCP_Office_Visit_raw: "$25 copay after deductible"
PCP_Office_Visit_money: 25.0
PCP_Office_Visit_percent: None
PCP_Office_Visit_applies_after_deductible: True
```

### 2. Parse Report (`parse_report.json`)

A JSON file listing ambiguous cells that couldn't be fully parsed:

```json
{
  "ambiguous_cells": [
    {
      "plan": "GEHA High Option",
      "enrollment_code": "N61",
      "column": "Specialist Visit",
      "raw": "May be covered after deductible is met"
    }
  ]
}
```

### 3. Legacy CSV (Optional)

If `--emit-legacy` is specified, generates a simplified CSV compatible with existing code.

## Parsing Logic

### Money and Percentage Extraction

The parser intelligently extracts monetary values and percentages:

**Examples:**
- `"$25 copay"` → `money: 25.0`
- `"20% coinsurance"` → `percent: 20.0`
- `"$500 deductible / $1,000 family max"` → `money: 500.0, money_max: 1000.0`
- `"Covered"` → `money: 0.0, percent: 0.0`
- `"Not Covered"` → `money: None, percent: None`

### Special Flags

Automatically detected from context:

- `applies_after_deductible` - Service requires deductible to be met
- `first_visit_only` - Cost applies only to first visit
- `network_only` - Coverage limited to in-network providers
- `prior_authorization` - Requires prior approval

### Column-Specific Parsing

**Deductibles:**
- Extracts individual and family amounts
- Detects "per person" vs "family maximum"

**Coinsurance:**
- Extracts percentage values
- Preserves context (e.g., "after deductible")

**PCP/Specialist:**
- Splits combined values like "$20 PCP / $35 Specialist"
- Handles percentage-based specialist costs

## Testing

### Run Unit Tests

```bash
cd backend
python -m pytest tests/test_parse_helpers.py -v
```

### Test Coverage

41 unit tests covering:
- Money and percentage extraction
- Flag detection
- Deductible parsing
- Coinsurance parsing
- PCP/Specialist splitting
- Edge cases and error handling

## Troubleshooting

### Common Issues

**1. "No module named 'openpyxl'"**
```bash
pip install openpyxl
```

**2. "pathspec did not match any files"**

Ensure you're running from the `backend` directory:
```bash
cd backend
python scripts/parse_opm.py ...
```

**3. Column not found errors**

The parser tries to auto-detect columns, but OPM may change column names. Check the Excel file and update the parser if needed.

### Validation

Always review the `parse_report.json` file after parsing. Ambiguous cells may require:
- Manual data entry
- Parser logic updates
- Business rule decisions

## Architecture

### Module Structure

```
backend/
├── scripts/
│   ├── parse_opm.py          # Main CLI script
│   └── parse_helpers.py      # Parsing helper functions
├── tests/
│   └── test_parse_helpers.py # Unit tests
├── inputs/                   # Source Excel files
├── data/                     # Output files
└── requirements.txt          # Python dependencies
```

### Key Functions

**`parse_money_percent(s)`**
- Extracts money and percentage values from text

**`detect_flags(raw)`**
- Identifies special conditions from cell text

**`parse_deductible(raw)`**
- Extracts deductible amounts and person/family markers

**`parse_coinsurance(raw)`**
- Extracts coinsurance percentages

**`safe_float(x)`**
- Safely converts values to float, handling currency symbols

## Integration

### Using Parsed Data in Code

```python
import pandas as pd

# Load parsed data
df = pd.read_csv('data/health_plan_info_parsed.csv')

# Access parsed values
for _, row in df.iterrows():
    plan_name = row['Plan']
    pcp_copay = row['PCP_Office_Visit_money']
    requires_deductible = row['PCP_Office_Visit_applies_after_deductible']
    
    if pcp_copay and not requires_deductible:
        print(f"{plan_name}: ${pcp_copay} copay, no deductible")
```

### Cost Calculator Integration

To use the new parsed format in cost calculations:

1. Update service cost lookups to use `*_money` and `*_percent` fields
2. Check `*_applies_after_deductible` flags before applying copays
3. Handle `*_network_only` flags in network calculations
4. Respect `*_prior_authorization` flags in eligibility checks

## Future Enhancements

Potential improvements:

- [ ] GUI interface for non-technical users
- [ ] Automatic OPM file download
- [ ] Historical data comparison
- [ ] Machine learning for ambiguous cell classification
- [ ] Multi-year data merging
- [ ] Enhanced validation rules
- [ ] Plan comparison reports

## Getting Help

For issues or questions:

1. Check the `parse_report.json` for parsing issues
2. Review the test suite for usage examples
3. Examine the helper function docstrings
4. Open an issue on the project repository

## License

See project LICENSE file.

## Contributors

Health Plan Tool Development Team
