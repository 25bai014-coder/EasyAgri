from fastapi import APIRouter, Query, Depends, HTTPException, Header
from typing import Optional, List
from datetime import datetime, timedelta
import requests
from app.config import settings
from app.database import get_supabase_client
from pydantic import BaseModel

router = APIRouter()


class MarketPrice(BaseModel):
    """Real market price from government data."""
    commodity: str
    market: str
    state: str
    price: float
    unit: str = "₹/quintal"
    date: str
    source: str = "data.gov.in / AGMARKNET"


class MarketPriceHistory(BaseModel):
    """Historical market price stored in Supabase."""
    id: int
    commodity: str
    market: str
    price: float
    date: str
    observed_at: str


@router.get("/", response_model=List[MarketPrice])
async def get_live_markets(
    state: Optional[str] = Query(None, description="State name"),
    commodity: Optional[str] = Query(None, description="Commodity type"),
):
    """
    Fetch live market prices from Government of India AGMARKNET.
    
    Real data source: data.gov.in / AGMARKNET API
    - No demo data used
    - Only returned if DATA_GOV_IN_API_KEY is configured
    """
    if not settings.data_gov_in_api_key:
        return {
            "status": "UNAVAILABLE_DATA",
            "message": "Live market data requires DATA_GOV_IN_API_KEY configuration"
        }
    
    try:
        headers = {"X-API-Key": settings.data_gov_in_api_key}
        params = {}
        if state:
            params["state"] = state
        if commodity:
            params["commodity"] = commodity
        
        # Real API call to data.gov.in
        response = requests.get(
            "https://api.data.gov.in/resource/9ef84268-d588-465a-a5c0-3b405fcc2df8",
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            records = data.get("records", [])
            
            markets = []
            for record in records[:50]:  # Limit to 50 results
                try:
                    market = MarketPrice(
                        commodity=record.get("commodity", "Unknown"),
                        market=record.get("market", "Unknown"),
                        state=record.get("state", "Unknown"),
                        price=float(record.get("price", 0)),
                        unit="₹/quintal",
                        date=record.get("arrival_date", str(datetime.now().date())),
                        source="data.gov.in / AGMARKNET"
                    )
                    markets.append(market)
                except (ValueError, TypeError):
                    continue
            
            return markets if markets else {"status": "UNAVAILABLE_DATA", "message": "No market data available"}
        else:
            return {"status": "UNAVAILABLE_DATA", "message": f"API error: {response.status_code}"}
    
    except Exception as e:
        return {"status": "UNAVAILABLE_DATA", "message": str(e)}


@router.get("/history", response_model=List[MarketPriceHistory])
async def get_market_history(
    commodity: str = Query(..., description="Commodity name"),
    market: Optional[str] = Query(None, description="Market name"),
    days: int = Query(30, ge=1, le=365, description="Days of history"),
    supabase=Depends(get_supabase_client)
):
    """
    Retrieve historical market prices from Supabase.
    
    Used for AI price predictions - requires at least 7 stored observations.
    """
    try:
        query = supabase.table("market_price_history").select("*")
        
        if commodity:
            query = query.eq("commodity", commodity)
        if market:
            query = query.eq("market", market)
        
        # Filter by date range
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        query = query.gte("observed_at", cutoff_date)
        
        data = query.order("observed_at", desc=True).limit(100).execute()
        
        if not data.data:
            return {"status": "UNAVAILABLE_DATA", "message": "No historical data available for this commodity"}
        
        return data.data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_market_data(
    x_admin_token: str = Header(...),
    supabase=Depends(get_supabase_client)
):
    """
    Admin-only endpoint to synchronize live market data into Supabase history.
    
    Requires: X-Admin-Token header matching INGEST_ADMIN_TOKEN
    """
    if x_admin_token != settings.ingest_admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    
    if not settings.data_gov_in_api_key:
        raise HTTPException(status_code=400, detail="DATA_GOV_IN_API_KEY not configured")
    
    try:
        # Fetch current market data
        headers = {"X-API-Key": settings.data_gov_in_api_key}
        response = requests.get(
            "https://api.data.gov.in/resource/9ef84268-d588-465a-a5c0-3b405fcc2df8",
            headers=headers,
            timeout=10,
            params={"limit": 100}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch live market data")
        
        records = response.json().get("records", [])
        inserted_count = 0
        
        for record in records:
            try:
                # Insert into Supabase with real data only
                supabase.table("market_price_history").insert({
                    "commodity": record.get("commodity"),
                    "market": record.get("market"),
                    "state": record.get("state"),
                    "price": float(record.get("price", 0)),
                    "observed_at": datetime.now().isoformat()
                }).execute()
                inserted_count += 1
            except Exception:
                continue
        
        return {
            "status": "success",
            "synced_records": inserted_count,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_markets(
    query: str = Query(..., min_length=1, description="Search term (state, commodity, or market)"),
    supabase=Depends(get_supabase_client)
):
    """Search for markets and commodities in real stored data."""
    try:
        # Search in Supabase historical data
        results = supabase.table("market_price_history").select("*").execute()
        
        matched = []
        for record in results.data:
            if (query.lower() in record.get("commodity", "").lower() or
                query.lower() in record.get("market", "").lower()):
                matched.append(record)
        
        return matched if matched else {"status": "UNAVAILABLE_DATA", "message": "No matching markets found"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
