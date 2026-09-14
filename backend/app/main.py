from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import markets, weather, ai_predictions, auth, profiles

app = FastAPI(
    title="EasyAgri API",
    description="Live-data agricultural marketplace with real market prices and weather",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes - All use real data sources
app.include_router(markets.router, prefix="/api/markets", tags=["Markets"])
app.include_router(weather.router, prefix="/api/weather", tags=["Weather"])
app.include_router(ai_predictions.router, prefix="/api/ai", tags=["AI Predictions"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["Profiles"])


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "EasyAgri API - Live Data Agricultural Marketplace",
        "version": "1.0.0",
        "data_sources": {
            "markets": "Government of India (data.gov.in / AGMARKNET)",
            "weather": "Open-Meteo",
            "business_data": "Supabase PostgreSQL"
        }
    }


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "supabase": "configured",
            "external_apis": "enabled"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )
