# OPM Reconciliation API Documentation

Complete API reference for the OPM Parser Reconciliation endpoints.

## Base URL

```
http://localhost:8000/api/opm
```

## Authentication

Currently no authentication required. Add authentication middleware if deploying to production.

## Endpoints

### 1. Health Check

Check if the OPM parser API is running and all required files are available.

**Endpoint:** `GET /opm/health`

**Response:**
```json
{
  "status": "healthy",
  "parser_available": true,
  "inputs_available": {
    "benefits": true,
    "payroll": true
  },
  "outputs_available": {
    "parsed_csv": true,
    "parse_report": true,
    "column_map": true,
    "overrides": false
  },
  "data_dir": "C:\\path\\to\\backend\\data",
  "scripts_dir": "C:\\path\\to\\backend\\scripts"
}
```

---

### 2. Get Parse Report

Fetch the complete parse report including ambiguous cells, unmapped columns, and statistics.

**Endpoint:** `GET /opm/parse-report`

**Response:**
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
  },
  "total_plans": 250,
  "total_columns": 85,
  "timestamp": "2025-10-13T12:00:00Z",
  "_meta": {
    "report_path": "C:\\path\\to\\parse_report.json",
    "csv_available": true,
    "overrides_active": false
  }
}
```

**Status Codes:**
- `200 OK` - Report retrieved successfully
- `404 Not Found` - Parse report doesn't exist (parser hasn't been run)

---

### 3. Get Parsed CSV

Download the parsed CSV file with all plan data.

**Endpoint:** `GET /opm/parsed-csv`

**Response:** Binary CSV file

**Headers:**
- `Content-Type: text/csv`
- `Content-Disposition: attachment; filename="health_plan_info_parsed.csv"`

**Status Codes:**
- `200 OK` - File downloaded successfully
- `404 Not Found` - CSV file doesn't exist

---

### 4. Get Overrides

Retrieve current overrides configuration (column mappings and plan-specific corrections).

**Endpoint:** `GET /opm/overrides`

**Response:**
```json
{
  "version": "1.0",
  "last_updated": "2025-10-13T12:00:00Z",
  "description": "Manual parser overrides",
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
  },
  "ignore_columns": []
}
```

**Status Codes:**
- `200 OK` - Overrides retrieved (returns empty structure if file doesn't exist)

---

### 5. Save Overrides

Save or update the overrides configuration.

**Endpoint:** `POST /opm/overrides`

**Request Body:**
```json
{
  "version": "1.0",
  "description": "Updated overrides",
  "column_map": {
    "New Column": "Canonical Name"
  },
  "plan_overrides": {
    "EnrollmentCode_123": {
      "Field_Name": "value"
    }
  },
  "ignore_columns": ["Column to ignore"]
}
```

**Response:**
```json
{
  "status": "ok",
  "message": "Overrides saved successfully",
  "overrides": { /* saved overrides */ }
}
```

**Status Codes:**
- `200 OK` - Overrides saved successfully
- `500 Internal Server Error` - Failed to save file

---

### 6. Get Column Map

Retrieve column mapping results from the last parse.

**Endpoint:** `GET /opm/column-map`

**Response:**
```json
{
  "mapped": {
    "Primary Care Visit": "Primary_Care_Office_Visit",
    "Specialist Visit": "Specialist_Office_Visit"
  },
  "unmapped": [
    "Ded. (Self)",
    "Spec Copay"
  ],
  "suggestions": {
    "Ded. (Self)": [
      ["Annual Deductible Self", 0.75],
      ["Annual Deductible Family", 0.45],
      ["Deductible Individual", 0.60]
    ]
  },
  "timestamp": "2025-10-13T12:00:00Z"
}
```

**Status Codes:**
- `200 OK` - Column map retrieved
- `404 Not Found` - Column map file doesn't exist (run parser with `--column-map-out`)

---

### 7. Accept Column Suggestion

Accept a suggested column mapping and add it to overrides.

**Endpoint:** `POST /opm/accept-suggestion`

**Request Body:**
```json
{
  "opm_column": "Ded. (Self)",
  "canonical_target": "Annual Deductible Self"
}
```

**Response:**
```json
{
  "status": "ok",
  "message": "Mapping added: 'Ded. (Self)' → 'Annual Deductible Self'",
  "overrides": { /* updated overrides */ }
}
```

**Status Codes:**
- `200 OK` - Mapping accepted and saved
- `500 Internal Server Error` - Failed to save overrides

---

### 8. Update Plan Override

Update a specific plan's parsed values (for fixing ambiguous cells).

**Endpoint:** `POST /opm/update-plan-override`

**Request Body:**
```json
{
  "plan": "GEHA Standard",
  "enrollment_code": "474",
  "column": "Primary Care Office Visit",
  "updates": {
    "Primary_Care_Office_Visit_money": 25.0,
    "Primary_Care_Office_Visit_secondary_coinsurance": 20.0,
    "Primary_Care_Office_Visit_cap": 500.0
  }
}
```

**Response:**
```json
{
  "status": "ok",
  "message": "Override saved for EnrollmentCode_474",
  "plan_key": "EnrollmentCode_474",
  "updates": { /* applied updates */ },
  "overrides": { /* full overrides object */ }
}
```

**Status Codes:**
- `200 OK` - Override saved successfully
- `500 Internal Server Error` - Failed to save

---

### 9. Run Parser

Trigger a parser execution with optional parameters.

**Endpoint:** `POST /opm/run-parser`

**Request Body (all optional):**
```json
{
  "benefits_file": "inputs/2026-fehb-plan-benefits_100525.xlsx",
  "payroll_file": "inputs/2026-fehb-payroll-rates_100525.xlsx",
  "min_score": 0.6,
  "use_fuzzy": true
}
```

**Response (Success):**
```json
{
  "status": "success",
  "message": "Parser completed successfully",
  "outputs": {
    "parsed_csv": true,
    "parse_report": true,
    "column_map": true
  },
  "stdout": "... last 1000 chars of output ...",
  "command": "python scripts/parse_opm.py --benefits ... --payroll ..."
}
```

**Response (Error):**
```json
{
  "status": "error",
  "message": "Parser execution failed",
  "returncode": 1,
  "stdout": "... output ...",
  "stderr": "... error messages ...",
  "command": "python scripts/parse_opm.py ..."
}
```

**Status Codes:**
- `200 OK` - Parser completed successfully
- `404 Not Found` - Input files not found
- `500 Internal Server Error` - Parser execution failed
- `504 Gateway Timeout` - Parser took longer than 5 minutes

---

### 10. Get Statistics

Get summary statistics about the parse.

**Endpoint:** `GET /opm/stats`

**Response:**
```json
{
  "total_plans": 250,
  "total_columns": 85,
  "ambiguous_cells_count": 15,
  "unmapped_columns_count": 3,
  "timestamp": "2025-10-13T12:00:00Z",
  "overrides_active": true,
  "files_available": {
    "parsed_csv": true,
    "column_map": true,
    "overrides": true
  }
}
```

**Status Codes:**
- `200 OK` - Statistics retrieved
- `404 Not Found` - Parse report doesn't exist

---

### 11. Get Ambiguous Cells (Paginated)

Get a paginated list of ambiguous cells.

**Endpoint:** `GET /opm/ambiguous-cells?skip=0&limit=100`

**Query Parameters:**
- `skip` (optional, default: 0) - Number of items to skip
- `limit` (optional, default: 100) - Maximum items to return

**Response:**
```json
{
  "total": 45,
  "skip": 0,
  "limit": 100,
  "items": [
    {
      "plan": "GEHA Standard",
      "enrollment_code": "474",
      "column": "Primary Care Office Visit",
      "raw": "$25 then 20% up to $500"
    }
  ],
  "has_more": false
}
```

**Status Codes:**
- `200 OK` - Cells retrieved
- `404 Not Found` - Parse report doesn't exist

---

### 12. Clear Overrides

Delete the overrides file (reset to default).

**Endpoint:** `DELETE /opm/overrides`

**Response:**
```json
{
  "status": "ok",
  "message": "Overrides cleared successfully"
}
```

**Status Codes:**
- `200 OK` - Overrides cleared (or didn't exist)
- `500 Internal Server Error` - Failed to delete file

---

## Error Responses

All endpoints may return the following error formats:

### 404 Not Found
```json
{
  "detail": "Parse report not found. Please run the parser first."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error loading parse_report.json: [error message]"
}
```

---

## Usage Examples

### Complete Workflow Example

```javascript
// 1. Check if parser is ready
const health = await fetch('/api/opm/health').then(r => r.json());
console.log('Parser available:', health.parser_available);

// 2. Run the parser
const runResult = await fetch('/api/opm/run-parser', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ use_fuzzy: true, min_score: 0.6 })
}).then(r => r.json());

if (runResult.status === 'success') {
  // 3. Get the parse report
  const report = await fetch('/api/opm/parse-report').then(r => r.json());
  
  // 4. Handle unmapped columns
  for (const column of report.unmapped_columns) {
    const suggestions = report.column_suggestions[column];
    if (suggestions && suggestions.length > 0) {
      const [bestMatch, score] = suggestions[0];
      if (score > 0.7) {
        // Accept high-confidence suggestions automatically
        await fetch('/api/opm/accept-suggestion', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            opm_column: column,
            canonical_target: bestMatch
          })
        });
      }
    }
  }
  
  // 5. Handle ambiguous cells
  for (const cell of report.ambiguous_cells) {
    // Present to user for manual correction
    console.log('Ambiguous:', cell.plan, cell.column, cell.raw);
    // User edits in UI, then save:
    await fetch('/api/opm/update-plan-override', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plan: cell.plan,
        enrollment_code: cell.enrollment_code,
        column: cell.column,
        updates: {
          [`${cell.column.replace(/ /g, '_')}_money`]: 25.0
        }
      })
    });
  }
  
  // 6. Rerun parser with overrides
  await fetch('/api/opm/run-parser', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  });
  
  // 7. Download final CSV
  window.open('/api/opm/parsed-csv', '_blank');
}
```

### Python Example

```python
import requests

BASE_URL = 'http://localhost:8000/api/opm'

# Run parser
response = requests.post(f'{BASE_URL}/run-parser', json={
    'use_fuzzy': True,
    'min_score': 0.6
})
result = response.json()

if result['status'] == 'success':
    # Get parse report
    report = requests.get(f'{BASE_URL}/parse-report').json()
    
    # Get statistics
    stats = requests.get(f'{BASE_URL}/stats').json()
    print(f"Total plans: {stats['total_plans']}")
    print(f"Ambiguous cells: {stats['ambiguous_cells_count']}")
    
    # Accept a suggestion
    requests.post(f'{BASE_URL}/accept-suggestion', json={
        'opm_column': 'Ded. (Self)',
        'canonical_target': 'Annual Deductible Self'
    })
    
    # Download CSV
    csv_data = requests.get(f'{BASE_URL}/parsed-csv')
    with open('health_plans.csv', 'wb') as f:
        f.write(csv_data.content)
```

---

## Rate Limits

Currently no rate limits. Consider adding rate limiting for production:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@router.post("/run-parser")
@limiter.limit("5/minute")  # Max 5 parser runs per minute
async def run_parser(...):
    ...
```

---

## Webhooks (Future Enhancement)

Consider adding webhooks to notify external systems when parsing completes:

```python
# In run_parser endpoint:
if result.returncode == 0:
    # Trigger webhook
    if webhook_url := os.getenv('OPM_WEBHOOK_URL'):
        requests.post(webhook_url, json={
            'event': 'parse_complete',
            'timestamp': datetime.utcnow().isoformat(),
            'stats': { /* stats */ }
        })
```

---

## Security Considerations

### Production Deployment Checklist

1. **Add Authentication**: Require API keys or OAuth tokens
2. **Validate File Paths**: Prevent directory traversal attacks
3. **Limit File Sizes**: Set maximum upload sizes for Excel files
4. **Rate Limiting**: Prevent abuse of expensive operations (parser runs)
5. **CORS Configuration**: Restrict allowed origins
6. **Input Validation**: Sanitize all user inputs
7. **Audit Logging**: Log all override changes with user IDs
8. **Backup Overrides**: Version control overrides.json changes

### Example Authentication

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != os.getenv('API_KEY'):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials

@router.post("/run-parser")
async def run_parser(request: ParserRunRequest, token = Depends(verify_token)):
    # Protected endpoint
    ...
```

---

## Performance Optimization

### Caching

Add caching for frequently accessed endpoints:

```python
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

@router.get("/parse-report")
@cache(expire=300)  # Cache for 5 minutes
async def get_parse_report():
    ...
```

### Background Tasks

Run parser in background to avoid request timeout:

```python
from fastapi import BackgroundTasks

@router.post("/run-parser")
async def run_parser(background_tasks: BackgroundTasks):
    background_tasks.add_task(execute_parser)
    return {"status": "started", "message": "Parser running in background"}
```

---

## Testing

### Example Test Suite

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get('/api/opm/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'healthy'

def test_get_parse_report():
    response = client.get('/api/opm/parse-report')
    assert response.status_code in [200, 404]

def test_save_overrides():
    overrides = {
        'version': '1.0',
        'column_map': {'Test': 'Test_Field'},
        'plan_overrides': {}
    }
    response = client.post('/api/opm/overrides', json=overrides)
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_accept_suggestion():
    response = client.post('/api/opm/accept-suggestion', json={
        'opm_column': 'Test Column',
        'canonical_target': 'Test_Field'
    })
    assert response.status_code == 200
```

---

## Monitoring

### Recommended Metrics

- Parser execution time
- Ambiguous cells per parse
- Override save frequency
- API endpoint response times
- Error rates per endpoint

### Example Prometheus Integration

```python
from prometheus_client import Counter, Histogram

parse_runs = Counter('opm_parser_runs_total', 'Total parser executions')
parse_duration = Histogram('opm_parser_duration_seconds', 'Parser execution time')

@router.post("/run-parser")
async def run_parser(...):
    parse_runs.inc()
    with parse_duration.time():
        # Execute parser
        ...
```

---

## Support

For issues or questions:
- Check parse_report.json for detailed error information
- Review backend logs for API errors
- Consult OVERRIDES_GUIDE.md for override syntax
- Check PARSER_README.md for parser CLI usage

---

## Changelog

### Version 1.0.0 (2025-10-13)
- Initial release
- 14 REST endpoints
- Complete CRUD operations for overrides
- Parser execution management
- Statistics and health monitoring
