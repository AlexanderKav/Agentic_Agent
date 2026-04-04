# app/api/v1/models/responses.py
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class AnalysisResponse(BaseModel):
    """Response model for analysis endpoint"""
    success: bool = Field(..., description="Whether the analysis was successful")
    insights: str = Field(..., description="Human-readable insights")
    raw_insights: dict[str, Any] | None = Field(None, description="Raw insight data from AI")
    results: dict[str, Any] | None = Field(None, description="Structured analysis results")
    plan: dict[str, Any] | None = Field(None, description="Execution plan that was followed")
    warnings: list[str] | None = Field(None, description="Any warnings during analysis")
    charts: dict[str, str] | None = Field(None, description="Generated chart filenames")
    execution_time: float | None = Field(None, description="Analysis execution time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "insights": "Your business generated $1,234,567 in revenue with a 25.5% profit margin. "
                           "Your top customer is Acme Corp contributing $456,789.",
                "raw_insights": {
                    "answer": "Here's your business overview...",
                    "confidence_score": 0.95
                },
                "results": {
                    "kpis": {
                        "total_revenue": 1234567,
                        "profit_margin": 0.255,
                        "total_customers": 150
                    }
                },
                "plan": {"plan": ["compute_kpis", "analyze_trends"]},
                "warnings": [],
                "charts": {"revenue_trend": "chart_abc123.png"},
                "execution_time": 2.34
            }
        }


class FileUploadResponse(BaseModel):
    """Response after file upload"""
    filename: str = Field(..., description="Original filename")
    rows: int = Field(..., description="Number of rows in the file")
    columns: list[str] = Field(..., description="Column names")
    preview: list[dict[str, Any]] = Field(..., description="First 5 rows of data for preview")
    analysis_results: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Analysis results (populated after processing)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "sales_data.csv",
                "rows": 1000,
                "columns": ["date", "revenue", "product", "customer"],
                "preview": [
                    {"date": "2024-01-01", "revenue": 10000, "product": "Widget A", "customer": "Acme Corp"},
                    {"date": "2024-01-02", "revenue": 15000, "product": "Widget B", "customer": "Beta LLC"}
                ],
                "analysis_results": {}
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status (healthy/unhealthy)")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="UTC timestamp of the health check")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str = Field(..., description="Human-readable error message")
    error_code: str | None = Field(None, description="Error code for programmatic handling")

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Invalid file type. Please upload CSV or Excel files.",
                "error_code": "INVALID_FILE_TYPE"
            }
        }


class PaginatedResponse(BaseModel):
    """Paginated response wrapper for list endpoints"""
    items: list[Any] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items across all pages")
    limit: int = Field(..., description="Number of items per page")
    offset: int = Field(..., description="Number of items skipped")
    has_more: bool = Field(..., description="Whether there are more items available")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "limit": 10,
                "offset": 0,
                "has_more": True
            }
        }


# For backward compatibility with history endpoints
AnalysisHistoryResponse = PaginatedResponse


__all__ = [
    'AnalysisResponse',
    'FileUploadResponse',
    'HealthResponse',
    'ErrorResponse',
    'PaginatedResponse',
    'AnalysisHistoryResponse',
]