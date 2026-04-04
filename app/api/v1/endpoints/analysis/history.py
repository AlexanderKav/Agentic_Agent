# app/api/v1/endpoints/analysis/history.py
import os
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.endpoints.auth import get_current_user
from app.api.v1.models.analysis import AnalysisHistory, AnalysisInsight, AnalysisMetric
from app.api.v1.models.user import User
from app.core.database import get_db

router = APIRouter()


@router.get("/history")
async def get_analysis_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0,
):
    """Get user's analysis history with optional metric filters."""
    query = db.query(AnalysisHistory).filter(AnalysisHistory.user_id == current_user.id)
    total = query.count()

    history = query.order_by(AnalysisHistory.created_at.desc()).offset(offset).limit(limit).all()

    result = []
    for h in history:
        summary_metrics = {}
        if hasattr(h, 'metrics') and h.metrics:
            revenue_metric = next((m for m in h.metrics if m.metric_type == 'total_revenue'), None)
            profit_metric = next((m for m in h.metrics if m.metric_type == 'profit_margin'), None)

            if revenue_metric:
                summary_metrics['total_revenue'] = float(revenue_metric.metric_value)
            if profit_metric:
                summary_metrics['profit_margin'] = float(profit_metric.metric_value)

        insight_count = len(h.insights) if hasattr(h, 'insights') and h.insights else 0

        result.append({
            "id": h.id,
            "type": h.analysis_type,
            "question": h.question,
            "created_at": h.created_at.isoformat(),
            "data_source": h.data_source,
            "summary_metrics": summary_metrics,
            "insight_count": insight_count
        })

    return {
        "items": result,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/history/{history_id}")
async def get_analysis_by_id(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_raw: bool = False,
):
    """Get specific analysis by ID with optional structured data."""
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == history_id,
        AnalysisHistory.user_id == current_user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    response = {
        "id": analysis.id,
        "type": analysis.analysis_type,
        "question": analysis.question,
        "created_at": analysis.created_at.isoformat(),
        "data_source": analysis.data_source,
        "structured_metrics": [],
        "insights": [],
        "charts": []
    }

    if hasattr(analysis, 'metrics') and analysis.metrics:
        metrics_by_category = {}
        for metric in analysis.metrics:
            metric_dict = {
                "metric_type": metric.metric_type,
                "metric_value": float(metric.metric_value) if metric.metric_value else None,
                "category": metric.category,
                "category_name": metric.category_name
            }
            if metric.metric_date:
                metric_dict["metric_date"] = metric.metric_date.isoformat()

            cat_key = metric.category or "general"
            if cat_key not in metrics_by_category:
                metrics_by_category[cat_key] = []
            metrics_by_category[cat_key].append(metric_dict)

        response["structured_metrics"] = metrics_by_category

    if hasattr(analysis, 'insights') and analysis.insights:
        insights_by_type = {}
        for insight in analysis.insights:
            insight_dict = {
                "text": insight.insight_text,
                "confidence_score": float(insight.confidence_score) if insight.confidence_score else None
            }
            if insight.insight_type not in insights_by_type:
                insights_by_type[insight.insight_type] = []
            insights_by_type[insight.insight_type].append(insight_dict)

        response["insights"] = insights_by_type

    if hasattr(analysis, 'charts') and analysis.charts:
        response["charts"] = [
            {
                "type": chart.chart_type,
                "path": chart.chart_path,
                "data": chart.chart_data
            }
            for chart in analysis.charts
        ]

    if include_raw and analysis.raw_results:
        response["raw_results"] = analysis.raw_results
    elif analysis.raw_results:
        response["raw_results_summary"] = {
            "has_raw_data": True,
            "note": "Use ?include_raw=true to get full raw results"
        }

    return response


@router.get("/history/{history_id}/metrics")
async def get_analysis_metrics(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    metric_type: str | None = None,
    category: str | None = None,
):
    """Get only structured metrics for an analysis (lightweight)."""
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == history_id,
        AnalysisHistory.user_id == current_user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    query = db.query(AnalysisMetric).filter(AnalysisMetric.analysis_id == history_id)

    if metric_type:
        query = query.filter(AnalysisMetric.metric_type == metric_type)
    if category:
        query = query.filter(AnalysisMetric.category == category)

    metrics = query.all()

    return {
        "analysis_id": history_id,
        "metrics": [
            {
                "type": m.metric_type,
                "value": float(m.metric_value) if m.metric_value else None,
                "category": m.category,
                "category_name": m.category_name,
                "date": m.metric_date.isoformat() if m.metric_date else None
            }
            for m in metrics
        ]
    }


@router.get("/history/{history_id}/insights")
async def get_analysis_insights(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    insight_type: str | None = None,
):
    """Get only insights for an analysis (lightweight)."""
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == history_id,
        AnalysisHistory.user_id == current_user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    query = db.query(AnalysisInsight).filter(AnalysisInsight.analysis_id == history_id)

    if insight_type:
        query = query.filter(AnalysisInsight.insight_type == insight_type)

    insights = query.all()

    return {
        "analysis_id": history_id,
        "insights": [
            {
                "text": i.insight_text,
                "type": i.insight_type,
                "confidence": float(i.confidence_score) if i.confidence_score else None
            }
            for i in insights
        ]
    }


@router.get("/history/{history_id}/charts")
async def get_analysis_charts(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get chart references for an analysis."""
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == history_id,
        AnalysisHistory.user_id == current_user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return {
        "analysis_id": history_id,
        "charts": [
            {
                "type": chart.chart_type,
                "path": chart.chart_path,
                "data": chart.chart_data,
                "url": f"/api/v1/analysis/chart/{chart.chart_path.split('/')[-1]}"
            }
            for chart in analysis.charts
        ]
    }


@router.delete("/history/{history_id}")
async def delete_analysis(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an analysis and all related data."""
    analysis = db.query(AnalysisHistory).filter(
        AnalysisHistory.id == history_id,
        AnalysisHistory.user_id == current_user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if hasattr(analysis, 'charts') and analysis.charts:
        for chart in analysis.charts:
            if chart.chart_path and os.path.exists(chart.chart_path):
                try:
                    os.remove(chart.chart_path)
                    print(f"Deleted chart file: {chart.chart_path}")
                except Exception as e:
                    print(f"Could not delete chart file: {e}")

    db.delete(analysis)
    db.commit()

    return {"message": "Analysis deleted successfully"}


@router.get("/history/aggregate/metrics")
async def get_aggregate_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    metric_type: str = "total_revenue",
    days: int = 30,
):
    """Get aggregated metrics across all analyses (for dashboards)."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    metrics = db.query(AnalysisMetric).join(AnalysisHistory).filter(
        AnalysisHistory.user_id == current_user.id,
        AnalysisHistory.created_at >= cutoff_date,
        AnalysisMetric.metric_type == metric_type
    ).all()

    if not metrics:
        return {"metric_type": metric_type, "values": [], "trend": None}

    daily_values = defaultdict(list)

    for metric in metrics:
        if metric.metric_date:
            date_key = metric.metric_date.isoformat()
        else:
            analysis = db.query(AnalysisHistory).filter(AnalysisHistory.id == metric.analysis_id).first()
            if analysis:
                date_key = analysis.created_at.date().isoformat()
            else:
                continue
        daily_values[date_key].append(float(metric.metric_value))

    aggregated = [
        {"date": date, "value": sum(values) / len(values)}
        for date, values in sorted(daily_values.items())
    ]

    trend = None
    if len(aggregated) >= 2:
        first_value = aggregated[0]["value"]
        last_value = aggregated[-1]["value"]
        if first_value > 0:
            percent_change = ((last_value - first_value) / first_value) * 100
            trend = {
                "direction": "up" if last_value > first_value else "down",
                "percent_change": round(percent_change, 1)
            }

    return {
        "metric_type": metric_type,
        "values": aggregated,
        "trend": trend,
        "period_days": days
    }


__all__ = ['router']