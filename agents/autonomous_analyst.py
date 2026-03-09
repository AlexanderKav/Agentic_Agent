import pandas as pd
from agents.insight_agent import make_json_safe  # import the JSON-safe helper

class AutonomousAnalyst:
    def __init__(self, planner, analytics, insight_agent, viz_agent):
        self.planner = planner
        self.analytics = analytics
        self.insight_agent = insight_agent
        self.viz_agent = viz_agent
        self.analytics_cache = {}

    def make_json_safe(obj):
        """Recursively convert all objects to JSON-serializable types."""
        if isinstance(obj, dict):
            return {str(k): make_json_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_json_safe(x) for x in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, (pd.Timestamp, pd.Timedelta)):
            return str(obj)
        elif obj is None:
            return None
        else:
            return obj


    def cached_run(self, tool_name):
        """Cache tool results to avoid repeated computation."""
        if tool_name in self.analytics_cache:
            return self.analytics_cache[tool_name]
        result = self.analytics.run_tool(tool_name)
        self.analytics_cache[tool_name] = result
        return result

    def run(self, question=None):
        """
        Run analysis based on a question.
        - Returns: JSON-safe raw_plan, plan, results, raw_insights, insights
        """
        # Step 1: Determine tools
        if question:
            raw_plan, plan = self.planner.create_plan(question)
        else:
            plan = {
                "plan": [
                    "compute_kpis",
                    "monthly_profit",
                    "monthly_growth",
                    "detect_revenue_spikes",
                    "forecast_revenue",
                    "visualization",
                    "revenue_by_customer",
                    "revenue_by_product",
                    "monthly_revenue_by_customer"
                ]
            }
            raw_plan = "Default general analysis plan applied."

        # Step 2: Run tools
        results = {}
        raw_results = {}

        for tool in plan["plan"]:
            if tool == "visualization":
                continue

            tool_result = self.cached_run(tool)
            raw_results[tool] = tool_result

            # Convert pandas → JSON-compatible
            if isinstance(tool_result, pd.DataFrame):
                tool_result = tool_result.copy()
                for col in tool_result.select_dtypes(include=["datetime64[ns]"]):
                    tool_result[col] = tool_result[col].astype(str)
                tool_result = tool_result.to_dict(orient="records")
            elif isinstance(tool_result, pd.Series):
                if pd.api.types.is_datetime64_any_dtype(tool_result.index):
                    tool_result.index = tool_result.index.astype(str)
                tool_result = tool_result.to_dict()

            # Make JSON-safe
            results[tool] = make_json_safe(tool_result)

        # Step 3: Generate charts
        charts = self.viz_agent.generate_from_results(raw_results)
        if charts:
            results["charts"] = make_json_safe(charts)

        # Step 4: Generate insights
        if question:
            raw_insights, insights = self.insight_agent.generate_insights(results, question)
        else:
            raw_insights, insights = self.insight_agent.generate_insights(
                results, question="General business performance overview"
            )

        # Ensure JSON-safe return values
        return (
            make_json_safe(raw_plan),
            make_json_safe(plan),
            make_json_safe(results),
            make_json_safe(raw_insights),
            make_json_safe(insights)
        )