"""Integration tests focusing on data preservation across the agent pipeline."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.analytics_agent import AnalyticsAgent
from agents.insight_agent import InsightAgent, make_json_safe
from agents.visualization_agent import VisualizationAgent
from tests.fixtures.sample_data import precise_test_data, varied_data, temp_chart_dir


class TestDataPipeline:
    """Test data preservation across the analytics → insight → visualization pipeline"""
    
    def test_analytics_to_insight_data_preservation(self, precise_test_data):
        """Test that key metrics survive the analytics → insight transition"""
        # Step 1: Analytics agent computes KPIs
        analytics = AnalyticsAgent(precise_test_data)
        kpis = analytics.compute_kpis()
        
        # Expected values based on test data
        expected_revenue = 4500  # 1000 + 2000 + 1500
        expected_cost = 1800     # 400 + 800 + 600
        expected_profit = 2700   # 4500 - 1800
        expected_margin = 0.6    # 2700 / 4500 = 0.6
        
        # Verify floor operations (kpis are floored)
        assert kpis["total_revenue"] == np.floor(expected_revenue)
        assert kpis["total_cost"] == np.floor(expected_cost)
        assert kpis["total_profit"] == np.floor(expected_profit)
        assert round(kpis["profit_margin"], 1) == round(expected_margin, 1)
        
        # Step 2: Convert to JSON-safe for insight agent
        json_safe_kpis = make_json_safe(kpis)
        
        # Step 3: Insight agent receives the data (with mocking to avoid real API calls)
        with patch('agents.insight_agent.ChatOpenAI') as mock_chat:
            # Create a mock LLM response
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "answer": "Analysis complete.",
                "supporting_insights": {},
                "anomalies": {},
                "recommended_metrics": {},
                "human_readable_summary": "Summary of the analysis."
            })
            mock_llm.invoke.return_value = mock_response
            mock_chat.return_value = mock_llm
            
            # Create insight agent with cost tracking disabled for testing
            insight = InsightAgent(enable_cost_tracking=False)
            
            # Call generate_insights with our data
            raw, parsed = insight.generate_insights({"kpis": json_safe_kpis})
            
            # Verify the LLM was called
            assert mock_llm.invoke.called
            call_args = mock_llm.invoke.call_args[0][0]
            call_str = str(call_args)
            
            # Check that our values appear in the call
            assert str(int(expected_revenue)) in call_str or str(expected_revenue) in call_str
            assert str(int(expected_profit)) in call_str or str(expected_profit) in call_str
    
    def test_analytics_to_viz_data_preservation(self, precise_test_data, temp_chart_dir):
        """Test that data for visualization remains intact"""
        analytics = AnalyticsAgent(precise_test_data)
        
        # Get monthly revenue series
        monthly_revenue = analytics.monthly_revenue()
        
        # Expected monthly revenue (should be aggregated by month)
        # All dates are in Jan 2024, so total revenue should be 4500
        assert monthly_revenue.sum() == 4500
        
        # Pass to visualization agent
        viz = VisualizationAgent(output_dir=temp_chart_dir)
        raw_results = {"monthly_revenue": monthly_revenue}
        charts = viz.generate_from_results(raw_results)
        
        # Verify chart was created
        assert "monthly_revenue" in charts
        assert os.path.exists(charts["monthly_revenue"])
    
    def test_complex_data_structure_preservation(self, precise_test_data):
        """Test that complex nested data structures survive JSON conversion"""
        analytics = AnalyticsAgent(precise_test_data)
        
        # Get complex data structures
        customer_revenue = analytics.revenue_by_customer()
        product_revenue = analytics.revenue_by_product()
        monthly_growth = analytics.monthly_growth()
        
        # Combine into nested structure
        complex_data = {
            "customer_analysis": {
                "revenue": customer_revenue.to_dict() if not customer_revenue.empty else {},
                "top_customer": customer_revenue.index[0] if not customer_revenue.empty else None
            },
            "product_analysis": {
                "revenue": product_revenue.to_dict() if not product_revenue.empty else {},
                "top_product": product_revenue.index[0] if not product_revenue.empty else None
            },
            "growth_metrics": {
                "monthly": monthly_growth.to_dict() if not monthly_growth.empty else {},
                "average_growth": float(monthly_growth.mean()) if not monthly_growth.empty else 0
            }
        }
        
        # Convert to JSON-safe
        json_safe = make_json_safe(complex_data)
        
        # Verify structure preserved
        assert "customer_analysis" in json_safe
        assert "product_analysis" in json_safe
        assert "growth_metrics" in json_safe
        assert isinstance(json_safe["customer_analysis"]["revenue"], dict)
        
        # Verify numeric values preserved
        assert json_safe["customer_analysis"]["top_customer"] is not None
    
    def test_dataframe_to_json_conversion(self, precise_test_data):
        """Test that DataFrames convert properly for insight agent"""
        analytics = AnalyticsAgent(precise_test_data)
        
        # Get customer revenue (returns Series)
        customer_revenue = analytics.revenue_by_customer()
        
        # Series should convert to dict using .to_dict() method
        series_dict = customer_revenue.to_dict()
        json_safe_series = make_json_safe(series_dict)
        assert isinstance(json_safe_series, dict)
        
        # Test with a DataFrame result
        test_df = pd.DataFrame({
            'customer': ['A', 'B'],
            'revenue': [2500, 2000]
        })
        
        # Convert DataFrame to records first, then make JSON safe
        df_records = test_df.to_dict(orient='records')
        json_safe_df = make_json_safe(df_records)
        assert isinstance(json_safe_df, list)
        assert all(isinstance(item, dict) for item in json_safe_df)
    
    def test_make_json_safe_series_behavior(self, precise_test_data):
        """Test the actual behavior of make_json_safe with Series"""
        analytics = AnalyticsAgent(precise_test_data)
        customer_revenue = analytics.revenue_by_customer()
        
        # make_json_safe should convert Series to dict
        json_safe = make_json_safe(customer_revenue)
        
        # This should now be a dict, not a Series
        assert isinstance(json_safe, dict)
        
        # Verify the dict contains the expected values
        assert "Customer A" in json_safe
        assert "Customer B" in json_safe
        assert json_safe["Customer A"] == 2500
        assert json_safe["Customer B"] == 2000
    
    def test_full_pipeline_error_handling(self, precise_test_data):
        """Test that the pipeline handles errors gracefully"""
        analytics = AnalyticsAgent(precise_test_data)
        
        # Get a valid result
        kpis = analytics.compute_kpis()
        
        # Simulate a problematic value
        problematic_data = {"kpis": kpis, "invalid": float('nan')}
        
        # Should not crash, should convert NaN to None
        json_safe = make_json_safe(problematic_data)
        assert json_safe["invalid"] is None


class TestJsonSafeFunction:
    """Test the make_json_safe function directly"""
    
    def test_make_json_safe_with_dict(self):
        """Test make_json_safe with dictionary input"""
        test_dict = {"a": 1, "b": 2}
        result = make_json_safe(test_dict)
        assert result == test_dict
    
    def test_make_json_safe_with_series(self, precise_test_data):
        """Test make_json_safe with Series input - converts to dict"""
        analytics = AnalyticsAgent(precise_test_data)
        test_series = analytics.revenue_by_customer()
        result = make_json_safe(test_series)
        # Should convert to dict
        assert isinstance(result, dict)
        assert "Customer A" in result
        assert "Customer B" in result
    
    def test_make_json_safe_with_dataframe(self):
        """Test make_json_safe with DataFrame input - converts to list of dicts"""
        test_df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = make_json_safe(test_df)
        # Should convert to list of dicts
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] == {"a": 1, "b": 3}
        assert result[1] == {"a": 2, "b": 4}
    
    def test_make_json_safe_with_numpy_types(self):
        """Test make_json_safe with numpy types"""
        test_dict = {
            "int": np.int64(42),
            "float": np.float64(3.14)
        }
        result = make_json_safe(test_dict)
        assert isinstance(result["int"], int)
        assert isinstance(result["float"], float)
    
    def test_make_json_safe_with_timestamp(self):
        """Test make_json_safe with pandas Timestamp"""
        test_dict = {"date": pd.Timestamp("2024-01-01")}
        result = make_json_safe(test_dict)
        assert isinstance(result["date"], str)
        assert "2024-01-01" in result["date"]
    
    def test_make_json_safe_with_nan(self):
        """Test make_json_safe with NaN values"""
        test_dict = {"value": float('nan')}
        result = make_json_safe(test_dict)
        assert result["value"] is None
    
    def test_make_json_safe_with_inf(self):
        """Test make_json_safe with Infinity values"""
        test_dict = {"value": float('inf')}
        result = make_json_safe(test_dict)
        assert result["value"] is None
    
    def test_make_json_safe_with_nested_structures(self):
        """Test make_json_safe with deeply nested structures"""
        test_data = {
            "level1": {
                "level2": {
                    "np_int": np.int64(100),
                    "np_float": np.float64(3.14159),
                    "timestamp": pd.Timestamp("2024-01-01 12:00:00")
                }
            }
        }
        
        result = make_json_safe(test_data)
        
        assert isinstance(result["level1"]["level2"]["np_int"], int)
        assert isinstance(result["level1"]["level2"]["np_float"], float)
        assert isinstance(result["level1"]["level2"]["timestamp"], str)

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])