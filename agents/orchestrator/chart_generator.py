"""
Chart Generator - Creates visualizations from analysis results.
Single responsibility: Generate and save charts.
"""

import logging
from typing import Any, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


class ChartGenerator:
    """
    Generates charts from analysis results.
    Delegates to the visualization agent.
    
    Features:
    - Automatic chart generation from tool results
    - Specialized product forecast charts
    - Batch chart generation
    - Error handling per chart
    - Support for Series and DataFrame visualizations
    """
    
    def __init__(self, viz_agent):
        """
        Initialize the Chart Generator.
        
        Args:
            viz_agent: VisualizationAgent instance for rendering charts
        """
        self.viz = viz_agent
        self._generated_charts: List[str] = []
    
    def generate_charts(self, raw_results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate all applicable charts from raw results.
        
        Args:
            raw_results: Dictionary of raw tool results
            
        Returns:
            Dictionary mapping chart names to file paths
        """
        charts: Dict[str, str] = {}
        
        if not raw_results:
            logger.debug("No raw results provided for chart generation")
            return charts
        
        try:
            # Generate standard charts via visualization agent
            charts = self.viz.generate_from_results(raw_results)
            self._generated_charts = list(charts.keys())
            
            # Log successful standard chart generation
            if charts:
                logger.info(f"Generated {len(charts)} standard charts: {list(charts.keys())}")
            
            # Generate specialized product forecast chart if data available
            forecast_chart = self._generate_product_forecast_chart(raw_results)
            if forecast_chart:
                charts["product_forecast"] = forecast_chart
                logger.info("Generated product forecast chart")
            
            return charts
            
        except Exception as e:
            logger.error(f"Error generating charts: {e}", exc_info=True)
            return {}
    
    def _generate_product_forecast_chart(self, raw_results: Dict[str, Any]) -> Optional[str]:
        """
        Generate a product forecast chart if forecast data is available.
        
        Args:
            raw_results: Raw results dictionary
            
        Returns:
            Path to forecast chart or None
        """
        forecast_data = raw_results.get("forecast_revenue_by_product")
        
        if not forecast_data:
            return None
        
        # Handle different forecast data formats
        if isinstance(forecast_data, dict):
            # Standard format from forecast_revenue_by_product
            if "forecasts" in forecast_data:
                period_label = forecast_data.get("period", "Next Quarter")
                return self.viz.plot_product_forecast(forecast_data, period_label)
            
            # Alternative format (direct forecast values)
            if forecast_data and any(isinstance(v, (int, float)) for v in forecast_data.values()):
                return self._generate_simple_product_chart(forecast_data)
        
        return None
    
    def _generate_simple_product_chart(self, forecast_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate a simple product chart from direct forecast values.
        
        Args:
            forecast_data: Dictionary of product -> forecast value
            
        Returns:
            Path to chart or None
        """
        try:
            # Create a standardized format for the chart generator
            formatted_data = {
                "forecasts": {
                    product: {"forecast_sum": value}
                    for product, value in forecast_data.items()
                    if isinstance(value, (int, float)) and value > 0
                },
                "period": "Next Period"
            }
            
            if formatted_data["forecasts"]:
                return self.viz.plot_product_forecast(formatted_data, "Next Period")
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not generate simple product chart: {e}")
            return None
    
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
            chart_path = None
            
            if isinstance(result, pd.Series):
                if not result.empty:
                    chart_path = self.viz._plot_series(result, tool_name)
                    logger.debug(f"Generated series chart for {tool_name}")
                else:
                    logger.debug(f"Skipping empty series for {tool_name}")
                    
            elif isinstance(result, pd.DataFrame):
                if not result.empty:
                    chart_path = self.viz._plot_dataframe(result, tool_name)
                    logger.debug(f"Generated dataframe chart for {tool_name}")
                else:
                    logger.debug(f"Skipping empty dataframe for {tool_name}")
            
            if chart_path:
                self._generated_charts.append(tool_name)
            
            return chart_path
            
        except Exception as e:
            logger.error(f"Error generating chart for {tool_name}: {e}")
            return None
    
    def generate_batch_charts(self, results: List[tuple]) -> Dict[str, str]:
        """
        Generate charts for multiple tools in batch.
        
        Args:
            results: List of (tool_name, result) tuples
            
        Returns:
            Dictionary mapping chart names to file paths
        """
        charts: Dict[str, str] = {}
        
        for tool_name, result in results:
            chart_path = self.generate_single_chart(tool_name, result)
            if chart_path:
                charts[tool_name] = chart_path
        
        return charts
    
    def get_generated_charts(self) -> List[str]:
        """
        Get list of chart names that have been generated.
        
        Returns:
            List of generated chart names
        """
        return self._generated_charts.copy()
    
    def has_charts(self) -> bool:
        """
        Check if any charts have been generated.
        
        Returns:
            True if charts exist
        """
        return len(self._generated_charts) > 0
    
    def clear_generated_charts(self) -> None:
        """Clear the list of generated chart names."""
        self._generated_charts.clear()
        logger.debug("Cleared generated charts list")
    
    def is_chart_generated(self, chart_name: str) -> bool:
        """
        Check if a specific chart has been generated.
        
        Args:
            chart_name: Name of the chart to check
            
        Returns:
            True if the chart was generated
        """
        return chart_name in self._generated_charts
    
    def get_chart_summary(self) -> Dict[str, Any]:
        """
        Get a summary of generated charts.
        
        Returns:
            Dictionary with chart statistics
        """
        return {
            'total_charts': len(self._generated_charts),
            'chart_names': self._generated_charts.copy(),
            'has_charts': self.has_charts()
        }


__all__ = ['ChartGenerator']