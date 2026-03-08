import pandas as pd

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

        for col in self.df.columns:
            lower_col = col.lower().strip()

            for standard, variants in self.STANDARD_SCHEMA.items():
                if lower_col in variants:
                    mapping[col] = standard
                    new_columns[col] = standard
                    break

        df_clean = self.df.rename(columns=new_columns)

        return df_clean, mapping