"""
Schema Mapper - Maps raw dataframe columns to standard schema with currency conversion
"""

import os
import re
import difflib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import requests


class SchemaMapper:
    """
    Maps raw dataframe columns to standard schema and converts currencies to USD.
    
    Features:
    - Fuzzy matching for column names
    - Multi-currency support with live or static rates
    - Automatic data type conversion
    - Comprehensive error handling and logging
    - Detailed conversion statistics
    """

    # Standard schema mapping with common column name variants
    STANDARD_SCHEMA: Dict[str, List[str]] = {
        "date": ["date", "day", "transaction_date", "sale_date", "created_at", "order_date", "invoice_date", "timestamp"],
        "customer": ["customer", "client", "account", "id", "buyer", "user", "user_id", "customer_id", "account_id"],
        "product": ["product", "plan", "item", "sku", "product_id", "service", "subscription"],
        "region": ["region", "market", "geo", "country", "city", "state", "territory", "area", "zone"],
        "revenue": ["revenue", "rev", "sales", "income", "turnover", "amount", "price", "value", "total", "sum"],
        "cost": ["cost", "expense", "cogs", "spend", "expenditure", "expenses", "costs", "fee"],
        "currency": ["currency", "curr", "currency_code", "currency_symbol"],
        "quantity": ["quantity", "qty", "units", "count", "volume", "number", "amount_units"],
        "payment_status": ["payment_status", "status", "payment", "pay_status", "order_status", "transaction_status"],
        "notes": ["notes", "comment", "remarks", "note", "comments", "description", "details", "additional_info"],
        "profit": ["profit", "gross_profit", "net_profit", "earnings", "income_after_costs"],
    }
    
    # Common currency codes and their symbols
    CURRENCY_MAP: Dict[str, str] = {
        '$': 'USD',
        '€': 'EUR',
        '£': 'GBP',
        '¥': 'JPY',
        '₹': 'INR',
        '₽': 'RUB',
        '₩': 'KRW',
        '₺': 'TRY',
        'CAD': 'CAD',
        'AUD': 'AUD',
        'CHF': 'CHF',
        'CNY': 'CNY',
        'HKD': 'HKD',
        'SGD': 'SGD',
        'NZD': 'NZD',
        'MXN': 'MXN',
        'BRL': 'BRL',
        'ZAR': 'ZAR',
        'SEK': 'SEK',
        'NOK': 'NOK',
        'DKK': 'DKK',
        'PLN': 'PLN',
        'CZK': 'CZK',
        'HUF': 'HUF',
        'ILS': 'ILS',
        'SAR': 'SAR',
        'AED': 'AED',
    }

    # Static exchange rates to USD (as of early 2025)
    STATIC_RATES_TO_USD: Dict[str, float] = {
        'USD': 1.0,
        'EUR': 1.18,
        'GBP': 1.38,
        'JPY': 0.0091,
        'CAD': 0.79,
        'AUD': 0.72,
        'CHF': 1.12,
        'CNY': 0.15,
        'INR': 0.012,
        'HKD': 0.13,
        'SGD': 0.74,
        'NZD': 0.68,
        'KRW': 0.00076,
        'MXN': 0.058,
        'BRL': 0.19,
        'RUB': 0.011,
        'ZAR': 0.054,
        'TRY': 0.031,
        'SEK': 0.096,
        'NOK': 0.095,
        'DKK': 0.16,
        'PLN': 0.25,
        'CZK': 0.044,
        'HUF': 0.0028,
        'ILS': 0.27,
        'SAR': 0.27,
        'AED': 0.27,
    }

    def __init__(
        self,
        df: pd.DataFrame,
        use_live_rates: bool = False,
        cache_duration_hours: int = 24,
        default_currency: str = 'USD',
        fuzzy_match_cutoff: float = 0.8
    ) -> None:
        """
        Initialize SchemaMapper with automatic currency conversion.
        
        Args:
            df: Input dataframe
            use_live_rates: Whether to fetch live exchange rates (default: False)
            cache_duration_hours: How long to cache exchange rates (default: 24)
            default_currency: Default currency when none is detected (default: 'USD')
            fuzzy_match_cutoff: Threshold for fuzzy column matching (0.0 to 1.0)
        """
        self.original_df: pd.DataFrame = df.copy()
        self.target_currency: str = default_currency
        self.use_live_rates: bool = use_live_rates
        self.cache_duration: int = cache_duration_hours
        self.fuzzy_match_cutoff: float = fuzzy_match_cutoff
        self.exchange_rate_cache: Dict[str, Tuple[float, datetime]] = {}
        self.last_rate_fetch: Optional[datetime] = None
        self.unmapped_columns: List[str] = []
        self.conversion_stats: Dict[str, Any] = {
            'total_rows': 0,
            'rows_converted': 0,
            'currencies_found': {},
            'conversion_errors': []
        }

    def map_schema(self) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
        """
        Map columns to standard schema and return ONLY standard columns.
        
        Returns:
            Tuple of (mapped_dataframe, column_mapping, warnings)
        """
        mapping: Dict[str, str] = {}
        new_columns: Dict[str, str] = {}
        warnings: List[str] = []
        used_standards: set = set()
        unmapped_columns: List[str] = []

        # First pass: identify all mapped columns
        for col in self.original_df.columns:
            lower_col = col.lower().strip()
            matched = False

            for standard, variants in self.STANDARD_SCHEMA.items():
                if standard in used_standards:
                    continue
                    
                # Exact match
                if lower_col in variants:
                    mapping[col] = standard
                    new_columns[col] = standard
                    used_standards.add(standard)
                    matched = True
                    break
                
                # Fuzzy match
                matches = difflib.get_close_matches(lower_col, variants, n=1, cutoff=self.fuzzy_match_cutoff)
                if matches:
                    mapping[col] = standard
                    new_columns[col] = standard
                    used_standards.add(standard)
                    matched = True
                    break

            if not matched:
                unmapped_columns.append(col)

        # Store unmapped columns for later reference
        self.unmapped_columns = unmapped_columns

        # Add warnings for unmapped columns
        self._add_unmapped_columns_warning(unmapped_columns, warnings)

        # Create mapped dataframe
        df_mapped = self._create_mapped_dataframe(new_columns, warnings)

        # Add missing standard columns
        self._add_missing_standard_columns(df_mapped, used_standards, warnings)

        # Reorder columns
        df_mapped = self._reorder_columns(df_mapped)

        # Perform currency conversion
        df_mapped = self._convert_to_usd(df_mapped, warnings)

        return df_mapped, mapping, warnings

    def _add_unmapped_columns_warning(self, unmapped_columns: List[str], warnings: List[str]) -> None:
        """Add warning about unmapped columns."""
        if unmapped_columns:
            if len(unmapped_columns) <= 5:
                warnings.append(
                    f"Columns not mapped to standard schema and will be dropped: {', '.join(unmapped_columns)}"
                )
            else:
                sample = ', '.join(unmapped_columns[:5])
                warnings.append(
                    f"{len(unmapped_columns)} columns not mapped to standard schema and will be dropped "
                    f"(sample: {sample}, ...)"
                )

    def _create_mapped_dataframe(self, new_columns: Dict[str, str], warnings: List[str]) -> pd.DataFrame:
        """Create dataframe with only mapped columns."""
        mapped_columns = list(new_columns.keys())
        
        if mapped_columns:
            df_mapped = self.original_df[mapped_columns].copy()
            df_mapped = df_mapped.rename(columns=new_columns)
            
            original_col_count = len(self.original_df.columns)
            mapped_col_count = len(mapped_columns)
            
            if original_col_count > mapped_col_count:
                warnings.append(
                    f"Dropped {original_col_count - mapped_col_count} unmapped columns "
                    f"({mapped_col_count} standard columns kept)"
                )
        else:
            df_mapped = pd.DataFrame()
            warnings.append("No columns could be mapped to standard schema")
        
        return df_mapped

    def _add_missing_standard_columns(
        self, 
        df_mapped: pd.DataFrame, 
        used_standards: set, 
        warnings: List[str]
    ) -> None:
        """Add missing standard columns with default values."""
        for standard_col in self.STANDARD_SCHEMA.keys():
            if standard_col not in df_mapped.columns:
                df_mapped[standard_col] = None
                
                if standard_col == 'currency':
                    df_mapped['currency'] = self.target_currency
                    warnings.append(f"Currency column added with default: {self.target_currency}")
                elif standard_col not in used_standards:
                    warnings.append(f"Missing column added with default None: {standard_col}")

    def _reorder_columns(self, df_mapped: pd.DataFrame) -> pd.DataFrame:
        """Reorder columns to match standard schema order."""
        column_order = [col for col in self.STANDARD_SCHEMA.keys() if col in df_mapped.columns]
        return df_mapped[column_order]

    def is_schema_acceptable(self, mapping: Dict[str, str], warnings: List[str]) -> Tuple[bool, str]:
        """
        Determine if the mapped schema is acceptable for analysis.
        
        Returns:
            Tuple of (is_acceptable, message)
        """
        # Critical columns that must exist
        critical_columns = ['revenue', 'date']
        mapped_critical = [col for col in critical_columns if col in mapping.values()]
        
        if len(mapped_critical) < len(critical_columns):
            missing = set(critical_columns) - set(mapping.values())
            return False, f"Missing critical columns: {missing}"
        
        # Check if too many columns are unmatched
        unmatched_warnings = [w for w in warnings if "not mapped" in w]
        if len(unmatched_warnings) > len(self.original_df.columns) * 0.3:
            return False, "Too many columns could not be mapped (>30% of columns)"
        
        return True, "Schema acceptable"

    def _normalize_currency(self, currency_value: Any) -> str:
        """Convert currency symbols to standard codes."""
        if pd.isna(currency_value):
            return self.target_currency
        
        currency_str = str(currency_value).strip().upper()
        
        # Check if it's a symbol
        if currency_str in self.CURRENCY_MAP:
            return self.CURRENCY_MAP[currency_str]
        
        # Check if it's already a code
        if currency_str in self.CURRENCY_MAP.values():
            return currency_str
        
        # Try to extract from common patterns
        if currency_str.startswith('US') or 'DOLLAR' in currency_str:
            return 'USD'
        elif currency_str.startswith('EU') or 'EURO' in currency_str:
            return 'EUR'
        elif currency_str.startswith('GB') or 'POUND' in currency_str or 'STERLING' in currency_str:
            return 'GBP'
        elif currency_str.startswith('JP') or 'YEN' in currency_str:
            return 'JPY'
        elif currency_str.startswith('IN') or 'RUPEE' in currency_str:
            return 'INR'
        
        return self.target_currency

    def _clean_currency_value(self, val: Any) -> Optional[float]:
        """Convert string currency to float, handling both US and European formats."""
        if pd.isna(val):
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            # Remove currency symbols and spaces
            cleaned = re.sub(r'[$€£¥₹₽₩₺\s]', '', val)
            
            # Handle European format (1.234,56 -> 1234.56)
            if ',' in cleaned and '.' in cleaned:
                if cleaned.rindex('.') > cleaned.rindex(','):
                    # US format: 1,234.56 -> remove commas
                    cleaned = cleaned.replace(',', '')
                else:
                    # European format: 1.234,56 -> replace . with '' and , with .
                    cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned:
                # Check if it's European (1,23) or US thousand separator (1,234)
                if len(cleaned.split(',')[-1]) == 2:  # European: 1,23
                    cleaned = cleaned.replace(',', '.')
                else:  # US thousand separator: 1,234
                    cleaned = cleaned.replace(',', '')
            
            try:
                return float(cleaned)
            except ValueError:
                self.conversion_stats['conversion_errors'].append({
                    'value': val,
                    'error': f"Could not convert to float: {val}"
                })
                return None
        return None

    def _convert_to_usd(self, df: pd.DataFrame, warnings: List[str]) -> pd.DataFrame:
        """Convert all non-USD revenue and cost columns to USD."""
        self.conversion_stats['total_rows'] = len(df)
        
        # Ensure currency column exists and is normalized
        if 'currency' in df.columns:
            df['currency'] = df['currency'].apply(self._normalize_currency)
        else:
            df['currency'] = self.target_currency
        
        # Count currencies before conversion
        currency_counts = df['currency'].value_counts().to_dict()
        self.conversion_stats['currencies_found'] = currency_counts
        
        # Convert revenue column
        df = self._convert_column_to_usd(df, 'revenue', warnings)
        
        # Convert cost column
        df = self._convert_column_to_usd(df, 'cost', warnings)
        
        # Recalculate profit if both revenue and cost exist
        df = self._recalculate_profit(df)
        
        # Add note that all monetary values are now in USD
        df['monetary_values_in_usd'] = True
        
        return df

    def _convert_column_to_usd(
        self, 
        df: pd.DataFrame, 
        column_name: str, 
        warnings: List[str]
    ) -> pd.DataFrame:
        """Convert a specific column to USD."""
        if column_name not in df.columns:
            return df
        
        # Keep original for reference
        df[f'{column_name}_original'] = df[column_name]
        df[f'{column_name}_original_currency'] = df['currency']
        
        # Clean the values
        df[f'{column_name}_clean'] = df[column_name].apply(self._clean_currency_value)
        
        # Initialize converted column
        df[f'{column_name}_converted'] = None
        
        # Convert non-USD values
        mask_non_usd = (df['currency'] != self.target_currency) & (df[f'{column_name}_clean'].notna())
        if mask_non_usd.any():
            df.loc[mask_non_usd, f'{column_name}_converted'] = df.loc[mask_non_usd].apply(
                lambda row: self._convert_to_usd_amount(row[f'{column_name}_clean'], row['currency']),
                axis=1
            )
            self.conversion_stats['rows_converted'] += mask_non_usd.sum()
            converted_currencies = df.loc[mask_non_usd, 'currency'].unique()
            warnings.append(f"{column_name.capitalize()} converted to USD from: {', '.join(converted_currencies)}")
        
        # For USD rows, just use the cleaned value
        mask_usd = (df['currency'] == self.target_currency) & (df[f'{column_name}_clean'].notna())
        if mask_usd.any():
            df.loc[mask_usd, f'{column_name}_converted'] = df.loc[mask_usd, f'{column_name}_clean']
        
        # Final column - use converted values, floor to 2 decimals
        df[column_name] = df[f'{column_name}_converted'].apply(
            lambda x: np.floor(x * 100) / 100 if pd.notna(x) else None
        )
        
        # Drop temporary columns
        df = df.drop(columns=[f'{column_name}_clean', f'{column_name}_converted'])
        
        return df

    def _recalculate_profit(self, df: pd.DataFrame) -> pd.DataFrame:
        """Recalculate profit if both revenue and cost exist (now both in USD)."""
        if 'revenue' in df.columns and 'cost' in df.columns:
            profit_mask = df['revenue'].notna() & df['cost'].notna()
            df['profit'] = None
            df.loc[profit_mask, 'profit'] = df.loc[profit_mask, 'revenue'] - df.loc[profit_mask, 'cost']
            df['profit'] = df['profit'].apply(
                lambda x: np.floor(x * 100) / 100 if pd.notna(x) else None
            )
        return df

    def _convert_to_usd_amount(self, amount: float, from_currency: str) -> float:
        """Convert amount from any currency to USD."""
        if pd.isna(amount) or from_currency == self.target_currency:
            return amount
        
        try:
            rate = self._get_exchange_rate_to_usd(from_currency)
            return amount * rate
        except Exception as e:
            self.conversion_stats['conversion_errors'].append({
                'currency': from_currency,
                'amount': amount,
                'error': str(e)
            })
            return amount

    def _get_exchange_rate_to_usd(self, from_currency: str) -> float:
        """Get exchange rate from any currency to USD."""
        cache_key = f"{from_currency}_{self.target_currency}"
        
        # Check cache
        if cache_key in self.exchange_rate_cache:
            rate, timestamp = self.exchange_rate_cache[cache_key]
            if datetime.now() - timestamp < timedelta(hours=self.cache_duration):
                return rate
        
        # Get rate
        if self.use_live_rates:
            rate = self._fetch_live_rate(from_currency, self.target_currency)
        else:
            rate = self._get_static_rate_to_usd(from_currency)
        
        # Update cache
        self.exchange_rate_cache[cache_key] = (rate, datetime.now())
        return rate

    def _get_static_rate_to_usd(self, from_currency: str) -> float:
        """Get static exchange rate to USD."""
        if from_currency not in self.STATIC_RATES_TO_USD:
            raise ValueError(f"Unsupported currency: {from_currency}. Cannot convert to USD.")
        return self.STATIC_RATES_TO_USD[from_currency]

    def _fetch_live_rate(self, from_currency: str, to_currency: str) -> float:
        """Fetch live exchange rate from API."""
        try:
            api_key = os.getenv('EXCHANGE_RATE_API_KEY', '')
            if not api_key:
                return self._get_static_rate_to_usd(from_currency)
            
            url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{from_currency}"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if response.status_code == 200 and 'conversion_rates' in data:
                return data['conversion_rates'][to_currency]
        except Exception as e:
            print(f"Warning: Failed to fetch live exchange rate: {e}")
        
        return self._get_static_rate_to_usd(from_currency)

    def get_conversion_summary(self) -> Dict[str, Any]:
        """Get summary of currency conversion operations."""
        return {
            "target_currency": self.target_currency,
            "total_rows": self.conversion_stats['total_rows'],
            "rows_converted": self.conversion_stats['rows_converted'],
            "currencies_found": self.conversion_stats['currencies_found'],
            "conversion_errors": self.conversion_stats['conversion_errors'],
            "live_rates_used": self.use_live_rates,
            "cache_duration_hours": self.cache_duration
        }

    def get_unmapped_columns(self) -> List[str]:
        """Get list of columns that were not mapped to the standard schema."""
        return self.unmapped_columns

    def add_custom_mapping(self, standard_column: str, variants: List[str]) -> None:
        """
        Add custom column name variants to the standard schema.
        
        Args:
            standard_column: The standard column name (must exist in STANDARD_SCHEMA)
            variants: List of additional column name variants to map
        """
        if standard_column in self.STANDARD_SCHEMA:
            self.STANDARD_SCHEMA[standard_column].extend(variants)
        else:
            raise KeyError(f"Standard column '{standard_column}' not found in schema")