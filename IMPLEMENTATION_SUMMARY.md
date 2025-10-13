# OPM Excel Parser - Implementation Summary

## Overview

This feature branch adds comprehensive Excel parsing capabilities to the Health Plan Tool, allowing users to download and parse their own OPM FEHB plan data files.

## What Was Implemented

### 1. Core Parser (`scripts/parse_opm.py`)
- **CLI tool** for parsing FEHB benefit and payroll Excel files
- **Smart parsing** of money values, percentages, and text descriptions
- **Special flag detection** (after deductible, prior auth, network-only, etc.)
- **Column-specific handlers** for deductibles, coinsurance, PCP/specialist costs
- **Payroll merging** by enrollment code with band selection
- **Multi-format output**: parsed CSV, legacy CSV, and validation report

### 2. Parsing Helpers (`scripts/parse_helpers.py`)
- Modular, well-tested parsing functions
- `parse_money_percent()` - Extract dollars and percentages
- `detect_flags()` - Identify special conditions
- `parse_deductible()` - Handle individual/family deductibles
- `parse_coinsurance()` - Extract coinsurance rates
- `parse_specialist_split()` - Separate PCP/specialist costs
- `safe_float()` - Robust numeric conversion
- `normalize_column_name()` - Standardize field names

### 3. Comprehensive Testing (`tests/test_parse_helpers.py`)
- **41 unit tests** covering all parser functions
- Edge case handling (None, empty, malformed data)
- Multiple test scenarios per function
- All tests passing ✅

### 4. Parser Validation API (`routers/parser.py`)
- `GET /api/parser/report` - View ambiguous cells that need review
- `GET /api/parser/stats` - Get parsing statistics
- `GET /api/parser/sample/{plan_name}` - View sample parsed fields
- `GET /api/parser/plans` - List all parsed plans
- Integrated into main FastAPI application

### 5. Documentation
- **PARSER_README.md** - Complete usage guide with examples
- Installation instructions
- CLI options and examples
- Output file descriptions
- Parsing logic explanation
- Troubleshooting guide
- Integration examples

## File Structure

```
backend/
├── scripts/
│   ├── parse_opm.py              # Main parser CLI (290 lines)
│   ├── parse_helpers.py           # Parsing utilities (270 lines)
│   └── PARSER_README.md           # User documentation
├── routers/
│   └── parser.py                  # Validation API (205 lines)
├── tests/
│   └── test_parse_helpers.py      # Unit tests (260 lines)
├── inputs/
│   ├── 2026-fehb-plan-benefits_100525.xlsx
│   └── 2026-fehb-payroll-rates_100525.xlsx
├── data/
│   ├── health_plan_info_parsed.csv    # Parsed output
│   ├── health_plan_info_legacy.csv    # Legacy format
│   └── parse_report.json              # Validation report
├── requirements.txt               # Updated dependencies
└── main.py                        # Updated router registration
```

## Git Commits

1. **feat: Add OPM Excel parser with helper functions** (18af8c0)
   - Created parse_opm.py and parse_helpers.py
   - Added openpyxl dependency

2. **test: Add comprehensive unit tests for parser helpers** (ac3454f)
   - 41 passing unit tests
   - Added pytest dependency
   - Included sample data files

3. **feat: Add parser validation API and documentation** (4918a0b)
   - Created parser validation endpoints
   - Added comprehensive README
   - Integrated into FastAPI app

4. **fix: Add fallback imports for parser router** (206b0d3)
   - Fixed import compatibility issues

## Usage

### Parse New OPM Files

```bash
cd backend
python scripts/parse_opm.py \
  --benefits inputs/2026-fehb-plan-benefits_100525.xlsx \
  --payroll inputs/2026-fehb-payroll-rates_100525.xlsx \
  --out data/health_plan_info_parsed.csv \
  --emit-legacy data/health_plan_info.csv
```

### Check Parse Quality

```bash
# Run tests
python -m pytest tests/test_parse_helpers.py -v

# Start API server
python -m uvicorn main:app --reload

# Check validation endpoint
curl http://localhost:8000/api/parser/report
curl http://localhost:8000/api/parser/stats
```

## Parsed Data Format

For each benefit column, the parser creates:
- `<field>_raw` - Original text
- `<field>_money` - Extracted dollar amount
- `<field>_percent` - Extracted percentage  
- `<field>_applies_after_deductible` - Boolean flag
- `<field>_first_visit_only` - Boolean flag
- `<field>_network_only` - Boolean flag
- `<field>_prior_authorization` - Boolean flag

Plus special fields for deductibles:
- `<field>_ded_money` - Individual deductible
- `<field>_ded_money_max` - Family max
- `<field>_ded_per_person` - Per person flag
- `<field>_ded_family` - Family flag

## Dependencies Added

- `openpyxl==3.1.5` - Excel file reading
- `pytest==8.4.2` - Testing framework

## Next Steps for Full Integration

### Phase 2 (Future Work)

1. **Update Cost Calculator**
   - Modify `services/cost_calculator.py` to use `*_money` and `*_percent` fields
   - Implement flag-aware calculations (deductible, prior auth, network)
   - Add tests for new calculation logic

2. **UI Parser Checker**
   - Create Material-UI component to display parse report
   - Show statistics dashboard
   - Allow users to browse ambiguous cells
   - Provide plan comparison view

3. **Data Migration**
   - Script to convert legacy CSV to new format
   - Maintain backward compatibility during transition
   - Gradual rollout strategy

4. **Enhanced Parsing**
   - Machine learning for ambiguous cell classification
   - Historical data comparison
   - Multi-year analysis
   - Automatic OPM file download

## Testing Results

### Unit Tests: ✅ All 41 passing
- Money/percent extraction: 8 tests
- Flag detection: 7 tests  
- Deductible parsing: 4 tests
- Coinsurance parsing: 3 tests
- Specialist splitting: 4 tests
- Safe float conversion: 6 tests
- Column normalization: 5 tests
- Ambiguity detection: 4 tests

### Parser Execution: ✅ Successful
- Parsed 2026 FEHB files
- Generated health_plan_info_parsed.csv
- Created parse_report.json with validation data
- Legacy CSV output working

### API Endpoints: ⚠️ Ready (import fix applied)
- Endpoints defined and integrated
- Need server testing after import fix verification

## Known Issues & Notes

1. **Parse Report has many ambiguous cells** - This is expected. Many cells contain language like "subject to approval" or "may be covered" that requires human interpretation.

2. **Cost calculator not yet integrated** - The parsed format is ready, but the calculator still uses the legacy format. This is intentional to avoid breaking existing functionality.

3. **UI component incomplete** - Started a Material-UI parser checker but removed it to avoid incomplete code. API is ready for future UI integration.

4. **Legacy column mapping** - The legacy CSV output uses a simple subset of fields. Full mapping to match exact old format can be added if needed.

## Branch Status

**Branch:** `feature/opm-excel-parser`  
**Status:** Ready for review  
**Base:** `main`  
**Commits:** 4  
**Files Changed:** 12 files, ~1500 lines added  

## Merge Readiness

- ✅ All tests passing
- ✅ Documentation complete
- ✅ No breaking changes to existing code
- ✅ New feature is opt-in (user must run parser)
- ✅ API endpoints defined and integrated
- ⚠️ Cost calculator integration deferred to Phase 2
- ⚠️ UI component deferred to Phase 2

## How to Test

1. **Clone and checkout:**
   ```bash
   git checkout feature/opm-excel-parser
   cd backend
   pip install -r requirements.txt
   ```

2. **Run parser:**
   ```bash
   python scripts/parse_opm.py \
     --benefits inputs/2026-fehb-plan-benefits_100525.xlsx \
     --payroll inputs/2026-fehb-payroll-rates_100525.xlsx \
     --out data/test_parsed.csv
   ```

3. **Run tests:**
   ```bash
   python -m pytest tests/test_parse_helpers.py -v
   ```

4. **Check API:**
   ```bash
   python -m uvicorn main:app --reload
   # Visit http://localhost:8000/docs
   # Try /api/parser/report endpoint
   ```

## Questions?

Refer to `backend/scripts/PARSER_README.md` for detailed usage instructions.
