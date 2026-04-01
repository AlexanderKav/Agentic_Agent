# agents/orchestrator/chart_generator.py
"""
Chart Generator - Creates visualizations from analysis results.
Single responsibility: Generate and save charts.
"""

from typing import Dict, Any, Optional
import pandas as pd

class ChartGenerator:
    """
    Generates charts from analysis results.
    Delegates to the visualization agent.
    """
    
    def __init__(self, viz_agent):
        self.viz = viz_agent
    
    def generate_charts(self, raw_results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate all applicable charts from raw results.
        
        Args:
            raw_results: Dictionary of raw tool results
            
        Returns:
            Dictionary mapping chart names to file paths
        """
        charts = {}
        
        if not raw_results:
            return charts
        
        try:
            # Use the visualization agent's main method
            charts = self.viz.generate_from_results(raw_results)
            
            # Check for product forecasts and create specialized chart
            if "forecast_revenue_by_product" in raw_results:
                forecast_data = raw_results["forecast_revenue_by_product"]
                if isinstance(forecast_data, dict) and "forecasts" in forecast_data:
                    period_label = forecast_data.get("period", "Next Quarter")
                    forecast_chart = self.viz.plot_product_forecast(forecast_data, period_label)
                    if forecast_chart:
                        charts["product_forecast"] = forecast_chart
            
            return charts
            
        except Exception as e:
            print(f"❌ Error generating charts: {e}")
            return {}
    
    def generate_single_chart(self, tool_name: str, result: Any) -> Optional[str]:
        """
        Generate a single chart for a specific tool.
        
        Args:
            tool_name: Name of the tool that produced the result
            result: The result to visualize
            
        Returns:
            Path to the generated chart or None
        """
        try:
            if isinstance(result, pd.Series):
                return self.viz._plot_series(result, tool_name)
            elif isinstance(result, pd.DataFrame):
                return self.viz._plot_dataframe(result, tool_name)
            
            return None
            
        except Exception as e:
            print(f"❌ Error generating chart for {tool_name}: {e}")
            return None