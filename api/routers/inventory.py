from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
from ..methods.inventory_engine import InventoryEngine

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    responses={404: {"description": "Not found"}},
)

class InventoryRequest(BaseModel):
    product_id: str
    forecast_data: List[dict]

class InventoryResponse(BaseModel):
    product_id: str
    reorder_point: float
    adjusted_reorder_point: float
    safety_stock: float
    average_monthly_demand: float
    standard_deviation: float
    units_in_transit: float

@router.post("/analyze", response_model=InventoryResponse)
async def analyze_inventory(request: InventoryRequest):
    try:
        # Convert forecast data to DataFrame
        df_forecast = pd.DataFrame(request.forecast_data)
        
        # Initialize inventory engine
        engine = InventoryEngine()
        
        # Analyze inventory
        analysis = engine.inventory_by_sku(df_forecast, request.product_id)
        
        return InventoryResponse(**analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stock/{product_id}")
async def get_current_stock(product_id: str):
    try:
        # This would typically come from your database or data source
        # For now, returning a mock response
        return {
            "product_id": product_id,
            "current_stock": 100.0,
            "last_updated": "2024-03-14T12:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 