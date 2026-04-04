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
from tests.fixtures.sample_data import sample_transaction_data, temp_chart_dir
from tests.fixtures.mock_responses import mock_planner_responses, mock_insight_responses


class TestEndToEndQuestionFlow:
    """Test complete question-to-answer flow with various question types"""
    
    def test_simple_kpi_question(self, sample_transaction_data, temp_chart_dir, 
                                  mock_planner_responses, mock_insight_responses):
        """Test simple question about basic KPIs"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        planner = mock_planner_responses["simple_kpi"]
        insight = mock_insight_responses["kpi_answer"]
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {"compute_kpis": "chart_path.png"}
            
            question = "What's our total revenue and profit margin?"
            raw_plan, plan, results, raw_insights, insights = system.run(question)
            
            # plan is a list of tool names
            assert isinstance(plan, list)
            assert "compute_kpis" in plan
            assert "visualization" in plan
            assert "compute_kpis" in results
            assert "charts" in results
            assert "revenue" in str(insights).lower()
            assert "margin" in str(insights).lower()
            
            planner.create_plan.assert_called_once_with(question)
            insight.generate_insights.assert_called_once()
    
    def test_complex_multi_tool_question(self, sample_transaction_data, temp_chart_dir,
                                         mock_planner_responses, mock_insight_responses):
        """Test complex question requiring multiple tools"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        planner = mock_planner_responses["complex"]
        insight = mock_insight_responses["complex_answer"]
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {
                "revenue_by_customer": "chart1.png",
                "revenue_by_product": "chart2.png",
                "monthly_growth": "chart3.png",
                "detect_revenue_spikes": "chart4.png"
            }
            
            question = "Show me top customers, top products, growth trends, and any anomalies"
            raw_plan, plan, results, raw_insights, insights = system.run(question)
            
            assert isinstance(plan, list)
            assert len(plan) >= 4
            assert "revenue_by_customer" in plan
            assert "revenue_by_product" in plan
            assert "monthly_growth" in plan
            assert "detect_revenue_spikes" in plan
            assert "visualization" in plan
            
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
                "monthly_revenue": "chart1.png",
                "forecast_revenue_with_explanation": "chart2.png"
            }
            
            question = "What will our revenue be next month?"
            raw_plan, plan, results, raw_insights, insights = system.run(question)
            
            assert isinstance(plan, list)
            # Use the actual tool name from the output
            assert "forecast_revenue_with_explanation" in plan
            assert "monthly_revenue" in plan
            assert "visualization" in plan
            assert "forecast_revenue_with_explanation" in results or "monthly_revenue" in results
            assert "charts" in results
            assert "forecast" in str(insights).lower() or "next month" in str(insights).lower()
    
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
            
            assert isinstance(plan, list)
            assert "detect_revenue_spikes" in plan
            assert "detect_revenue_spikes" in results
            assert "charts" in results
            assert "anomal" in str(insights).lower() or "spike" in str(insights).lower()
    
    def test_default_execution_without_question(self, sample_transaction_data, temp_chart_dir,
                                                mock_insight_responses):
        """Test system execution with no question (default plan)"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
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
            
            assert raw_plan == "Default general analysis plan applied."
            assert isinstance(plan, list)
            assert "compute_kpis" in plan
            # Note: monthly_profit may not be in the default plan
            # The actual default plan includes: compute_kpis, visualization, revenue_by_product, 
            # revenue_by_customer, monthly_revenue_by_product, detect_revenue_spikes
            assert "visualization" in plan
            assert "revenue_by_customer" in plan or "revenue_by_product" in plan
            
            assert len(results) > 0
            assert "charts" in results
            
            planner.create_plan.assert_not_called()
            insight.generate_insights.assert_called_once()


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
            
            assert raw_plan == "Default general analysis plan applied."
            assert isinstance(plan, list)
            assert "compute_kpis" in plan
            assert "visualization" in plan
            assert "charts" in results
            
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
            
            assert isinstance(plan, list)
            assert "compute_kpis" in plan
            assert "visualization" in plan
            assert "charts" in results
            planner.create_plan.assert_called_once_with(long_question)
    
    def test_question_with_period(self, sample_transaction_data, temp_chart_dir,
                                   mock_planner_responses, mock_insight_responses):
        """Test question with time period extraction"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        planner = mock_planner_responses["product_forecast"]
        insight = mock_insight_responses["forecast_answer"]
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {"product_forecast": "chart.png"}
            
            question = "What will be our top products in Q1 2025?"
            raw_plan, plan, results, raw_insights, insights = system.run(question)
            
            assert isinstance(plan, list)
            assert "forecast_revenue_by_product" in plan
            assert "visualization" in plan
            assert "charts" in results
    
    def test_error_recovery(self, sample_transaction_data, temp_chart_dir):
        """Test system recovery from errors"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        failing_planner = MagicMock()
        failing_planner.create_plan.side_effect = Exception("Planner error")
        
        insight = MagicMock()
        insight.generate_insights.return_value = ({"raw": "data"}, "Fallback insights")
        
        system = AutonomousAnalyst(failing_planner, analytics, insight, viz)
        
        raw_plan, plan, results, raw_insights, insights = system.run("Test question")
        
        assert "compute_kpis" in results
        assert "error" in results["compute_kpis"]
        assert "Planner error" in results["compute_kpis"]["error"]
    
    def test_result_formatting(self, sample_transaction_data, temp_chart_dir,
                                mock_planner_responses, mock_insight_responses):
        """Test that results are properly formatted for output"""
        analytics = AnalyticsAgent(sample_transaction_data)
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        planner = mock_planner_responses["simple_kpi"]
        insight = mock_insight_responses["kpi_answer"]
        
        system = AutonomousAnalyst(planner, analytics, insight, viz)
        
        with patch.object(system.viz_agent, 'generate_from_results') as mock_viz:
            mock_viz.return_value = {"compute_kpis": "chart.png"}
            
            raw_plan, plan, results, raw_insights, insights = system.run("What's our revenue?")
            
            assert isinstance(raw_plan, str)
            assert isinstance(plan, list)
            assert isinstance(results, dict)
            assert isinstance(raw_insights, dict)
            assert isinstance(insights, (str, dict))
            
            import json
            json.dumps(results)  # Should not raise exception


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])