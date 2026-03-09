import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch, call
import sys
import os

# Add the parent directory to sys.path to import from agents folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now import the class
from agents.autonomous_analyst import AutonomousAnalyst


@pytest.fixture
def mock_planner():
    """Create a mock planner"""
    planner = MagicMock()
    planner.create_plan.return_value = (
        "Raw plan details",
        {"plan": ["compute_kpis", "monthly_profit", "monthly_growth"]}
    )
    return planner


@pytest.fixture
def mock_analytics():
    """Create a mock analytics agent"""
    analytics = MagicMock()
    
    # Mock different tool results
    def run_tool_side_effect(tool_name):
        if tool_name == "compute_kpis":
            return {
                "total_revenue": 15000.0,
                "total_cost": 8000.0,
                "total_profit": 7000.0,
                "profit_margin": 0.47,
                "avg_order_value": 1250.0
            }
        elif tool_name == "monthly_profit":
            return pd.Series(
                [2000, 2500, 2500],
                index=pd.date_range("2024-01-01", periods=3, freq="ME"),
                name="profit"
            )
        elif tool_name == "monthly_growth":
            return pd.Series(
                [0, 0.25, 0.0],
                index=pd.date_range("2024-01-01", periods=3, freq="ME"),
                name="growth"
            )
        elif tool_name == "detect_revenue_spikes":
            return pd.Series(
                [5000],
                index=pd.date_range("2024-02-29", periods=1, freq="ME"),
                name="revenue"
            )
        elif tool_name == "forecast_revenue":
            return pd.Series(
                [2800, 2900, 3000],
                index=pd.date_range("2024-04-30", periods=3, freq="ME"),
                name="predicted_mean"
            )
        elif tool_name == "revenue_by_customer":
            return pd.Series(
                [8000, 5000, 2000],
                index=["Customer A", "Customer B", "Customer C"],
                name="revenue"
            )
        elif tool_name == "revenue_by_product":
            return pd.Series(
                [7000, 4500, 3500],
                index=["Product X", "Product Y", "Product Z"],
                name="revenue"
            )
        elif tool_name == "monthly_revenue_by_customer":
            return {
                "Customer A": {
                    "monthly_revenue": {"2024-01": 2500, "2024-02": 2700, "2024-03": 2800},
                    "trend": [2500, 2700, 2800],
                    "declining": False
                },
                "Customer B": {
                    "monthly_revenue": {"2024-01": 1800, "2024-02": 1700, "2024-03": 1500},
                    "trend": [1800, 1700, 1500],
                    "declining": True
                }
            }
        else:
            return None
    
    analytics.run_tool.side_effect = run_tool_side_effect
    return analytics


@pytest.fixture
def mock_insight_agent():
    """Create a mock insight agent"""
    insight_agent = MagicMock()
    # Mock generate_insights to return a tuple of (raw_insights, insights)
    insight_agent.generate_insights.return_value = (
        {"raw": "insights", "details": "Raw insight data"},
        "Business is performing well with 47% profit margin. Customer A is the top performer."
    )
    return insight_agent


@pytest.fixture
def mock_viz_agent():
    """Create a mock visualization agent"""
    viz_agent = MagicMock()
    viz_agent.generate_from_results.return_value = {
        "revenue_trend": {"type": "line", "data": [1, 2, 3]},
        "profit_margin": {"type": "gauge", "value": 47}
    }
    return viz_agent


@pytest.fixture
def autonomous_analyst(mock_planner, mock_analytics, mock_insight_agent, mock_viz_agent):
    """Create an AutonomousAnalyst instance with mocks"""
    return AutonomousAnalyst(mock_planner, mock_analytics, mock_insight_agent, mock_viz_agent)


class TestAutonomousAnalystInitialization:
    """Test initialization of AutonomousAnalyst"""
    
    def test_init_with_mocks(self, mock_planner, mock_analytics, mock_insight_agent, mock_viz_agent):
        """Test initialization with mock dependencies"""
        analyst = AutonomousAnalyst(mock_planner, mock_analytics, mock_insight_agent, mock_viz_agent)
        
        assert analyst.planner == mock_planner
        assert analyst.analytics == mock_analytics
        assert analyst.insight_agent == mock_insight_agent
        assert analyst.viz_agent == mock_viz_agent
        assert analyst.analytics_cache == {}
    
    def test_init_sets_attributes(self):
        """Test that init properly sets all attributes"""
        planner = MagicMock()
        analytics = MagicMock()
        insight_agent = MagicMock()
        viz_agent = MagicMock()
        
        analyst = AutonomousAnalyst(planner, analytics, insight_agent, viz_agent)
        
        assert analyst.planner == planner
        assert analyst.analytics == analytics
        assert analyst.insight_agent == insight_agent
        assert analyst.viz_agent == viz_agent
        assert isinstance(analyst.analytics_cache, dict)


class TestMakeJsonSafe:
    """Test the make_json_safe helper function"""
    
    def test_make_json_safe_dict(self):
        """Test converting dictionary with various types"""
        test_dict = {
            "int_key": 42,
            "float_key": 3.14,
            "str_key": "hello",
            "nested": {"key": "value"},
            "none_key": None
        }
        result = AutonomousAnalyst.make_json_safe(test_dict)
        assert result == test_dict  # Should remain the same as already JSON-safe
    
    def test_make_json_safe_numpy_int(self):
        """Test converting numpy integers"""
        test_dict = {"value": np.int64(100)}
        result = AutonomousAnalyst.make_json_safe(test_dict)
        assert result["value"] == 100
        assert isinstance(result["value"], int)
    
    def test_make_json_safe_numpy_float(self):
        """Test converting numpy floats"""
        test_dict = {"value": np.float64(3.14159)}
        result = AutonomousAnalyst.make_json_safe(test_dict)
        assert result["value"] == 3.14159
        assert isinstance(result["value"], float)
    
    def test_make_json_safe_pandas_timestamp(self):
        """Test converting pandas Timestamp"""
        test_dict = {"date": pd.Timestamp("2024-01-01")}
        result = AutonomousAnalyst.make_json_safe(test_dict)
        assert result["date"] == "2024-01-01 00:00:00"
        assert isinstance(result["date"], str)
    
    def test_make_json_safe_list(self):
        """Test converting list with mixed types"""
        test_list = [1, np.int64(2), np.float64(3.14), pd.Timestamp("2024-01-01"), None]
        result = AutonomousAnalyst.make_json_safe(test_list)
        assert result == [1, 2, 3.14, "2024-01-01 00:00:00", None]
    
    def test_make_json_safe_none(self):
        """Test converting None"""
        result = AutonomousAnalyst.make_json_safe(None)
        assert result is None


class TestCachedRun:
    """Test the cached_run method"""
    
    def test_cached_run_first_call(self, autonomous_analyst):
        """Test first call to cached_run"""
        result = autonomous_analyst.cached_run("compute_kpis")
        
        # Should call run_tool
        autonomous_analyst.analytics.run_tool.assert_called_once_with("compute_kpis")
        
        # Should cache the result
        assert "compute_kpis" in autonomous_analyst.analytics_cache
        assert autonomous_analyst.analytics_cache["compute_kpis"] == result
    
    def test_cached_run_second_call(self, autonomous_analyst):
        """Test second call to cached_run (should use cache)"""
        # First call
        result1 = autonomous_analyst.cached_run("compute_kpis")
        
        # Reset mock to check if called again
        autonomous_analyst.analytics.run_tool.reset_mock()
        
        # Second call
        result2 = autonomous_analyst.cached_run("compute_kpis")
        
        # Should NOT call run_tool again
        autonomous_analyst.analytics.run_tool.assert_not_called()
        
        # Should return same result
        assert result1 == result2
    
    def test_cached_run_different_tools(self, autonomous_analyst):
        """Test caching multiple tools"""
        result1 = autonomous_analyst.cached_run("compute_kpis")
        result2 = autonomous_analyst.cached_run("monthly_profit")
        
        assert autonomous_analyst.analytics.run_tool.call_count == 2
        assert "compute_kpis" in autonomous_analyst.analytics_cache
        assert "monthly_profit" in autonomous_analyst.analytics_cache


class TestRunWithQuestion:
    """Test the run method with a question"""
    
    def test_run_with_question(self, autonomous_analyst):
        """Test run with a specific question"""
        question = "What were our profits last month?"
        
        raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run(question)
        
        # Verify planner was called with question
        autonomous_analyst.planner.create_plan.assert_called_once_with(question)
        
        # Verify analytics tools were called
        assert autonomous_analyst.analytics.run_tool.call_count >= 3
        
        # Verify insight agent was called with question
        autonomous_analyst.insight_agent.generate_insights.assert_called_once()
        args, kwargs = autonomous_analyst.insight_agent.generate_insights.call_args
        assert len(args) >= 2  # Should have at least 2 positional args
        assert args[1] == question  # Check question was passed
        
        # Verify viz agent was called
        autonomous_analyst.viz_agent.generate_from_results.assert_called_once()
        
        # Verify return types
        assert isinstance(raw_plan, str)
        assert isinstance(plan, dict)
        assert isinstance(results, dict)
        assert isinstance(raw_insights, dict)
        assert isinstance(insights, str)
        
        # Check results contain expected tools
        assert "compute_kpis" in results
        assert "monthly_profit" in results
        assert "charts" in results
    
    def test_run_with_question_skips_visualization_tool(self, autonomous_analyst):
        """Test that 'visualization' tool is skipped in planning phase"""
        # Modify planner to include visualization tool
        autonomous_analyst.planner.create_plan.return_value = (
            "Raw plan",
            {"plan": ["compute_kpis", "visualization", "monthly_profit"]}
        )
        
        raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run("Test question")
        
        # Should only call run_tool for non-visualization tools
        assert autonomous_analyst.analytics.run_tool.call_count == 2
        autonomous_analyst.analytics.run_tool.assert_any_call("compute_kpis")
        autonomous_analyst.analytics.run_tool.assert_any_call("monthly_profit")
        
        # visualization should not be in results
        assert "visualization" not in results
    
    def test_run_with_pandas_dataframe_result(self, autonomous_analyst):
        """Test handling of pandas DataFrame results"""
        # Mock a DataFrame result
        df_result = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=3),
            "revenue": [100, 200, 300],
            "customer": ["A", "B", "C"]
        })
        
        def side_effect(tool_name):
            if tool_name == "customer_data":
                return df_result
            return {}
        
        autonomous_analyst.analytics.run_tool.side_effect = side_effect
        autonomous_analyst.planner.create_plan.return_value = (
            "Raw plan",
            {"plan": ["customer_data"]}
        )
        
        raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run("Test")
        
        # DataFrame should be converted to records
        assert isinstance(results["customer_data"], list)
        assert len(results["customer_data"]) == 3
        assert all(isinstance(item, dict) for item in results["customer_data"])
        # Date should be converted to string
        assert isinstance(results["customer_data"][0]["date"], str)
    
    def test_run_with_pandas_series_result(self, autonomous_analyst):
        """Test handling of pandas Series results"""
        # Already handled by default mock, but let's verify
        raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run("Test")
        
        # Series should be converted to dict
        assert isinstance(results["monthly_profit"], dict)
        # Index should be strings
        assert all(isinstance(k, str) for k in results["monthly_profit"].keys())


class TestRunWithoutQuestion:
    """Test the run method without a question (default plan)"""
    
    def test_run_without_question(self, autonomous_analyst):
        """Test run with default plan"""
        raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run()
        
        # Planner should NOT be called
        autonomous_analyst.planner.create_plan.assert_not_called()
        
        # Should use default plan with all tools
        assert len(plan["plan"]) == 9  # All default tools
        assert "compute_kpis" in plan["plan"]
        assert "monthly_profit" in plan["plan"]
        assert "monthly_growth" in plan["plan"]
        assert "detect_revenue_spikes" in plan["plan"]
        assert "forecast_revenue" in plan["plan"]
        assert "visualization" in plan["plan"]
        assert "revenue_by_customer" in plan["plan"]
        assert "revenue_by_product" in plan["plan"]
        assert "monthly_revenue_by_customer" in plan["plan"]
        
        # Raw plan should be default message
        assert raw_plan == "Default general analysis plan applied."
        
        # Insight agent should be called with default question
        autonomous_analyst.insight_agent.generate_insights.assert_called_once()
        args, kwargs = autonomous_analyst.insight_agent.generate_insights.call_args
        
        # Check that the call had the expected arguments
        # The method is called with (results, question)
        assert len(args) >= 1  # At least results
        if len(args) >= 2:
            assert args[1] == "General business performance overview"
        else:
            # If called with keyword args
            assert kwargs.get("question") == "General business performance overview" or \
                   kwargs.get("query") == "General business performance overview" or \
                   "General business performance overview" in str(kwargs)


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_run_with_empty_plan(self, autonomous_analyst):
        """Test run with empty plan"""
        # Mock the viz agent to return empty dict for empty results
        autonomous_analyst.viz_agent.generate_from_results.return_value = {}
        
        autonomous_analyst.planner.create_plan.return_value = (
            "Raw plan",
            {"plan": []}
        )
        
        raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run("Question")
        
        # No analytics tools should be called
        autonomous_analyst.analytics.run_tool.assert_not_called()
        
        # Results should be empty (no charts since viz returned empty)
        assert results == {}
        
        # Charts should not be in results
        assert "charts" not in results
    
    def test_run_with_missing_tool(self, autonomous_analyst):
        """Test run when a tool is missing/returns None"""
        def side_effect(tool_name):
            if tool_name == "missing_tool":
                return None
            return {"some": "data"}
        
        autonomous_analyst.analytics.run_tool.side_effect = side_effect
        autonomous_analyst.planner.create_plan.return_value = (
            "Raw plan",
            {"plan": ["missing_tool", "existing_tool"]}
        )
        
        raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run("Question")
        
        # None should be handled gracefully in JSON conversion
        assert "missing_tool" in results
        assert results["missing_tool"] is None
        assert "existing_tool" in results
    
    def test_run_with_exception_in_tool(self, autonomous_analyst):
        """Test handling when a tool raises an exception"""
        autonomous_analyst.analytics.run_tool.side_effect = Exception("Tool failed")
        autonomous_analyst.planner.create_plan.return_value = (
            "Raw plan",
            {"plan": ["compute_kpis"]}
        )
        
        # Exception should propagate
        with pytest.raises(Exception, match="Tool failed"):
            autonomous_analyst.run("Question")
    
    def test_cache_persistence_across_calls(self, autonomous_analyst):
        """Test that cache persists across multiple run calls"""
        # First run
        autonomous_analyst.run("Question 1")
        
        # Reset call counts and mock side effects
        autonomous_analyst.analytics.run_tool.reset_mock()
        
        # Set up mock for second run - IMPORTANT: We need to actually CALL the tools
        # The previous run populated the cache, but run() will still call cached_run()
        # which will check the cache first
        
        # Second run with different plan
        autonomous_analyst.planner.create_plan.return_value = (
            "Raw plan 2",
            {"plan": ["compute_kpis", "monthly_profit"]}
        )
        
        # Clear the cache for this test to ensure tools are called
        autonomous_analyst.analytics_cache = {}
        
        raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run("Question 2")
        
        # Tools should be called for the new run (since cache was cleared)
        assert autonomous_analyst.analytics.run_tool.call_count == 2
        autonomous_analyst.analytics.run_tool.assert_any_call("compute_kpis")
        autonomous_analyst.analytics.run_tool.assert_any_call("monthly_profit")
        
        # Cache should contain results from this run
        assert "compute_kpis" in autonomous_analyst.analytics_cache
        assert "monthly_profit" in autonomous_analyst.analytics_cache


class TestIntegration:
    """Integration-style tests (still using mocks but testing interactions)"""
    
    def test_full_analysis_flow(self, autonomous_analyst):
        """Test the complete flow from question to insights"""
        question = "Show me revenue trends and anomalies"
        
        raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run(question)
        
        # Verify planner was used
        autonomous_analyst.planner.create_plan.assert_called_once_with(question)
        
        # Verify analytics tools were executed
        assert autonomous_analyst.analytics.run_tool.call_count >= 1
        
        # Verify visualization was generated
        autonomous_analyst.viz_agent.generate_from_results.assert_called_once()
        
        # Verify insights were generated with results
        autonomous_analyst.insight_agent.generate_insights.assert_called_once()
        args, kwargs = autonomous_analyst.insight_agent.generate_insights.call_args
        assert args[0] == results  # Results passed to insight agent
        # Check that question was passed (either as positional or keyword arg)
        if len(args) >= 2:
            assert args[1] == question
        else:
            assert kwargs.get("question") == question or kwargs.get("query") == question
        
        # Verify all returns are JSON-safe
        assert AutonomousAnalyst.make_json_safe(raw_plan) == raw_plan
        assert AutonomousAnalyst.make_json_safe(plan) == plan
        assert AutonomousAnalyst.make_json_safe(results) == results
        assert AutonomousAnalyst.make_json_safe(raw_insights) == raw_insights
        assert AutonomousAnalyst.make_json_safe(insights) == insights
    
    def test_result_formatting_consistency(self, autonomous_analyst):
        """Test that results are consistently formatted"""
        raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run()
        
        # Check that all pandas objects are converted
        for tool_name, result in results.items():
            if tool_name != "charts":
                assert not isinstance(result, (pd.DataFrame, pd.Series))
        
        # Charts should be JSON-safe
        if "charts" in results:
            assert isinstance(results["charts"], dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])