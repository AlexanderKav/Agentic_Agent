"""Integration tests focusing on format compatibility between components."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import os
import sys
import json
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.analytics_agent import AnalyticsAgent
from agents.insight_agent import InsightAgent, make_json_safe
from agents.visualization_agent import VisualizationAgent
from tests.fixtures.sample_data import varied_data, temp_chart_dir


class TestFormatCompatibility:
    """Test format compatibility between agents"""
    
    def test_series_to_dict_conversion(self, varied_data):
        """Test that pandas Series can be converted to dict for insight agent"""
        analytics = AnalyticsAgent(varied_data)

        # Get various Series results
        monthly_revenue = analytics.monthly_revenue()
        monthly_growth = analytics.monthly_growth()
        customer_revenue = analytics.revenue_by_customer()

        # make_json_safe converts Series to dict
        json_safe_monthly = make_json_safe(monthly_revenue)
        json_safe_growth = make_json_safe(monthly_growth)
        json_safe_customer = make_json_safe(customer_revenue)

        # These should be dicts (Series converted to dict)
        assert isinstance(json_safe_monthly, dict)
        assert isinstance(json_safe_growth, dict)
        assert isinstance(json_safe_customer, dict)
        
        # Keys should be strings (dates converted to strings)
        for key in json_safe_monthly.keys():
            assert isinstance(key, str)
    
    def test_dataframe_to_records_conversion(self, varied_data, temp_chart_dir):
        """Test DataFrame conversion for visualization agent"""
        analytics = AnalyticsAgent(varied_data)

        # Create a DataFrame result
        test_df = varied_data.groupby('customer')[['revenue', 'cost']].sum().reset_index()

        viz = VisualizationAgent(output_dir=temp_chart_dir)
        raw_results = {"customer_summary": test_df}

        # Visualization agent should handle DataFrame
        charts = viz.generate_from_results(raw_results)

        assert "customer_summary" in charts
        assert os.path.exists(charts["customer_summary"])
    
    def test_insight_agent_receives_json_serializable(self, varied_data):
        """Test that insight agent receives properly formatted data"""
        analytics = AnalyticsAgent(varied_data)

        # Get mixed result types
        results = {
            "kpis": analytics.compute_kpis(),  # dict
            "monthly": analytics.monthly_revenue(),  # Series
            "customers": analytics.revenue_by_customer(),  # Series
            "spikes": analytics.detect_revenue_spikes()  # dict or Series
        }

        # Convert to JSON-safe for insight agent
        json_safe_results = {}
        for key, value in results.items():
            if isinstance(value, pd.Series):
                json_safe_results[key] = make_json_safe(value)
            else:
                json_safe_results[key] = make_json_safe(value)

        # Mock the insight agent to avoid real API calls
        with patch('agents.insight_agent.ChatOpenAI') as mock_chat:
            # Create a mock LLM
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
            
            insight = InsightAgent(enable_cost_tracking=False)
            
            # This should not raise JSON serialization errors
            raw, parsed = insight.generate_insights(json_safe_results)
            
            # Verify the data was passed correctly
            assert mock_llm.invoke.called
    
    def test_viz_agent_handles_various_series_types(self, varied_data, temp_chart_dir):
        """Test visualization agent handles different types of Series"""
        analytics = AnalyticsAgent(varied_data)

        # Get various Series types
        series_types = {
            "monthly_revenue": analytics.monthly_revenue(),
            "monthly_growth": analytics.monthly_growth(),
            "customer_revenue": analytics.revenue_by_customer(),
            "product_revenue": analytics.revenue_by_product(),
            "revenue_spikes": analytics.detect_revenue_spikes()
        }

        viz = VisualizationAgent(output_dir=temp_chart_dir)
        
        # Convert Series to dict for visualization (visualization expects dict or DataFrame)
        viz_input = {}
        for name, series in series_types.items():
            if isinstance(series, pd.Series) and not series.empty:
                viz_input[name] = series
        
        charts = viz.generate_from_results(viz_input)

        # All non-empty series should generate charts
        for name in viz_input.keys():
            assert name in charts
            assert os.path.exists(charts[name])
    
    def test_numpy_types_json_serializable(self):
        """Test that numpy numeric types convert to JSON-serializable"""
        data_with_numpy = {
            "int_value": np.int64(42),
            "float_value": np.float64(3.14159),
            "array_value": np.array([1, 2, 3]),
            "nested": {
                "int_val": np.int32(100),
                "float_val": np.float32(2.718)
            }
        }

        json_safe = make_json_safe(data_with_numpy)

        # Should be Python native types
        assert isinstance(json_safe["int_value"], int)
        assert isinstance(json_safe["float_value"], float)
        # array_value should be a list (not a string)
        assert isinstance(json_safe["array_value"], list)
        assert json_safe["array_value"] == [1, 2, 3]
        assert isinstance(json_safe["nested"]["int_val"], int)
        assert isinstance(json_safe["nested"]["float_val"], float)
        
        # Should be JSON serializable
        json_str = json.dumps(json_safe)
        assert json_str is not None

        json_safe = make_json_safe(data_with_numpy)

        # Should be Python native types
        assert isinstance(json_safe["int_value"], int)
        assert isinstance(json_safe["float_value"], float)
        assert isinstance(json_safe["array_value"], list)
        assert isinstance(json_safe["nested"]["int_val"], int)
        assert isinstance(json_safe["nested"]["float_val"], float)
        
        # Should be JSON serializable
        json_str = json.dumps(json_safe)
        assert json_str is not None
    
    def test_timestamp_handling(self, varied_data):
        """Test that pandas Timestamps convert properly"""
        analytics = AnalyticsAgent(varied_data)

        monthly = analytics.monthly_revenue()
        
        # make_json_safe converts Series to dict with string keys
        json_safe = make_json_safe(monthly)

        # Should be a dict
        assert isinstance(json_safe, dict)
        
        # Keys should be strings (timestamps converted to strings)
        for key in json_safe.keys():
            assert isinstance(key, str)
        
        # Should be JSON serializable
        json_str = json.dumps(json_safe)
        assert json_str is not None
    
    def test_empty_and_none_handling(self):
        """Test handling of empty and None values"""
        empty_series = pd.Series([], dtype=float)
        empty_df = pd.DataFrame()
        
        test_cases = {
            "none_value": None,
            "empty_dict": {},
            "empty_list": [],
            "empty_series": empty_series,
            "empty_df": empty_df,
            "mixed": {
                "a": None,
                "b": empty_series,
                "c": []
            }
        }

        json_safe = make_json_safe(test_cases)

        # None should remain None
        assert json_safe["none_value"] is None

        # Empty collections should remain empty
        assert json_safe["empty_dict"] == {}
        assert json_safe["empty_list"] == []
        
        # Empty Series should become empty dict
        assert json_safe["empty_series"] == {}
        
        # Empty DataFrame should become empty list
        assert json_safe["empty_df"] == []
        
        # Should be JSON serializable
        json_str = json.dumps(json_safe)
        assert json_str is not None
    
    def test_nan_and_inf_handling(self):
        """Test handling of NaN and Infinity values"""
        test_cases = {
            "nan_value": float('nan'),
            "inf_value": float('inf'),
            "neg_inf": float('-inf'),
            "nested": {
                "nan": np.nan,
                "inf": np.inf
            }
        }

        json_safe = make_json_safe(test_cases)

        # NaN and Inf should be converted to None
        assert json_safe["nan_value"] is None
        assert json_safe["inf_value"] is None
        assert json_safe["neg_inf"] is None
        assert json_safe["nested"]["nan"] is None
        assert json_safe["nested"]["inf"] is None
        
        # Should be JSON serializable
        json_str = json.dumps(json_safe)
        assert json_str is not None
    
    def test_complex_nested_structure(self, varied_data):
        """Test complex nested structure conversion"""
        analytics = AnalyticsAgent(varied_data)
        
        # Create a complex nested structure
        complex_data = {
            "metadata": {
                "timestamp": pd.Timestamp("2024-01-01 10:30:00"),
                "version": np.float64(1.2),
                "count": np.int64(100)
            },
            "data": [
                {"value": np.float64(3.14), "flag": True, "date": pd.Timestamp("2024-01-01")},
                {"value": np.float64(2.718), "flag": False, "date": pd.Timestamp("2024-01-02")}
            ],
            "analysis": {
                "monthly": analytics.monthly_revenue(),
                "kpis": analytics.compute_kpis()
            }
        }
        
        json_safe = make_json_safe(complex_data)
        
        # Verify structure
        assert isinstance(json_safe["metadata"]["timestamp"], str)
        assert isinstance(json_safe["metadata"]["version"], float)
        assert isinstance(json_safe["metadata"]["count"], int)
        assert isinstance(json_safe["data"], list)
        assert isinstance(json_safe["data"][0]["value"], float)
        assert isinstance(json_safe["data"][0]["date"], str)
        assert isinstance(json_safe["analysis"]["monthly"], dict)
        assert isinstance(json_safe["analysis"]["kpis"], dict)
        
        # Should be JSON serializable
        json_str = json.dumps(json_safe)
        assert json_str is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])