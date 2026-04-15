# OPM Parser Enhancement Implementation Plan

## Overview
This document provides a comprehensive plan for enhancing the OPM Excel parser with:
1. **Fuzzy Column Mapping** - Automatic mapping of OPM column names to normalized keys
2. **Manual Reconciliation GUI** - UI for reviewing and correcting ambiguous parses
3. **Extended NLP Parser** - Advanced parsing for complex benefit rules

## Phase 1: Core Infrastructure ✅ COMPLETED

### 1.1 Fuzzy Column Mapping Module ✅
**File**: `backend/scripts/opm_fuzzy_map.py`

**Features Implemented**:
- `normalize()` - Token-based string normalization (lowercase, punctuation removal, stopwords)
- `jaccard()` - Jaccard similarity coefficient for token overlap
- `seq_ratio()` - Sequence similarity using difflib
- `score_candidate()` - Weighted scoring (60% Jaccard + 40% sequence)
- `fuzzy_map_columns()` - Automatic column mapping with configurable threshold
- `suggest_mappings()` - Generate top-N suggestions for unmapped columns
- `apply_manual_overrides()` - Apply user corrections from overrides.json

**Test Coverage**: 60+ tests in `backend/tests/test_fuzzy_map.py`

### 1.2 Extended NLP Parser ✅
**File**: `backend/scripts/opm_nlp_parser.py`

**Features Implemented**:
- **Simple Rules**: `"$25"`, `"20%"`, `"$100-$200"` (ranges)
- **Multi-step Rules**: `"$25 then 20%"`, `"$25 then 20% up to $500"`
- **Alternative Rules**: `"$25 or 15%"`, `"20% or $50"`
- **Cap Rules**: `"20% up to $500"`, `"50% after deductible up to $1500"`
- **Visit Limits**: `"First 3 visits $25"`, `"Initial 5 visits covered"`
- **Flag Detection**:
  - `applies_after_deductible` - "after deductible", "deductible applies"
  - `first_visit_only` - "first visit only"
  - `network_only` - "network only", "in-network only"
  - `prior_authorization` - "prior authorization required"
- **Coverage Status**: `"No charge"`, `"Not covered"`, `"Covered in full"`

**Data Structure**: `BenefitRule` dataclass with fields:
- `copay`, `coinsurance`, `cap`
- `min_value`, `max_value` (for ranges)
- `secondary_copay`, `secondary_coinsurance` (for multi-step)
- `visits_limit`
- Boolean flags
- `is_covered` (None/True/False)
- `raw` (original text)

**Test Coverage**: 80+ tests in `backend/tests/test_nlp_parser.py`

## Phase 2: Parser Integration (IN PROGRESS)

### 2.1 Update parse_opm.py to Use New Modules
**File**: `backend/scripts/parse_opm.py`

**Changes Needed**:

```python
# Add imports at top
from opm_fuzzy_map import (
    fuzzy_map_columns, 
    apply_manual_overrides, 
    suggest_mappings
)
from opm_nlp_parser import ExtendedNLPParser

def load_overrides(overrides_path='data/overrides.json'):
    """Load manual column mapping overrides."""
    if os.path.exists(overrides_path):
        with open(overrides_path, 'r') as f:
            return json.load(f)
    return {}

def save_column_map(mapping, unmapped, suggestions, path='data/column_map.json'):
    """Save column mapping for reproducibility and UI display."""
    data = {
        'mapping': mapping,
        'unmapped': unmapped,
        'suggestions': suggestions,
        'timestamp': datetime.now().isoformat()
    }
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def transform(benefits_path, payroll_path, output_csv, output_legacy_csv, 
              output_json, overrides_path=None, column_map_path=None):
    """Enhanced transform with fuzzy mapping and NLP parsing."""
    
    # 1. Load Excel file
    benefits_df = pd.read_excel(benefits_path, sheet_name=0, header=0)
    
    # 2. Fuzzy map columns
    sheet_columns = list(benefits_df.columns)
    mapping, unmapped = fuzzy_map_columns(sheet_columns, min_score=0.6, verbose=True)
    
    # 3. Load and apply manual overrides
    if overrides_path:
        overrides = load_overrides(overrides_path)
        mapping = apply_manual_overrides(mapping, overrides.get('column_mapping', {}))
    
    # 4. Generate suggestions for unmapped columns
    suggestions = suggest_mappings(unmapped, top_n=3)
    
    # 5. Save column map
    if column_map_path:
        save_column_map(mapping, unmapped, suggestions, column_map_path)
    
    # 6. Rename columns using mapping
    # (Only rename columns that were successfully mapped)
    rename_dict = {k: v for k, v in mapping.items() if k in benefits_df.columns}
    benefits_df.rename(columns=rename_dict, inplace=True)
    
    # 7. Initialize NLP parser
    nlp_parser = ExtendedNLPParser()
    
    # 8. Process each benefit column with enhanced parsing
    parsed_data = []
    ambiguous_cells = []
    
    for idx, row in benefits_df.iterrows():
        row_data = {}
        
        for col in benefits_df.columns:
            cell_value = row[col]
            
            if pd.isna(cell_value) or cell_value == '':
                continue
            
            # Use NLP parser for benefit columns
            if should_parse_as_benefit(col):
                rule = nlp_parser.parse(str(cell_value))
                
                # Store parsed fields
                row_data[f'{col}_copay'] = rule.copay
                row_data[f'{col}_coinsurance'] = rule.coinsurance
                row_data[f'{col}_cap'] = rule.cap
                row_data[f'{col}_applies_after_deductible'] = rule.applies_after_deductible
                row_data[f'{col}_prior_authorization'] = rule.prior_authorization
                row_data[f'{col}_network_only'] = rule.network_only
                row_data[f'{col}_first_visit_only'] = rule.first_visit_only
                row_data[f'{col}_visits_limit'] = rule.visits_limit
                row_data[f'{col}_raw'] = rule.raw
                
                # Flag ambiguous if no clear parse
                if rule.copay is None and rule.coinsurance is None and rule.is_covered is None:
                    ambiguous_cells.append({
                        'plan': row.get('Plan Name', 'Unknown'),
                        'column': col,
                        'value': cell_value,
                        'row': idx
                    })
            else:
                # Non-benefit columns stored as-is
                row_data[col] = cell_value
        
        parsed_data.append(row_data)
    
    # 9. Create DataFrame from parsed data
    parsed_df = pd.DataFrame(parsed_data)
    
    # 10. Merge payroll data (existing logic)
    # ...
    
    # 11. Save outputs
    parsed_df.to_csv(output_csv, index=False)
    
    # 12. Update parse report with new information
    report = {
        'ambiguous_cells': ambiguous_cells,
        'unmapped_columns': unmapped,
        'column_suggestions': suggestions,
        'total_plans': len(parsed_df),
        'total_columns': len(parsed_df.columns),
        'timestamp': datetime.now().isoformat()
    }
    
    with open(output_json, 'w') as f:
        json.dump(report, f, indent=2)
    
    return parsed_df, report

def should_parse_as_benefit(column_name):
    """Determine if column should use NLP parser."""
    benefit_keywords = [
        'copay', 'coinsurance', 'deductible', 'visit', 'care',
        'hospital', 'surgery', 'diagnostic', 'tier', 'therapy',
        'prescription', 'drug', 'maximum', 'emergency', 'urgent'
    ]
    col_lower = column_name.lower()
    return any(kw in col_lower for kw in benefit_keywords)
```

**CLI Arguments to Add**:
```python
parser.add_argument('--overrides', help='Path to overrides.json', 
                   default='data/overrides.json')
parser.add_argument('--column-map', help='Path to save column_map.json',
                   default='data/column_map.json')
parser.add_argument('--min-score', type=float, default=0.6,
                   help='Minimum fuzzy match score (0.0-1.0)')
```

### 2.2 Overrides.json Schema
**File**: `backend/data/overrides.json`

```json
{
  "version": "1.0",
  "last_updated": "2025-10-13T10:30:00Z",
  "column_mapping": {
    "Ded. (Self)": "Annual Deductible Self",
    "PCP Visit": "Primary Care Office Visit",
    "Specialist": "Specialist Office Visit"
  },
  "cell_overrides": {
    "Kaiser Permanente Standard|Primary Care Office Visit": {
      "copay": 25.0,
      "coinsurance": null,
      "applies_after_deductible": false,
      "note": "Manual correction - parser confused by formatting"
    },
    "BCBS Basic|Emergency Care": {
      "copay": 150.0,
      "coinsurance": null,
      "cap": null,
      "note": "Waived if admitted - not captured by parser"
    }
  },
  "ignore_columns": [
    "Internal ID",
    "Legacy Field XYZ"
  ]
}
```

### 2.3 Column Map Output
**File**: `backend/data/column_map.json`

```json
{
  "timestamp": "2025-10-13T10:30:00Z",
  "mapping": {
    "Plan Name": "Plan Name",
    "Short Name": "Short Name",
    "Annual Ded. (Self)": "Annual Deductible Self",
    "PCP Office Visit": "Primary Care Office Visit"
  },
  "unmapped": [
    "Internal Code XYZ",
    "Custom Field ABC"
  ],
  "suggestions": {
    "Internal Code XYZ": [
      ["Plan Code", 0.42],
      ["Enrollment Code", 0.38],
      ["Brochure Number", 0.25]
    ],
    "Custom Field ABC": [
      ["Annual Deductible Self", 0.35],
      ["Type of Account", 0.28]
    ]
  }
}
```

## Phase 3: Backend API Endpoints (TODO)

### 3.1 Create New Router
**File**: `backend/routers/opm.py`

```python
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, List, Any
import json
import os
import subprocess

router = APIRouter(prefix="/api/opm", tags=["opm"])

@router.get("/parse-report")
async def get_parse_report():
    """Get parsing report with ambiguous cells."""
    path = "data/parse_report.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Parse report not found")
    
    with open(path, 'r') as f:
        return json.load(f)

@router.get("/column-map")
async def get_column_map():
    """Get column mapping with suggestions for unmapped columns."""
    path = "data/column_map.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Column map not found")
    
    with open(path, 'r') as f:
        return json.load(f)

@router.get("/overrides")
async def get_overrides():
    """Get current manual overrides."""
    path = "data/overrides.json"
    if not os.path.exists(path):
        return {
            "version": "1.0",
            "column_mapping": {},
            "cell_overrides": {},
            "ignore_columns": []
        }
    
    with open(path, 'r') as f:
        return json.load(f)

@router.post("/overrides")
async def save_overrides(overrides: Dict[str, Any] = Body(...)):
    """Save manual overrides."""
    path = "data/overrides.json"
    
    # Validate structure
    required_keys = ["version", "column_mapping", "cell_overrides"]
    if not all(k in overrides for k in required_keys):
        raise HTTPException(status_code=400, detail="Invalid overrides structure")
    
    with open(path, 'w') as f:
        json.dump(overrides, f, indent=2)
    
    return {"status": "success", "message": "Overrides saved"}

@router.post("/reparse")
async def trigger_reparse():
    """Trigger parser to re-run with current overrides."""
    try:
        result = subprocess.run([
            "python", "scripts/parse_opm.py",
            "--benefits", "inputs/2026-fehb-plan-benefits_100525.xlsx",
            "--payroll", "inputs/2026-fehb-payroll-rates_100525.xlsx",
            "--out", "data/health_plan_info_parsed.csv",
            "--overrides", "data/overrides.json",
            "--column-map", "data/column_map.json"
        ], capture_output=True, text=True, cwd="backend")
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, 
                              detail=f"Parser failed: {result.stderr}")
        
        return {
            "status": "success",
            "message": "Parser completed successfully",
            "output": result.stdout
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ambiguous-cells")
async def get_ambiguous_cells(plan: str = None, column: str = None):
    """Get list of ambiguous cells, optionally filtered."""
    path = "data/parse_report.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Parse report not found")
    
    with open(path, 'r') as f:
        report = json.load(f)
    
    cells = report.get('ambiguous_cells', [])
    
    # Apply filters
    if plan:
        cells = [c for c in cells if c.get('plan') == plan]
    if column:
        cells = [c for c in cells if c.get('column') == column]
    
    return cells

@router.post("/accept-suggestion")
async def accept_suggestion(
    column: str = Body(...),
    suggested_target: str = Body(...)
):
    """Accept a column mapping suggestion."""
    # Load current overrides
    overrides_path = "data/overrides.json"
    overrides = {}
    if os.path.exists(overrides_path):
        with open(overrides_path, 'r') as f:
            overrides = json.load(f)
    
    # Add to column mapping
    if 'column_mapping' not in overrides:
        overrides['column_mapping'] = {}
    
    overrides['column_mapping'][column] = suggested_target
    overrides['last_updated'] = datetime.now().isoformat()
    
    # Save
    with open(overrides_path, 'w') as f:
        json.dump(overrides, f, indent=2)
    
    return {"status": "success", "mapping": {column: suggested_target}}
```

**Integration**: Add to `main.py`:
```python
from routers import opm
app.include_router(opm.router)
```

## Phase 4: Frontend React Component (TODO)

### 4.1 OPM Reconciliation Component
**File**: `frontend/src/components/OpmReconcile.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import {
  Box, Card, CardContent, Typography, Button, TextField,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Chip, Dialog, DialogTitle, DialogContent, DialogActions,
  Select, MenuItem, FormControl, InputLabel, Tabs, Tab, Alert,
  CircularProgress, IconButton
} from '@mui/material';
import {
  CheckCircle, Cancel, Edit, Refresh, Download, Upload
} from '@mui/icons-material';
import { apiClient } from '../api/apiClient';

interface AmbiguousCell {
  plan: string;
  column: string;
  value: string;
  row: number;
}

interface ColumnSuggestion {
  target: string;
  score: number;
}

interface ColumnMap {
  mapping: Record<string, string>;
  unmapped: string[];
  suggestions: Record<string, ColumnSuggestion[]>;
  timestamp: string;
}

interface ParseReport {
  ambiguous_cells: AmbiguousCell[];
  unmapped_columns: string[];
  total_plans: number;
  total_columns: number;
}

export const OpmReconcile: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [parseReport, setParseReport] = useState<ParseReport | null>(null);
  const [columnMap, setColumnMap] = useState<ColumnMap | null>(null);
  const [loading, setLoading] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedCell, setSelectedCell] = useState<AmbiguousCell | null>(null);
  const [editedValues, setEditedValues] = useState<any>({});
  const [reparsing, setReparsing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [reportResp, mapResp] = await Promise.all([
        apiClient.get('/api/opm/parse-report'),
        apiClient.get('/api/opm/column-map')
      ]);
      setParseReport(reportResp.data);
      setColumnMap(mapResp.data);
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptSuggestion = async (column: string, target: string) => {
    try {
      await apiClient.post('/api/opm/accept-suggestion', {
        column,
        suggested_target: target
      });
      await loadData();  // Refresh
    } catch (error) {
      console.error('Failed to accept suggestion:', error);
    }
  };

  const handleReparse = async () => {
    setReparsing(true);
    try {
      await apiClient.post('/api/opm/reparse');
      await loadData();
    } catch (error) {
      console.error('Reparse failed:', error);
    } finally {
      setReparsing(false);
    }
  };

  const handleEditCell = (cell: AmbiguousCell) => {
    setSelectedCell(cell);
    setEditedValues({
      copay: null,
      coinsurance: null,
      applies_after_deductible: false
    });
    setEditDialogOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!selectedCell) return;
    
    try {
      const overrides = await apiClient.get('/api/opm/overrides');
      const key = `${selectedCell.plan}|${selectedCell.column}`;
      
      overrides.data.cell_overrides[key] = {
        ...editedValues,
        note: 'Manual correction from UI'
      };
      
      await apiClient.post('/api/opm/overrides', overrides.data);
      setEditDialogOpen(false);
      await loadData();
    } catch (error) {
      console.error('Failed to save edit:', error);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        OPM Parser Reconciliation
      </Typography>

      <Box display="flex" gap={2} mb={3}>
        <Button
          variant="contained"
          startIcon={<Refresh />}
          onClick={handleReparse}
          disabled={reparsing}
        >
          {reparsing ? 'Reparsing...' : 'Re-parse with Overrides'}
        </Button>
        <Button variant="outlined" startIcon={<Download />}>
          Export Overrides
        </Button>
        <Button variant="outlined" startIcon={<Upload />}>
          Import Overrides
        </Button>
      </Box>

      {parseReport && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Parsed {parseReport.total_plans} plans with {parseReport.total_columns} columns. 
          Found {parseReport.ambiguous_cells.length} ambiguous cells and{' '}
          {parseReport.unmapped_columns.length} unmapped columns.
        </Alert>
      )}

      <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 2 }}>
        <Tab label="Ambiguous Cells" />
        <Tab label="Column Mapping" />
        <Tab label="Statistics" />
      </Tabs>

      {/* Tab 1: Ambiguous Cells */}
      {activeTab === 0 && parseReport && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Ambiguous Benefit Cells
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              These cells couldn't be parsed automatically. Review and correct them manually.
            </Typography>
            
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Plan</TableCell>
                    <TableCell>Column</TableCell>
                    <TableCell>Original Value</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {parseReport.ambiguous_cells.map((cell, idx) => (
                    <TableRow key={idx}>
                      <TableCell>{cell.plan}</TableCell>
                      <TableCell>{cell.column}</TableCell>
                      <TableCell>
                        <code>{cell.value}</code>
                      </TableCell>
                      <TableCell>
                        <IconButton 
                          size="small" 
                          color="primary"
                          onClick={() => handleEditCell(cell)}
                        >
                          <Edit />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Tab 2: Column Mapping */}
      {activeTab === 1 && columnMap && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Column Mapping
            </Typography>
            
            {columnMap.unmapped.length > 0 && (
              <>
                <Typography variant="subtitle1" color="error" gutterBottom>
                  Unmapped Columns ({columnMap.unmapped.length})
                </Typography>
                {columnMap.unmapped.map((col) => (
                  <Card key={col} variant="outlined" sx={{ mb: 2, p: 2 }}>
                    <Typography variant="body1" fontWeight="bold">
                      {col}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Suggestions:
                    </Typography>
                    <Box display="flex" gap={1} flexWrap="wrap">
                      {columnMap.suggestions[col]?.map(([target, score], idx) => (
                        <Chip
                          key={idx}
                          label={`${target} (${(score * 100).toFixed(0)}%)`}
                          onClick={() => handleAcceptSuggestion(col, target)}
                          color={score > 0.8 ? 'success' : score > 0.6 ? 'warning' : 'default'}
                        />
                      ))}
                    </Box>
                  </Card>
                ))}
              </>
            )}

            <Typography variant="subtitle1" color="success.main" sx={{ mt: 3 }} gutterBottom>
              Mapped Columns ({Object.keys(columnMap.mapping).length})
            </Typography>
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>OPM Column</TableCell>
                    <TableCell>→</TableCell>
                    <TableCell>Internal Field</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(columnMap.mapping).map(([opm, internal]) => (
                    <TableRow key={opm}>
                      <TableCell>{opm}</TableCell>
                      <TableCell>→</TableCell>
                      <TableCell><strong>{internal}</strong></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Tab 3: Statistics */}
      {activeTab === 2 && parseReport && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Parsing Statistics
            </Typography>
            <Box display="grid" gridTemplateColumns="repeat(2, 1fr)" gap={2}>
              <Card variant="outlined">
                <CardContent>
                  <Typography color="text.secondary">Total Plans</Typography>
                  <Typography variant="h4">{parseReport.total_plans}</Typography>
                </CardContent>
              </Card>
              <Card variant="outlined">
                <CardContent>
                  <Typography color="text.secondary">Total Columns</Typography>
                  <Typography variant="h4">{parseReport.total_columns}</Typography>
                </CardContent>
              </Card>
              <Card variant="outlined">
                <CardContent>
                  <Typography color="text.secondary">Ambiguous Cells</Typography>
                  <Typography variant="h4" color="warning.main">
                    {parseReport.ambiguous_cells.length}
                  </Typography>
                </CardContent>
              </Card>
              <Card variant="outlined">
                <CardContent>
                  <Typography color="text.secondary">Unmapped Columns</Typography>
                  <Typography variant="h4" color="error.main">
                    {parseReport.unmapped_columns.length}
                  </Typography>
                </CardContent>
              </Card>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Edit Benefit Cell</DialogTitle>
        <DialogContent>
          {selectedCell && (
            <>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Plan: {selectedCell.plan} | Column: {selectedCell.column}
              </Typography>
              <Typography variant="body1" sx={{ mb: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
                Original: <code>{selectedCell.value}</code>
              </Typography>
              
              <Box display="grid" gap={2}>
                <TextField
                  label="Copay ($)"
                  type="number"
                  value={editedValues.copay || ''}
                  onChange={(e) => setEditedValues({
                    ...editedValues,
                    copay: parseFloat(e.target.value) || null
                  })}
                  fullWidth
                />
                <TextField
                  label="Coinsurance (%)"
                  type="number"
                  value={editedValues.coinsurance || ''}
                  onChange={(e) => setEditedValues({
                    ...editedValues,
                    coinsurance: parseFloat(e.target.value) || null
                  })}
                  fullWidth
                />
                <FormControl fullWidth>
                  <InputLabel>Applies After Deductible</InputLabel>
                  <Select
                    value={editedValues.applies_after_deductible}
                    onChange={(e) => setEditedValues({
                      ...editedValues,
                      applies_after_deductible: e.target.value
                    })}
                  >
                    <MenuItem value={false}>No</MenuItem>
                    <MenuItem value={true}>Yes</MenuItem>
                  </Select>
                </FormControl>
              </Box>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveEdit}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
```

### 4.2 Add Route to App
**File**: `frontend/src/App.tsx`

```typescript
import { OpmReconcile } from './components/OpmReconcile';

// Add route:
<Route path="/opm-reconcile" element={<OpmReconcile />} />
```

### 4.3 Add Navigation Link
Add link in settings or admin menu:
```typescript
<MenuItem onClick={() => navigate('/opm-reconcile')}>
  <ListItemIcon><Settings /></ListItemIcon>
  <ListItemText>OPM Parser Settings</ListItemText>
</MenuItem>
```

## Phase 5: Documentation (TODO)

### 5.1 Create Parser Documentation
**File**: `backend/docs/parser_enhancement.md`

Contents:
- Fuzzy mapping algorithm explanation
- NLP parser rule examples
- Overrides.json schema documentation
- UI workflow guide
- Troubleshooting guide
- API endpoint reference

### 5.2 Update PARSER_README.md
Add sections:
- Fuzzy column mapping
- Manual overrides
- Using the reconciliation UI
- Advanced parsing features

## Testing Strategy

### Unit Tests ✅
- `test_fuzzy_map.py` - 60+ tests for fuzzy matching
- `test_nlp_parser.py` - 80+ tests for benefit parsing

### Integration Tests (TODO)
- Test full parse workflow with fuzzy mapping
- Test overrides application
- Test API endpoints
- Test UI interactions

### Manual Testing Checklist (TODO)
- [ ] Upload OPM file and verify column mapping
- [ ] Review unmapped columns and accept suggestions
- [ ] Edit ambiguous cell and verify override saved
- [ ] Reparse with overrides and verify changes
- [ ] Export/import overrides
- [ ] Test with multiple OPM file formats (different years)

## Deployment Considerations

1. **Backward Compatibility**: 
   - Parser can run with or without fuzzy mapping
   - `--no-fuzzy` flag to disable new features
   - Legacy parse output still generated

2. **Performance**:
   - Fuzzy matching adds ~2-3 seconds per 100 columns
   - NLP parser adds ~1-2 seconds per 1000 cells
   - Acceptable for manual parser runs

3. **Data Migration**:
   - No migration needed
   - New features are opt-in
   - Existing parsed data remains valid

## Success Metrics

- **Automation**: >80% of columns auto-mapped correctly
- **Parsing Accuracy**: >90% of benefit cells parsed without manual review
- **User Efficiency**: <5 minutes to reconcile ambiguous items per file
- **Reliability**: <1% false positive rate on "covered" vs "not covered"

## Next Steps

1. ✅ Complete Phase 1 (Core Infrastructure)
2. 🔄 Complete Phase 2 (Parser Integration) - IN PROGRESS
3. ⏳ Complete Phase 3 (Backend API)
4. ⏳ Complete Phase 4 (Frontend UI)
5. ⏳ Complete Phase 5 (Documentation)
6. ⏳ Testing and refinement
7. ⏳ Merge to main branch
