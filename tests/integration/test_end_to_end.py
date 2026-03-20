"""End-to-end integration tests testing the complete flow from question to answer."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.autonomous_analyst import AutonomousAnalyst
from agents.analytics_agent import AnalyticsAgent
from agents.visualization_agent import VisualizationAgent
from ..fixtures.sample_data import sample_transaction_data, temp_chart_dir
from ..fixtures.mock_responses import mock_planner_responses, mock_insight_responses, mock_llm_environment


class TestEndToEndQuestionFlow:
    """Test complete question-to-answer flow with various question types"""
    
    def test_simple_kpi_question(self, sample_transaction_data, temp_chart_dir, 
                                  mock_planner_responses, mock_insight_responses):
        """Test simple question about basic KPIs"""
        # Use real analytics and viz
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        # Use mocked planner and insight
        planner = mock_planner_responses["simple_kpi"]
        insight = mock_insight_responses["kpi_answer"]
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        # Mock visualization
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {"compute_kpis": "chart_path.png"}
            
            question = "What's our total revenue and profit margin?"
            raw_plan, plan, results, raw_insights, insights = system.run(question)
            
            # Assertions
            assert "compute_kpis" in plan["plan"]
            assert "visualization" in plan["plan"]
            assert "compute_kpis" in results
            assert "charts" in results
            assert "revenue" in insights.lower()
            assert "margin" in insights.lower()
            
            # Verify mocks were called
            planner.create_plan.assert_called_once_with(question)
            insight.generate_insights.assert_called_once()
    
    def test_complex_multi_tool_question(self, sample_transaction_data, temp_chart_dir,
                                         mock_planner_responses, mock_insight_responses):
        """Test complex question requiring multiple tools"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        # Override planner for complex case
        planner = mock_planner_responses["complex"]
        insight = mock_insight_responses["complex_answer"]
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        # Mock visualization
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {
                "revenue_by_customer": "chart1.png",
                "revenue_by_product": "chart2.png",
                "monthly_growth": "chart3.png",
                "detect_revenue_spikes": "chart4.png"
            }
            
            question = "Show me top customers, top products, growth trends, and any anomalies"
            raw_plan, plan, results, raw_insights, insights = system.run(question)
            
            # Assertions
            assert len(plan["plan"]) >= 4
            assert "revenue_by_customer" in plan["plan"]
            assert "revenue_by_product" in plan["plan"]
            assert "monthly_growth" in plan["plan"]
            assert "detect_revenue_spikes" in plan["plan"]
            assert "visualization" in plan["plan"]
            
            # Check results contain all expected tools
            assert "revenue_by_customer" in results
            assert "revenue_by_product" in results
            assert "monthly_growth" in results
            assert "detect_revenue_spikes" in results
            assert "charts" in results
    
    def test_forecast_question(self, sample_transaction_data, temp_chart_dir,
                               mock_planner_responses, mock_insight_responses):
        """Test question about revenue forecasting"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        planner = mock_planner_responses["forecast"]
        insight = mock_insight_responses["forecast_answer"]
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {
                "monthly_profit": "chart1.png",
                "forecast_revenue": "chart2.png"
            }
            
            question = "What will our revenue be next month?"
            raw_plan, plan, results, raw_insights, insights = system.run(question)
            
            # Assertions
            assert "forecast_revenue" in plan["plan"]
            assert "forecast_revenue" in results
            assert "charts" in results
            assert "forecast" in insights.lower() or "next month" in insights.lower()
    
    def test_anomaly_detection_question(self, sample_transaction_data, temp_chart_dir,
                                        mock_planner_responses, mock_insight_responses):
        """Test question about detecting anomalies"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        planner = mock_planner_responses["anomaly"]
        insight = mock_insight_responses["anomaly_answer"]
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {
                "detect_revenue_spikes": "chart1.png",
                "monthly_profit": "chart2.png"
            }
            
            question = "Are there any unusual revenue patterns I should know about?"
            raw_plan, plan, results, raw_insights, insights = system.run(question)
            
            # Assertions
            assert "detect_revenue_spikes" in plan["plan"]
            assert "detect_revenue_spikes" in results
            assert "charts" in results
            assert "anomal" in insights.lower() or "spike" in insights.lower()
    
    def test_default_execution_without_question(self, sample_transaction_data, temp_chart_dir,
                                                mock_insight_responses):
        """Test system execution with no question (default plan)"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        # Planner should NOT be used for default execution
        planner = MagicMock()
        insight = mock_insight_responses["default_answer"]
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {
                "monthly_profit": "chart1.png",
                "monthly_growth": "chart2.png",
                "forecast_revenue": "chart3.png",
                "revenue_by_customer": "chart4.png",
                "revenue_by_product": "chart5.png"
            }
            
            raw_plan, plan, results, raw_insights, insights = system.run()
            
            # Assertions
            assert raw_plan == "Default general analysis plan applied."
            assert len(plan["plan"]) == 10  # All default tools
            assert "compute_kpis" in plan["plan"]
            assert "monthly_profit" in plan["plan"]
            assert "monthly_growth" in plan["plan"]
            assert "detect_revenue_spikes" in plan["plan"]
            assert "forecast_revenue" in plan["plan"]
            assert "visualization" in plan["plan"]
            assert "revenue_by_customer" in plan["plan"]
            assert "revenue_by_product" in plan["plan"]
            assert "monthly_revenue_by_customer" in plan["plan"]
            assert "monthly_revenue_by_product" in plan["plan"] 
            
            # Check results contain at least some tools
            assert len(results) > 0
            assert "charts" in results
            
            # Verify planner was NOT called (since no question)
            planner.create_plan.assert_not_called()
            
            # Verify insight was called with default question
            insight.generate_insights.assert_called_once()
            call_args = insight.generate_insights.call_args
            if len(call_args[0]) >= 2:
                assert call_args[0][1] == "General business performance overview"


class TestEndToEndEdgeCases:
    """Test edge cases in the end-to-end flow"""
    
    def test_empty_question_handling(self, sample_transaction_data, temp_chart_dir,
                                      mock_insight_responses):
        """Test handling of empty question string"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        planner = MagicMock()
        insight = mock_insight_responses["default_answer"]
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {"compute_kpis": "chart.png"}
            
            raw_plan, plan, results, raw_insights, insights = system.run("")
            
            # Should default to general analysis
            assert raw_plan == "Default general analysis plan applied."
            # Update from 9 to 10 because we added monthly_revenue_by_product
            assert len(plan["plan"]) == 10  # All default tools (was 9)
            assert "charts" in results
            
            # Verify planner was NOT called
            planner.create_plan.assert_not_called()
    
    def test_very_long_question(self, sample_transaction_data, temp_chart_dir,
                                 mock_planner_responses, mock_insight_responses):
        """Test handling of very long questions"""
        long_question = "What is our revenue? " * 50
        
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        planner = mock_planner_responses["simple_kpi"]
        insight = mock_insight_responses["kpi_answer"]
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {"compute_kpis": "chart.png"}
            
            raw_plan, plan, results, raw_insights, insights = system.run(long_question)
            
            # Should still work
            assert "compute_kpis" in plan["plan"]
            assert "charts" in results
            planner.create_plan.assert_called_once_with(long_question)