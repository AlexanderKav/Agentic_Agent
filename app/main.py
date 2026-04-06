# app/main.py
import os
from datetime import datetime

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Rate limiting imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Import the routers correctly
from app.api.v1.endpoints import analysis, auth, email, monitoring
from app.api.v1.endpoints.analysis import chart
from app.api.v1.models.responses import HealthResponse
from app.services.key_rotation import get_key_rotation_service

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

# Set up rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ==================== CORS CONFIGURATION ====================
# Get allowed origins from environment variable (for production)
# Default to local development origins
CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_STR.split(",")]

# Add common Vercel patterns for production
if os.getenv("ENVIRONMENT") == "production":
    ALLOWED_ORIGINS.extend([
        "https://agentic-analyst.vercel.app",
        "https://*.vercel.app",  # All Vercel preview deployments
    ])

# Remove duplicates while preserving order
ALLOWED_ORIGINS = list(dict.fromkeys(ALLOWED_ORIGINS))

print(f"🔧 CORS allowed origins: {ALLOWED_ORIGINS}")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== ROUTERS ====================
# Include routers
app.include_router(analysis.router)
app.include_router(monitoring.router)
app.include_router(auth.router)
app.include_router(email.router)

# Explicitly include chart router
app.include_router(chart.router, prefix="/api/v1/analysis", tags=["charts"])

# ==================== STARTUP EVENT ====================
@app.on_event("startup")
async def startup_event():
    """Run startup tasks"""
    # Create database tables
    from app.core.database import Base, engine

    print("🔧 Creating database tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables verified/created")

    # Check key rotation on startup
    rotation_service = get_key_rotation_service()
    rotation_service.check_and_rotate_if_needed('SECRET_KEY')
    rotation_service.check_and_rotate_if_needed('AUDIT_SECRET_KEY')

    # Enable database encryption extension (for PostgreSQL)
    from app.core.database import SessionLocal
    from app.core.encryption import get_db_encryption
    
    encryption = get_db_encryption()
    db = SessionLocal()
    try:
        encryption.enable_pgcrypto_extension(db)
        print("✅ pgcrypto extension enabled (PostgreSQL)")
    except Exception as e:
        print(f"⚠️ Could not enable pgcrypto: {e}")
    finally:
        db.close()
    
    # Log startup completion
    print("🚀 Agentic Analyst API started successfully!")
    print(f"📚 API Docs available at: /api/docs")
    print(f"❤️ Health check available at: /health")

# ==================== ENDPOINTS ====================
@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Agentic Analyst API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health",
        "environment": os.getenv("ENVIRONMENT", "development")
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Global health check"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


# ==================== MAIN ====================
if __name__ == "__main__":
    # For local development only
    # In production, use: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )