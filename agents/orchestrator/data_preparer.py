"""
Data Preparer - Combines execution results for the insight agent.
Single responsibility: Prepare structured data for insight generation.
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class DataPreparer:
    """
    Prepares combined data from execution results for the insight agent.
    Formats metrics, trends, and anomalies in a structured way.
    
    Features:
    - Extracts and formats KPIs
    - Processes growth metrics with statistics
    - Handles product monthly trends
    - Processes forecast data
    - Calculates risk indicators
    """
    
    def __init__(self, analytics_agent):
        """
        Initialize the Data Preparer.
        
        Args:
            analytics_agent: AnalyticsAgent instance for additional data
        """
        self.analytics = analytics_agent
    
    def prepare_for_insights(
        self, 
        execution_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combine execution results into structured format for insight agent.
        
        Args:
            execution_results: Dictionary of tool results (values are ExecutionResult objects)
            
        Returns:
            Structured data ready for insight generation
        """
        combined: Dict[str, Any] = {}
        
        # Extract results from ExecutionResult objects if needed
        results = self._extract_results(execution_results)
        
        # Process each type of result
        self._process_kpis(results, combined)
        self._process_growth_metrics(results, combined)
        self._process_profit_metrics(results, combined)
        self._process_product_data(results, combined)
        self._process_forecast_data(results, combined)
        self._process_region_data(results, combined)
        self._process_customer_data(results, combined)
        self._process_anomalies(results, combined)
        self._process_payment_metrics(results, combined)
        
        # Add derived metrics
        self._add_missing_customers_risk(combined)
        self._add_derived_metrics(combined)
        
        return combined
    
    def _extract_results(self, execution_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract actual results from ExecutionResult objects."""
        results = {}
        for tool_name, result in execution_results.items():
            if hasattr(result, 'result'):
                results[tool_name] = result.result
            else:
                results[tool_name] = result
        return results
    
    def _process_kpis(self, results: Dict[str, Any], combined: Dict[str, Any]) -> None:
        """Extract and process KPI metrics."""
        if 'compute_kpis' not in results:
            return
        
        kpis = results['compute_kpis']
        if not isinstance(kpis, dict):
            return
        
        # Basic KPIs
        combined['total_revenue'] = kpis.get('total_revenue', 0)
        combined['total_cost'] = kpis.get('total_cost', 0)
        combined['total_profit'] = kpis.get('total_profit', 0)
        combined['profit_margin'] = kpis.get('profit_margin', 0)
        combined['avg_order_value'] = kpis.get('avg_order_value', 0)
        combined['total_transactions'] = kpis.get('total_transactions', 0)
        
        # Additional KPIs if available
        if 'total_customers' in kpis:
            combined['total_customers'] = kpis['total_customers']
        if 'customer_retention_rate' in kpis:
            combined['customer_retention_rate'] = kpis['customer_retention_rate']
    
    def _process_growth_metrics(self, results: Dict[str, Any], combined: Dict[str, Any]) -> None:
        """Extract and process growth metrics with statistics."""
        if 'monthly_growth' not in results:
            return
        
        growth = results['monthly_growth']
        if not isinstance(growth, dict):
            return
        
        combined['monthly_growth'] = growth
        
        # Calculate summary statistics
        growth_values = [v for v in growth.values() if isinstance(v, (int, float)) and v != 0]
        
        if growth_values:
            combined['positive_growth_months'] = len([v for v in growth_values if v > 0])
            combined['negative_growth_months'] = len([v for v in growth_values if v < 0])
            combined['max_growth'] = max(growth_values)
            combined['min_growth'] = min(growth_values)
            combined['avg_growth'] = sum(growth_values) / len(growth_values)
            combined['growth_volatility'] = self._calculate_volatility(growth_values)
            
            # Get latest growth
            if growth:
                latest_month = list(growth.keys())[-1]
                latest_value = list(growth.values())[-1]
                combined['latest_growth'] = latest_value
                combined['latest_growth_month'] = latest_month
    
    def _process_profit_metrics(self, results: Dict[str, Any], combined: Dict[str, Any]) -> None:
        """Extract and process profit metrics."""
        if 'monthly_profit' not in results:
            return
        
        profit = results['monthly_profit']
        if isinstance(profit, dict):
            combined['monthly_profit'] = profit
        elif isinstance(profit, (int, float)):
            combined['total_profit'] = profit
    
    def _process_product_data(self, results: Dict[str, Any], combined: Dict[str, Any]) -> None:
        """Extract and process product-related data."""
        # Monthly revenue by product (trends)
        if 'monthly_revenue_by_product' in results:
            product_data = results['monthly_revenue_by_product']
            if isinstance(product_data, dict):
                self._extract_product_monthly_trends(product_data, combined)
                combined['monthly_revenue_by_product_raw'] = product_data
        
        # Revenue by product (totals)
        if 'revenue_by_product' in results:
            product_totals = results['revenue_by_product']
            if isinstance(product_totals, dict):
                self._extract_product_totals(product_totals, combined)
                combined['revenue_by_product_raw'] = product_totals
    
    def _process_forecast_data(self, results: Dict[str, Any], combined: Dict[str, Any]) -> None:
        """Extract and process forecast data."""
        # Product-level forecast
        if 'forecast_revenue_by_product' in results:
            forecast_data = results['forecast_revenue_by_product']
            if isinstance(forecast_data, dict):
                self._extract_product_forecast(forecast_data, combined)
        
        # Overall forecast
        if 'forecast_revenue_with_explanation' in results:
            overall_forecast = results['forecast_revenue_with_explanation']
            if isinstance(overall_forecast, dict):
                combined['overall_forecast'] = overall_forecast
        
        # Confidence forecast
        if 'forecast_with_confidence' in results:
            confidence_forecast = results['forecast_with_confidence']
            if isinstance(confidence_forecast, dict):
                combined['confidence_forecast'] = confidence_forecast
        
        # Ensemble forecast
        if 'forecast_ensemble' in results:
            ensemble_forecast = results['forecast_ensemble']
            if isinstance(ensemble_forecast, dict):
                combined['ensemble_forecast'] = ensemble_forecast
    
    def _process_region_data(self, results: Dict[str, Any], combined: Dict[str, Any]) -> None:
        """Extract and process region data."""
        if 'revenue_by_region' in results:
            region_data = results['revenue_by_region']
            if isinstance(region_data, dict):
                combined['revenue_by_region'] = region_data
                self._extract_top_regions(region_data, combined)
    
    def _process_customer_data(self, results: Dict[str, Any], combined: Dict[str, Any]) -> None:
        """Extract and process customer data."""
        if 'revenue_by_customer' in results:
            customer_data = results['revenue_by_customer']
            if isinstance(customer_data, dict):
                self._extract_top_customers(customer_data, combined)
                combined['revenue_by_customer_raw'] = customer_data
        
        # Monthly customer trends
        if 'monthly_revenue_by_customer' in results:
            customer_trends = results['monthly_revenue_by_customer']
            if isinstance(customer_trends, dict):
                combined['customer_monthly_trends'] = customer_trends
                self._extract_declining_customers(customer_trends, combined)
    
    def _process_anomalies(self, results: Dict[str, Any], combined: Dict[str, Any]) -> None:
        """Extract and process anomaly detection results."""
        if 'detect_revenue_spikes' in results:
            anomalies = results['detect_revenue_spikes']
            if isinstance(anomalies, dict):
                combined['anomalies'] = anomalies
                combined['anomaly_count'] = self._count_anomalies(anomalies)
    
    def _process_payment_metrics(self, results: Dict[str, Any], combined: Dict[str, Any]) -> None:
        """Extract and process payment metrics."""
        if 'revenue_by_payment_status' in results:
            payment_data = results['revenue_by_payment_status']
            if isinstance(payment_data, dict):
                self._extract_payment_metrics(payment_data, combined)
    
    def _extract_product_monthly_trends(self, product_data: Dict, combined: Dict) -> None:
        """Format product monthly trends for insight agent."""
        formatted = {}
        
        for product, details in product_data.items():
            if isinstance(details, dict) and 'monthly_revenue' in details:
                product_name = self._clean_product_name(product)
                formatted[f"{product_name}_monthly_trend"] = details['monthly_revenue']
        
        if formatted:
            combined['product_monthly_trends'] = formatted
    
    def _extract_product_totals(self, product_data: Dict, combined: Dict) -> None:
        """Format product totals."""
        formatted = {}
        for product, revenue in product_data.items():
            if isinstance(revenue, (int, float)):
                product_name = self._clean_product_name(product)
                formatted[product_name] = revenue
        combined['revenue_by_product'] = formatted
    
    def _extract_product_forecast(self, forecast_data: Dict, combined: Dict) -> None:
        """Extract and format product forecast data."""
        combined['product_forecast'] = forecast_data
        
        # Extract top product for quick reference
        if 'top_product' in forecast_data:
            combined['top_product_forecast'] = forecast_data['top_product']
            combined['top_product_forecast_value'] = forecast_data.get('top_product_forecast', 0)
        
        # Extract all forecasts in a readable format
        forecasts = forecast_data.get('forecasts', {})
        if forecasts:
            forecast_summary = {}
            for product, details in forecasts.items():
                if isinstance(details, dict):
                    product_name = self._clean_product_name(product)
                    forecast_summary[product_name] = {
                        'total_forecast': details.get('forecast_sum', 0),
                        'monthly_forecast': details.get('forecast', []),
                        'months': details.get('forecast_months', []),
                        'method': details.get('method', 'Unknown'),
                        'trend': self._determine_trend(details.get('forecast', []))
                    }
            combined['forecast_summary'] = forecast_summary
    
    def _extract_top_regions(self, region_data: Dict, combined: Dict) -> None:
        """Extract top regions."""
        if region_data:
            sorted_regions = sorted(
                [(k, v) for k, v in region_data.items() if isinstance(v, (int, float))],
                key=lambda x: x[1],
                reverse=True
            )[:5]
            combined['top_regions'] = dict(sorted_regions)
    
    def _extract_top_customers(self, customer_data: Dict, combined: Dict) -> None:
        """Extract top 5 customers."""
        if customer_data:
            sorted_customers = sorted(
                [(k, v) for k, v in customer_data.items() if isinstance(v, (int, float))],
                key=lambda x: x[1],
                reverse=True
            )[:5]
            combined['top_customers'] = dict(sorted_customers)
    
    def _extract_declining_customers(self, customer_trends: Dict, combined: Dict) -> None:
        """Extract customers with declining trends."""
        declining = []
        for customer, data in customer_trends.items():
            if isinstance(data, dict) and data.get('declining', False):
                declining.append(customer)
        
        if declining:
            combined['declining_customers'] = declining
            combined['declining_customers_count'] = len(declining)
    
    def _extract_payment_metrics(self, payment_data: Dict, combined: Dict) -> None:
        """Extract payment-related risk metrics."""
        combined['payment_status_counts'] = payment_data
        
        # Calculate revenue at risk
        failed = payment_data.get('failed', 0)
        pending = payment_data.get('pending', 0)
        combined['revenue_at_risk'] = failed + pending
        
        combined['failed_payments_count'] = failed
        combined['pending_payments_count'] = pending
        
        # Calculate percentages if total revenue is available
        total_revenue = combined.get('total_revenue', 0)
        if total_revenue > 0:
            combined['revenue_at_risk_percentage'] = round(
                (failed + pending) / total_revenue * 100, 1
            )
    
    def _add_missing_customers_risk(self, combined: Dict[str, Any]) -> None:
        """Add missing customers indicator from analytics."""
        try:
            if hasattr(self.analytics, 'df') and 'customer' in self.analytics.df.columns:
                missing = self.analytics.df['customer'].isna().sum()
                combined['missing_customers'] = int(missing)
                
                total_rows = len(self.analytics.df)
                if total_rows > 0 and missing > 0:
                    combined['missing_customers_percentage'] = round(
                        (missing / total_rows) * 100, 1
                    )
        except Exception as e:
            logger.debug(f"Could not calculate missing customers: {e}")
    
    def _add_derived_metrics(self, combined: Dict[str, Any]) -> None:
        """Add derived metrics based on available data."""
        # Calculate revenue concentration if top customers exist
        if 'top_customers' in combined and 'total_revenue' in combined:
            top_revenue = sum(combined['top_customers'].values())
            total_revenue = combined['total_revenue']
            if total_revenue > 0:
                combined['revenue_concentration'] = round(
                    top_revenue / total_revenue * 100, 1
                )
        
        # Calculate profit trend if monthly profit exists
        if 'monthly_profit' in combined and isinstance(combined['monthly_profit'], dict):
            profit_values = [v for v in combined['monthly_profit'].values() if isinstance(v, (int, float))]
            if len(profit_values) >= 2:
                combined['profit_trend'] = 'increasing' if profit_values[-1] > profit_values[0] else 'decreasing'
    
    def _clean_product_name(self, product: str) -> str:
        """Clean product name for display."""
        return product.replace('_', ' ').replace('Plan', ' Plan')
    
    def _determine_trend(self, forecast_values: List) -> str:
        """Determine trend direction from forecast values."""
        if len(forecast_values) >= 2:
            return 'increasing' if forecast_values[-1] > forecast_values[0] else 'decreasing'
        return 'stable'
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (standard deviation) of growth values."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return round(variance ** 0.5, 4)
    
    def _count_anomalies(self, anomalies: Dict) -> int:
        """Count number of anomalies in the anomalies dictionary."""
        count = 0
        for value in anomalies.values():
            if isinstance(value, dict):
                count += len(value)
            elif isinstance(value, list):
                count += len(value)
            elif value:
                count += 1
        return count


__all__ = ['DataPreparer']