import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA

class AnalyticsAgent:

    def __init__(self, df):
        self.df = df.copy()

        # Ensure proper data types
        if "date" in self.df.columns:
            self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
        for col in ["revenue", "cost", "quantity"]:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

        # Calculate profit if possible
        if "revenue" in self.df.columns and "cost" in self.df.columns:
            self.df["profit"] = self.df["revenue"] - self.df["cost"]

    # -----------------------------
    # KPIs
    # -----------------------------
    def compute_kpis(self):
        total_revenue = np.floor(self.df["revenue"].sum())
        total_cost = np.floor(self.df["cost"].sum())
        total_profit = np.floor(self.df["profit"].sum())

        profit_margin = 0
        if total_revenue > 0:
            profit_margin = total_profit / total_revenue
            profit_margin = np.floor(profit_margin * 100) / 100  # floor to 2 decimals

        avg_order_value = np.floor(self.df["revenue"].mean())

        return {
            "total_revenue": float(total_revenue),
            "total_cost": float(total_cost),
            "total_profit": float(total_profit),
            "profit_margin": float(profit_margin),
            "avg_order_value": float(avg_order_value)
        }

    # -----------------------------
    # Revenue breakdowns
    # -----------------------------
    def revenue_by_customer(self):
        return np.floor(self.df.groupby("customer")["revenue"].sum().sort_values(ascending=False))

    def revenue_by_product(self):
        return np.floor(self.df.groupby("product")["revenue"].sum().sort_values(ascending=False))

    def revenue_by_region(self):
        return np.floor(self.df.groupby("region")["revenue"].sum().sort_values(ascending=False))

    # -----------------------------
    # Monthly metrics
    # -----------------------------
    def monthly_revenue(self):
        series = self.df.set_index("date").resample("ME")["revenue"].sum()
        return np.floor(series)

    def monthly_profit(self):
        series = self.df.set_index("date").resample("ME")["profit"].sum()
        return np.floor(series)

    def monthly_growth(self):
        monthly = self.monthly_revenue()
        growth = monthly.pct_change().fillna(0)
        return np.floor(growth * 100) / 100  # floor to 2 decimals

    # -----------------------------
    # Quantity metrics
    # -----------------------------
    def total_units_sold(self):
        if "quantity" not in self.df.columns:
            return None
        return np.floor(self.df["quantity"].sum())

    def revenue_per_unit(self):
        if "quantity" not in self.df.columns or self.df["quantity"].sum() == 0:
            return None
        return np.floor(self.df["revenue"].sum() / self.df["quantity"].sum())

    # -----------------------------
    # Payment analysis
    # -----------------------------
    def revenue_by_payment_status(self):
        if "payment_status" not in self.df.columns:
            return None
        return np.floor(self.df.groupby("payment_status")["revenue"].sum())

    # -----------------------------
    # Anomaly detection
    # -----------------------------
    def detect_revenue_spikes(self):
        monthly = self.monthly_revenue()
        threshold = monthly.mean() + 2 * monthly.std()
        anomalies = monthly[monthly > threshold]
        return anomalies  # Series already floored by monthly_revenue

    # -----------------------------
    # Generate human-readable summary
    # -----------------------------
    def generate_summary(self):
        summary = ""
        kpis = self.compute_kpis()

        summary += (
            f"Total revenue: ${kpis['total_revenue']:,.0f}, "
            f"total cost: ${kpis['total_cost']:,.0f}, "
            f"total profit: ${kpis['total_profit']:,.0f}, "
            f"profit margin: {kpis['profit_margin']:.0%}.\n"
        )

        top_cust = self.revenue_by_customer().head(3)
        if not top_cust.empty:
            customers = ", ".join([f"{c} (${r:,.0f})" for c, r in top_cust.items()])
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

        if "payment_status" in self.df.columns:
            unpaid = self.df[self.df["payment_status"] != "paid"]
            if not unpaid.empty:
                unpaid_amount = np.floor(unpaid["revenue"].sum())
                summary += f"Outstanding unpaid revenue: ${unpaid_amount:,.0f}.\n"

        return summary

    # -----------------------------
    # Forecast revenue
    # -----------------------------
    def forecast_revenue(self):
        monthly = self.monthly_revenue()
        model = ARIMA(monthly, order=(1, 1, 1))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=3)
        return np.floor(forecast)

    # -----------------------------
    # Run tool by name
    # -----------------------------
    def run_tool(self, tool_name):
        tools = {
            "compute_kpis": self.compute_kpis,
            "revenue_by_customer": self.revenue_by_customer,
            "monthly_growth": self.monthly_growth,
            "monthly_profit": self.monthly_profit,
            "detect_revenue_spikes": self.detect_revenue_spikes,
            "forecast_revenue": self.forecast_revenue,
            "revenue_by_product": self.revenue_by_product,
            "monthly_revenue_by_customer": self.monthly_revenue_by_customer
        }

        if tool_name not in tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        return tools[tool_name]()
    # -----------------------------
    # Monthly revenue per customer
    # -----------------------------
    def monthly_revenue_by_customer(self, months_to_check=6):
        """
        Returns a dictionary with revenue per customer per month and monthly decline info.
        Format:
        {
            "Customer A": {
                "monthly_revenue": {"2024-01": 1200.0, "2024-02": 1100.0, ...},
                "declining": True,   # True if revenue decreased over last `months_to_check`
                "trend": [1200.0, 1100.0, ...]  # list of last N months revenue for trend analysis
            },
            "Customer B": {...},
            ...
        }
        """

        if "customer" not in self.df.columns:
            return {}

        df_monthly = self.df.copy()
        df_monthly["customer"] = df_monthly["customer"].replace("", "Unknown Customer")
        df_monthly["month"] = df_monthly["date"].dt.to_period("M")
        grouped = df_monthly.groupby(["customer", "month"])["revenue"].sum().reset_index()

        result = {}

        for customer, group in grouped.groupby("customer"):
            # Sort months ascending
            group = group.sort_values("month")
            monthly_dict = {str(row["month"]): float(np.floor(row["revenue"])) for _, row in group.iterrows()}

            # Take last `months_to_check` months
            last_months = list(monthly_dict.values())[-months_to_check:]

            # Determine if declining trend: simple check if each month <= previous month
            declining = all(earlier >= later for earlier, later in zip(last_months, last_months[1:])) if len(last_months) > 1 else False

            result[customer] = {
                "monthly_revenue": monthly_dict,
                "trend": last_months,
                "declining": declining
            }

        return result