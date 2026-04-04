"""Integration tests focusing on error handling and graceful degradation."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.analytics_agent import AnalyticsAgent
from agents.autonomous_analyst import AutonomousAnalyst
from agents.planner_agent import PlannerAgent
from agents.insight_agent import InsightAgent
from agents.visualization_agent import VisualizationAgent
from tests.fixtures.sample_data import (
    sample_transaction_data, 
    temp_chart_dir
)
from tests.fixtures.sample_data import (
    bad_data,
    empty_dataframe,
    missing_columns_data
)
from tests.fixtures.mock_responses import mock_planner_responses, mock_insight_responses


class TestErrorPropagation:
    """Test how errors propagate through the system"""
    
    def test_analytics_handles_bad_data_gracefully(self, bad_data):
        """Test that analytics agent doesn't crash with bad data"""
        analytics = AnalyticsAgent(bad_data)
        
        # These should not raise exceptions
        kpis = analytics.compute_kpis()
        assert isinstance(kpis, dict)
        
        customer_revenue = analytics.revenue_by_customer()
        assert isinstance(customer_revenue, pd.Series)
        
        # Monthly revenue might be empty but shouldn't crash
        monthly = analytics.monthly_revenue()
        assert isinstance(monthly, pd.Series)
    
    def test_system_handles_empty_data(self, empty_dataframe, temp_chart_dir,
                                        mock_planner_responses, mock_insight_responses):
        """Test that the full system handles empty data gracefully"""
        # Use real analytics with empty data (no columns at all)
        analytics = AnalyticsAgent(empty_dataframe)
        
        planner = mock_planner_responses["simple_kpi"]
        insight = mock_insight_responses["default_answer"]
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        # Mock visualization
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {}
            
            raw_plan, plan, results, raw_insights, insights = system.run("analyze this")
        
        # With empty data, no tools succeed because there's no data to analyze
        # The system should still return a response
        assert results is not None
        assert insights is not None
    
    def test_missing_columns_handling(self, missing_columns_data, temp_chart_dir,
                                       mock_planner_responses, mock_insight_responses):
        """Test system handles missing required columns"""
        # Use real analytics with data missing required columns
        analytics = AnalyticsAgent(missing_columns_data)
        
        planner = mock_planner_responses["simple_kpi"]
        insight = mock_insight_responses["default_answer"]
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        # Mock visualization
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {}
            
            raw_plan, plan, results, raw_insights, insights = system.run("analyze this")
        
        # With missing revenue column, compute_kpis fails
        # The system should still return a response
        assert results is not None
        assert insights is not None
    
    def test_llm_failure_handling(self, sample_transaction_data, temp_chart_dir,
                                   mock_planner_responses):
        """Test system handles LLM failures gracefully"""
        analytics = AnalyticsAgent(sample_transaction_data)
        
        planner = mock_planner_responses["simple_kpi"]
        
        # Create insight that fails
        failing_insight = MagicMock()
        failing_insight.generate_insights.side_effect = Exception("LLM API Error")
        
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        system = AutonomousAnalyst(planner, analytics, failing_insight, viz)
        
        # Mock visualization
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {}
            
            # The system should handle the error gracefully
            raw_plan, plan, results, raw_insights, insights = system.run("analyze this")
        
        # Should still have results
        assert "compute_kpis" in results
        assert insights is not None
    
    def test_partial_tool_failure(self, sample_transaction_data, temp_chart_dir):
        """Test when some tools fail but others succeed"""
        # Use real analytics with longer data for forecasting
        dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
        np.random.seed(42)
        
        long_data = pd.DataFrame({
            'date': dates,
            'revenue': np.random.randint(1000, 5000, len(dates)),
            'cost': np.random.randint(500, 2500, len(dates)),
            'customer': np.random.choice(['A', 'B', 'C'], len(dates)),
            'product': np.random.choice(['X', 'Y', 'Z'], len(dates))
        })
        
        analytics = AnalyticsAgent(long_data)
        
        with patch('agents.planner_agent.ChatOpenAI'), \
            patch('agents.insight_agent.ChatOpenAI'):
            
            planner = PlannerAgent()
            insight = InsightAgent(enable_cost_tracking=False)
            viz = VisualizationAgent(output_dir=temp_chart_dir)
            
            # Mock planner to include forecast tool
            planner.create_plan = MagicMock(return_value=(
                "Raw plan",
                {"plan": ["compute_kpis", "forecast_revenue", "visualization"]}
            ))
            
            # Mock insight
            insight.generate_insights = MagicMock(return_value=(
                {"raw": "insights"},
                "Analysis complete."
            ))
            
            system = AutonomousAnalyst(planner, analytics, insight, viz)
            
            # Mock visualization
            with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
                mock_viz.return_value = {}
                
                raw_plan, plan, results, raw_insights, insights = system.run("analyze this")
            
            # Verify that compute_kpis works
            assert "compute_kpis" in results
            assert isinstance(results["compute_kpis"], dict)
            assert results is not None
    
    def test_viz_agent_handles_empty_results(self, temp_chart_dir):
        """Test visualization agent handles empty results gracefully"""
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        # Empty raw_results
        charts = viz.generate_from_results({})
        assert charts == {}
        
        # Results with no visualizable data
        charts = viz.generate_from_results({
            "string": "not visualizable",
            "dict": {"key": "value"},
            "none": None
        })
        assert charts == {}
    
    def test_planner_error_handling(self, sample_transaction_data, temp_chart_dir):
        """Test system handles planner errors gracefully"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        # Create a failing planner
        failing_planner = MagicMock()
        failing_planner.create_plan.side_effect = Exception("Planner service unavailable")
        
        insight = MagicMock()
        insight.generate_insights.return_value = ({"raw": "data"}, "Fallback insights")
        
        system = AutonomousAnalyst(failing_planner, analytics, insight, viz)
        
        # Mock visualization
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {}
            
            raw_plan, plan, results, raw_insights, insights = system.run("Test question")
        
        # Should return error results
        assert "compute_kpis" in results
        assert "error" in results["compute_kpis"]
        assert "Planner service unavailable" in results["compute_kpis"]["error"]
    
    def test_insight_error_fallback(self, sample_transaction_data, temp_chart_dir,
                                     mock_planner_responses):
        """Test that insight agent has fallback when LLM fails"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        planner = mock_planner_responses["simple_kpi"]
        
        # Create insight that fails then falls back
        failing_insight = MagicMock()
        # First call fails, second call succeeds
        failing_insight.generate_insights.side_effect = [
            Exception("API Error"),
            ({"raw": "fallback"}, "Fallback analysis complete")
        ]
        
        system = AutonomousAnalyst(planner, analytics, failing_insight, viz)
        
        # Mock visualization
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {}
            
            # First attempt should handle error
            raw_plan, plan, results, raw_insights, insights = system.run("analyze this")
        
        # Should still have results
        assert results is not None
        assert insights is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])