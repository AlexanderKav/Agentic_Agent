# agents/orchestrator/data_preparer.py
"""
Data Preparer - Combines execution results for the insight agent.
Single responsibility: Prepare structured data for insight generation.
"""

from typing import Dict, Any, List
from collections import defaultdict


class DataPreparer:
    """
    Prepares combined data from execution results for the insight agent.
    Formats metrics, trends, and anomalies in a structured way.
    """
    
    def __init__(self, analytics_agent):
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
        combined = {}
        
        # Extract results from ExecutionResult objects if needed
        results = {}
        for tool_name, result in execution_results.items():
            if hasattr(result, 'result'):
                results[tool_name] = result.result
            else:
                results[tool_name] = result
        
        # Extract KPIs
        if 'compute_kpis' in results:
            kpis = results['compute_kpis']
            if isinstance(kpis, dict):
                self._extract_kpis(kpis, combined)
        
        # Extract monthly growth
        if 'monthly_growth' in results:
            growth = results['monthly_growth']
            if isinstance(growth, dict):
                self._extract_growth_metrics(growth, combined)
        
        # Extract monthly profit
        if 'monthly_profit' in results:
            profit = results['monthly_profit']
            if isinstance(profit, dict):
                combined['monthly_profit'] = profit
        
        # Extract revenue by product (with monthly trends)
        if 'monthly_revenue_by_product' in results:
            product_data = results['monthly_revenue_by_product']
            if isinstance(product_data, dict):
                self._extract_product_monthly_trends(product_data, combined)
                combined['monthly_revenue_by_product_raw'] = product_data
        
        # Extract revenue by product (totals only)
        if 'revenue_by_product' in results:
            product_totals = results['revenue_by_product']
            if isinstance(product_totals, dict):
                self._extract_product_totals(product_totals, combined)
                combined['revenue_by_product_raw'] = product_totals
        
        # ========== NEW: Extract Forecast Data ==========
        if 'forecast_revenue_by_product' in results:
            forecast_data = results['forecast_revenue_by_product']
            if isinstance(forecast_data, dict):
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
                            product_name = product.replace('_', ' ').replace('Plan', ' Plan')
                            forecast_summary[product_name] = {
                                'total_forecast': details.get('forecast_sum', 0),
                                'monthly_forecast': details.get('forecast', []),
                                'months': details.get('forecast_months', []),
                                'method': details.get('method', 'Unknown'),
                                'trend': 'increasing' if len(details.get('forecast', [])) > 1 and details['forecast'][-1] > details['forecast'][0] else 'decreasing'
                            }
                    combined['forecast_summary'] = forecast_summary
        
        # Extract overall forecast
        if 'forecast_revenue_with_explanation' in results:
            overall_forecast = results['forecast_revenue_with_explanation']
            if isinstance(overall_forecast, dict):
                combined['overall_forecast'] = overall_forecast
        
        # Extract forecast with confidence
        if 'forecast_with_confidence' in results:
            confidence_forecast = results['forecast_with_confidence']
            if isinstance(confidence_forecast, dict):
                combined['confidence_forecast'] = confidence_forecast
        
        # Extract revenue by region
        if 'revenue_by_region' in results:
            region_data = results['revenue_by_region']
            if isinstance(region_data, dict):
                combined['revenue_by_region'] = region_data
        
        # Extract top customers
        if 'revenue_by_customer' in results:
            customer_data = results['revenue_by_customer']
            if isinstance(customer_data, dict):
                self._extract_top_customers(customer_data, combined)
                combined['revenue_by_customer_raw'] = customer_data
        
        # Extract anomalies
        if 'detect_revenue_spikes' in results:
            anomalies = results['detect_revenue_spikes']
            if isinstance(anomalies, dict):
                combined['anomalies'] = anomalies
        
        # Extract payment status
        if 'revenue_by_payment_status' in results:
            payment_data = results['revenue_by_payment_status']
            if isinstance(payment_data, dict):
                self._extract_payment_metrics(payment_data, combined)
        
        # Add missing customers risk indicator
        self._add_missing_customers_risk(combined)
        
        return combined
    
    def _extract_kpis(self, kpis: Dict, combined: Dict):
        """Extract KPI metrics"""
        combined['total_revenue'] = kpis.get('total_revenue', 0)
        combined['total_cost'] = kpis.get('total_cost', 0)
        combined['total_profit'] = kpis.get('total_profit', 0)
        combined['profit_margin'] = kpis.get('profit_margin', 0)
        combined['avg_order_value'] = kpis.get('avg_order_value', 0)
        combined['total_transactions'] = kpis.get('total_transactions', 0)
    
    def _extract_growth_metrics(self, growth: Dict, combined: Dict):
        """Extract and calculate growth metrics"""
        combined['monthly_growth'] = growth
        
        # Calculate summary statistics
        growth_values = [v for v in growth.values() if isinstance(v, (int, float)) and v != 0]
        
        if growth_values:
            combined['positive_growth_months'] = len([v for v in growth_values if v > 0])
            combined['negative_growth_months'] = len([v for v in growth_values if v < 0])
            combined['max_growth'] = max(growth_values)
            combined['min_growth'] = min(growth_values)
            combined['avg_growth'] = sum(growth_values) / len(growth_values)
            
            # Get latest growth
            latest_month = list(growth.keys())[-1] if growth else None
            latest_value = list(growth.values())[-1] if growth else 0
            combined['latest_growth'] = latest_value
            combined['latest_growth_month'] = latest_month
    
    def _extract_product_monthly_trends(self, product_data: Dict, combined: Dict):
        """Format product monthly trends for insight agent"""
        formatted = {}
        
        for product, details in product_data.items():
            if isinstance(details, dict) and 'monthly_revenue' in details:
                product_name = product.replace('_', ' ').replace('Plan', ' Plan')
                formatted[f"{product_name}_monthly_trend"] = details['monthly_revenue']
        
        if formatted:
            combined['product_monthly_trends'] = formatted
    
    def _extract_product_totals(self, product_data: Dict, combined: Dict):
        """Format product totals"""
        formatted = {}
        for product, revenue in product_data.items():
            if isinstance(revenue, (int, float)):
                product_name = product.replace('_', ' ').replace('Plan', ' Plan')
                formatted[product_name] = revenue
        combined['revenue_by_product'] = formatted
    
    def _extract_top_customers(self, customer_data: Dict, combined: Dict):
        """Extract top 5 customers"""
        if customer_data:
            sorted_customers = sorted(customer_data.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)[:5]
            combined['top_customers'] = dict(sorted_customers)
    
    def _extract_payment_metrics(self, payment_data: Dict, combined: Dict):
        """Extract payment-related risk metrics"""
        combined['payment_status_counts'] = payment_data
        
        # Calculate revenue at risk if we have revenue data
        if 'revenue' in payment_data:
            failed = payment_data.get('failed', 0)
            pending = payment_data.get('pending', 0)
            combined['revenue_at_risk'] = failed + pending
        
        combined['failed_payments_count'] = payment_data.get('failed', 0)
        combined['pending_payments_count'] = payment_data.get('pending', 0)
    
    def _add_missing_customers_risk(self, combined: Dict):
        """Add missing customers indicator from analytics"""
        try:
            if hasattr(self.analytics, 'df') and 'customer' in self.analytics.df.columns:
                missing = self.analytics.df['customer'].isna().sum()
                combined['missing_customers'] = int(missing)
                if missing > 0:
                    combined['missing_customers_percentage'] = round(
                        (missing / len(self.analytics.df)) * 100, 1
                    )
        except:
            pass