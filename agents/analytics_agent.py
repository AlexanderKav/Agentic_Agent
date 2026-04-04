"""
Analytics Agent - Performs data analysis with monitoring, self-healing, and cost tracking
"""

import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose

from agents.monitoring import get_performance_tracker, timer, get_audit_logger, get_cost_tracker
from agents.self_healing import get_healing_agent

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)


class AnalyticsAgent:
    """
    Performs data analysis on standardized dataframes.
    Works with SchemaMapper output which provides consistent column names.
    """

    def __init__(self, df: pd.DataFrame):
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
    # Helper Methods
    # -----------------------------
    def _safe_floor(self, value: float) -> float:
        """Safely apply floor operation, handling NaN values."""
        if pd.isna(value):
            return 0.0
        return float(np.floor(value))

    def _is_declining_trend(self, trend_values: List[float]) -> bool:
        """Check if trend is declining."""
        if len(trend_values) < 2:
            return False
        return all(earlier >= later for earlier, later in zip(trend_values, trend_values[1:]))

    def _get_monthly_revenue(self, df: pd.DataFrame) -> pd.Series:
        """Helper to get monthly revenue from a dataframe."""
        if 'date' not in df.columns or 'revenue' not in df.columns:
            return pd.Series(dtype=float)
        
        df_copy = df.copy()
        df_copy['date'] = pd.to_datetime(df_copy['date'])
        df_copy['month'] = df_copy['date'].dt.to_period('M')
        
        monthly = df_copy.groupby('month')['revenue'].sum()
        monthly.index = monthly.index.to_timestamp()
        
        return monthly

    # -----------------------------
    # KPIs
    # -----------------------------
    @timer(operation='compute_kpis')
    def compute_kpis(self) -> Dict[str, float]:
        """Compute KPIs with monitoring."""
        try:
            if "revenue" not in self.df.columns:
                recovered = self._recover_kpis_with_alternatives()
                if recovered:
                    return recovered
                raise KeyError("Revenue column not found in dataframe")
            
            total_revenue = self._safe_floor(self.df["revenue"].sum())
            
            total_cost = 0.0
            total_profit = total_revenue
            profit_margin = 1.0
            
            if "cost" in self.df.columns:
                total_cost = self._safe_floor(self.df["cost"].sum())
                total_profit = total_revenue - total_cost
                profit_margin = total_profit / total_revenue if total_revenue > 0 else 0
                profit_margin = np.floor(profit_margin * 100) / 100

            avg_order_value = self._safe_floor(self.df["revenue"].mean())
            
            result = {
                "total_revenue": float(total_revenue),
                "total_cost": float(total_cost),
                "total_profit": float(total_profit),
                "profit_margin": float(profit_margin),
                "avg_order_value": float(avg_order_value)
            }
            
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
            context = {
                'tool': 'compute_kpis',
                'error_type': 'missing_column',
                'data_shape': self.df.shape,
                'available_columns': list(self.df.columns)
            }
            self.healer.analyze_failure(e, context)
            self.audit_logger.log_action(
                action_type='compute_kpis_error',
                agent='analytics',
                details={'error': str(e), 'context': context},
                session_id=self.session_id
            )
            raise
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'compute_kpis'})
            self.audit_logger.log_action(
                action_type='compute_kpis_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            raise

    def _recover_kpis_with_alternatives(self) -> Optional[Dict[str, float]]:
        """Recovery method for missing columns - kept for backward compatibility."""
        try:
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
                total_revenue = self._safe_floor(self.df[revenue_col].sum())
                
                if cost_col:
                    total_cost = self._safe_floor(self.df[cost_col].sum())
                    total_profit = total_revenue - total_cost
                    profit_margin = total_profit / total_revenue if total_revenue > 0 else 0
                else:
                    total_cost = self._safe_floor(total_revenue * 0.6)
                    total_profit = total_revenue - total_cost
                    profit_margin = 0.4
                
                avg_order_value = self._safe_floor(self.df[revenue_col].mean())
                
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
            return None

    # -----------------------------
    # Revenue breakdowns
    # -----------------------------
    @timer(operation='revenue_by_customer')
    def revenue_by_customer(self) -> pd.Series:
        """Get revenue by customer with monitoring."""
        try:
            if "customer" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='revenue_by_customer_missing',
                    agent='analytics',
                    details={'error': 'customer column missing'},
                    session_id=self.session_id
                )
                return pd.Series(dtype=float)
            
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
            raise

    @timer(operation='revenue_by_product')
    def revenue_by_product(self) -> pd.Series:
        """Get revenue by product with monitoring."""
        try:
            if "product" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='revenue_by_product_missing',
                    agent='analytics',
                    details={'error': 'product column missing'},
                    session_id=self.session_id
                )
                return pd.Series(dtype=float)
            
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
            raise

    @timer(operation='revenue_by_region')
    def revenue_by_region(self) -> pd.Series:
        """Get revenue by region with monitoring."""
        try:
            if "region" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='revenue_by_region_missing',
                    agent='analytics',
                    details={'error': 'region column missing'},
                    session_id=self.session_id
                )
                return pd.Series(dtype=float)
            
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
            raise

    # -----------------------------
    # Monthly metrics
    # -----------------------------
    @timer(operation='monthly_revenue')
    def monthly_revenue(self) -> pd.Series:
        """Get monthly revenue with monitoring."""
        try:
            if "date" not in self.df.columns or "revenue" not in self.df.columns:
                return pd.Series(dtype=float)
            
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
            raise

    @timer(operation='monthly_profit')
    def monthly_profit(self) -> pd.Series:
        """Get monthly profit with monitoring."""
        try:
            if "date" not in self.df.columns or "profit" not in self.df.columns:
                return pd.Series(dtype=float)
            
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
            raise

    @timer(operation='monthly_growth')
    def monthly_growth(self) -> pd.Series:
        """Get monthly growth with monitoring."""
        try:
            monthly = self.monthly_revenue()
            if monthly.empty or len(monthly) < 2:
                return pd.Series(dtype=float)
            
            growth = monthly.pct_change().fillna(0)
            result = np.floor(growth * 100) / 100
            
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
            raise

    # -----------------------------
    # ENHANCED FORECASTING METHODS
    # -----------------------------
    
    @timer(operation='detect_seasonality')
    def detect_seasonality(self) -> Dict[str, Any]:
        """Detect seasonal patterns in monthly data."""
        try:
            monthly = self.monthly_revenue()
            
            if len(monthly) < 24:  # Need at least 2 years of data
                return {
                    "has_seasonality": False,
                    "message": "Insufficient data for seasonality detection (need at least 24 months)",
                    "months_available": len(monthly)
                }
            
            try:
                # Decompose the time series
                decomposition = seasonal_decompose(monthly, model='additive', period=12)
                
                # Calculate seasonal strength
                seasonal_variance = decomposition.seasonal.var()
                residual_variance = decomposition.resid.var()
                seasonal_strength = 1 - (residual_variance / seasonal_variance) if seasonal_variance > 0 else 0
                
                if seasonal_strength > 0.3:
                    # Find peak month
                    avg_seasonal = decomposition.seasonal.groupby(decomposition.seasonal.index.month).mean()
                    peak_month_idx = avg_seasonal.argmax()
                    peak_month = pd.to_datetime(f"2024-{peak_month_idx}-01").strftime('%B')
                    
                    # Find trough month
                    trough_month_idx = avg_seasonal.argmin()
                    trough_month = pd.to_datetime(f"2024-{trough_month_idx}-01").strftime('%B')
                    
                    return {
                        "has_seasonality": True,
                        "strength": round(seasonal_strength, 2),
                        "peak_month": peak_month,
                        "trough_month": trough_month,
                        "seasonal_pattern": avg_seasonal.to_dict(),
                        "explanation": f"Strong seasonal pattern detected. Revenue typically peaks in {peak_month} and troughs in {trough_month}.",
                        "recommendation": "Consider adjusting inventory and marketing spend to align with seasonal peaks."
                    }
                else:
                    return {
                        "has_seasonality": False,
                        "strength": round(seasonal_strength, 2),
                        "message": "No strong seasonal pattern detected",
                        "explanation": "Revenue doesn't show consistent seasonal patterns across years."
                    }
                    
            except Exception as e:
                self.audit_logger.log_action(
                    action_type='seasonality_detection_error',
                    agent='analytics',
                    details={'error': str(e)},
                    session_id=self.session_id
                )
                return {
                    "has_seasonality": False,
                    "message": f"Could not detect seasonality: {str(e)}"
                }
                
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'detect_seasonality'})
            return {"has_seasonality": False, "error": str(e)}

    @timer(operation='forecast_revenue_with_explanation')
    def forecast_revenue_with_explanation(self, steps: int = 3, period_label: Optional[str] = None) -> Dict[str, Any]:
        """
        Forecast revenue with natural language explanation.
        
        Args:
            steps: Number of months to forecast (default 3 for quarter)
            period_label: Optional label (for consistency with other forecast methods)
        """
        try:
            monthly = self.monthly_revenue()
            
            # Debug print
            print(f"📊 Monthly revenue shape: {monthly.shape if hasattr(monthly, 'shape') else len(monthly)}")
            print(f"📊 Monthly revenue data: {monthly.head() if not monthly.empty else 'Empty'}")
            
            if monthly.empty or len(monthly) < 12:
                return {
                    "forecast": None,
                    "explanation": f"Insufficient data for forecasting (need at least 12 months, have {len(monthly)})",
                    "error": "insufficient_data",
                    "months_available": len(monthly)
                }
            
            # Handle nulls
            if monthly.isna().any():
                print(f"⚠️ Found {monthly.isna().sum()} null values, interpolating...")
                monthly = monthly.interpolate(method='time').fillna(method='ffill')
            
            # Check if data is numeric
            if not pd.api.types.is_numeric_dtype(monthly):
                print(f"❌ Monthly data is not numeric: {monthly.dtype}")
                return {
                    "forecast": None,
                    "explanation": "Revenue data is not numeric - cannot forecast",
                    "error": "invalid_data_type"
                }
            
            try:
                # Fit ARIMA model
                model = ARIMA(monthly, order=(1, 1, 1))
                model_fit = model.fit()
                forecast = model_fit.forecast(steps=steps)
                result = np.floor(forecast)
                
                # Calculate trend
                last_3_months = monthly.iloc[-3:].mean()
                forecast_3_months = result[:3].mean() if len(result) >= 3 else result.mean()
                trend_direction = "increasing" if forecast_3_months > last_3_months else "decreasing"
                avg_change = abs(forecast_3_months - last_3_months) / 3 if last_3_months > 0 else 0
                
                latest_value = monthly.iloc[-1]
                
                # Use period_label if provided
                period_text = f" for {period_label}" if period_label else ""
                
                print(f"✅ Forecast generated: {result.tolist()}")
                
                return {
                    "forecast": result.tolist() if hasattr(result, 'tolist') else list(result),
                    "explanation": f"Based on historical trends, revenue is projected to {trend_direction} by ${avg_change:,.0f} per month over the next {steps} months{period_text}. Current monthly revenue is ${latest_value:,.0f}.",
                    "trend_direction": trend_direction,
                    "avg_monthly_change": avg_change,
                    "latest_revenue": float(latest_value),
                    "forecast_values": result.tolist() if hasattr(result, 'tolist') else list(result),
                    "confidence": "medium",
                    "method": "ARIMA (1,1,1)",
                    "period": period_label
                }
                
            except Exception as model_error:
                print(f"❌ ARIMA model error: {model_error}")
                # Fallback to simple moving average
                print("🔄 Falling back to moving average forecast")
                ma_forecast = monthly.rolling(3).mean().iloc[-1] * np.ones(steps)
                result = np.floor(ma_forecast)
                
                return {
                    "forecast": result.tolist() if hasattr(result, 'tolist') else list(result),
                    "explanation": f"Using simple moving average forecast (ARIMA failed). Revenue is projected to be around ${result[0]:,.0f} next month.",
                    "method": "Moving Average (fallback)",
                    "fallback_used": True,
                    "period": period_label
                }
            
        except Exception as e:
            print(f"❌ forecast_revenue_with_explanation error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "forecast": None,
                "explanation": f"Could not generate forecast: {str(e)}",
                "error": str(e)
            }

    @timer(operation='forecast_with_confidence')
    # In the AnalyticsAgent class, update the forecast methods to accept period_label parameter

    @timer(operation='forecast_with_confidence')
    def forecast_with_confidence(self, steps: int = 3, confidence_level: float = 0.95, period_label: str = None) -> Dict[str, Any]:
        """Forecast revenue with confidence intervals.
        
        Args:
            steps: Number of months to forecast
            confidence_level: Confidence level (0.95 = 95%)
            period_label: Optional label for the forecast period (e.g., "Q1 2025")
        """
        try:
            monthly = self.monthly_revenue()
            
            if monthly.empty or len(monthly) < 12:
                return {
                    "forecast": None,
                    "explanation": f"Insufficient data for forecasting (need at least 12 months, have {len(monthly)})",
                    "error": "insufficient_data"
                }
            
            # Handle nulls
            if monthly.isna().any():
                monthly = monthly.interpolate(method='time').fillna(method='ffill')
            
            # Fit ARIMA model
            model = ARIMA(monthly, order=(1, 1, 1))
            model_fit = model.fit()
            
            # Get forecast with confidence intervals
            forecast_result = model_fit.get_forecast(steps=steps)
            forecast = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=1 - confidence_level)
            
            result = np.floor(forecast)
            lower = np.floor(conf_int.iloc[:, 0])
            upper = np.floor(conf_int.iloc[:, 1])
            
            self.audit_logger.log_action(
                action_type='forecast_with_confidence',
                agent='analytics',
                details={
                    'steps': steps,
                    'confidence_level': confidence_level,
                    'forecast': result.tolist() if hasattr(result, 'tolist') else list(result),
                    'period_label': period_label
                },
                session_id=self.session_id
            )
            
            period_text = f" for {period_label}" if period_label else ""
            
            return {
                "forecast": result.tolist() if hasattr(result, 'tolist') else list(result),
                "lower_bound": lower.tolist() if hasattr(lower, 'tolist') else list(lower),
                "upper_bound": upper.tolist() if hasattr(upper, 'tolist') else list(upper),
                "confidence_level": confidence_level,
                "explanation": f"With {confidence_level * 100:.0f}% confidence, revenue next month will be between ${lower.iloc[0]:,.0f} and ${upper.iloc[0]:,.0f}.{period_text}",
                "method": "ARIMA (1,1,1) with confidence intervals",
                "period": period_label
            }
            
        except Exception as e:
            context = {'tool': 'forecast_with_confidence', 'error': str(e)}
            self.healer.analyze_failure(e, context)
            return {
                "forecast": None,
                "explanation": f"Could not generate confidence intervals: {str(e)}",
                "error": str(e)
            }


    @timer(operation='forecast_ensemble')
    def forecast_ensemble(self, steps: int = 3, period_label: str = None) -> Dict[str, Any]:
        """Compare multiple forecasting methods and return ensemble.
        
        Args:
            steps: Number of months to forecast
            period_label: Optional label for the forecast period (e.g., "Q1 2025")
        """
        try:
            monthly = self.monthly_revenue()
            
            if monthly.empty or len(monthly) < 12:
                return {
                    "forecast": None,
                    "explanation": f"Insufficient data for forecasting (need at least 12 months, have {len(monthly)})",
                    "error": "insufficient_data"
                }
            
            # Handle nulls
            if monthly.isna().any():
                monthly = monthly.interpolate(method='time').fillna(method='ffill')
            
            forecasts = {}
            
            # Method 1: ARIMA
            try:
                arima_model = ARIMA(monthly, order=(1, 1, 1)).fit()
                forecasts["ARIMA"] = np.floor(arima_model.forecast(steps=steps)).tolist()
            except Exception as e:
                forecasts["ARIMA"] = {"error": str(e)}
            
            # Method 2: Simple Moving Average (3-month)
            try:
                ma_forecast = monthly.rolling(3).mean().iloc[-1] * np.ones(steps)
                forecasts["Moving Average"] = np.floor(ma_forecast).tolist()
            except Exception as e:
                forecasts["Moving Average"] = {"error": str(e)}
            
            # Method 3: Exponential Smoothing (if enough data)
            try:
                if len(monthly) >= 24:
                    ets_model = ExponentialSmoothing(
                        monthly, 
                        seasonal_periods=12, 
                        trend='add', 
                        seasonal='add'
                    ).fit()
                    forecasts["ETS"] = np.floor(ets_model.forecast(steps=steps)).tolist()
            except Exception as e:
                forecasts["ETS"] = {"error": str(e)}
            
            # Calculate ensemble average (only for successful numeric forecasts)
            numeric_forecasts = []
            for name, fcast in forecasts.items():
                if isinstance(fcast, list) and all(isinstance(x, (int, float)) for x in fcast):
                    numeric_forecasts.append(np.array(fcast))
            
            if numeric_forecasts:
                ensemble = np.mean(numeric_forecasts, axis=0)
                ensemble_floor = np.floor(ensemble).tolist()
            else:
                ensemble_floor = None
            
            self.audit_logger.log_action(
                action_type='forecast_ensemble',
                agent='analytics',
                details={
                    'methods_used': [m for m in forecasts if isinstance(forecasts[m], list)],
                    'steps': steps,
                    'period_label': period_label
                },
                session_id=self.session_id
            )
            
            period_text = f" for {period_label}" if period_label else ""
            
            return {
                "forecasts": forecasts,
                "ensemble": ensemble_floor,
                "explanation": f"Combined forecast using multiple methods for more reliable predictions.{period_text}",
                "methods_successful": [m for m in forecasts if isinstance(forecasts[m], list)],
                "recommended": "ensemble" if ensemble_floor else list(forecasts.keys())[0],
                "period": period_label
            }
            
        except Exception as e:
            context = {'tool': 'forecast_ensemble', 'error': str(e)}
            self.healer.analyze_failure(e, context)
            return {
                "forecast": None,
                "explanation": f"Could not generate ensemble forecast: {str(e)}",
                "error": str(e)
            }


    @timer(operation='forecast_revenue')
    def forecast_revenue(self, steps: int = 3, period_label: str = None) -> Optional[pd.Series]:
        """Forecast revenue with monitoring (original method).
        
        Args:
            steps: Number of months to forecast
            period_label: Optional label for the forecast period (e.g., "Q1 2025")
        """
        try:
            monthly = self.monthly_revenue()
            
            print(f"📊 Monthly revenue for forecast: {len(monthly)} months")
            
            if monthly.empty or len(monthly) < 12:
                self.audit_logger.log_action(
                    action_type='forecast_insufficient_data',
                    agent='analytics',
                    details={'months_available': len(monthly), 'period_label': period_label},
                    session_id=self.session_id
                )
                return None
            
            # Handle nulls
            if monthly.isna().any():
                monthly = monthly.interpolate(method='time').fillna(method='ffill')
            
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
            result = np.floor(forecast)
            
            self.audit_logger.log_action(
                action_type='forecast_revenue',
                agent='analytics',
                details={
                    'historical_periods': len(monthly),
                    'forecast_steps': steps,
                    'forecast': [float(x) for x in result],
                    'period_label': period_label
                },
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            print(f"❌ forecast_revenue error: {e}")
            import traceback
            traceback.print_exc()
            return None

    # -----------------------------
    # Quantity metrics
    # -----------------------------
    @timer(operation='total_units_sold')
    def total_units_sold(self) -> Optional[float]:
        """Get total units sold with monitoring."""
        try:
            if "quantity" not in self.df.columns:
                return None
                
            result = self._safe_floor(self.df["quantity"].sum())
            
            self.audit_logger.log_action(
                action_type='total_units_sold',
                agent='analytics',
                details={'total_units': float(result)},
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'total_units_sold'})
            raise

    @timer(operation='revenue_per_unit')
    def revenue_per_unit(self) -> Optional[float]:
        """Get revenue per unit with monitoring."""
        try:
            if "quantity" not in self.df.columns:
                return None
            
            total_quantity = self.df["quantity"].sum()
            if total_quantity == 0:
                return None
                
            result = self._safe_floor(self.df["revenue"].sum() / total_quantity)
            
            self.audit_logger.log_action(
                action_type='revenue_per_unit',
                agent='analytics',
                details={'revenue_per_unit': float(result)},
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'revenue_per_unit'})
            raise

    # -----------------------------
    # Payment analysis
    # -----------------------------
    @timer(operation='revenue_by_payment_status')
    def revenue_by_payment_status(self) -> Optional[pd.Series]:
        """Get revenue by payment status with monitoring."""
        try:
            if "payment_status" not in self.df.columns:
                return None
            
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
            raise

    # -----------------------------
    # Anomaly detection
    # -----------------------------
    @timer(operation='detect_revenue_spikes')
    def detect_revenue_spikes(self, threshold_std: int = 2, by_product: bool = False) -> Dict[str, Any]:
        """Detect revenue spikes with consistent format for UI.
        
        Args:
            threshold_std: Number of standard deviations for threshold
            by_product: If True, detect anomalies by product
        """
        try:
            self.audit_logger.log_action(
                action_type='detect_revenue_spikes',
                agent='analytics',
                details={'threshold_std': threshold_std, 'by_product': by_product},
                session_id=self.session_id
            )
            
            if by_product and 'product' in self.df.columns:
                # Detect anomalies by product
                anomalies_by_product = {}
                
                for product in self.df['product'].unique():
                    product_df = self.df[self.df['product'] == product]
                    product_monthly = self._get_monthly_revenue(product_df)
                    
                    if len(product_monthly) >= 3:
                        threshold = product_monthly.mean() + threshold_std * product_monthly.std()
                        anomalies = product_monthly[product_monthly > threshold]
                        
                        for date, value in anomalies.items():
                            product_name = product.replace('_', ' ').replace('Plan', ' Plan')
                            month_name = date.strftime('%B')
                            anomalies_by_product[product_name] = {
                                month_name: f"The revenue was ${value:,.0f}, which is significantly higher than the average of ${product_monthly.mean():,.0f} for {product_name}"
                            }
                
                # Also detect drops (lower than average - threshold)
                for product in self.df['product'].unique():
                    product_df = self.df[self.df['product'] == product]
                    product_monthly = self._get_monthly_revenue(product_df)
                    
                    if len(product_monthly) >= 3:
                        avg = product_monthly.mean()
                        std = product_monthly.std()
                        lower_threshold = avg - (threshold_std * std)
                        drops = product_monthly[product_monthly < lower_threshold]
                        
                        for date, value in drops.items():
                            product_name = product.replace('_', ' ').replace('Plan', ' Plan')
                            month_name = date.strftime('%B')
                            if product_name not in anomalies_by_product:
                                anomalies_by_product[product_name] = {}
                            anomalies_by_product[product_name][month_name] = f"The revenue dropped significantly to ${value:,.0f}, which is much lower than the average of ${avg:,.0f} for {product_name}"
                
                return anomalies_by_product if anomalies_by_product else {}
            
            else:
                # Overall revenue spikes
                monthly = self.monthly_revenue()
                if monthly.empty or len(monthly) < 3:
                    return {}
                
                avg = monthly.mean()
                std = monthly.std()
                upper_threshold = avg + threshold_std * std
                lower_threshold = avg - threshold_std * std
                
                spikes = monthly[monthly > upper_threshold]
                drops = monthly[monthly < lower_threshold]
                
                anomalies = {}
                
                for date, value in spikes.items():
                    month_name = date.strftime('%B')
                    anomalies[f"Overall Revenue"] = {
                        month_name: f"Revenue spike detected: ${value:,.0f} (vs average ${avg:,.0f})"
                    }
                
                for date, value in drops.items():
                    month_name = date.strftime('%B')
                    if "Overall Revenue" not in anomalies:
                        anomalies["Overall Revenue"] = {}
                    anomalies["Overall Revenue"][month_name] = f"Revenue dropped to ${value:,.0f} (vs average ${avg:,.0f})"
                
                return anomalies
                
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'detect_revenue_spikes'})
            print(f"Error detecting revenue spikes: {e}")
            return {}

    # -----------------------------
    # Generate human-readable summary
    # -----------------------------
    @timer(operation='generate_summary')
    def generate_summary(self) -> str:
        """Generate summary with monitoring."""
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
            if anomalies:
                summary += f"Revenue anomalies detected.\n"

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
            raise

    # -----------------------------
    # Monthly revenue per product
    # -----------------------------
    @timer(operation='monthly_revenue_by_product')
    def monthly_revenue_by_product(self) -> Dict[str, Any]:
        """Get monthly revenue per product."""
        try:
            if "product" not in self.df.columns or "date" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='monthly_revenue_by_product_missing',
                    agent='analytics',
                    details={'error': 'product or date column missing'},
                    session_id=self.session_id
                )
                return {}
            
            df = self.df.dropna(subset=["date", "revenue"]).copy()
            if df.empty:
                return {}
            
            df["month"] = df["date"].dt.to_period("M")
            grouped = df.groupby(["product", "month"])["revenue"].sum().reset_index()
            
            result = {}
            for product, group in grouped.groupby("product"):
                monthly = {str(row["month"]): float(np.floor(row["revenue"])) for _, row in group.iterrows()}
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
            raise

    # -----------------------------
    # Monthly revenue per customer
    # -----------------------------
    @timer(operation='monthly_revenue_by_customer')
    def monthly_revenue_by_customer(self, months_to_check: int = 6) -> Dict[str, Any]:
        """
        Returns a dictionary with revenue per customer per month and monthly decline info.
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

            df = self.df.dropna(subset=["date", "revenue"]).copy()
            if df.empty:
                return {}
            
            df["customer"] = df["customer"].fillna("Unknown").replace("", "Unknown")
            df["month"] = df["date"].dt.to_period("M")
            
            grouped = df.groupby(["customer", "month"])["revenue"].sum().reset_index()

            result = {}
            declining_count = 0

            for customer, group in grouped.groupby("customer"):
                group = group.sort_values("month")
                monthly_dict = {str(row["month"]): float(np.floor(row["revenue"])) for _, row in group.iterrows()}
                last_months = list(monthly_dict.values())[-months_to_check:]

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
            raise

    # -----------------------------
    # Full monthly revenue per product
    # -----------------------------
    @timer(operation='monthly_revenue_by_product_full')
    def monthly_revenue_by_product_full(self) -> pd.DataFrame:
        """
        Get full monthly revenue per product (not just last 6 months)
        Returns DataFrame with product, month, revenue
        """
        try:
            if "product" not in self.df.columns or "date" not in self.df.columns:
                self.audit_logger.log_action(
                    action_type='monthly_revenue_by_product_missing',
                    agent='analytics',
                    details={'error': 'product or date column missing'},
                    session_id=self.session_id
                )
                return pd.DataFrame()
            
            # Drop rows with missing dates or revenue
            df = self.df.dropna(subset=["date", "revenue"]).copy()
            if df.empty:
                return pd.DataFrame()
            
            # Create month period
            df["month"] = df["date"].dt.to_period("M")
            
            # Group by product and month
            result = df.groupby(["product", "month"])["revenue"].sum().reset_index()
            result["month_str"] = result["month"].astype(str)
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {'tool': 'monthly_revenue_by_product_full'})
            self.audit_logger.log_action(
                action_type='monthly_revenue_by_product_full_error',
                agent='analytics',
                details={'error': str(e)},
                session_id=self.session_id
            )
            return pd.DataFrame()

    # -----------------------------
    # Forecast revenue by product
    # -----------------------------
    @timer(operation='forecast_revenue_by_product')
    def forecast_revenue_by_product(self, steps: int = 3, period_label: Optional[str] = None) -> Dict[str, Any]:
        """
        Forecast revenue for each product individually.
        
        Args:
            steps: Number of months to forecast (default 3 for quarter)
            period_label: Optional label like "Q1 2025" or "next quarter"
        
        Returns dictionary with product forecasts
        """
        try:
            # Get historical monthly data by product
            product_data = self.monthly_revenue_by_product_full()
            
            if product_data.empty:
                return {
                    "error": "No product data available",
                    "forecasts": {}
                }
            
            # Calculate the forecast period label if not provided
            if period_label is None:
                # Get the last date from the data to determine the forecast period
                if 'date' in self.df.columns:
                    last_date = pd.to_datetime(self.df['date']).max()
                    # Calculate next quarter from last data point
                    next_month = last_date + pd.DateOffset(months=1)
                    next_quarter_end = next_month + pd.DateOffset(months=steps - 1)
                    
                    # Format based on steps
                    if steps == 3:
                        # Quarter format
                        quarter = (next_month.month - 1) // 3 + 1
                        year = next_month.year
                        period_label = f"Q{quarter} {year}"
                    else:
                        period_label = f"{next_month.strftime('%b %Y')} - {next_quarter_end.strftime('%b %Y')}"
                else:
                    # Fallback to current date
                    now = datetime.now()
                    current_quarter = (now.month - 1) // 3 + 1
                    next_quarter = current_quarter + 1 if current_quarter < 4 else 1
                    next_year = now.year + 1 if current_quarter == 4 else now.year
                    period_label = f"Q{next_quarter} {next_year}"
            
            print(f"📊 Forecasting for period: {period_label}")
            
            forecasts = {}
            products = product_data["product"].unique()
            
            # Create future dates for the forecast period
            if 'date' in self.df.columns:
                last_date = pd.to_datetime(self.df['date']).max()
            else:
                last_date = datetime.now()
                
            forecast_months = []
            for i in range(1, steps + 1):
                next_date = last_date + pd.DateOffset(months=i)
                forecast_months.append(next_date.strftime('%B %Y'))
            
            for product in products:
                # Get time series for this product
                product_series = product_data[product_data["product"] == product].copy()
                product_series = product_series.sort_values("month")
                
                # Create monthly time series with proper index
                monthly = pd.Series(
                    product_series["revenue"].values,
                    index=pd.to_datetime(product_series["month"].astype(str))
                )
                
                # Resample to monthly frequency (fill missing months with 0)
                monthly = monthly.resample("ME").sum().fillna(0)
                
                print(f"📊 Product {product}: {len(monthly)} months of data")
                
                # Need at least 3 months
                if len(monthly) < 3:
                    forecasts[product] = {
                        "forecast": None,
                        "forecast_sum": None,
                        "forecast_months": forecast_months,
                        "explanation": f"Insufficient data for {product} (need 3 months, have {len(monthly)})",
                        "error": "insufficient_data"
                    }
                    continue
                
                try:
                    # Use simple moving average for small datasets
                    if len(monthly) < 6:
                        print(f"⚠️ {product} has only {len(monthly)} months, using simple moving average")
                        # Calculate growth trend from available data
                        if len(monthly) >= 2:
                            # Calculate average monthly growth
                            monthly_pct = monthly.pct_change().dropna()
                            if len(monthly_pct) > 0 and monthly_pct.mean() != 0:
                                avg_growth = monthly_pct.mean()
                                # Project forward using growth rate
                                last_value = monthly.iloc[-1]
                                forecast = []
                                for i in range(steps):
                                    next_value = last_value * (1 + avg_growth) ** (i + 1)
                                    forecast.append(next_value)
                            else:
                                # Use simple average of last 3 months
                                ma = monthly.rolling(window=min(3, len(monthly)), min_periods=1).mean()
                                last_ma = ma.iloc[-1]
                                forecast = [last_ma] * steps
                        else:
                            # Only one month of data, use that value
                            forecast = [monthly.iloc[-1]] * steps
                        
                        forecast_sum = sum(forecast)
                        forecasts[product] = {
                            "forecast": np.floor(forecast).tolist(),
                            "forecast_sum": np.floor(forecast_sum),
                            "forecast_months": forecast_months,
                            "method": "Trend Projection (limited data)",
                            "explanation": f"Using trend projection from {len(monthly)} months of data."
                        }
                    else:
                        # Handle zeros (some products may have no sales in certain months)
                        if (monthly == 0).any():
                            print(f"⚠️ {product} has {(monthly == 0).sum()} zero months, using moving average")
                            ma = monthly.rolling(window=3, min_periods=1).mean()
                            forecast = ma.iloc[-1] * np.ones(steps)
                            forecast_sum = forecast.sum()
                            forecasts[product] = {
                                "forecast": np.floor(forecast).tolist(),
                                "forecast_sum": np.floor(forecast_sum),
                                "forecast_months": forecast_months,
                                "method": "Moving Average (due to zeros)",
                                "explanation": f"{product} has intermittent sales, using moving average for forecast."
                            }
                        else:
                            # Use ARIMA for products with consistent data
                            model = ARIMA(monthly, order=(1, 0, 1))
                            model_fit = model.fit()
                            forecast = model_fit.forecast(steps=steps)
                            forecast_sum = forecast.sum()
                            forecasts[product] = {
                                "forecast": np.floor(forecast).tolist(),
                                "forecast_sum": np.floor(forecast_sum),
                                "forecast_months": forecast_months,
                                "method": "ARIMA (1,0,1)",
                                "historical_avg": float(monthly.mean()),
                                "latest_monthly": float(monthly.iloc[-1])
                            }
                        
                except Exception as e:
                    print(f"❌ Error forecasting {product}: {e}")
                    # Fallback to simple average
                    avg = monthly.mean()
                    forecast_sum = avg * steps
                    forecasts[product] = {
                        "forecast": [np.floor(avg)] * steps,
                        "forecast_sum": np.floor(forecast_sum),
                        "forecast_months": forecast_months,
                        "method": "Simple Average (fallback)",
                        "explanation": f"Using average of historical data: ${avg:,.0f} per month"
                    }
            
            # Sort products by forecast_sum to identify top performer
            sorted_products = sorted(
                [(p, f.get("forecast_sum", 0)) for p, f in forecasts.items() if f.get("forecast_sum")],
                key=lambda x: x[1],
                reverse=True
            )
            
            self.audit_logger.log_action(
                action_type='forecast_revenue_by_product',
                agent='analytics',
                details={
                    'products_forecasted': list(forecasts.keys()),
                    'period': period_label,
                    'forecast_months': forecast_months,
                    'top_product': sorted_products[0][0] if sorted_products else None,
                    'top_product_forecast': sorted_products[0][1] if sorted_products else None
                },
                session_id=self.session_id
            )
            
            return {
                "forecasts": forecasts,
                "period": period_label,
                "forecast_months": forecast_months,
                "steps": steps,
                "top_product": sorted_products[0][0] if sorted_products else None,
                "top_product_forecast": sorted_products[0][1] if sorted_products else None,
                "ranked_products": [{"product": p, "forecast": f} for p, f in sorted_products]
            }
            
        except Exception as e:
            print(f"❌ forecast_revenue_by_product error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "forecasts": {}
            }

    # -----------------------------
    # Run tool by name
    # -----------------------------
    @timer(operation='run_tool')
    def run_tool(self, tool_name: str) -> Any:
        """Run tool by name with monitoring."""
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
            "forecast_revenue_with_explanation": self.forecast_revenue_with_explanation,
            "forecast_with_confidence": self.forecast_with_confidence,
            "forecast_ensemble": self.forecast_ensemble,
            "detect_seasonality": self.detect_seasonality,
            "generate_summary": self.generate_summary,
            "monthly_revenue_by_customer": self.monthly_revenue_by_customer,
            "monthly_revenue_by_product": self.monthly_revenue_by_product,
            "monthly_revenue_by_product_full": self.monthly_revenue_by_product_full,
            "forecast_revenue_by_product": self.forecast_revenue_by_product,
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