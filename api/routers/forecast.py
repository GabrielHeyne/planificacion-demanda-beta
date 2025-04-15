from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
from ..methods.forecast_engine import ForecastEngine 

router = APIRouter(
    prefix="/forecast",
    tags=["forecast"],
    responses={404: {"description": "Not found"}},
)

class ForecastRequest(BaseModel):
    product_id: str
    historical_data: List[dict]
    forecast_horizon: int
    seasonality: Optional[int] = None

class ForecastResponse(BaseModel):
    product_id: str
    forecast: List[dict]
    metrics: dict

@router.post("/predict", response_model=ForecastResponse)
async def predict_forecast(request: ForecastRequest):
    try:
        # Convert historical data to DataFrame
        df = pd.DataFrame(request.historical_data)
        
        # Initialize forecast engine
        engine = ForecastEngine()
        
        # Generate forecast
        forecast, metrics = engine.generate_forecast(
            df,
            request.product_id,
            request.forecast_horizon,
            request.seasonality
        )
        
        return ForecastResponse(
            product_id=request.product_id,
            forecast=forecast.to_dict('records'),
            metrics=metrics
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
