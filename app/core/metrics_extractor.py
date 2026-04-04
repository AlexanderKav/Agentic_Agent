# app/core/metrics_extractor.py
from datetime import datetime
from typing import Any

import pandas as pd


class MetricsExtractor:
    """Extract structured metrics from analysis results"""

    def extract(self, results: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract all metrics from results"""
        metrics = []

        # Extract KPIs
        if 'kpis' in results:
            metrics.extend(self._extract_kpis(results['kpis']))

        # Extract revenue by product
        if 'revenue_by_product' in results:
            metrics.extend(self._extract_revenue_by_category(
                results['revenue_by_product'],
                'product'
            ))

        # Extract revenue by region
        if 'revenue_by_region' in results:
            metrics.extend(self._extract_revenue_by_category(
                results['revenue_by_region'],
                'region'
            ))

        # Extract top customers
        if 'top_customers' in results:
            metrics.extend(self._extract_revenue_by_category(
                results['top_customers'],
                'customer'
            ))

        # Extract monthly trends
        if 'monthly_trend' in results:
            metrics.extend(self._extract_monthly_trends(results['monthly_trend']))

        return metrics

    def _extract_kpis(self, kpis: dict) -> list[dict]:
        """Extract KPI metrics"""
        metrics = []

        kpi_mappings = [
            ('total_revenue', 'revenue', 'total_revenue'),
            ('total_profit', 'profit', 'total_profit'),
            ('profit_margin', 'margin', 'profit_margin'),
            ('avg_order_value', 'revenue', 'avg_order_value'),
            ('total_transactions', 'count', 'total_transactions'),
            ('total_customers', 'count', 'total_customers')
        ]

        for kpi_key, category, metric_type in kpi_mappings:
            if kpi_key in kpis:
                metrics.append({
                    'metric_type': metric_type,
                    'metric_value': float(kpis[kpi_key]),
                    'category': category,
                    'metric_date': None
                })

        return metrics

    def _extract_revenue_by_category(self, data: dict, category: str) -> list[dict]:
        """Extract revenue by category (product, region, customer)"""
        metrics = []

        for name, value in data.items():
            if isinstance(value, (int, float)):
                metrics.append({
                    'metric_type': 'revenue',
                    'metric_value': float(value),
                    'category': category,
                    'category_name': str(name),
                    'metric_date': None
                })
            elif isinstance(value, dict) and 'total_revenue' in value:
                # Handle nested structure like { "product": { "total_revenue": 100 } }
                metrics.append({
                    'metric_type': 'revenue',
                    'metric_value': float(value['total_revenue']),
                    'category': category,
                    'category_name': str(name),
                    'metric_date': None
                })

        return metrics

    def _extract_monthly_trends(self, monthly_data: dict) -> list[dict]:
        """Extract monthly trend metrics"""
        metrics = []

        for date_str, revenue in monthly_data.items():
            try:
                # Parse date - handle various formats
                date_obj = self._parse_date(date_str)
                if date_obj is None:
                    continue

                metrics.append({
                    'metric_type': 'monthly_revenue',
                    'metric_value': float(revenue),
                    'category': 'time_series',
                    'category_name': 'monthly',
                    'metric_date': date_obj
                })
            except (ValueError, TypeError, AttributeError):
                continue

        return metrics

    def _parse_date(self, date_str: Any) -> datetime.date | None:
        """
        Parse date from various formats.
        
        Supported formats:
        - 'YYYY-MM' (2024-01)
        - 'YYYY-MM-DD' (2024-01-15)
        - 'Mon YYYY' (Jan 2024)
        - 'Month YYYY' (January 2024)
        - pandas Timestamp
        - datetime object
        """
        if isinstance(date_str, (datetime, pd.Timestamp)):
            return date_str.date() if hasattr(date_str, 'date') else date_str

        if not isinstance(date_str, str):
            return None

        # Try different date formats
        formats = ['%Y-%m', '%Y-%m-%d', '%b %Y', '%B %Y', '%Y-%m-%d %H:%M:%S']
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Fallback to pandas
        try:
            return pd.to_datetime(date_str).date()
        except (ValueError, TypeError):
            return None


__all__ = ['MetricsExtractor']