"""
Parser validation endpoint for checking parsed OPM data quality.
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import pandas as pd
from typing import Dict, Any, List

router = APIRouter(prefix="/api/parser", tags=["parser"])

DATA_DIR = Path(__file__).parent.parent / "data"
PARSE_REPORT_PATH = DATA_DIR / "parse_report.json"
PARSED_CSV_PATH = DATA_DIR / "health_plan_info_parsed.csv"


@router.get("/report")
async def get_parse_report() -> Dict[str, Any]:
    """
    Get the parse report showing ambiguous cells and parsing issues.
    
    Returns:
        Dict containing:
        - ambiguous_cells: List of cells that couldn't be fully parsed
        - total_ambiguous: Count of ambiguous cells
        - report_exists: Whether a report file was found
    """
    try:
        if not PARSE_REPORT_PATH.exists():
            return {
                "report_exists": False,
                "ambiguous_cells": [],
                "total_ambiguous": 0,
                "message": "No parse report found. Run the parser first."
            }
        
        with open(PARSE_REPORT_PATH, 'r') as f:
            report = json.load(f)
        
        ambiguous = report.get('ambiguous_cells', [])
        
        return {
            "report_exists": True,
            "ambiguous_cells": ambiguous[:100],  # Limit to first 100 for performance
            "total_ambiguous": len(ambiguous),
            "message": f"Found {len(ambiguous)} ambiguous cells"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading parse report: {str(e)}")


@router.get("/stats")
async def get_parse_stats() -> Dict[str, Any]:
    """
    Get statistics about the parsed data.
    
    Returns:
        Dict containing:
        - total_plans: Number of plans parsed
        - total_columns: Number of columns in parsed data
        - parsed_columns: Count of columns with *_money or *_percent suffixes
        - sample_plan: First plan name for verification
    """
    try:
        if not PARSED_CSV_PATH.exists():
            return {
                "parsed_data_exists": False,
                "message": "No parsed data found. Run the parser first."
            }
        
        df = pd.read_csv(PARSED_CSV_PATH, nrows=1000)  # Load first 1000 rows for stats
        
        # Count columns by type
        money_cols = [col for col in df.columns if col.endswith('_money')]
        percent_cols = [col for col in df.columns if col.endswith('_percent')]
        raw_cols = [col for col in df.columns if col.endswith('_raw')]
        flag_cols = [col for col in df.columns if any(
            col.endswith(f'_{flag}') for flag in 
            ['applies_after_deductible', 'first_visit_only', 'network_only', 'prior_authorization']
        )]
        
        # Get sample data
        sample_plan = df.iloc[0].get('Plan', 'Unknown') if len(df) > 0 else None
        
        return {
            "parsed_data_exists": True,
            "total_plans": len(df),
            "total_columns": len(df.columns),
            "parsed_column_types": {
                "money_fields": len(money_cols),
                "percent_fields": len(percent_cols),
                "raw_fields": len(raw_cols),
                "flag_fields": len(flag_cols)
            },
            "sample_plan": sample_plan,
            "message": f"Parsed data contains {len(df)} plans with {len(df.columns)} columns"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading parsed data: {str(e)}")


@router.get("/sample/{plan_name}")
async def get_plan_sample(plan_name: str, limit: int = 10) -> Dict[str, Any]:
    """
    Get a sample of parsed fields for a specific plan.
    
    Args:
        plan_name: Name of the plan to retrieve
        limit: Maximum number of parsed fields to return (default 10)
    
    Returns:
        Dict containing sample parsed fields with raw, money, and percent values
    """
    try:
        if not PARSED_CSV_PATH.exists():
            raise HTTPException(status_code=404, detail="No parsed data found")
        
        df = pd.read_csv(PARSED_CSV_PATH)
        
        # Find the plan
        plan_row = df[df['Plan'].str.contains(plan_name, case=False, na=False)]
        
        if len(plan_row) == 0:
            raise HTTPException(status_code=404, detail=f"Plan '{plan_name}' not found")
        
        plan_row = plan_row.iloc[0]
        
        # Extract parsed fields (those with _raw, _money, _percent)
        parsed_fields = []
        processed_bases = set()
        
        for col in df.columns:
            if col.endswith('_raw'):
                base = col[:-4]  # Remove '_raw' suffix
                if base in processed_bases:
                    continue
                processed_bases.add(base)
                
                field_data = {
                    "field_name": base,
                    "raw": plan_row.get(col),
                    "money": plan_row.get(f"{base}_money"),
                    "percent": plan_row.get(f"{base}_percent")
                }
                
                # Add any flags
                flags = {}
                for flag in ['applies_after_deductible', 'first_visit_only', 'network_only', 'prior_authorization']:
                    flag_col = f"{base}_{flag}"
                    if flag_col in df.columns:
                        flags[flag] = bool(plan_row.get(flag_col))
                
                if flags:
                    field_data['flags'] = flags
                
                # Only include fields that have some data
                if field_data['raw'] is not None or field_data['money'] is not None or field_data['percent'] is not None:
                    parsed_fields.append(field_data)
                
                if len(parsed_fields) >= limit:
                    break
        
        return {
            "plan_name": str(plan_row.get('Plan')),
            "enrollment_code": str(plan_row.get('Enrollment_Code')),
            "total_parsed_fields": len(processed_bases),
            "sample_fields": parsed_fields
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving plan sample: {str(e)}")


@router.get("/plans")
async def list_plans() -> Dict[str, Any]:
    """
    Get a list of all plans in the parsed data.
    
    Returns:
        Dict containing:
        - plans: List of plan names
        - total: Total number of plans
    """
    try:
        if not PARSED_CSV_PATH.exists():
            raise HTTPException(status_code=404, detail="No parsed data found")
        
        df = pd.read_csv(PARSED_CSV_PATH)
        
        plans = df[['Plan', 'Short_Name', 'Option', 'Enrollment_Code']].to_dict('records')
        
        return {
            "plans": plans,
            "total": len(plans)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing plans: {str(e)}")
