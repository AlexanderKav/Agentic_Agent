import pandas as pd

class AutonomousAnalyst:
    def __init__(self, planner, analytics, insight_agent, viz_agent):
        self.planner = planner
        self.analytics = analytics
        self.insight_agent = insight_agent
        self.viz_agent = viz_agent
        self.analytics_cache = {}

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
        - If question is None, generate general insights automatically.
        - Returns: raw_plan, plan, results, raw_insights, insights
        """
        # ------------------------
        # Step 1: Determine tools
        # ------------------------
        if question:
            raw_plan, plan = self.planner.create_plan(question)
        else:
            # Default general analysis plan
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

        # ------------------------
        # Step 2: Run tools
        # ------------------------
        results = {}
        raw_results = {}

        for tool in plan["plan"]:
            if tool == "visualization":
                continue

            tool_result = self.cached_run(tool)
            raw_results[tool] = tool_result

            # Convert pandas → JSON-compatible dict
            if isinstance(tool_result, pd.DataFrame):
                tool_result = tool_result.copy()
                for col in tool_result.select_dtypes(include=["datetime64[ns]"]):
                    tool_result[col] = tool_result[col].astype(str)
                tool_result = tool_result.to_dict(orient="records")

            elif isinstance(tool_result, pd.Series):
                if pd.api.types.is_datetime64_any_dtype(tool_result.index):
                    tool_result.index = tool_result.index.astype(str)
                tool_result = tool_result.to_dict()

            results[tool] = tool_result

        # ------------------------
        # Step 3: Generate charts
        # ------------------------
        charts = self.viz_agent.generate_from_results(raw_results)
        if charts:
            results["charts"] = charts

        # ------------------------
        # Step 4: Generate insights
        # ------------------------
        if question:
            raw_insights, insights = self.insight_agent.generate_insights(results, question)
        else:
            # General insights
            raw_insights, insights = self.insight_agent.generate_insights(results, question="General business performance overview")

        return raw_plan, plan, results, raw_insights, insights