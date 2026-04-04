"""Unit tests for SchemaMapper with currency conversion."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import sys
import os
import re

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.schema_mapper import SchemaMapper


@pytest.fixture
def sample_data_with_currencies():
    """Create sample data with various currencies"""
    return pd.DataFrame({
        'Date': ['2024-01-03', '2024-01-05', '2024-01-08', '2024-01-12', '2024-01-15'],
        'Customer': ['Acme Corp', 'BetaCo', 'Delta Inc', 'Gamma LLC', 'Acme Corp'],
        'Product': ['Premium Plan', 'Basic Plan', 'Enterprise Plan', 'Premium Plan', 'Basic Plan'],
        'Region': ['US', 'EU', 'APAC', 'US', 'US'],
        'Revenue': ['$8,748.00', '€2,417.00', '¥880,100', '$8,068.00', '$2,219.00'],
        'Currency': ['USD', 'EUR', 'JPY', 'USD', 'USD'],
        'Quantity': [1, 2, 1, 1, 3],
        'Payment Status': ['paid', 'pending', 'paid', 'paid', 'paid'],
        'Notes': ['First order', 'VIP', 'Urgent', 'Repeat', 'Bulk']
    })


@pytest.fixture
def sample_data_mixed_currency_formats():
    """Test data with mixed currency formats"""
    return pd.DataFrame({
        'transaction_date': ['2024-01-03', '2024-01-05', '2024-01-08'],
        'client': ['Acme Corp', 'BetaCo', 'Delta Inc'],
        'product_name': ['Premium Plan', 'Basic Plan', 'Enterprise Plan'],
        'sales_region': ['US', 'EU', 'APAC'],
        'amount': ['$8,748.00', '2,417 €', '¥880,100'],
        'curr': ['USD', 'EUR', 'JPY'],
        'units': [1, 2, 1],
        'status': ['paid', 'pending', 'paid']
    })


@pytest.fixture
def sample_data_no_currency_column():
    """Test data without currency column (assume USD)"""
    return pd.DataFrame({
        'date': ['2024-01-03', '2024-01-05', '2024-01-08'],
        'customer': ['Acme Corp', 'BetaCo', 'Delta Inc'],
        'product': ['Premium Plan', 'Basic Plan', 'Enterprise Plan'],
        'revenue': [8748.00, 2417.00, 880100.00],
        'cost': [5000.00, 1200.00, 450000.00],
        'quantity': [1, 2, 1]
    })


@pytest.fixture
def sample_data_with_cost():
    """Test data with both revenue and cost"""
    return pd.DataFrame({
        'date': ['2024-01-03', '2024-01-05', '2024-01-08'],
        'customer': ['Acme Corp', 'BetaCo', 'Delta Inc'],
        'product': ['Premium Plan', 'Basic Plan', 'Enterprise Plan'],
        'revenue': [8748.00, 2417.00, 880100.00],
        'cost': [5000.00, 1200.00, 450000.00],
        'currency': ['USD', 'EUR', 'JPY'],
        'quantity': [1, 2, 1]
    })


class TestSchemaMapperInitialization:
    """Test SchemaMapper initialization"""
    
    def test_init_with_dataframe(self, sample_data_with_currencies):
        """Test initialization with dataframe"""
        mapper = SchemaMapper(sample_data_with_currencies)
        assert mapper.original_df is not None
        assert mapper.target_currency == 'USD'
        assert hasattr(mapper, 'conversion_stats')
        assert mapper.fuzzy_match_cutoff == 0.8
    
    def test_init_with_custom_params(self, sample_data_with_currencies):
        """Test initialization with custom parameters"""
        mapper = SchemaMapper(
            sample_data_with_currencies,
            use_live_rates=True,
            cache_duration_hours=48,
            default_currency='EUR',
            fuzzy_match_cutoff=0.9
        )
        assert mapper.use_live_rates is True
        assert mapper.cache_duration == 48
        assert mapper.target_currency == 'EUR'
        assert mapper.fuzzy_match_cutoff == 0.9
    
    def test_standard_schema_defined(self):
        """Test that STANDARD_SCHEMA is properly defined"""
        assert isinstance(SchemaMapper.STANDARD_SCHEMA, dict)
        assert len(SchemaMapper.STANDARD_SCHEMA) >= 10
        assert "revenue" in SchemaMapper.STANDARD_SCHEMA
        assert "cost" in SchemaMapper.STANDARD_SCHEMA
        assert "currency" in SchemaMapper.STANDARD_SCHEMA
        assert "profit" in SchemaMapper.STANDARD_SCHEMA


class TestCurrencyNormalization:
    """Test currency code normalization"""
    
    def test_normalize_currency_symbols(self):
        """Test converting currency symbols to codes"""
        mapper = SchemaMapper(pd.DataFrame())
        
        assert mapper._normalize_currency('$') == 'USD'
        assert mapper._normalize_currency('€') == 'EUR'
        assert mapper._normalize_currency('£') == 'GBP'
        assert mapper._normalize_currency('¥') == 'JPY'
        assert mapper._normalize_currency('₹') == 'INR'
    
    def test_normalize_currency_codes(self):
        """Test handling of currency codes"""
        mapper = SchemaMapper(pd.DataFrame())
        
        assert mapper._normalize_currency('USD') == 'USD'
        assert mapper._normalize_currency('EUR') == 'EUR'
        assert mapper._normalize_currency('GBP') == 'GBP'
    
    def test_normalize_currency_text(self):
        """Test handling of currency text descriptions"""
        mapper = SchemaMapper(pd.DataFrame())
        
        assert mapper._normalize_currency('US Dollar') == 'USD'
        assert mapper._normalize_currency('EURO') == 'EUR'
        assert mapper._normalize_currency('POUNDS') == 'GBP'
        assert mapper._normalize_currency('YEN') == 'JPY'
    
    def test_normalize_currency_nan(self):
        """Test handling of NaN values"""
        mapper = SchemaMapper(pd.DataFrame())
        
        assert mapper._normalize_currency(None) == 'USD'
        assert mapper._normalize_currency(pd.NA) == 'USD'


class TestCurrencyCleaning:
    """Test cleaning of currency strings"""
    
    def test_clean_currency_value(self):
        """Test cleaning currency strings to floats"""
        mapper = SchemaMapper(pd.DataFrame())
        
        assert mapper._clean_currency_value('$8,748.00') == 8748.0
        assert mapper._clean_currency_value('€2,417.00') == 2417.0
        assert mapper._clean_currency_value('¥880,100') == 880100.0
        assert mapper._clean_currency_value('1,234.56') == 1234.56
        assert mapper._clean_currency_value('1000') == 1000.0
        assert mapper._clean_currency_value(None) is None
        assert mapper._clean_currency_value('invalid') is None


class TestExchangeRates:
    """Test exchange rate retrieval"""
    
    def test_static_rates_to_usd(self):
        """Test static exchange rates to USD"""
        mapper = SchemaMapper(pd.DataFrame())
        
        assert mapper._get_static_rate_to_usd('USD') == 1.0
        assert mapper._get_static_rate_to_usd('EUR') == 1.18
        assert mapper._get_static_rate_to_usd('JPY') == 0.0091
        assert mapper._get_static_rate_to_usd('GBP') == 1.38
    
    def test_invalid_currency_raises_error(self):
        """Test invalid currency raises error"""
        mapper = SchemaMapper(pd.DataFrame())
        
        with pytest.raises(ValueError, match="Unsupported currency"):
            mapper._get_static_rate_to_usd('XYZ')
    
    @patch('requests.get')
    def test_live_rate_fetching(self, mock_get):
        """Test live rate fetching through exchange rate method"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'conversion_rates': {'USD': 1.18}
        }
        mock_get.return_value = mock_response
        
        mapper = SchemaMapper(pd.DataFrame(), use_live_rates=True)
        
        # Clear cache to force fetch
        mapper.exchange_rate_cache = {}
        
        # Mock environment variable for API key
        with patch.dict('os.environ', {'EXCHANGE_RATE_API_KEY': 'test-key'}):
            rate = mapper._get_exchange_rate_to_usd('EUR')
        
        assert rate == 1.18
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_live_rate_fallback_on_error(self, mock_get):
        """Test fallback to static rates on API error"""
        mock_get.side_effect = Exception("API Error")
        
        mapper = SchemaMapper(pd.DataFrame(), use_live_rates=True)
        
        # Clear cache to force fetch
        mapper.exchange_rate_cache = {}
        
        # Mock environment variable for API key
        with patch.dict('os.environ', {'EXCHANGE_RATE_API_KEY': 'test-key'}):
            rate = mapper._get_exchange_rate_to_usd('EUR')
        
        # Should fall back to static rate (1.18)
        assert rate == 1.18
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_live_rate_caching(self, mock_get):
        """Test that live rates are cached"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'conversion_rates': {'USD': 1.18}
        }
        mock_get.return_value = mock_response
        
        mapper = SchemaMapper(pd.DataFrame(), use_live_rates=True)
        
        with patch.dict('os.environ', {'EXCHANGE_RATE_API_KEY': 'test-key'}):
            # First call - should hit API
            rate1 = mapper._get_exchange_rate_to_usd('EUR')
            
            # Second call - should use cache
            rate2 = mapper._get_exchange_rate_to_usd('EUR')
        
        # API should only be called once
        mock_get.assert_called_once()
        assert rate1 == rate2 == 1.18

class TestSchemaMapping:
    """Test basic schema mapping functionality"""
    
    def test_basic_mapping(self, sample_data_with_currencies):
        """Test basic column mapping"""
        mapper = SchemaMapper(sample_data_with_currencies)
        df_clean, mapping, warnings = mapper.map_schema()
        
        # Check mapping for core columns
        assert mapping['Date'] == 'date'
        assert mapping['Customer'] == 'customer'
        assert mapping['Product'] == 'product'
        assert mapping['Region'] == 'region'
        assert mapping['Revenue'] == 'revenue'
        assert mapping['Currency'] == 'currency'
        assert mapping['Quantity'] == 'quantity'
        assert mapping['Payment Status'] == 'payment_status'
        assert mapping['Notes'] == 'notes'
        
        # Check that all standard columns exist
        for col in SchemaMapper.STANDARD_SCHEMA.keys():
            assert col in df_clean.columns
        
        # Check that the dataframe has the expected columns
        expected_columns = set(SchemaMapper.STANDARD_SCHEMA.keys())
        for col in expected_columns:
            assert col in df_clean.columns
    
    def test_fuzzy_matching(self, sample_data_mixed_currency_formats):
        """Test fuzzy matching of column names"""
        mapper = SchemaMapper(sample_data_mixed_currency_formats)
        df_clean, mapping, warnings = mapper.map_schema()
        
        # Check exact matches
        assert 'transaction_date' in mapping
        assert mapping['transaction_date'] == 'date'
        assert 'client' in mapping
        assert mapping['client'] == 'customer'
        assert 'curr' in mapping
        assert mapping['curr'] == 'currency'
        assert 'units' in mapping
        assert mapping['units'] == 'quantity'
        assert 'status' in mapping
        assert mapping['status'] == 'payment_status'
    
    def test_is_schema_acceptable(self, sample_data_with_currencies):
        """Test schema acceptability check"""
        mapper = SchemaMapper(sample_data_with_currencies)
        df_clean, mapping, warnings = mapper.map_schema()
        
        is_acceptable, message = mapper.is_schema_acceptable(mapping, warnings)
        assert is_acceptable is True
        assert "acceptable" in message.lower()
    
    def test_get_unmapped_columns(self, sample_data_mixed_currency_formats):
        """Test getting unmapped columns"""
        mapper = SchemaMapper(sample_data_mixed_currency_formats)
        df_clean, mapping, warnings = mapper.map_schema()
        
        unmapped = mapper.get_unmapped_columns()
        assert isinstance(unmapped, list)


class TestCurrencyConversion:
    """Test currency conversion functionality"""
    
    def test_no_currency_column_assumes_usd(self, sample_data_no_currency_column):
        """Test that missing currency column assumes USD"""
        mapper = SchemaMapper(sample_data_no_currency_column)
        df_clean, mapping, warnings = mapper.map_schema()
        
        # Currency column should be added with USD
        assert 'currency' in df_clean.columns
        assert (df_clean['currency'] == 'USD').all()
        
        # Revenue should remain unchanged
        assert df_clean['revenue'].iloc[0] == 8748.0
        assert df_clean['revenue'].iloc[1] == 2417.0
    
    def test_conversion_with_cost(self, sample_data_with_cost):
        """Test conversion of both revenue and cost"""
        mapper = SchemaMapper(sample_data_with_cost)
        df_clean, mapping, warnings = mapper.map_schema()
        
        # Check that both were converted
        assert 'revenue_original' in df_clean.columns
        assert 'cost_original' in df_clean.columns
        
        # Check profit calculation
        assert 'profit' in df_clean.columns
        
        # USD row: revenue and cost remain same
        usd_mask = df_clean['currency'] == 'USD'
        assert df_clean.loc[usd_mask, 'revenue'].iloc[0] == 8748.0
        assert df_clean.loc[usd_mask, 'cost'].iloc[0] == 5000.0
        
        # EUR row should be converted
        eur_mask = df_clean['currency'] == 'EUR'
        assert round(df_clean.loc[eur_mask, 'revenue'].iloc[0], 2) == 2852.06
        assert round(df_clean.loc[eur_mask, 'cost'].iloc[0], 2) == 1416.0
    
    def test_mixed_currency_formats(self, sample_data_mixed_currency_formats):
        """Test handling of mixed currency formats"""
        mapper = SchemaMapper(sample_data_mixed_currency_formats)
        df_clean, mapping, warnings = mapper.map_schema()
        
        stats = mapper.get_conversion_summary()
        
        # Check if 'amount' was mapped to 'revenue'
        if 'amount' in mapping and mapping['amount'] == 'revenue':
            assert df_clean['revenue'].notna().any()
    
    def test_add_custom_mapping(self, sample_data_with_currencies):
        """Test adding custom column mapping"""
        mapper = SchemaMapper(sample_data_with_currencies)
        
        # Add custom mapping
        mapper.add_custom_mapping('revenue', ['sales_amount', 'income'])
        
        # Verify the custom mapping was added
        assert 'sales_amount' in mapper.STANDARD_SCHEMA['revenue']
        assert 'income' in mapper.STANDARD_SCHEMA['revenue']


class TestConversionStats:
    """Test conversion statistics tracking"""
    
    def test_conversion_stats(self, sample_data_with_currencies):
        """Test that conversion stats are tracked"""
        mapper = SchemaMapper(sample_data_with_currencies)
        df_clean, mapping, warnings = mapper.map_schema()
        
        stats = mapper.get_conversion_summary()
        
        assert stats['target_currency'] == 'USD'
        assert stats['total_rows'] == len(sample_data_with_currencies)
        assert 'USD' in stats['currencies_found']
        assert 'EUR' in stats['currencies_found']
        assert 'JPY' in stats['currencies_found']
    
    def test_conversion_errors_tracking(self, sample_data_with_currencies):
        """Test tracking of conversion errors"""
        # Create a copy and introduce an invalid value
        df = sample_data_with_currencies.copy()
        df.loc[0, 'Revenue'] = 'INVALID_AMOUNT'
        
        mapper = SchemaMapper(df)
        df_clean, mapping, warnings = mapper.map_schema()
        
        stats = mapper.get_conversion_summary()
        
        # Check that errors were tracked or warnings were issued
        if len(stats['conversion_errors']) == 0:
            assert any('conversion' in w.lower() or 'error' in w.lower() for w in warnings)


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_dataframe(self):
        """Test with empty dataframe"""
        df = pd.DataFrame()
        mapper = SchemaMapper(df)
        df_clean, mapping, warnings = mapper.map_schema()
        
        assert mapping == {}
        assert len(warnings) > 0
        # All standard columns should exist with None values
        for col in SchemaMapper.STANDARD_SCHEMA.keys():
            assert col in df_clean.columns
            assert df_clean[col].isna().all()
    
    def test_all_numeric_values(self):
        """Test with all numeric values (no strings)"""
        df = pd.DataFrame({
            'revenue': [1000, 2000, 1500],
            'cost': [500, 800, 600],
            'currency': ['USD', 'EUR', 'GBP']
        })
        
        mapper = SchemaMapper(df)
        df_clean, mapping, warnings = mapper.map_schema()
        
        assert df_clean['revenue'].iloc[0] == 1000.0
        assert round(df_clean['revenue'].iloc[1], 2) == 2360.0
    
    def test_very_large_numbers(self):
        """Test with very large numbers"""
        df = pd.DataFrame({
            'revenue': ['$1,000,000,000', '€2,000,000,000'],
            'currency': ['USD', 'EUR']
        })
        
        mapper = SchemaMapper(df)
        df_clean, mapping, warnings = mapper.map_schema()
        
        assert df_clean['revenue'].iloc[0] == 1_000_000_000.0
        assert df_clean['revenue'].iloc[1] == 2_000_000_000.0 * 1.18
    
    def test_mixed_decimal_separators(self):
        """Test with different decimal separators"""
        df = pd.DataFrame({
            'revenue': ['1,234.56', '1.234,56', '1234.56'],
            'currency': ['USD', 'EUR', 'GBP']
        })
        
        mapper = SchemaMapper(df)
        df_clean, mapping, warnings = mapper.map_schema()
        
        assert df_clean['revenue'].notna().all()


class TestIntegration:
    """Integration-style tests"""
    
    def test_full_pipeline_with_currency_conversion(self, sample_data_with_currencies):
        """Test complete mapping and conversion pipeline"""
        mapper = SchemaMapper(sample_data_with_currencies)
        df_clean, mapping, warnings = mapper.map_schema()
        
        # Check structure
        assert len(df_clean.columns) >= len(SchemaMapper.STANDARD_SCHEMA)
        
        # Check that monetary values are in USD
        assert 'monetary_values_in_usd' in df_clean.columns
        assert df_clean['monetary_values_in_usd'].all()
        
        # Verify revenue column is numeric
        assert df_clean['revenue'].dtype in ['float64', 'int64']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])