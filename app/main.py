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
from app.services.key_rotation import get_key_rotation_service

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

@app.on_event("startup")
async def startup_event():
    """Run startup tasks"""
    # Create database tables
    from app.core.database import engine, Base
    from app.api.v1.models import User, AnalysisHistory, AnalysisMetric, AnalysisInsight, AnalysisChart
    
    print("🔧 Creating database tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables verified/created")
    
    # Check key rotation on startup
    rotation_service = get_key_rotation_service()
    rotation_service.check_and_rotate_if_needed('SECRET_KEY')
    rotation_service.check_and_rotate_if_needed('AUDIT_SECRET_KEY')
    
    # Enable database encryption extension (for PostgreSQL)
    from app.core.encryption import get_db_encryption
    from app.core.database import SessionLocal
    encryption = get_db_encryption()
    db = SessionLocal()
    try:
        encryption.enable_pgcrypto_extension(db)
        print("✅ pgcrypto extension enabled (PostgreSQL)")
    except Exception as e:
        print(f"⚠️ Could not enable pgcrypto: {e}")
    finally:
        db.close()


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