import pandas as pd
import difflib

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
        "notes": ["notes", "comment", "remarks"]
    }

    def __init__(self, df):
        self.df = df

    def map_schema(self):
        mapping = {}
        new_columns = {}
        warnings = []

        for col in self.df.columns:
            lower_col = col.lower().strip()
            matched = False

            for standard, variants in self.STANDARD_SCHEMA.items():
                # Exact match
                if lower_col in variants:
                    mapping[col] = standard
                    new_columns[col] = standard
                    matched = True
                    break
                # Fuzzy match
                elif difflib.get_close_matches(lower_col, variants, n=1, cutoff=0.8):
                    mapping[col] = standard
                    new_columns[col] = standard
                    matched = True
                    break

            if not matched:
                warnings.append(col)

        df_clean = self.df.rename(columns=new_columns)

        # Add missing standard columns with default None
        for standard_col in self.STANDARD_SCHEMA.keys():
            if standard_col not in df_clean.columns:
                df_clean[standard_col] = None
                warnings.append(f"Missing column added: {standard_col}")

        return df_clean, mapping, warnings