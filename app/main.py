# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
from dotenv import load_dotenv
import os

# Rate limiting imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import the routers correctly
from app.api.v1.endpoints import analysis, monitoring
from app.api.v1.models.responses import HealthResponse

from app.api.v1.endpoints import auth, email
load_dotenv()
# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title="Agentic Analyst API",
    description="Autonomous AI agent for business analytics",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)


app.include_router(auth.router)
app.include_router(email.router)

# Set up rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analysis.router)
app.include_router(monitoring.router)


@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Agentic Analyst API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/api/v1/analysis/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Global health check"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )