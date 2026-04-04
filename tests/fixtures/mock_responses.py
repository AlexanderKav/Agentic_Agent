"""Shared mock responses for LLM-dependent agents."""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Optional


class MockLLMResponse:
    """Mock LLM response for testing."""
    
    def __init__(self, content: str):
        self.content = content


class MockChatOpenAI:
    """Mock ChatOpenAI for testing."""
    
    def __init__(self, *args, **kwargs):
        self.model = kwargs.get('model', 'gpt-4o-mini')
        self.temperature = kwargs.get('temperature', 0.6)
    
    def invoke(self, messages):
        """Mock invoke method."""
        return MockLLMResponse(self._get_response(messages))
    
    def _get_response(self, messages):
        """Get mock response based on messages."""
        return '{"plan": ["compute_kpis", "visualization"], "period": null}'


@pytest.fixture
def mock_planner_responses():
    """Mock responses for PlannerAgent"""
    
    def get_mock_plan(plan_tools: List[str], period: Optional[str] = None) -> MagicMock:
        """Create a mock planner with specific plan"""
        mock_planner = MagicMock()
        mock_planner.create_plan.return_value = (
            f"Raw plan: {plan_tools}",
            {"plan": plan_tools, "period": period}
        )
        return mock_planner
    
    return {
        "simple_kpi": get_mock_plan(["compute_kpis", "visualization"]),
        "complex": get_mock_plan([
            "revenue_by_customer",
            "revenue_by_product",
            "monthly_growth",
            "detect_revenue_spikes",
            "visualization"
        ]),
        "forecast": get_mock_plan(
            ["monthly_revenue", "forecast_revenue_with_explanation", "visualization"],
            period="Q1 2025"
        ),
        "anomaly": get_mock_plan(
            ["detect_revenue_spikes", "monthly_profit", "visualization"]
        ),
        "product_forecast": get_mock_plan(
            ["monthly_revenue_by_product", "forecast_revenue_by_product", "visualization"],
            period="Q1 2025"
        ),
        "revenue_analysis": get_mock_plan([
            "revenue_by_product",
            "revenue_by_region",
            "revenue_by_customer",
            "monthly_revenue_by_product",
            "visualization"
        ]),
        "risk": get_mock_plan([
            "detect_revenue_spikes",
            "revenue_by_payment_status",
            "monthly_revenue_by_product",
            "visualization"
        ])
    }


@pytest.fixture
def mock_insight_responses():
    """Mock responses for InsightAgent"""
    
    def create_mock_insight(
        answer_text: str,
        summary_text: str = None,
        anomalies: Dict = None,
        recommendations: Dict = None
    ) -> MagicMock:
        """Create a mock insight agent with specific response"""
        mock_insight = MagicMock()
        
        if summary_text is None:
            summary_text = answer_text
        
        insight_dict = {
            "answer": answer_text,
            "human_readable_summary": summary_text,
            "supporting_insights": {},
            "anomalies": anomalies or {},
            "recommended_metrics": recommendations or {}
        }
        
        mock_insight.generate_insights.return_value = (
            insight_dict,
            insight_dict
        )
        return mock_insight
    
    return {
        "kpi_answer": create_mock_insight(
            "Total revenue is $247,500 with a profit margin of 45%.",
            "Revenue is strong with healthy profit margins."
        ),
        "complex_answer": create_mock_insight(
            "Acme Corp is the top customer with $45K revenue. Widget Pro leads products at $52K.",
            "Customer and product analysis complete."
        ),
        "forecast_answer": create_mock_insight(
            "Based on historical trends, revenue is forecasted to grow to $85K next quarter.",
            "Revenue forecast shows positive growth for Q1 2025.",
            recommendations={"focus_products": ["Widget Pro", "Enterprise Plan"]}
        ),
        "anomaly_answer": create_mock_insight(
            "Two revenue anomalies detected: Feb 15 ($12K spike) and Mar 3 ($8K spike).",
            "Anomalies detected in revenue patterns.",
            anomalies={"2024-02-15": 12000, "2024-03-03": 8000}
        ),
        "product_answer": create_mock_insight(
            "Widget Pro is the top product with $52K revenue. Enterprise Plan follows at $48K.",
            "Product performance analysis complete.",
            recommendations={"increase_inventory": ["Widget Pro"]}
        ),
        "risk_answer": create_mock_insight(
            "Revenue at risk: $25,000 from pending payments. Failed payments: $5,000.",
            "Payment risk analysis complete.",
            anomalies={"payment_risk": "High pending payments detected"}
        ),
        "default_answer": create_mock_insight(
            "General business overview: Revenue is strong with good margins.",
            "Business health is positive."
        ),
    }


@pytest.fixture
def mock_llm_environment():
    """Context manager for mocking all LLM dependencies"""
    
    class MockLLMContext:
        def __enter__(self):
            self.planner_patch = patch('agents.planner_agent.ChatOpenAI', return_value=MockChatOpenAI())
            self.insight_patch = patch('agents.insight_agent.ChatOpenAI', return_value=MockChatOpenAI())
            self.mock_planner = self.planner_patch.__enter__()
            self.mock_insight = self.insight_patch.__enter__()
            return self
        
        def __exit__(self, *args):
            self.insight_patch.__exit__(*args)
            self.planner_patch.__exit__(*args)
    
    return MockLLMContext()


@pytest.fixture
def mock_llm_response_factory():
    """Factory to create custom mock LLM responses"""
    
    def create_planner_response(plan: List[str], period: Optional[str] = None) -> MagicMock:
        mock = MagicMock()
        mock.create_plan.return_value = (
            f"Mock plan: {plan}",
            {"plan": plan, "period": period}
        )
        return mock
    
    def create_insight_response(
        answer: str,
        summary: str = None,
        confidence: float = 0.9
    ) -> MagicMock:
        mock = MagicMock()
        insight_dict = {
            "answer": answer,
            "human_readable_summary": summary or answer,
            "confidence_score": confidence
        }
        mock.generate_insights.return_value = (insight_dict, insight_dict)
        return mock
    
    return {
        "planner": create_planner_response,
        "insight": create_insight_response
    }


@pytest.fixture
def integrated_system_with_mocks(
    sample_transaction_data,
    temp_chart_dir,
    mock_planner_responses,
    mock_insight_responses
):
    """Create integrated system with mocked LLM components"""
    from agents.analytics_agent import AnalyticsAgent
    from agents.autonomous_analyst import AutonomousAnalyst
    from agents.visualization_agent import VisualizationAgent
    
    analytics = AnalyticsAgent(sample_transaction_data)
    viz = VisualizationAgent(output_dir=temp_chart_dir)
    
    # Default to simple KPI mocks
    planner = mock_planner_responses["simple_kpi"]
    insight = mock_insight_responses["kpi_answer"]
    
    system = AutonomousAnalyst(planner, analytics, insight, viz)
    system._mock_planner = planner
    system._mock_insight = insight
    
    return system


__all__ = [
    'MockLLMResponse',
    'MockChatOpenAI',
    'mock_planner_responses',
    'mock_insight_responses',
    'mock_llm_environment',
    'mock_llm_response_factory',
    'integrated_system_with_mocks'
]