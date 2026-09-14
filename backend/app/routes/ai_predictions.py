from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression
from app.database import get_supabase_client
from pydantic import BaseModel

router = APIRouter()


class PricePrediction(BaseModel):
    """Price prediction based on real historical data."""
    commodity: str
    predicted_price: float
    confidence: float
    model: str = "Linear Regression"
    based_on_observations: int
    forecast_date: str
    status: str = "AI_ESTIMATE"


class DemandPrediction(BaseModel):
    """Demand prediction based on real buyer records."""
    commodity: str
    predicted_demand: float
    unit: str = "quintals"
    confidence: float
    based_on_records: int
    forecast_date: str
    status: str = "AI_ESTIMATE"


def get_historical_prices(supabase, commodity: str, days: int = 90) -> List[dict]:
    """Fetch real historical prices from Supabase."""
    try:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        response = supabase.table("market_price_history").select("*").eq(
            "commodity", commodity
        ).gte("observed_at", cutoff).order("observed_at", desc=False).execute()
        
        return response.data if response.data else []
    except:
        return []


@router.post("/predict-price", response_model=PricePrediction)
async def predict_price(
    commodity: str = Query(..., description="Commodity name"),
    supabase=Depends(get_supabase_client)
):
    """
    Predict future commodity price using real historical data from Supabase.
    
    Requirements:
    - Minimum 7 stored observations in market_price_history
    - Uses Linear Regression on real prices
    - Returns AI_ESTIMATE label
    - Returns UNAVAILABLE_DATA if insufficient history
    """
    try:
        # Get real historical prices
        prices = get_historical_prices(supabase, commodity)
        
        if len(prices) < 7:
            return {
                "commodity": commodity,
                "predicted_price": 0,
                "confidence": 0,
                "based_on_observations": len(prices),
                "forecast_date": datetime.now().isoformat(),
                "status": "UNAVAILABLE_DATA"
            }
        
        # Prepare data for ML model
        X = np.arange(len(prices)).reshape(-1, 1)
        y = np.array([p.get("price", 0) for p in prices])
        
        # Train model on real data
        model = LinearRegression()
        model.fit(X, y)
        
        # Predict next value
        next_day = np.array([[len(prices)]])
        predicted = float(model.predict(next_day)[0])
        
        # Calculate confidence (R² score)
        score = model.score(X, y)
        confidence = min(max(score, 0), 1)
        
        return PricePrediction(
            commodity=commodity,
            predicted_price=round(predicted, 2),
            confidence=round(confidence, 2),
            based_on_observations=len(prices),
            forecast_date=(datetime.now() + timedelta(days=1)).isoformat(),
            status="AI_ESTIMATE"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict-demand", response_model=DemandPrediction)
async def predict_demand(
    commodity: str = Query(..., description="Commodity name"),
    supabase=Depends(get_supabase_client)
):
    """
    Predict demand for commodity using real buyer demand records from Supabase.
    
    Requirements:
    - Reads real buyer_demand table records
    - Returns AI_ESTIMATE label
    - Returns UNAVAILABLE_DATA if no demand records exist
    """
    try:
        # Get real buyer demand records
        response = supabase.table("buyer_demand").select("quantity").eq(
            "commodity", commodity
        ).execute()
        
        demands = response.data if response.data else []
        
        if not demands:
            return {
                "commodity": commodity,
                "predicted_demand": 0,
                "confidence": 0,
                "based_on_records": 0,
                "forecast_date": datetime.now().isoformat(),
                "status": "UNAVAILABLE_DATA"
            }
        
        # Calculate average demand from real records
        quantities = [d.get("quantity", 0) for d in demands if d.get("quantity")]
        avg_demand = np.mean(quantities) if quantities else 0
        
        # Use standard deviation for confidence
        if len(quantities) > 1:
            std = np.std(quantities)
            confidence = 1 / (1 + std / avg_demand) if avg_demand > 0 else 0
        else:
            confidence = 0.5
        
        return DemandPrediction(
            commodity=commodity,
            predicted_demand=round(avg_demand, 2),
            confidence=round(min(max(confidence, 0), 1), 2),
            based_on_records=len(demands),
            forecast_date=(datetime.now() + timedelta(days=7)).isoformat(),
            status="AI_ESTIMATE"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def get_models():
    """List available prediction models."""
    return {
        "models": [
            {
                "name": "Linear Regression",
                "type": "price_prediction",
                "min_observations": 7,
                "description": "Trends price based on historical market data"
            },
            {
                "name": "Demand Averaging",
                "type": "demand_prediction",
                "min_records": 1,
                "description": "Averages buyer demand records"
            }
        ],
        "data_source": "Real Supabase records only",
        "demo_data": False
    }
