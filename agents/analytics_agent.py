"""
Analytics Agent - Performs data analysis with monitoring, self-healing, and cost tracking
"""

import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from agents.monitoring import get_performance_tracker, timer, get_audit_logger, get_cost_tracker
from agents.self_healing import get_healing_agent

class AnalyticsAgent:
    """
    Performs data analysis on standardized dataframes.
    Works with SchemaMapper output which provides consistent column names.
    """

    def __init__(self, df):
        """
        Initialize analytics agent with dataframe.
        
        Args:
            df: DataFrame from SchemaMapper (should have standard column names)
        """
        self.df = df.copy()
        
        # Initialize monitoring
        self.perf_tracker = get_performance_tracker()
        self.audit_logger = get_audit_logger()
        self.cost_tracker = get_cost_tracker()
        self.healer = get_healing_agent()
        self.session_id = id(self)

        # Ensure proper data types - columns should exist from SchemaMapper
        if "date" in self.df.columns:
            self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
        
        for col in ["revenue", "cost", "quantity"]:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

        # Calculate profit if possible
        if "revenue" in self.df.columns and "cost" in self.df.columns:
            self.df["profit"] = self.df["revenue"] - self.df["cost"]
            
        # Audit log initialization
        self.audit_logger.log_action(
            action_type='analytics_init',
            agent='analytics',
            details={
                'data_shape': self.df.shape, 
                'columns': list(self.df.columns),
                'has_profit': 'profit' in self.df.columns
            },
            session_id=self.session_id
        )

    # -----------------------------
    # KPIs
    # -----------------------------
    @timer(operation='compute_kpis')
    def compute_kpis(self):
        """Compute KPIs with monitoring"""
        try:
            # With SchemaMapper, revenue should always exist
            # But we'll still check defensively
            if "revenue" not in self.df.columns:
                # Try recovery before failing
                recovered = self._recover_kpis_with_alternatives()
                if recovered:
                    return recovered
                raise KeyError("Revenue column not found in dataframe")
            
            total_revenue = np.floor(self.df["revenue"].sum())
            
            # Cost and profit are optional
            total_cost = 0
            total_profit = total_revenue
            profit_margin = 1.0
            
            if "cost" in self.df.columns:
                total_cost = np.floor(self.df["cost"].sum())
                total_profit = total_revenue - total_cost
                profit_margin = total_profit / total_revenue if total_revenue > 0 else 0
                profit_margin = np.floor(profit_margin * 100) / 100

            avg_order_value = np.floor(self.df["revenue"].mean())
            
            result = {
                "total_revenue": float(total_revenue),
                "total_cost": float(total_cost),
                "total_profit": float(total_profit),
                "profit_margin": float(profit_margin),
                "avg_order_value": float(avg_order_value)
            }
            
            # Audit log
            self.audit_logger.log_action(
                action_type='compute_kpis',
                agent='analytics',
                details={
                    'result_summary': {
                        'revenue': result['total_revenue'],
                        'profit': result['total_profit'],
                        'margin': result['profit_margin']
                    }
                },
                session_id=self.session_id
            )
            
            return result
            
        except KeyError as e:
            # Missing column - let healing agent learn
            context = {
                'tool': 'compute_kpis',
                'error_type': 'missing_column',
                'data_shape': self.df.shape,
                'available_columns': list(self.df.columns)
            }
            action = self.healer.analyze_failure(e, context)
            
            self.audit_logger.log_action(
                action_type='compute_kpis_error',
                agent='analytics',
                details={'error': str(e), 'context': context},
                session_id=self.session_id
            )
            raise
            
        except Exception as e:
            # Other errors
            self.healer.analyze_failure(e, {'tool': 'compute_kpis'})
            self.audit_logger.log_action(
                action_type='compute_kpis_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    def _recover_kpis_with_alternatives(self):
        """Recovery method for missing columns - kept for backward compatibility"""
        try:
            # Find columns that might contain revenue data
            revenue_col = None
            cost_col = None
            
            revenue_keywords = ['revenue', 'sales', 'rev', 'income', 'turnover', 'amount']
            cost_keywords = ['cost', 'expense', 'cogs', 'spend', 'expenditure', 'expenses']
            
            for col in self.df.columns:
                col_lower = col.lower()
                if any(kw in col_lower for kw in revenue_keywords):
                    revenue_col = col
                    break
            
            for col in self.df.columns:
                col_lower = col.lower()
                if any(kw in col_lower for kw in cost_keywords):
                    cost_col = col
                    break
            
            if revenue_col:
                total_revenue = np.floor(self.df[revenue_col].sum())
                
                if cost_col:
                    total_cost = np.floor(self.df[cost_col].sum())
                    total_profit = total_revenue - total_cost
                    profit_margin = total_profit / total_revenue if total_revenue > 0 else 0
                else:
                    # If no cost column, estimate from revenue (40% typical margin)
                    total_cost = np.floor(total_revenue * 0.6)
                    total_profit = total_revenue - total_cost
                    profit_margin = 0.4
                
                avg_order_value = np.floor(self.df[revenue_col].mean())
                
                result = {
                    "total_revenue": float(total_revenue),
                    "total_cost": float(total_cost),
                    "total_profit": float(total_profit),
                    "profit_margin": float(np.floor(profit_margin * 100) / 100),
                    "avg_order_value": float(avg_order_value)
                }
                
                self.audit_logger.log_action(
                    action_type='recovery_success',
                    agent='analytics',
                    details={
                        'method': '_recover_kpis_with_alternatives',
                        'revenue_col': revenue_col,
                        'cost_col': cost_col
                    },
                    session_id=self.session_id
                )
                
                return result
            return None
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': '_recover_kpis_with_alternatives'})
            self.audit_logger.log_action(
                action_type='recovery_failed',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            return None

    # -----------------------------
    # Revenue breakdowns
    # -----------------------------
    @timer(operation='revenue_by_customer')
    def revenue_by_customer(self):
        """Get revenue by customer with monitoring"""
        try:
            if "customer" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='revenue_by_customer_missing',
                    agent='analytics',
                    details={'error': 'customer column missing'},
                    session_id=self.session_id
                )
                return pd.Series(dtype=float)
            
            # Handle empty customer names
            df = self.df.copy()
            df["customer"] = df["customer"].fillna("Unknown").replace("", "Unknown")
            
            result = np.floor(df.groupby("customer")["revenue"].sum().sort_values(ascending=False))
            
            self.audit_logger.log_action(
                action_type='revenue_by_customer',
                agent='analytics',
                details={
                    'unique_customers': len(result),
                    'top_customer': result.index[0] if not result.empty else None,
                    'top_value': float(result.iloc[0]) if not result.empty else 0
                },
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'revenue_by_customer'})
            self.audit_logger.log_action(
                action_type='revenue_by_customer_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    @timer(operation='monthly_revenue_by_product')
    def monthly_revenue_by_product(self):
        """Get monthly revenue per product"""
        try:
            if "product" not in self.df.columns or "date" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='monthly_revenue_by_product_missing',
                    agent='analytics',
                    details={'error': 'product or date column missing'},
                    session_id=self.session_id
                )
                return {}
            
            # Drop rows with missing dates or revenue
            df = self.df.dropna(subset=["date", "revenue"]).copy()
            if df.empty:
                return {}
            
            # Create month period
            df["month"] = df["date"].dt.to_period("M")
            
            # Group by product and month
            grouped = df.groupby(["product", "month"])["revenue"].sum().reset_index()
            
            # Convert to dictionary format: {product: {month: revenue}}
            result = {}
            for product, group in grouped.groupby("product"):
                monthly = {str(row["month"]): float(np.floor(row["revenue"])) for _, row in group.iterrows()}
                # Get last 6 months for trend
                trend = list(monthly.values())[-6:] if monthly else []
                result[product] = {
                    "monthly_revenue": monthly,
                    "trend": trend,
                    "total_revenue": sum(monthly.values()),
                    "declining": self._is_declining_trend(trend) if len(trend) > 1 else False
                }
            
            self.audit_logger.log_action(
                action_type='monthly_revenue_by_product',
                agent='analytics',
                details={'unique_products': len(result)},
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'monthly_revenue_by_product'})
            self.audit_logger.log_action(
                action_type='monthly_revenue_by_product_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    def _is_declining_trend(self, trend_values):
        """Check if trend is declining"""
        if len(trend_values) < 2:
            return False
        # Simple check: each subsequent value is less than or equal to previous
        return all(earlier >= later for earlier, later in zip(trend_values, trend_values[1:]))

    @timer(operation='revenue_by_product')
    def revenue_by_product(self):
        """Get revenue by product with monitoring"""
        try:
            if "product" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='revenue_by_product_missing',
                    agent='analytics',
                    details={'error': 'product column missing'},
                    session_id=self.session_id
                )
                return pd.Series(dtype=float)
            
            # Handle empty product names
            df = self.df.copy()
            df["product"] = df["product"].fillna("Unknown").replace("", "Unknown")
            
            result = np.floor(df.groupby("product")["revenue"].sum().sort_values(ascending=False))
            
            self.audit_logger.log_action(
                action_type='revenue_by_product',
                agent='analytics',
                details={
                    'unique_products': len(result),
                    'top_product': result.index[0] if not result.empty else None,
                    'top_value': float(result.iloc[0]) if not result.empty else 0
                },
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'revenue_by_product'})
            self.audit_logger.log_action(
                action_type='revenue_by_product_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    @timer(operation='revenue_by_region')
    def revenue_by_region(self):
        """Get revenue by region with monitoring"""
        try:
            if "region" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='revenue_by_region_missing',
                    agent='analytics',
                    details={'error': 'region column missing'},
                    session_id=self.session_id
                )
                return pd.Series(dtype=float)
            
            # Handle empty region names
            df = self.df.copy()
            df["region"] = df["region"].fillna("Unknown").replace("", "Unknown")
            
            result = np.floor(df.groupby("region")["revenue"].sum().sort_values(ascending=False))
            
            self.audit_logger.log_action(
                action_type='revenue_by_region',
                agent='analytics',
                details={
                    'unique_regions': len(result),
                    'top_region': result.index[0] if not result.empty else None,
                    'top_value': float(result.iloc[0]) if not result.empty else 0
                },
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'revenue_by_region'})
            self.audit_logger.log_action(
                action_type='revenue_by_region_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    # -----------------------------
    # Monthly metrics
    # -----------------------------
    @timer(operation='monthly_revenue')
    def monthly_revenue(self):
        """Get monthly revenue with monitoring"""
        try:
            if "date" not in self.df.columns or "revenue" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='monthly_revenue_missing',
                    agent='analytics',
                    details={'error': 'date or revenue column missing'},
                    session_id=self.session_id
                )
                return pd.Series(dtype=float)
            
            # Drop rows with missing dates
            df = self.df.dropna(subset=["date"])
            if df.empty:
                return pd.Series(dtype=float)
            
            series = df.set_index("date").resample("ME")["revenue"].sum()
            result = np.floor(series)
            
            self.audit_logger.log_action(
                action_type='monthly_revenue',
                agent='analytics',
                details={
                    'months': len(result),
                    'total': float(result.sum()),
                    'avg_monthly': float(result.mean()) if not result.empty else 0
                },
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'monthly_revenue'})
            self.audit_logger.log_action(
                action_type='monthly_revenue_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    @timer(operation='monthly_profit')
    def monthly_profit(self):
        """Get monthly profit with monitoring"""
        try:
            if "date" not in self.df.columns or "profit" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='monthly_profit_missing',
                    agent='analytics',
                    details={'error': 'date or profit column missing'},
                    session_id=self.session_id
                )
                return pd.Series(dtype=float)
            
            # Drop rows with missing dates
            df = self.df.dropna(subset=["date"])
            if df.empty:
                return pd.Series(dtype=float)
            
            series = df.set_index("date").resample("ME")["profit"].sum()
            result = np.floor(series)
            
            self.audit_logger.log_action(
                action_type='monthly_profit',
                agent='analytics',
                details={
                    'months': len(result),
                    'total': float(result.sum()),
                    'avg_monthly': float(result.mean()) if not result.empty else 0
                },
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'monthly_profit'})
            self.audit_logger.log_action(
                action_type='monthly_profit_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    @timer(operation='monthly_growth')
    def monthly_growth(self):
        """Get monthly growth with monitoring"""
        try:
            monthly = self.monthly_revenue()
            if monthly.empty or len(monthly) < 2:
                return pd.Series(dtype=float)
            
            growth = monthly.pct_change().fillna(0)
            result = np.floor(growth * 100) / 100  # floor to 2 decimals
            
            if not result.empty:
                self.audit_logger.log_action(
                    action_type='monthly_growth',
                    agent='analytics',
                    details={
                        'avg_growth': float(result.mean()),
                        'latest_growth': float(result.iloc[-1]),
                        'positive_months': int((result > 0).sum())
                    },
                    session_id=self.session_id
                )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'monthly_growth'})
            self.audit_logger.log_action(
                action_type='monthly_growth_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    # -----------------------------
    # Quantity metrics
    # -----------------------------
    @timer(operation='total_units_sold')
    def total_units_sold(self):
        """Get total units sold with monitoring"""
        try:
            if "quantity" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='total_units_sold_missing',
                    agent='analytics',
                    details={'error': 'quantity column missing'},
                    session_id=self.session_id
                )
                return None
                
            result = np.floor(self.df["quantity"].sum())
            
            self.audit_logger.log_action(
                action_type='total_units_sold',
                agent='analytics',
                details={'total_units': float(result)},
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'total_units_sold'})
            self.audit_logger.log_action(
                action_type='total_units_sold_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    @timer(operation='revenue_per_unit')
    def revenue_per_unit(self):
        """Get revenue per unit with monitoring"""
        try:
            if "quantity" not in self.df.columns:
                return None
            
            total_quantity = self.df["quantity"].sum()
            if total_quantity == 0:
                return None
                
            result = np.floor(self.df["revenue"].sum() / total_quantity)
            
            self.audit_logger.log_action(
                action_type='revenue_per_unit',
                agent='analytics',
                details={'revenue_per_unit': float(result)},
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'revenue_per_unit'})
            self.audit_logger.log_action(
                action_type='revenue_per_unit_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    # -----------------------------
    # Payment analysis
    # -----------------------------
    @timer(operation='revenue_by_payment_status')
    def revenue_by_payment_status(self):
        """Get revenue by payment status with monitoring"""
        try:
            if "payment_status" not in self.df.columns:
                return None
            
            # Handle empty payment status
            df = self.df.copy()
            df["payment_status"] = df["payment_status"].fillna("unknown").replace("", "unknown")
            
            result = np.floor(df.groupby("payment_status")["revenue"].sum())
            
            self.audit_logger.log_action(
                action_type='revenue_by_payment_status',
                agent='analytics',
                details={
                    'statuses': list(result.index),
                    'paid': float(result.get('paid', 0)),
                    'pending': float(result.get('pending', 0)),
                    'failed': float(result.get('failed', 0)),
                    'unknown': float(result.get('unknown', 0))
                },
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'revenue_by_payment_status'})
            self.audit_logger.log_action(
                action_type='revenue_by_payment_status_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    # -----------------------------
    # Anomaly detection
    # -----------------------------
    @timer(operation='detect_revenue_spikes')
    def detect_revenue_spikes(self, threshold_std=2):
        """Detect revenue spikes with monitoring"""
        try:
            monthly = self.monthly_revenue()
            if monthly.empty or len(monthly) < 3:
                return pd.Series(dtype=float)
            
            threshold = monthly.mean() + threshold_std * monthly.std()
            anomalies = monthly[monthly > threshold]
            
            self.audit_logger.log_action(
                action_type='detect_revenue_spikes',
                agent='analytics',
                details={
                    'threshold': float(threshold),
                    'threshold_std': threshold_std,
                    'anomalies_found': len(anomalies),
                    'anomaly_months': [str(d) for d in anomalies.index] if not anomalies.empty else []
                },
                session_id=self.session_id
            )
            
            return anomalies
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'detect_revenue_spikes'})
            self.audit_logger.log_action(
                action_type='detect_revenue_spikes_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    # -----------------------------
    # Generate human-readable summary
    # -----------------------------
    @timer(operation='generate_summary')
    def generate_summary(self):
        """Generate summary with monitoring"""
        try:
            summary = ""
            kpis = self.compute_kpis()

            summary += (
                f"Total revenue: ${kpis['total_revenue']:,.0f}, "
                f"total cost: ${kpis['total_cost']:,.0f}, "
                f"total profit: ${kpis['total_profit']:,.0f}, "
                f"profit margin: {kpis['profit_margin']:.0%}.\n"
            )

            top_cust = self.revenue_by_customer()
            if not top_cust.empty:
                top_3 = top_cust.head(3)
                customers = ", ".join([f"{c} (${r:,.0f})" for c, r in top_3.items()])
                summary += f"Top customers: {customers}.\n"

            growth = self.monthly_growth()
            if not growth.empty:
                latest_month = growth.index[-1].strftime("%B %Y")
                latest_growth = growth.iloc[-1] * 100
                summary += f"Latest month ({latest_month}) growth: {latest_growth:.0f}%.\n"

            anomalies = self.detect_revenue_spikes()
            if not anomalies.empty:
                months = ", ".join([d.strftime("%B %Y") for d in anomalies.index])
                summary += f"Revenue anomalies detected in: {months}.\n"

            payment_by_status = self.revenue_by_payment_status()
            if payment_by_status is not None and not payment_by_status.empty:
                unpaid = payment_by_status.get('pending', 0) + payment_by_status.get('failed', 0)
                if unpaid > 0:
                    summary += f"Outstanding unpaid revenue: ${unpaid:,.0f}.\n"
            
            self.audit_logger.log_action(
                action_type='generate_summary',
                agent='analytics',
                details={'summary_length': len(summary)},
                session_id=self.session_id
            )

            return summary
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'generate_summary'})
            self.audit_logger.log_action(
                action_type='generate_summary_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    # -----------------------------
    # Forecast revenue
    # -----------------------------
    @timer(operation='forecast_revenue')
    def forecast_revenue(self, steps=3):
        """Forecast revenue with monitoring"""
        try:
            monthly = self.monthly_revenue()
            
            # Check if we have enough data
            if monthly.empty or len(monthly) < 12:
                self.audit_logger.log_action(
                    action_type='forecast_insufficient_data',
                    agent='analytics',
                    details={'months_available': len(monthly)},
                    session_id=self.session_id
                )
                return None
            
            # Check for and handle nulls
            if monthly.isna().any():
                # Count nulls
                null_count = monthly.isna().sum()
                self.audit_logger.log_action(
                    action_type='forecast_null_values',
                    agent='analytics',
                    details={'null_months': null_count, 'total_months': len(monthly)},
                    session_id=self.session_id
                )
                
                # Handle nulls with interpolation (better than fill for time series)
                monthly = monthly.interpolate(method='time')
                
                # If still has nulls at edges, use fill methods
                if monthly.isna().any():
                    monthly = monthly.fillna(method='ffill').fillna(method='bfill')
            
            # Final check - if still have nulls, can't forecast
            if monthly.isna().any():
                self.audit_logger.log_action(
                    action_type='forecast_unrecoverable_nulls',
                    agent='analytics',
                    details={'message': 'Cannot recover from null values'},
                    session_id=self.session_id
                )
                return None
            
            # Track model training cost
            self.cost_tracker.track_call(
                model='statsmodels',
                input_tokens=len(monthly),
                output_tokens=steps,
                agent='analytics.forecast',
                user='system',
                session_id=self.session_id
            )
            
            model = ARIMA(monthly, order=(1, 1, 1))
            model_fit = model.fit()
            forecast = model_fit.forecast(steps=steps)
            
            # Convert to numpy array and floor
            result = np.floor(forecast.values) if hasattr(forecast, 'values') else np.floor(forecast)
            
            self.audit_logger.log_action(
                action_type='forecast_revenue',
                agent='analytics',
                details={
                    'historical_periods': len(monthly),
                    'forecast_steps': steps,
                    'forecast': [float(x) for x in result]
                },
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            context = {
                'tool': 'forecast_revenue',
                'monthly_data_length': len(monthly) if 'monthly' in locals() else 0
            }
            self.healer.analyze_failure(e, context)
            self.audit_logger.log_action(
                action_type='forecast_revenue_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            # Return None instead of raising to be more graceful
            return None

    # -----------------------------
    # Run tool by name
    # -----------------------------
    @timer(operation='run_tool')
    def run_tool(self, tool_name):
        """Run tool by name with monitoring"""
        tools = {
            "compute_kpis": self.compute_kpis,
            "revenue_by_customer": self.revenue_by_customer,
            "revenue_by_product": self.revenue_by_product,
            "revenue_by_region": self.revenue_by_region,
            "monthly_revenue": self.monthly_revenue,
            "monthly_profit": self.monthly_profit,
            "monthly_growth": self.monthly_growth,
            "total_units_sold": self.total_units_sold,
            "revenue_per_unit": self.revenue_per_unit,
            "revenue_by_payment_status": self.revenue_by_payment_status,
            "detect_revenue_spikes": self.detect_revenue_spikes,
            "forecast_revenue": self.forecast_revenue,
            "generate_summary": self.generate_summary,
            "monthly_revenue_by_customer": self.monthly_revenue_by_customer,
            "monthly_revenue_by_product": self.monthly_revenue_by_product 
        }

        if tool_name not in tools:
            error_msg = f"Unknown tool: {tool_name}"
            self.audit_logger.log_action(
                action_type='run_tool_error',
                agent='analytics',
                details={'error': error_msg, 'tool': tool_name},
                session_id=self.session_id
            )
            raise ValueError(error_msg)

        self.audit_logger.log_action(
            action_type='run_tool',
            agent='analytics',
            details={'tool': tool_name},
            session_id=self.session_id
        )

        return tools[tool_name]()

    # -----------------------------
    # Monthly revenue per customer
    # -----------------------------
    @timer(operation='monthly_revenue_by_customer')
    def monthly_revenue_by_customer(self, months_to_check=6):
        """
        Returns a dictionary with revenue per customer per month and monthly decline info.
        Format:
        {
            "Customer A": {
                "monthly_revenue": {"2024-01": 1200.0, "2024-02": 1100.0, ...},
                "declining": True,
                "trend": [1200.0, 1100.0, ...]
            },
            ...
        }
        """
        try:
            if "customer" not in self.df.columns or "date" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='monthly_revenue_by_customer_missing',
                    agent='analytics',
                    details={'error': 'customer or date column missing'},
                    session_id=self.session_id
                )
                return {}

            # Prepare data
            df = self.df.dropna(subset=["date", "revenue"]).copy()
            if df.empty:
                return {}
            
            df["customer"] = df["customer"].fillna("Unknown").replace("", "Unknown")
            df["month"] = df["date"].dt.to_period("M")
            
            grouped = df.groupby(["customer", "month"])["revenue"].sum().reset_index()

            result = {}
            declining_count = 0

            for customer, group in grouped.groupby("customer"):
                # Sort months ascending
                group = group.sort_values("month")
                monthly_dict = {str(row["month"]): float(np.floor(row["revenue"])) for _, row in group.iterrows()}

                # Take last `months_to_check` months
                last_months = list(monthly_dict.values())[-months_to_check:]

                # Determine if declining trend: each month <= previous month
                declining = all(earlier >= later for earlier, later in zip(last_months, last_months[1:])) if len(last_months) > 1 else False
                
                if declining:
                    declining_count += 1

                result[customer] = {
                    "monthly_revenue": monthly_dict,
                    "trend": last_months,
                    "declining": declining
                }

            self.audit_logger.log_action(
                action_type='monthly_revenue_by_customer',
                agent='analytics',
                details={
                    'total_customers': len(result),
                    'declining_customers': declining_count,
                    'months_analyzed': months_to_check
                },
                session_id=self.session_id
            )

            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'monthly_revenue_by_customer'})
            self.audit_logger.log_action(
                action_type='monthly_revenue_by_customer_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise