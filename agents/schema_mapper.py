import pandas as pd
import difflib
import numpy as np
from datetime import datetime, timedelta
import requests
import os
import re

class SchemaMapper:

    STANDARD_SCHEMA = {
        "date": ["date", "day", "transaction_date"],
        "customer": ["customer", "client", "account"],
        "product": ["product", "plan", "item"],
        "region": ["region", "market", "geo"],
        "revenue": ["revenue", "rev", "sales"],
        "cost": ["cost", "expense", "cogs"],
        "currency": ["currency", "curr"],
        "quantity": ["quantity", "qty", "units"],
        "payment_status": ["payment_status", "status", "payment"],
        "notes": ["notes", "comment", "remarks", "note", "comments", "description"],
    }
    
    # Common currency codes and their symbols
    CURRENCY_MAP = {
        '$': 'USD',
        '€': 'EUR',
        '£': 'GBP',
        '¥': 'JPY',
        '₹': 'INR',
        'CAD': 'CAD',
        'AUD': 'AUD',
        'CHF': 'CHF',
        'CNY': 'CNY',
        'HKD': 'HKD',
        'SGD': 'SGD',
        'NZD': 'NZD',
        'KRW': 'KRW',
        'MXN': 'MXN',
        'BRL': 'BRL',
        'RUB': 'RUB',
        'ZAR': 'ZAR',
        'TRY': 'TRY',
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

    def __init__(self, df, use_live_rates=False, cache_duration_hours=24):
        """
        Initialize SchemaMapper with automatic USD conversion
        
        Args:
            df: Input dataframe
            use_live_rates: Whether to fetch live exchange rates (default: False)
            cache_duration_hours: How long to cache exchange rates (default: 24)
        """
        self.df = df
        self.target_currency = 'USD'  # Always USD
        self.use_live_rates = use_live_rates
        self.cache_duration = cache_duration_hours
        self.exchange_rate_cache = {}
        self.last_rate_fetch = None
        self.conversion_stats = {
            'total_rows': 0,
            'rows_converted': 0,
            'currencies_found': {},
            'conversion_errors': []
        }

    def map_schema(self):
        mapping = {}
        new_columns = {}
        warnings = []
        used_standards = set()  # Track which standard columns have been used

        for col in self.df.columns:
            lower_col = col.lower().strip()
            matched = False

            for standard, variants in self.STANDARD_SCHEMA.items():
                # Skip if this standard column already has a mapping
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
                elif difflib.get_close_matches(lower_col, variants, n=1, cutoff=0.8):
                    mapping[col] = standard
                    new_columns[col] = standard
                    used_standards.add(standard)
                    matched = True
                    break

            if not matched:
                warnings.append(col)

        df_clean = self.df.rename(columns=new_columns)

        # Add missing standard columns with default None
        for standard_col in self.STANDARD_SCHEMA.keys():
            if standard_col not in df_clean.columns:
                df_clean[standard_col] = None
                if standard_col == 'currency' and 'currency' not in used_standards:
                    df_clean['currency'] = 'USD'
                    warnings.append("Currency column added with default: USD")
                else:
                    warnings.append(f"Missing column added: {standard_col}")

        # Perform currency conversion
        df_clean = self._convert_to_usd(df_clean, warnings)

        return df_clean, mapping, warnings
    
    def is_schema_acceptable(self, mapping, warnings):
        """Determine if the mapped schema is acceptable for analysis"""
        
        # Critical columns that must exist
        critical_columns = ['revenue', 'date']
        mapped_critical = [col for col in critical_columns if col in mapping.values()]
        
        if len(mapped_critical) < len(critical_columns):
            missing = set(critical_columns) - set(mapping.values())
            return False, f"Missing critical columns: {missing}"
        
        # Check if too many columns are unmatched
        if len(warnings) > len(self.df.columns) * 0.3:  # More than 30% unmatched
            return False, "Too many columns could not be mapped"
        
        return True, "Schema acceptable"

    def _convert_to_usd(self, df, warnings):
        """Convert all non-USD revenue and cost columns to USD"""

        self.conversion_stats['total_rows'] = len(df)
        
        # Ensure currency column exists and is normalized
        if 'currency' in df.columns:
            df['currency'] = df['currency'].apply(self._normalize_currency)
        else:
            df['currency'] = 'USD'
        
        # Count currencies before conversion
        currency_counts = df['currency'].value_counts().to_dict()
        self.conversion_stats['currencies_found'] = currency_counts
        
        # Helper function to clean currency strings
        def clean_currency_value(val):
            """Convert string currency to float, handling both US and European formats"""
            if pd.isna(val):
                return None
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                # Remove currency symbols and spaces
                cleaned = re.sub(r'[$€£¥₹\s]', '', val)
                
                # Handle European format (1.234,56 -> 1234.56)
                if ',' in cleaned and '.' in cleaned:
                    # If both present, assume US format with commas as thousand separators
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
                # If only dots, assume decimal separator
                
                try:
                    return float(cleaned)
                except ValueError:
                    self.conversion_stats['conversion_errors'].append({
                        'value': val,
                        'error': f"Could not convert to float: {val}"
                    })
                    return None
            return None
        
        # Convert revenue column if it exists
        if 'revenue' in df.columns:
            df['revenue_original'] = df['revenue']  # Keep original for reference
            df['revenue_original_currency'] = df['currency']  # Track original currency
            
            # First clean the revenue values
            df['revenue_clean'] = df['revenue'].apply(clean_currency_value)
            
            # Initialize converted column with None
            df['revenue_converted'] = None
            
            # Convert non-USD values
            mask_non_usd = (df['currency'] != 'USD') & (df['revenue_clean'].notna())
            if mask_non_usd.any():
                self.conversion_stats['rows_converted'] += mask_non_usd.sum()
                df.loc[mask_non_usd, 'revenue_converted'] = df.loc[mask_non_usd].apply(
                    lambda row: self._convert_to_usd_amount(
                        row['revenue_clean'], 
                        row['currency']
                    ), 
                    axis=1
                )
                converted_currencies = df.loc[mask_non_usd, 'currency'].unique()
                warnings.append(f"Revenue converted to USD from: {', '.join(converted_currencies)}")
            
            # For USD rows, just use the cleaned value
            mask_usd = (df['currency'] == 'USD') & (df['revenue_clean'].notna())
            if mask_usd.any():
                df.loc[mask_usd, 'revenue_converted'] = df.loc[mask_usd, 'revenue_clean']
            
            # Final revenue column - use converted values, floor to 2 decimals
            df['revenue'] = df['revenue_converted'].apply(
                lambda x: np.floor(x * 100) / 100 if pd.notna(x) else None
            )
            
            # Drop temporary columns
            df = df.drop(columns=['revenue_clean', 'revenue_converted'])
        
        # Convert cost column if it exists
        if 'cost' in df.columns:
            df['cost_original'] = df['cost']  # Keep original for reference
            df['cost_original_currency'] = df['currency']  # Track original currency
            
            # First clean the cost values
            df['cost_clean'] = df['cost'].apply(clean_currency_value)
            
            # Initialize converted column with None
            df['cost_converted'] = None
            
            # Convert non-USD values
            mask_non_usd = (df['currency'] != 'USD') & (df['cost_clean'].notna())
            if mask_non_usd.any():
                df.loc[mask_non_usd, 'cost_converted'] = df.loc[mask_non_usd].apply(
                    lambda row: self._convert_to_usd_amount(
                        row['cost_clean'], 
                        row['currency']
                    ), 
                    axis=1
                )
            
            # For USD rows, just use the cleaned value
            mask_usd = (df['currency'] == 'USD') & (df['cost_clean'].notna())
            if mask_usd.any():
                df.loc[mask_usd, 'cost_converted'] = df.loc[mask_usd, 'cost_clean']
            
            # Final cost column - use converted values, floor to 2 decimals
            df['cost'] = df['cost_converted'].apply(
                lambda x: np.floor(x * 100) / 100 if pd.notna(x) else None
            )
            
            # Drop temporary columns
            df = df.drop(columns=['cost_clean', 'cost_converted'])
        
        # Recalculate profit if both revenue and cost exist (now both in USD)
        if 'revenue' in df.columns and 'cost' in df.columns:
            # Only calculate profit where both values exist
            profit_mask = df['revenue'].notna() & df['cost'].notna()
            df['profit'] = None
            df.loc[profit_mask, 'profit'] = df.loc[profit_mask, 'revenue'] - df.loc[profit_mask, 'cost']
            df['profit'] = df['profit'].apply(
                lambda x: np.floor(x * 100) / 100 if pd.notna(x) else None
            )
        
        # Add a note that all monetary values are now in USD
        df['monetary_values_in_usd'] = True
        
        return df

    def _normalize_currency(self, currency_value):
        """Convert currency symbols to standard codes"""
        if pd.isna(currency_value):
            return 'USD'  # Default to USD if unknown
        
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
        
        # Default to USD
        return 'USD'

    def _convert_to_usd_amount(self, amount, from_currency):
        """Convert amount from any currency to USD"""
        if pd.isna(amount) or from_currency == 'USD':
            return amount
        
        try:
            rate = self._get_exchange_rate_to_usd(from_currency)
            converted = amount * rate
            self.conversion_stats['rows_converted'] += 1
            return converted
        except Exception as e:
            self.conversion_stats['conversion_errors'].append({
                'currency': from_currency,
                'amount': amount,
                'error': str(e)
            })
            # Return original amount if conversion fails (with warning)
            return amount

    def _get_exchange_rate_to_usd(self, from_currency):
        """Get exchange rate from any currency to USD"""
        cache_key = f"{from_currency}_USD"
        
        # Check cache
        if cache_key in self.exchange_rate_cache:
            rate, timestamp = self.exchange_rate_cache[cache_key]
            if datetime.now() - timestamp < timedelta(hours=self.cache_duration):
                return rate
        
        # Get rate
        if self.use_live_rates:
            rate = self._fetch_live_rate(from_currency, 'USD')
        else:
            rate = self._get_static_rate_to_usd(from_currency)
        
        # Update cache
        self.exchange_rate_cache[cache_key] = (rate, datetime.now())
        return rate

    def _get_static_rate_to_usd(self, from_currency):
        """Static exchange rates to USD (as of early 2025)"""
        rates_to_usd = {
            'USD': 1.0,
            'EUR': 1.18,   # 1 EUR = 1.18 USD
            'GBP': 1.38,   # 1 GBP = 1.38 USD
            'JPY': 0.0091, # 1 JPY = 0.0091 USD
            'CAD': 0.79,   # 1 CAD = 0.79 USD
            'AUD': 0.72,   # 1 AUD = 0.72 USD
            'CHF': 1.12,   # 1 CHF = 1.12 USD
            'CNY': 0.15,   # 1 CNY = 0.15 USD
            'INR': 0.012,  # 1 INR = 0.012 USD
            'HKD': 0.13,   # 1 HKD = 0.13 USD
            'SGD': 0.74,   # 1 SGD = 0.74 USD
            'NZD': 0.68,   # 1 NZD = 0.68 USD
            'KRW': 0.00076,# 1 KRW = 0.00076 USD
            'MXN': 0.058,  # 1 MXN = 0.058 USD
            'BRL': 0.19,   # 1 BRL = 0.19 USD
            'RUB': 0.011,  # 1 RUB = 0.011 USD
            'ZAR': 0.054,  # 1 ZAR = 0.054 USD
            'TRY': 0.031,  # 1 TRY = 0.031 USD
            'SEK': 0.096,  # 1 SEK = 0.096 USD
            'NOK': 0.095,  # 1 NOK = 0.095 USD
            'DKK': 0.16,   # 1 DKK = 0.16 USD
            'PLN': 0.25,   # 1 PLN = 0.25 USD
            'CZK': 0.044,  # 1 CZK = 0.044 USD
            'HUF': 0.0028, # 1 HUF = 0.0028 USD
            'ILS': 0.27,   # 1 ILS = 0.27 USD
            'SAR': 0.27,   # 1 SAR = 0.27 USD
            'AED': 0.27,   # 1 AED = 0.27 USD
        }
        
        if from_currency not in rates_to_usd:
            raise ValueError(f"Unsupported currency: {from_currency}. Cannot convert to USD.")
        
        return rates_to_usd[from_currency]

    def _fetch_live_rate(self, from_currency, to_currency):
        """Fetch live exchange rate from API"""
        try:
            # You can use any free exchange rate API
            api_key = os.getenv('EXCHANGE_RATE', '')
            url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{from_currency}"
            
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if response.status_code == 200 and 'conversion_rates' in data:
                return data['conversion_rates'][to_currency]
            else:
                # Fallback to static rates
                return self._get_static_rate_to_usd(from_currency)
                
        except Exception as e:
            print(f"Warning: Failed to fetch live exchange rate: {e}")
            return self._get_static_rate_to_usd(from_currency)

    def get_conversion_summary(self):
        """Get summary of currency conversion operations"""
        return {
            "target_currency": "USD",
            "total_rows": self.conversion_stats['total_rows'],
            "rows_converted": self.conversion_stats['rows_converted'],
            "currencies_found": self.conversion_stats['currencies_found'],
            "conversion_errors": self.conversion_stats['conversion_errors'],
            "live_rates_used": self.use_live_rates
        }