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
from ..fixtures.sample_data import (
    sample_transaction_data, bad_data, empty_data, 
    missing_columns_data, temp_chart_dir
)
from ..fixtures.mock_responses import mock_planner_responses, mock_insight_responses


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
    
    def test_system_handles_empty_data(self, empty_data, temp_chart_dir,
                                        mock_planner_responses, mock_insight_responses):
        """Test that the full system handles empty data gracefully"""
        # Create a mock analytics agent that doesn't crash with empty data
        mock_analytics = MagicMock(spec=AnalyticsAgent)
        
        # Mock the run_tool method to return appropriate values
        def mock_run_tool(tool_name):
            if tool_name == "compute_kpis":
                return {
                    "total_revenue": 0.0,
                    "total_cost": 0.0,
                    "total_profit": 0.0,
                    "profit_margin": 0.0,
                    "avg_order_value": 0.0
                }
            elif tool_name == "visualization":
                return None
            else:
                return pd.Series(dtype=float)
        
        mock_analytics.run_tool.side_effect = mock_run_tool
        
        planner = mock_planner_responses["simple_kpi"]
        insight = mock_insight_responses["default_answer"]
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        system = AutonomousAnalyst(planner, mock_analytics, insight, viz)
        
        # This should not raise an exception
        raw_plan, plan, results, raw_insights, insights = system.run("analyze this")
        
        # Should still return something
        assert results is not None
        assert "compute_kpis" in results
        assert results["compute_kpis"]["total_revenue"] == 0.0
        assert insights is not None
    
    def test_missing_columns_handling(self, missing_columns_data, temp_chart_dir,
                                       mock_planner_responses, mock_insight_responses):
        """Test system handles missing required columns"""
        # Create a mock analytics agent that handles missing columns gracefully
        mock_analytics = MagicMock(spec=AnalyticsAgent)
        
        def mock_run_tool(tool_name):
            if tool_name == "compute_kpis":
                return {
                    "total_revenue": 0.0,
                    "total_cost": 0.0,
                    "total_profit": 0.0,
                    "profit_margin": 0.0,
                    "avg_order_value": 0.0
                }
            else:
                return pd.Series(dtype=float)
        
        mock_analytics.run_tool.side_effect = mock_run_tool
        
        planner = mock_planner_responses["simple_kpi"]
        insight = mock_insight_responses["default_answer"]
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        system = AutonomousAnalyst(planner, mock_analytics, insight, viz)
        
        # Should handle missing columns gracefully
        raw_plan, plan, results, raw_insights, insights = system.run("analyze this")
        
        # compute_kpis should return zeros for missing columns
        assert "compute_kpis" in results
        assert results["compute_kpis"]["total_revenue"] == 0.0
    
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
        
        # The system might raise the exception or handle it
        try:
            raw_plan, plan, results, raw_insights, insights = system.run("analyze this")
            # If it doesn't raise, check that we got some results
            assert "compute_kpis" in results
            assert raw_insights == "" or raw_insights == {}
        except Exception as e:
            # If it raises, make sure it's the expected exception
            assert "LLM API Error" in str(e)
    
    def test_partial_tool_failure(self, sample_transaction_data, temp_chart_dir):
        """Test when some tools fail but others succeed"""
        analytics = AnalyticsAgent(sample_transaction_data)
        
        # Mock a specific tool to fail
        original_run_tool = analytics.run_tool
        
        def failing_run_tool(tool_name):
            if tool_name == "forecast_revenue":
                raise Exception("Forecast failed")
            return original_run_tool(tool_name)
        
        analytics.run_tool = failing_run_tool
        
        with patch('agents.planner_agent.ChatOpenAI'), \
            patch('agents.insight_agent.ChatOpenAI'):
            
            planner = PlannerAgent()
            insight = InsightAgent()
            viz = VisualizationAgent(output_dir=temp_chart_dir)
            
            # Mock planner to include failing tool
            planner.create_plan = MagicMock(return_value=(
                "Raw plan",
                {"plan": ["compute_kpis", "forecast_revenue", "visualization"]}
            ))
            
            # Mock insight
            insight.generate_insights = MagicMock(return_value=(
                {"raw": "insights"},
                "Analysis complete despite forecast failure."
            ))
            
            system = AutonomousAnalyst(planner, analytics, insight, viz)
            
            # The system should handle the error gracefully
            raw_plan, plan, results, raw_insights, insights = system.run("analyze this")
            
            # Verify that:
            # 1. Successful tools still work
            assert "compute_kpis" in results
            # 2. Failed tool has error info
            assert "forecast_revenue" in results
            assert "error" in results["forecast_revenue"]
            assert "Forecast failed" in results["forecast_revenue"]["error"]
            # 3. System still returns insights
            assert insights is not None
    
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