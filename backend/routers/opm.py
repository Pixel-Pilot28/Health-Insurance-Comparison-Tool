"""
OPM Parser Reconciliation API Router

Provides endpoints for:
- Fetching parse reports and results
- Managing overrides (column mappings and plan-specific corrections)
- Triggering parser reruns
- Downloading parsed CSV data
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import os
import subprocess
from pathlib import Path

router = APIRouter(prefix="/opm", tags=["OPM Parser"])

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = BASE_DIR / "scripts"
INPUTS_DIR = BASE_DIR / "inputs"

# File paths
PARSE_REPORT_PATH = DATA_DIR / "parse_report.json"
PARSED_CSV_PATH = DATA_DIR / "health_plan_info_parsed.csv"
LEGACY_CSV_PATH = DATA_DIR / "health_plan_info.csv"
OVERRIDES_PATH = DATA_DIR / "overrides.json"
COLUMN_MAP_PATH = DATA_DIR / "column_map.json"
BENEFITS_XLSX = INPUTS_DIR / "2026-fehb-plan-benefits_100525.xlsx"
PAYROLL_XLSX = INPUTS_DIR / "2026-fehb-payroll-rates_100525.xlsx"


# Pydantic models
class OverridesModel(BaseModel):
    version: str = "1.0"
    last_updated: Optional[str] = None
    description: Optional[str] = None
    column_map: Dict[str, str] = {}
    plan_overrides: Dict[str, Dict[str, Any]] = {}
    ignore_columns: List[str] = []
    notes: Optional[str] = None


class ColumnMappingModel(BaseModel):
    opm_column: str
    canonical_target: str


class ParserRunRequest(BaseModel):
    benefits_file: Optional[str] = None
    payroll_file: Optional[str] = None
    min_score: float = 0.6
    use_fuzzy: bool = True


class AmbiguousCellUpdate(BaseModel):
    plan: str
    enrollment_code: str
    column: str
    updates: Dict[str, Any]


# Utility functions
def load_json_file(path: Path) -> Dict:
    """Load JSON file or return empty dict if not exists"""
    if not path.exists():
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading {path.name}: {str(e)}")


def save_json_file(path: Path, data: Dict) -> None:
    """Save data to JSON file with pretty formatting"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving {path.name}: {str(e)}")


# Endpoints
@router.get("/parse-report")
async def get_parse_report():
    """
    Get the parse report with ambiguous cells, unmapped columns, and statistics.
    
    Returns:
        JSON object containing:
        - ambiguous_cells: List of cells that couldn't be parsed confidently
        - unmapped_columns: Columns that fuzzy mapping couldn't match
        - column_suggestions: Suggested mappings for unmapped columns
        - stats: Parsing statistics (total plans, columns, etc.)
        - timestamp: When the parse was run
    """
    if not PARSE_REPORT_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Parse report not found. Please run the parser first."
        )
    
    report = load_json_file(PARSE_REPORT_PATH)
    
    # Enhance report with additional metadata
    report["_meta"] = {
        "report_path": str(PARSE_REPORT_PATH),
        "csv_available": PARSED_CSV_PATH.exists(),
        "overrides_active": OVERRIDES_PATH.exists()
    }
    
    return JSONResponse(content=report)


@router.get("/parsed-csv")
async def get_parsed_csv():
    """
    Download the parsed CSV file.
    
    Returns:
        CSV file with all parsed plan data
    """
    if not PARSED_CSV_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Parsed CSV not found. Please run the parser first."
        )
    
    return FileResponse(
        path=PARSED_CSV_PATH,
        media_type="text/csv",
        filename="health_plan_info_parsed.csv"
    )


@router.get("/overrides")
async def get_overrides():
    """
    Get current overrides configuration.
    
    Returns:
        JSON object with column_map and plan_overrides
    """
    if not OVERRIDES_PATH.exists():
        # Return default structure if file doesn't exist
        return JSONResponse(content={
            "version": "1.0",
            "description": "No overrides configured yet",
            "column_map": {},
            "plan_overrides": {},
            "ignore_columns": []
        })
    
    overrides = load_json_file(OVERRIDES_PATH)
    return JSONResponse(content=overrides)


@router.post("/overrides")
async def save_overrides(payload: OverridesModel):
    """
    Save or update overrides configuration.
    
    Body:
        OverridesModel with column_map and plan_overrides
    
    Returns:
        Success status and saved overrides
    """
    # Add timestamp if not provided
    if not payload.last_updated:
        from datetime import datetime
        payload.last_updated = datetime.utcnow().isoformat() + "Z"
    
    # Convert to dict and save
    overrides_dict = payload.model_dump(exclude_none=True)
    save_json_file(OVERRIDES_PATH, overrides_dict)
    
    return JSONResponse(content={
        "status": "ok",
        "message": "Overrides saved successfully",
        "overrides": overrides_dict
    })


@router.get("/column-map")
async def get_column_map():
    """
    Get the column mapping results from last parse.
    
    Returns:
        JSON object with mapped columns, unmapped columns, and suggestions
    """
    if not COLUMN_MAP_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Column map not found. Run parser with --column-map-out flag."
        )
    
    column_map = load_json_file(COLUMN_MAP_PATH)
    return JSONResponse(content=column_map)


@router.post("/accept-suggestion")
async def accept_column_suggestion(mapping: ColumnMappingModel):
    """
    Accept a suggested column mapping and add it to overrides.
    
    Body:
        - opm_column: The OPM Excel column name
        - canonical_target: The target canonical field name
    
    Returns:
        Updated overrides
    """
    # Load current overrides
    overrides = load_json_file(OVERRIDES_PATH) if OVERRIDES_PATH.exists() else {
        "version": "1.0",
        "column_map": {},
        "plan_overrides": {}
    }
    
    # Add mapping
    if "column_map" not in overrides:
        overrides["column_map"] = {}
    
    overrides["column_map"][mapping.opm_column] = mapping.canonical_target
    
    # Update timestamp
    from datetime import datetime
    overrides["last_updated"] = datetime.utcnow().isoformat() + "Z"
    
    # Save
    save_json_file(OVERRIDES_PATH, overrides)
    
    return JSONResponse(content={
        "status": "ok",
        "message": f"Mapping added: '{mapping.opm_column}' → '{mapping.canonical_target}'",
        "overrides": overrides
    })


@router.post("/update-plan-override")
async def update_plan_override(update: AmbiguousCellUpdate):
    """
    Update a specific plan's parsed values.
    
    Body:
        - plan: Plan name
        - enrollment_code: Enrollment code
        - column: Column being updated
        - updates: Dict of field updates (e.g., {column_money: 25.0, column_cap: 500.0})
    
    Returns:
        Updated overrides
    """
    # Load current overrides
    overrides = load_json_file(OVERRIDES_PATH) if OVERRIDES_PATH.exists() else {
        "version": "1.0",
        "column_map": {},
        "plan_overrides": {}
    }
    
    # Generate plan key
    plan_key = f"EnrollmentCode_{update.enrollment_code}"
    
    # Initialize plan_overrides if needed
    if "plan_overrides" not in overrides:
        overrides["plan_overrides"] = {}
    
    if plan_key not in overrides["plan_overrides"]:
        overrides["plan_overrides"][plan_key] = {}
    
    # Add note about the update
    overrides["plan_overrides"][plan_key]["_note"] = f"Manual update for {update.column}"
    
    # Merge updates
    overrides["plan_overrides"][plan_key].update(update.updates)
    
    # Update timestamp
    from datetime import datetime
    overrides["last_updated"] = datetime.utcnow().isoformat() + "Z"
    
    # Save
    save_json_file(OVERRIDES_PATH, overrides)
    
    return JSONResponse(content={
        "status": "ok",
        "message": f"Override saved for {plan_key}",
        "plan_key": plan_key,
        "updates": update.updates,
        "overrides": overrides
    })


@router.post("/run-parser")
async def run_parser(request: Optional[ParserRunRequest] = None):
    """
    Trigger a parser run with optional parameters.
    
    Body (optional):
        - benefits_file: Path to benefits Excel file (default: 2026-fehb-plan-benefits_100525.xlsx)
        - payroll_file: Path to payroll Excel file (default: 2026-fehb-payroll-rates_100525.xlsx)
        - min_score: Fuzzy matching threshold (default: 0.6)
        - use_fuzzy: Enable/disable fuzzy mapping (default: true)
    
    Returns:
        Status of parser execution
    """
    if request is None:
        request = ParserRunRequest()
    
    # Build command
    benefits_file = request.benefits_file or str(BENEFITS_XLSX)
    payroll_file = request.payroll_file or str(PAYROLL_XLSX)
    
    # Verify input files exist
    if not Path(benefits_file).exists():
        raise HTTPException(status_code=404, detail=f"Benefits file not found: {benefits_file}")
    if not Path(payroll_file).exists():
        raise HTTPException(status_code=404, detail=f"Payroll file not found: {payroll_file}")
    
    # Build command
    cmd = [
        "python",
        str(SCRIPTS_DIR / "parse_opm.py"),
        "--benefits", benefits_file,
        "--payroll", payroll_file,
        "--out", str(PARSED_CSV_PATH),
        "--emit-legacy", str(LEGACY_CSV_PATH),
        "--column-map-out", str(COLUMN_MAP_PATH),
        "--min-score", str(request.min_score)
    ]
    
    # Add overrides if file exists
    if OVERRIDES_PATH.exists():
        cmd.extend(["--overrides", str(OVERRIDES_PATH)])
    
    # Add no-fuzzy flag if disabled
    if not request.use_fuzzy:
        cmd.append("--no-fuzzy")
    
    try:
        # Run parser
        result = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            # Check if output files were created
            output_exists = {
                "parsed_csv": PARSED_CSV_PATH.exists(),
                "parse_report": PARSE_REPORT_PATH.exists(),
                "column_map": COLUMN_MAP_PATH.exists()
            }
            
            return JSONResponse(content={
                "status": "success",
                "message": "Parser completed successfully",
                "outputs": output_exists,
                "stdout": result.stdout[-1000:] if result.stdout else "",  # Last 1000 chars
                "command": " ".join(cmd)
            })
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Parser execution failed",
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "command": " ".join(cmd)
                }
            )
    
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Parser execution timed out (>5 minutes)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running parser: {str(e)}")


@router.get("/stats")
async def get_parser_stats():
    """
    Get summary statistics about the parse.
    
    Returns:
        Statistics including total plans, ambiguous cells, unmapped columns, etc.
    """
    if not PARSE_REPORT_PATH.exists():
        raise HTTPException(status_code=404, detail="Parse report not found")
    
    report = load_json_file(PARSE_REPORT_PATH)
    
    stats = {
        "total_plans": report.get("total_plans", 0),
        "total_columns": report.get("total_columns", 0),
        "ambiguous_cells_count": len(report.get("ambiguous_cells", [])),
        "unmapped_columns_count": len(report.get("unmapped_columns", [])),
        "timestamp": report.get("timestamp", "unknown"),
        "overrides_active": OVERRIDES_PATH.exists(),
        "files_available": {
            "parsed_csv": PARSED_CSV_PATH.exists(),
            "column_map": COLUMN_MAP_PATH.exists(),
            "overrides": OVERRIDES_PATH.exists()
        }
    }
    
    return JSONResponse(content=stats)


@router.get("/ambiguous-cells")
async def get_ambiguous_cells(skip: int = 0, limit: int = 100):
    """
    Get paginated list of ambiguous cells.
    
    Query params:
        - skip: Number of items to skip (default: 0)
        - limit: Max items to return (default: 100)
    
    Returns:
        Paginated list of ambiguous cells
    """
    if not PARSE_REPORT_PATH.exists():
        raise HTTPException(status_code=404, detail="Parse report not found")
    
    report = load_json_file(PARSE_REPORT_PATH)
    ambiguous = report.get("ambiguous_cells", [])
    
    total = len(ambiguous)
    paginated = ambiguous[skip:skip + limit]
    
    return JSONResponse(content={
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": paginated,
        "has_more": (skip + limit) < total
    })


@router.delete("/overrides")
async def clear_overrides():
    """
    Delete the overrides file (reset to default).
    
    Returns:
        Success status
    """
    if OVERRIDES_PATH.exists():
        try:
            OVERRIDES_PATH.unlink()
            return JSONResponse(content={
                "status": "ok",
                "message": "Overrides cleared successfully"
            })
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting overrides: {str(e)}")
    else:
        return JSONResponse(content={
            "status": "ok",
            "message": "No overrides file to clear"
        })


@router.get("/health")
async def health_check():
    """
    Health check endpoint for OPM parser API.
    
    Returns:
        Status and availability of required files
    """
    return JSONResponse(content={
        "status": "healthy",
        "parser_available": (SCRIPTS_DIR / "parse_opm.py").exists(),
        "inputs_available": {
            "benefits": BENEFITS_XLSX.exists(),
            "payroll": PAYROLL_XLSX.exists()
        },
        "outputs_available": {
            "parsed_csv": PARSED_CSV_PATH.exists(),
            "parse_report": PARSE_REPORT_PATH.exists(),
            "column_map": COLUMN_MAP_PATH.exists(),
            "overrides": OVERRIDES_PATH.exists()
        },
        "data_dir": str(DATA_DIR),
        "scripts_dir": str(SCRIPTS_DIR)
    })
