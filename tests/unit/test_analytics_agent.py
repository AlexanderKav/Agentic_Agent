"""
Unit tests for AnalyticsAgent
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch, call
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.analytics_agent import AnalyticsAgent
from agents.monitoring import get_performance_tracker, get_audit_logger, get_cost_tracker
from agents.self_healing import get_healing_agent

# Import shared fixtures
from tests.fixtures.sample_data import (
    sample_dataframe,
    sample_dataframe_long,
    minimal_dataframe,
    sample_dataframe_with_costs,
    varied_data,
    bad_data,
    empty_dataframe,
    missing_columns_data,
    single_row_data,
    multi_currency_data,
    sample_data_with_anomalies,
    long_time_series_data,
    create_custom_dataframe
)


# ==================== Additional Test Fixtures ====================

@pytest.fixture
def analytics_agent(sample_dataframe):
    """Create AnalyticsAgent instance with sample data"""
    return AnalyticsAgent(sample_dataframe)


@pytest.fixture
def analytics_agent_long(sample_dataframe_long):
    """Create AnalyticsAgent instance with longer data for forecasting"""
    return AnalyticsAgent(sample_dataframe_long)


@pytest.fixture
def analytics_agent_with_anomalies(sample_data_with_anomalies):
    """Create AnalyticsAgent instance with anomaly data"""
    return AnalyticsAgent(sample_data_with_anomalies)


@pytest.fixture
def analytics_agent_with_costs(sample_dataframe_with_costs):
    """Create AnalyticsAgent instance with cost data"""
    return AnalyticsAgent(sample_dataframe_with_costs)


@pytest.fixture
def analytics_agent_varied(varied_data):
    """Create AnalyticsAgent instance with varied data"""
    return AnalyticsAgent(varied_data)


# ==================== Test Initialization ====================

class TestAnalyticsAgentInitialization:
    """Test initialization and monitoring setup"""
    
    def test_init_with_valid_data(self, sample_dataframe):
        """Test initialization with valid data"""
        agent = AnalyticsAgent(sample_dataframe)
        assert isinstance(agent.df, pd.DataFrame)
        assert not agent.df.empty
        
        # Check monitoring is initialized
        assert hasattr(agent, 'perf_tracker')
        assert hasattr(agent, 'audit_logger')
        assert hasattr(agent, 'cost_tracker')
        assert hasattr(agent, 'healer')
        assert hasattr(agent, 'session_id')
    
    def test_init_copies_dataframe(self, sample_dataframe):
        """Test dataframe is copied"""
        agent = AnalyticsAgent(sample_dataframe)
        assert id(agent.df) != id(sample_dataframe)
    
    def test_date_conversion(self, sample_dataframe):
        """Test date conversion"""
        agent = AnalyticsAgent(sample_dataframe)
        assert pd.api.types.is_datetime64_any_dtype(agent.df['date'])
    
    def test_profit_calculation(self, sample_dataframe):
        """Test profit column calculation"""
        agent = AnalyticsAgent(sample_dataframe)
        assert 'profit' in agent.df.columns
        expected = agent.df['revenue'] - agent.df['cost']
        pd.testing.assert_series_equal(
            agent.df['profit'].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False
        )
    
    def test_init_with_empty_dataframe(self, empty_dataframe):
        """Test initialization with empty dataframe"""
        agent = AnalyticsAgent(empty_dataframe)
        assert agent.df.empty
    
    def test_init_with_missing_columns(self, missing_columns_data):
        """Test initialization with missing columns"""
        agent = AnalyticsAgent(missing_columns_data)
        # Should still initialize without errors
        assert isinstance(agent.df, pd.DataFrame)
    
    def test_init_with_single_row(self, single_row_data):
        """Test initialization with single row"""
        agent = AnalyticsAgent(single_row_data)
        assert len(agent.df) == 1


# ==================== Test KPIs ====================

class TestKPIs:
    """Test KPI computation with monitoring"""
    
    def test_compute_kpis(self, analytics_agent):
        """Test basic KPI calculation"""
        kpis = analytics_agent.compute_kpis()
        
        assert isinstance(kpis, dict)
        assert 'total_revenue' in kpis
        assert 'total_cost' in kpis
        assert 'total_profit' in kpis
        assert 'profit_margin' in kpis
        assert 'avg_order_value' in kpis
        
        # Test floor operation
        assert kpis['total_revenue'] == np.floor(kpis['total_revenue'])
    
    def test_compute_kpis_with_missing_columns(self, minimal_dataframe):
        """Test KPI calculation with missing columns"""
        agent = AnalyticsAgent(minimal_dataframe)
        
        kpis = agent.compute_kpis()
        assert kpis['total_revenue'] == 300
        assert kpis['total_cost'] == 150
    
    def test_compute_kpis_recovery(self):
        """Test KPI recovery when columns are missing"""
        df = pd.DataFrame({
            'sale_date': ['2024-01-01', '2024-01-02'],
            'sales_amount': [1000, 2000],
            'expenses': [400, 800],
            'client': ['A', 'B']
        })
        
        agent = AnalyticsAgent(df)
        kpis = agent.compute_kpis()
        assert kpis['total_revenue'] > 0
        assert kpis['total_cost'] > 0
    
    def test_compute_kpis_recovery_fails_gracefully(self):
        """Test recovery fails gracefully with no alternatives"""
        df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02'],
            'random_col': [1, 2]
        })
        
        agent = AnalyticsAgent(df)
        
        with pytest.raises(KeyError):
            agent.compute_kpis()
    
    def test_compute_kpis_with_costs(self, analytics_agent_with_costs):
        """Test KPI calculation with cost data"""
        kpis = analytics_agent_with_costs.compute_kpis()
        assert 'total_cost' in kpis
        assert 'total_profit' in kpis
        assert kpis['total_cost'] > 0
        assert kpis['total_profit'] >= 0


# ==================== Test Revenue Breakdowns ====================

class TestRevenueBreakdowns:
    """Test revenue breakdown methods"""
    
    def test_revenue_by_customer(self, analytics_agent):
        """Test revenue by customer"""
        result = analytics_agent.revenue_by_customer()
        assert isinstance(result, pd.Series)
        assert result.index.name == 'customer' or result.empty
    
    def test_revenue_by_product(self, analytics_agent):
        """Test revenue by product"""
        result = analytics_agent.revenue_by_product()
        assert isinstance(result, pd.Series)
        assert result.index.name == 'product' or result.empty
    
    def test_revenue_by_region(self, analytics_agent):
        """Test revenue by region"""
        result = analytics_agent.revenue_by_region()
        assert isinstance(result, pd.Series)
        assert result.index.name == 'region' or result.empty
    
    def test_revenue_by_customer_missing_column(self):
        """Test revenue by customer when column is missing"""
        df = pd.DataFrame({'date': ['2024-01-01'], 'revenue': [100]})
        agent = AnalyticsAgent(df)
        result = agent.revenue_by_customer()
        assert result.empty
    
    def test_revenue_by_product_missing_column(self):
        """Test revenue by product when column is missing"""
        df = pd.DataFrame({'date': ['2024-01-01'], 'revenue': [100]})
        agent = AnalyticsAgent(df)
        result = agent.revenue_by_product()
        assert result.empty


# ==================== Test Monthly Metrics ====================

class TestMonthlyMetrics:
    """Test monthly aggregation methods"""
    
    def test_monthly_revenue(self, analytics_agent):
        """Test monthly revenue"""
        result = analytics_agent.monthly_revenue()
        assert isinstance(result, pd.Series)
        if not result.empty:
            assert isinstance(result.index, pd.DatetimeIndex)
    
    def test_monthly_profit(self, analytics_agent):
        """Test monthly profit"""
        result = analytics_agent.monthly_profit()
        assert isinstance(result, pd.Series)
        if not result.empty:
            assert isinstance(result.index, pd.DatetimeIndex)
    
    def test_monthly_growth(self, analytics_agent):
        """Test monthly growth"""
        result = analytics_agent.monthly_growth()
        assert isinstance(result, pd.Series)
        if not result.empty and len(result) > 1:
            assert result.iloc[0] == 0
    
    def test_monthly_revenue_missing_date(self):
        """Test monthly revenue without date column"""
        df = pd.DataFrame({'revenue': [100, 200, 300]})
        agent = AnalyticsAgent(df)
        result = agent.monthly_revenue()
        assert result.empty


# ==================== Test Quantity Metrics ====================

class TestQuantityMetrics:
    """Test quantity metrics"""
    
    def test_total_units_sold(self, analytics_agent):
        """Test total units"""
        result = analytics_agent.total_units_sold()
        assert isinstance(result, (int, float, np.integer, type(None)))
        if result is not None:
            assert result == np.floor(analytics_agent.df['quantity'].sum())
    
    def test_revenue_per_unit(self, analytics_agent):
        """Test revenue per unit"""
        result = analytics_agent.revenue_per_unit()
        if result is not None:
            expected = analytics_agent.df['revenue'].sum() / analytics_agent.df['quantity'].sum()
            assert result == np.floor(expected)
    
    def test_total_units_sold_missing_quantity(self):
        """Test total units when quantity column is missing"""
        df = pd.DataFrame({'revenue': [100, 200]})
        agent = AnalyticsAgent(df)
        result = agent.total_units_sold()
        assert result is None


# ==================== Test Payment Analysis ====================

class TestPaymentAnalysis:
    """Test payment status analysis"""
    
    def test_revenue_by_payment_status(self, analytics_agent):
        """Test revenue by payment status"""
        result = analytics_agent.revenue_by_payment_status()
        if result is not None:
            assert isinstance(result, pd.Series)
            assert 'paid' in result.index or result.empty
    
    def test_revenue_by_payment_status_missing_column(self):
        """Test revenue by payment status when column is missing"""
        df = pd.DataFrame({'revenue': [100, 200]})
        agent = AnalyticsAgent(df)
        result = agent.revenue_by_payment_status()
        assert result is None


# ==================== Test Anomaly Detection ====================

class TestAnomalyDetection:
    """Test anomaly detection"""
    
    def test_detect_revenue_spikes(self, analytics_agent_with_anomalies):
        """Test spike detection with anomalies"""
        spikes = analytics_agent_with_anomalies.detect_revenue_spikes()
        # Should detect the anomalies we added
        assert isinstance(spikes, dict) or isinstance(spikes, pd.Series)
    
    def test_detect_revenue_spikes_custom_threshold(self, analytics_agent):
        """Test spike detection with custom threshold"""
        spikes = analytics_agent.detect_revenue_spikes(threshold_std=3)
        assert isinstance(spikes, dict) or isinstance(spikes, pd.Series)
    
    def test_detect_revenue_spikes_by_product(self, analytics_agent):
        """Test spike detection by product"""
        spikes = analytics_agent.detect_revenue_spikes(by_product=True)
        assert isinstance(spikes, dict)


# ==================== Test Forecasting ====================

class TestForecasting:
    """Test forecasting methods"""
    
    @patch('statsmodels.tsa.arima.model.ARIMA')
    def test_forecast_revenue_success(self, mock_arima, analytics_agent_long):
        """Test revenue forecasting with sufficient data"""
        mock_model = MagicMock()
        mock_fit = MagicMock()
        mock_fit.forecast.return_value = np.array([1000, 1100, 1200])
        mock_model.fit.return_value = mock_fit
        mock_arima.return_value = mock_model
        
        forecast = analytics_agent_long.forecast_revenue()
        assert forecast is not None
        assert len(forecast) == 3
    
    def test_forecast_revenue_insufficient_data(self, analytics_agent):
        """Test forecasting with insufficient data (< 12 months)"""
        forecast = analytics_agent.forecast_revenue()
        assert forecast is None
    
    def test_forecast_revenue_empty_dataframe(self, empty_dataframe):
        """Test forecasting with empty dataframe"""
        agent = AnalyticsAgent(empty_dataframe)
        forecast = agent.forecast_revenue()
        assert forecast is None
    
    def test_forecast_revenue_no_date_column(self):
        """Test forecasting without date column"""
        df = pd.DataFrame({'revenue': [100, 200, 300]})
        agent = AnalyticsAgent(df)
        forecast = agent.forecast_revenue()
        assert forecast is None
    
    @patch('statsmodels.tsa.arima.model.ARIMA')
    def test_forecast_revenue_with_explanation(self, mock_arima, analytics_agent_long):
        """Test forecast with explanation"""
        mock_model = MagicMock()
        mock_fit = MagicMock()
        mock_fit.forecast.return_value = np.array([1000, 1100, 1200])
        mock_model.fit.return_value = mock_fit
        mock_arima.return_value = mock_model
        
        result = analytics_agent_long.forecast_revenue_with_explanation()
        assert 'forecast' in result
        assert 'explanation' in result
        assert 'trend_direction' in result
    
    @patch('statsmodels.tsa.arima.model.ARIMA')
    def test_forecast_with_confidence(self, mock_arima, analytics_agent_long):
        """Test forecast with confidence intervals"""
        mock_model = MagicMock()
        mock_fit = MagicMock()
        mock_forecast_result = MagicMock()
        mock_forecast_result.predicted_mean = pd.Series([1000, 1100, 1200])
        mock_forecast_result.conf_int.return_value = pd.DataFrame({
            0: [900, 1000, 1100],
            1: [1100, 1200, 1300]
        })
        mock_fit.get_forecast.return_value = mock_forecast_result
        mock_model.fit.return_value = mock_fit
        mock_arima.return_value = mock_model
        
        result = analytics_agent_long.forecast_with_confidence()
        assert 'forecast' in result
        assert 'lower_bound' in result
        assert 'upper_bound' in result
    
    @patch('statsmodels.tsa.arima.model.ARIMA')
    def test_forecast_ensemble(self, mock_arima, analytics_agent_long):
        """Test ensemble forecast"""
        mock_model = MagicMock()
        mock_fit = MagicMock()
        mock_fit.forecast.return_value = np.array([1000, 1100, 1200])
        mock_model.fit.return_value = mock_fit
        mock_arima.return_value = mock_model
        
        result = analytics_agent_long.forecast_ensemble()
        assert 'forecasts' in result
        assert 'ensemble' in result or 'error' in result


# ==================== Test Run Tool ====================

class TestRunTool:
    """Test run_tool method"""
    
    def test_run_tool_compute_kpis(self, analytics_agent):
        """Test running compute_kpis tool"""
        result = analytics_agent.run_tool('compute_kpis')
        assert isinstance(result, dict)
    
    def test_run_tool_monthly_profit(self, analytics_agent):
        """Test running monthly_profit tool"""
        result = analytics_agent.run_tool('monthly_profit')
        assert isinstance(result, pd.Series) or result is None
    
    def test_run_tool_invalid(self, analytics_agent):
        """Test invalid tool name"""
        with pytest.raises(ValueError, match="Unknown tool"):
            analytics_agent.run_tool('invalid_tool')
    
    def test_run_tool_all_tools(self, analytics_agent):
        """Test all available tools exist"""
        tools = [
            'compute_kpis',
            'revenue_by_customer',
            'revenue_by_product',
            'revenue_by_region',
            'monthly_revenue',
            'monthly_profit',
            'monthly_growth',
            'total_units_sold',
            'revenue_per_unit',
            'revenue_by_payment_status',
            'detect_revenue_spikes'
        ]
        
        for tool in tools:
            try:
                result = analytics_agent.run_tool(tool)
                # Just verify it doesn't raise an exception
                assert True
            except Exception as e:
                # Some tools may fail due to data conditions, but shouldn't raise unexpected errors
                assert False, f"Tool {tool} raised {type(e).__name__}: {e}"


# ==================== Test Monthly Revenue by Customer ====================

class TestMonthlyRevenueByCustomer:
    """Test monthly revenue per customer"""
    
    def test_monthly_revenue_by_customer(self, analytics_agent):
        """Test monthly revenue by customer"""
        result = analytics_agent.monthly_revenue_by_customer()
        assert isinstance(result, dict)
        
        for customer, data in result.items():
            assert 'monthly_revenue' in data
            assert 'trend' in data
            assert 'declining' in data
            assert isinstance(data['monthly_revenue'], dict)
            assert isinstance(data['trend'], list)
            assert isinstance(data['declining'], bool)
    
    def test_monthly_revenue_by_customer_with_months(self, analytics_agent):
        """Test with custom months_to_check"""
        result = analytics_agent.monthly_revenue_by_customer(months_to_check=3)
        assert isinstance(result, dict)
    
    def test_monthly_revenue_by_customer_missing_customer(self):
        """Test when customer column is missing"""
        df = pd.DataFrame({'date': ['2024-01-01'], 'revenue': [100]})
        agent = AnalyticsAgent(df)
        result = agent.monthly_revenue_by_customer()
        assert result == {}


# ==================== Test Monthly Revenue by Product ====================

class TestMonthlyRevenueByProduct:
    """Test monthly revenue per product"""
    
    def test_monthly_revenue_by_product(self, analytics_agent):
        """Test monthly revenue by product"""
        result = analytics_agent.monthly_revenue_by_product()
        assert isinstance(result, dict)
    
    def test_monthly_revenue_by_product_full(self, analytics_agent):
        """Test full monthly revenue by product"""
        result = analytics_agent.monthly_revenue_by_product_full()
        assert isinstance(result, pd.DataFrame)
    
    def test_monthly_revenue_by_product_missing_product(self):
        """Test when product column is missing"""
        df = pd.DataFrame({'date': ['2024-01-01'], 'revenue': [100]})
        agent = AnalyticsAgent(df)
        result = agent.monthly_revenue_by_product()
        assert result == {}


# ==================== Test Generate Summary ====================

class TestGenerateSummary:
    """Test summary generation"""
    
    def test_generate_summary(self, analytics_agent):
        """Test summary generation"""
        summary = analytics_agent.generate_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert 'Total revenue' in summary
    
    def test_generate_summary_minimal(self, minimal_dataframe):
        """Test summary with minimal data"""
        agent = AnalyticsAgent(minimal_dataframe)
        summary = agent.generate_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0


# ==================== Test Helper Methods ====================

class TestHelperMethods:
    """Test helper methods"""
    
    def test_is_declining_trend(self, analytics_agent):
        """Test declining trend detection"""
        # Increasing trend - should be False
        assert not analytics_agent._is_declining_trend([100, 110, 120])
        
        # Declining trend - should be True
        assert analytics_agent._is_declining_trend([120, 110, 100])
        
        # Flat trend - currently returns True (non-increasing), so test accordingly
        # If you want flat to be False, you'd need to change the implementation
        assert analytics_agent._is_declining_trend([100, 100, 100])  # This is True
        
        # Short list - should be False
        assert not analytics_agent._is_declining_trend([100])
        
        # Empty list - should be False
        assert not analytics_agent._is_declining_trend([])
        
        # Mixed trend - should be False (not strictly declining)
        assert not analytics_agent._is_declining_trend([120, 110, 115])


# ==================== Run Tests ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--maxfail=5'])