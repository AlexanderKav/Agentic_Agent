import pytest
import json
import os
import re
from unittest.mock import patch, MagicMock
import sys

# Add the parent directory to sys.path to import from agents folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.planner_agent import PlannerAgent


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    return monkeypatch


@pytest.fixture
def planner_agent(mock_env_vars):
    """Create a PlannerAgent instance with mocked OpenAI"""
    with patch('agents.planner_agent.ChatOpenAI') as mock_chat_openai:
        # Create a mock LLM
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm
        
        # Create the agent
        agent = PlannerAgent()
        
        # Store mock for testing
        agent._mock_llm = mock_llm
        
        return agent


class TestPlannerAgentInitialization:
    """Test PlannerAgent initialization"""
    
    @patch('agents.planner_agent.ChatOpenAI')
    def test_init_with_api_key(self, mock_chat_openai, monkeypatch):
        """Test initialization with API key"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        
        agent = PlannerAgent()
        
        mock_chat_openai.assert_called_once_with(
            model="gpt-4o-mini",
            temperature=0.6,
            api_key="test-key-123",
            max_tokens=None
        )
        assert agent.llm is not None
        assert agent.prompt is not None
    
    @patch('agents.planner_agent.ChatOpenAI')
    def test_init_with_custom_params(self, mock_chat_openai, monkeypatch):
        """Test initialization with custom parameters"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        
        agent = PlannerAgent(model="gpt-4o", temperature=0.8, max_tokens=1000)
        
        mock_chat_openai.assert_called_once_with(
            model="gpt-4o",
            temperature=0.8,
            api_key="test-key-123",
            max_tokens=1000
        )
    
    def test_prompt_template(self, planner_agent):
        """Test that prompt template is properly formatted"""
        template_str = planner_agent.prompt.messages[0].prompt.template
        
        assert "{question}" in template_str
        assert "Available tools:" in template_str
        assert "compute_kpis" in template_str
        assert "revenue_by_customer" in template_str
        assert "revenue_by_product" in template_str
        assert "monthly_growth" in template_str
        assert "monthly_profit" in template_str
        assert "detect_revenue_spikes" in template_str
        assert "forecast_revenue" in template_str
        assert "visualization" in template_str
        assert "monthly_revenue_by_customer" in template_str
        assert "Return ONLY valid JSON:" in template_str


class TestCreatePlan:
    """Test the create_plan method"""
    
    def test_create_plan_top_customers(self, planner_agent):
        """Test creating plan for top customers question"""
        mock_response = MagicMock()
        mock_response.content = '{"plan": ["revenue_by_customer", "monthly_growth", "visualization"]}'
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "Who are the top three customers this year and their spending trend?"
        raw, parsed = planner_agent.create_plan(question)
        
        # Check that LLM was called with correct question
        planner_agent._mock_llm.invoke.assert_called_once()
        call_args = planner_agent._mock_llm.invoke.call_args[0][0]
        assert question in str(call_args)
        
        # Verify the parsed plan
        assert "plan" in parsed
        assert isinstance(parsed["plan"], list)
        assert "revenue_by_customer" in parsed["plan"]
        assert "monthly_growth" in parsed["plan"]
        assert "visualization" in parsed["plan"]
        assert raw == mock_response.content
    
    def test_create_plan_top_products(self, planner_agent):
        """Test creating plan for top products question"""
        mock_response = MagicMock()
        mock_response.content = '{"plan": ["revenue_by_product", "monthly_growth", "visualization"]}'
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "Show me our top selling products this quarter"
        raw, parsed = planner_agent.create_plan(question)
        
        assert parsed["plan"] == ["revenue_by_product", "monthly_growth", "visualization"]
    
    def test_create_plan_forecast(self, planner_agent):
        """Test creating plan for forecast question"""
        mock_response = MagicMock()
        mock_response.content = '{"plan": ["monthly_revenue", "forecast_revenue_with_explanation", "visualization"]}'
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "Can you forecast our revenue for the next 3 months?"
        raw, parsed = planner_agent.create_plan(question)
        
        assert "forecast_revenue_with_explanation" in parsed["plan"]
        assert "visualization" in parsed["plan"]
    
    def test_create_plan_anomaly_detection(self, planner_agent):
        """Test creating plan for anomaly detection question"""
        mock_response = MagicMock()
        mock_response.content = '{"plan": ["monthly_revenue", "detect_revenue_spikes", "visualization"]}'
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "Are there any unusual revenue spikes I should know about?"
        raw, parsed = planner_agent.create_plan(question)
        
        assert "detect_revenue_spikes" in parsed["plan"]
    
    def test_create_plan_profit_analysis(self, planner_agent):
        """Test creating plan for profit analysis question"""
        mock_response = MagicMock()
        mock_response.content = '{"plan": ["compute_kpis", "monthly_profit", "visualization"]}'
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "How are our profits trending this year?"
        raw, parsed = planner_agent.create_plan(question)
        
        assert "compute_kpis" in parsed["plan"]
        assert "monthly_profit" in parsed["plan"]
    
    def test_create_plan_complex_question(self, planner_agent):
        """Test creating plan for complex multi-part question"""
        mock_response = MagicMock()
        mock_response.content = '''
        {
            "plan": [
                "compute_kpis",
                "revenue_by_customer",
                "revenue_by_product",
                "monthly_growth",
                "detect_revenue_spikes",
                "forecast_revenue_with_explanation",
                "visualization"
            ]
        }
        '''
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "Give me a complete business overview including KPIs, top customers and products, growth trends, any anomalies, and a revenue forecast"
        raw, parsed = planner_agent.create_plan(question)
        
        assert len(parsed["plan"]) >= 5
        assert "visualization" in parsed["plan"]
        assert parsed["plan"][-1] == "visualization"
    
    def test_create_plan_single_tool(self, planner_agent):
        """Test creating plan with just one tool"""
        mock_response = MagicMock()
        mock_response.content = '{"plan": ["compute_kpis"]}'
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "What's our total revenue?"
        raw, parsed = planner_agent.create_plan(question)
        
        assert parsed["plan"] == ["compute_kpis"]
        assert len(parsed["plan"]) == 1
    
    def test_create_plan_without_visualization(self, planner_agent):
        """Test creating plan without visualization when not needed"""
        mock_response = MagicMock()
        mock_response.content = '{"plan": ["compute_kpis"]}'
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "What's our profit margin?"
        raw, parsed = planner_agent.create_plan(question)
        
        assert "visualization" not in parsed["plan"]
    
    def test_create_plan_with_period_extraction(self, planner_agent):
        """Test that period is extracted from question"""
        mock_response = MagicMock()
        mock_response.content = '{"plan": ["forecast_revenue_by_product"], "period": "Q1 2025"}'
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "What will be our top products in Q1 2025?"
        raw, parsed = planner_agent.create_plan(question)
        
        assert parsed["period"] == "Q1 2025"


class TestErrorHandling:
    """Test error handling in create_plan"""
    
    def test_invalid_json_response(self, planner_agent):
        """Test handling of invalid JSON response from LLM"""
        mock_response = MagicMock()
        mock_response.content = "Here's the plan: revenue_by_customer and monthly_growth"
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "Who are our top customers?"
        
        # Should fall back to default plan
        raw, parsed = planner_agent.create_plan(question)
        
        # Should still return something
        assert "plan" in parsed
        assert isinstance(parsed["plan"], list)
    
    def test_malformed_json_response(self, planner_agent):
        """Test handling of malformed JSON response"""
        mock_response = MagicMock()
        mock_response.content = '{"plan": ["revenue_by_customer", "monthly_growth" missing brackets'
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "Who are our top customers?"
        
        # Should fall back to default plan
        raw, parsed = planner_agent.create_plan(question)
        
        assert "plan" in parsed
    
    def test_empty_response(self, planner_agent):
        """Test handling of empty response"""
        mock_response = MagicMock()
        mock_response.content = ""
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "Who are our top customers?"
        
        # Should fall back to default plan
        raw, parsed = planner_agent.create_plan(question)
        
        assert "plan" in parsed
    
    def test_llm_exception(self, planner_agent):
        """Test handling of LLM exception"""
        planner_agent._mock_llm.invoke.side_effect = Exception("API Error")
        
        question = "Who are our top customers?"
        
        # Should fall back to default plan
        raw, parsed = planner_agent.create_plan(question)
        
        assert "plan" in parsed
        assert "error" in raw.lower()


class TestToolSelectionLogic:
    """Test that the planner selects appropriate tools based on question intent"""
    
    def test_get_required_tools_for_question(self, planner_agent):
        """Test getting tools based on data requirements"""
        # Test with forecast question (requires 12+ months)
        tools = planner_agent.get_required_tools_for_question(
            "forecast revenue for next quarter", 
            months_available=12
        )
        assert "forecast_revenue_with_explanation" in tools
        
        # Test with insufficient data
        tools = planner_agent.get_required_tools_for_question(
            "forecast revenue for next quarter",
            months_available=6
        )
        assert "forecast_revenue_with_explanation" not in tools


class TestEdgeCases:
    """Test edge cases and special scenarios"""
    
    def test_create_plan_with_special_characters(self, planner_agent):
        """Test question with special characters"""
        mock_response = MagicMock()
        mock_response.content = '{"plan": ["compute_kpis", "visualization"]}'
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "What's our revenue? (including Q1 data)"
        raw, parsed = planner_agent.create_plan(question)
        
        assert "compute_kpis" in parsed["plan"]
    
    def test_create_plan_with_very_long_question(self, planner_agent):
        """Test with a very long question"""
        mock_response = MagicMock()
        mock_response.content = '{"plan": ["compute_kpis", "monthly_growth", "forecast_revenue_with_explanation", "visualization"]}'
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "I would like to know the total revenue, profit margin, month-over-month growth trends, and also if you could provide a forecast for the next quarter that would be great, and please include any relevant visualizations " * 3
        raw, parsed = planner_agent.create_plan(question)
        
        assert len(parsed["plan"]) >= 3
    
    def test_create_plan_with_multiple_intents(self, planner_agent):
        """Test question with multiple intents"""
        mock_response = MagicMock()
        mock_response.content = '''
        {
            "plan": [
                "compute_kpis",
                "revenue_by_customer",
                "revenue_by_product",
                "monthly_growth",
                "visualization"
            ]
        }
        '''
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        question = "Show me overall KPIs, top customers and products, and growth trends"
        raw, parsed = planner_agent.create_plan(question)
        
        assert len(parsed["plan"]) == 5
        assert "compute_kpis" in parsed["plan"]
        assert "revenue_by_customer" in parsed["plan"]
        assert "revenue_by_product" in parsed["plan"]
        assert "monthly_growth" in parsed["plan"]
        assert "visualization" in parsed["plan"]


class TestIntegration:
    """Integration-style tests (with mocked LLM)"""
    
    def test_full_planning_flow(self, planner_agent):
        """Test the complete planning flow"""
        question = "Show me our top 5 customers, their monthly trends, and forecast next quarter's revenue"
        
        mock_response = MagicMock()
        mock_response.content = '''
        {
            "plan": [
                "revenue_by_customer",
                "monthly_revenue_by_customer",
                "forecast_revenue_with_explanation",
                "visualization"
            ]
        }
        '''
        planner_agent._mock_llm.invoke.return_value = mock_response
        
        raw, parsed = planner_agent.create_plan(question)
        
        assert "plan" in parsed
        assert isinstance(parsed["plan"], list)
        assert "revenue_by_customer" in parsed["plan"]
        assert "monthly_revenue_by_customer" in parsed["plan"]
        assert "forecast_revenue_with_explanation" in parsed["plan"]
        assert "visualization" in parsed["plan"]
        assert parsed["plan"][-1] == "visualization"
    
    def test_fallback_plan_on_error(self, planner_agent):
        """Test fallback plan when LLM fails"""
        planner_agent._mock_llm.invoke.side_effect = Exception("API Error")
        
        question = "What are our top products?"
        raw, parsed = planner_agent.create_plan(question)
        
        # Should have a fallback plan
        assert "plan" in parsed
        assert len(parsed["plan"]) > 0
        assert "compute_kpis" in parsed["plan"]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])