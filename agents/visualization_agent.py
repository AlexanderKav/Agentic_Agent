"""
Visualization Agent - Generates charts from analysis results
"""

import os
from typing import Any, Dict, Optional

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")


class VisualizationAgent:
    """
    Agent for generating charts and visualizations from analysis results.
    
    Supports:
    - Time series line plots
    - Bar charts for categorical data
    - DataFrame line plots
    - Product forecast bar charts
    """

    def __init__(self, output_dir: str = "agents/charts") -> None:
        """Initialize visualization agent with output directory."""
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        print("Charts will be saved to:", self.output_dir)

    def __del__(self) -> None:
        """Clean up any open matplotlib figures."""
        plt.close('all')

    # --------------------------------------------------
    # Generic Series Chart
    # --------------------------------------------------
    def _plot_series(self, series: pd.Series, name: str) -> str:
        """
        Plot a pandas Series (time series or categorical).
        
        Args:
            series: pandas Series with index as labels/dates and values as data
            name: Name for the chart file and title
            
        Returns:
            Path to the saved chart file
            
        Raises:
            ValueError: If series is empty or contains only null values
        """
        if series.empty:
            raise ValueError(f"Cannot plot empty series: {name}")
        
        if series.isnull().all():
            raise ValueError(f"Series contains only null values: {name}")
        
        series = series.copy()

        # Determine if it's time series or categorical
        is_time_series = False
        try:
            pd.to_datetime(series.index)
            is_time_series = True
        except (ValueError, TypeError):
            pass

        # Adjust figure size based on number of items
        n_items = len(series)
        if n_items > 20:
            figsize = (14, 8)
        elif n_items > 10:
            figsize = (12, 6)
        else:
            figsize = (10, 6)

        plt.figure(figsize=figsize)

        if is_time_series:
            # Time series - use line plot
            plt.plot(series.index, series.values, marker="o", linewidth=2, markersize=6)
            plt.xlabel("Time")
            plt.xticks(rotation=45, ha='right')
        else:
            # Categorical - use bar plot
            if n_items > 15:
                # Too many categories - use horizontal bar
                series = series.sort_values()
                plt.barh(range(n_items), series.values)
                plt.yticks(range(n_items), series.index, fontsize=8)
                plt.ylabel("Category")
            else:
                # Few categories - use vertical bar
                plt.bar(series.index, series.values)
                plt.xticks(rotation=45, ha='right')
                plt.xlabel("Category")

        plt.title(name.replace("_", " ").title())
        plt.ylabel("Revenue ($)")
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{name}.png")
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filepath

    # --------------------------------------------------
    # DataFrame Chart
    # --------------------------------------------------
    def _plot_dataframe(self, df: pd.DataFrame, name: str) -> str:
        """
        Plot a pandas DataFrame.
        
        Args:
            df: DataFrame to plot
            name: Name for the chart file and title
            
        Returns:
            Path to the saved chart file
        """
        if df.empty:
            raise ValueError(f"Cannot plot empty DataFrame: {name}")

        plt.figure(figsize=(8, 5))
        df.plot()
        plt.title(name.replace("_", " ").title())
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{name}.png")
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        return filepath

    # --------------------------------------------------
    # Auto Visualization Engine
    # --------------------------------------------------
    def generate_from_results(self, raw_results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate charts from analytics agent results.
        
        Args:
            raw_results: Dictionary of tool_name -> result (pandas Series/DataFrame)
            
        Returns:
            Dictionary of tool_name -> chart file path
        """
        charts = {}

        for tool_name, result in raw_results.items():
            try:
                # Series
                if isinstance(result, pd.Series):
                    if not result.empty:
                        chart_path = self._plot_series(result, tool_name)
                        charts[tool_name] = chart_path

                # DataFrame
                elif isinstance(result, pd.DataFrame):
                    if not result.empty:
                        chart_path = self._plot_dataframe(result, tool_name)
                        charts[tool_name] = chart_path

            except Exception as e:
                print(f"Visualization failed for {tool_name}: {e}")

        return charts
    
    # --------------------------------------------------
    # Product Forecast Chart
    # --------------------------------------------------
    def plot_product_forecast(self, forecasts: Dict[str, Any], period_label: str = "Next Quarter") -> Optional[str]:
        """
        Plot product-level forecasts as a grouped bar chart with dynamic period label.
        
        Args:
            forecasts: Dictionary from forecast_revenue_by_product
            period_label: The period being forecasted (e.g., "Q1 2025", "Next Quarter")
            
        Returns:
            Path to the saved chart file, or None if plotting fails
        """
        try:
            # Handle nested forecast structure
            if isinstance(forecasts, dict) and 'forecasts' in forecasts:
                forecast_data = forecasts.get("forecasts", {})
                period_label = forecasts.get("period", period_label)
            else:
                forecast_data = forecasts
            
            # Prepare data for plotting
            products = []
            forecast_values = []
            
            for product, data in forecast_data.items():
                if isinstance(data, dict):
                    forecast_sum = data.get("forecast_sum")
                    if forecast_sum is not None and forecast_sum > 0:
                        # Clean product name
                        product_name = product.replace('_', ' ').replace('Plan', ' Plan')
                        products.append(product_name)
                        forecast_values.append(forecast_sum)
            
            if not products:
                print("⚠️ No forecast data to plot")
                return None
            
            # Sort by forecast value descending
            sorted_data = sorted(zip(products, forecast_values), key=lambda x: x[1], reverse=True)
            products = [x[0] for x in sorted_data]
            forecast_values = [x[1] for x in sorted_data]
            
            # Create color map
            colors = plt.cm.viridis([i / len(products) for i in range(len(products))])
            
            plt.figure(figsize=(12, 6))
            bars = plt.bar(products, forecast_values, color=colors)
            
            # Add value labels on bars
            for bar, value in zip(bars, forecast_values):
                plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 500,
                        f'${value:,.0f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
            
            # Format the period label for title
            title_text = f"Forecasted Revenue by Product - {period_label}"
            plt.title(title_text, fontsize=14, fontweight='bold')
            plt.ylabel("Forecasted Revenue ($)", fontsize=12)
            plt.xlabel("Product", fontsize=12)
            plt.xticks(rotation=45, ha='right', fontsize=10)
            plt.grid(axis='y', alpha=0.3)
            
            # Add note about forecast period
            plt.figtext(0.99, 0.01, f"Forecast period: {period_label}", 
                        ha='right', va='bottom', fontsize=9, style='italic', alpha=0.7)
            
            plt.tight_layout()
            
            # Create filename with period label
            safe_period = period_label.replace(' ', '_').replace('/', '_').replace('?', '')
            filepath = os.path.join(self.output_dir, f"product_forecast_{safe_period}.png")
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ Saved product forecast chart: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Error plotting product forecast: {e}")
            import traceback
            traceback.print_exc()
            return None