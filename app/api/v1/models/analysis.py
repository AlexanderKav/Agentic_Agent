# app/api/v1/models/analysis.py
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"
    __table_args__ = {'comment': 'Stores historical analysis results'}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    analysis_type = Column(String(50))  # 'file', 'database', 'google_sheets', 'async_file'
    question = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='completed')  # 'pending', 'processing', 'completed', 'failed'

    # Hybrid: Keep raw JSON for full context (backward compatible)
    raw_results = Column(JSON)  # Full analysis results (replaces old 'results' column)
    data_source = Column(JSON)  # Sanitized (no passwords)

    # Relationships to new structured tables
    metrics = relationship("AnalysisMetric", back_populates="analysis", cascade="all, delete-orphan")
    charts = relationship("AnalysisChart", back_populates="analysis", cascade="all, delete-orphan")
    insights = relationship("AnalysisInsight", back_populates="analysis", cascade="all, delete-orphan")

    # Relationship to User
    user = relationship("User", back_populates="analyses")

    def extract_and_store_metrics(self, results: dict[str, Any]) -> None:
        """Extract key metrics from analysis results and store them"""
        from app.core.metrics_extractor import MetricsExtractor
        extractor = MetricsExtractor()
        metrics = extractor.extract(results)

        for metric in metrics:
            db_metric = AnalysisMetric(
                analysis_id=self.id,
                metric_type=metric['metric_type'],
                metric_value=metric['metric_value'],
                metric_date=metric.get('metric_date'),
                category=metric.get('category'),
                category_name=metric.get('category_name')
            )
            self.metrics.append(db_metric)

    def extract_and_store_insights(self, insights_data: dict[str, Any]) -> None:
        """Extract insights from analysis results"""
        from app.core.insights_extractor import InsightsExtractor
        extractor = InsightsExtractor()
        insights = extractor.extract(insights_data)

        for insight in insights:
            db_insight = AnalysisInsight(
                analysis_id=self.id,
                insight_text=insight['text'],
                insight_type=insight['type'],
                confidence_score=insight.get('confidence_score')
            )
            self.insights.append(db_insight)

    def store_chart_reference(self, chart_type: str, chart_path: str, chart_data: Optional[dict] = None) -> None:
        """Store chart reference"""
        chart = AnalysisChart(
            analysis_id=self.id,
            chart_type=chart_type,
            chart_path=chart_path,
            chart_data=chart_data
        )
        self.charts.append(chart)

    def __repr__(self) -> str:
        return f"<AnalysisHistory(id={self.id}, type={self.analysis_type}, user_id={self.user_id})>"


class AnalysisMetric(Base):
    """Structured metrics table for queryable KPIs"""
    __tablename__ = "analysis_metrics"
    __table_args__ = (
        Index('idx_analysis_metrics_type_value', 'metric_type', 'metric_value'),
        Index('idx_analysis_metrics_category', 'category', 'category_name'),
        Index('idx_analysis_metrics_date', 'metric_date'),
        {'comment': 'Stores structured KPIs and metrics from analyses'}
    )

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analysis_history.id"), nullable=False)
    metric_type = Column(String(50))  # 'total_revenue', 'profit_margin', 'avg_order_value', etc.
    metric_value = Column(Numeric(20, 2))  # For numeric metrics
    metric_date = Column(Date, nullable=True)  # For time-series metrics
    category = Column(String(100), nullable=True)  # 'product', 'region', 'customer'
    category_name = Column(String(255), nullable=True)  # Specific product/region/customer name

    # Relationships
    analysis = relationship("AnalysisHistory", back_populates="metrics")

    def __repr__(self) -> str:
        return f"<AnalysisMetric(id={self.id}, type={self.metric_type}, value={self.metric_value})>"


class AnalysisChart(Base):
    """Chart storage reference"""
    __tablename__ = "analysis_charts"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analysis_history.id"), nullable=False)
    chart_type = Column(String(50))  # 'monthly_growth', 'revenue_by_product', etc.
    chart_path = Column(String(255))  # Path to saved chart image
    chart_data = Column(JSON, nullable=True)  # Optional: chart configuration data

    # Relationships
    analysis = relationship("AnalysisHistory", back_populates="charts")

    def __repr__(self) -> str:
        return f"<AnalysisChart(id={self.id}, type={self.chart_type})>"


class AnalysisInsight(Base):
    """Structured insights table"""
    __tablename__ = "analysis_insights"
    __table_args__ = (
        Index('idx_analysis_insights_type', 'insight_type'),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='check_confidence_score'),
        {'comment': 'Stores structured insights from AI analysis'}
    )

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analysis_history.id"), nullable=False)
    insight_text = Column(Text)  # The actual insight text
    insight_type = Column(String(50))  # 'answer', 'anomaly', 'recommendation', 'summary'
    confidence_score = Column(Numeric(5, 2), nullable=True)  # 0-1 confidence score

    # Relationships
    analysis = relationship("AnalysisHistory", back_populates="insights")

    def __repr__(self) -> str:
        return f"<AnalysisInsight(id={self.id}, type={self.insight_type})>"