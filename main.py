from connectors.google_sheets import GoogleSheetsConnector
from agents.schema_mapper import SchemaMapper
import os 
from dotenv import load_dotenv

SHEET_ID = "1twP-fGO3diHJJNR-LIZIpeRtwcZc-YjRuUcN7cLCjIA"

connector = GoogleSheetsConnector(sheet_id=SHEET_ID)
df = connector.fetch_sheet()

mapper = SchemaMapper(df)
clean_df, mapping = mapper.map_schema()

print("Column Mapping:")
print(mapping)

print("\nCleaned DataFrame:")
print(clean_df.head())



print("-----------------------------")
from agents.analytics_agent import AnalyticsAgent

analytics = AnalyticsAgent(clean_df)

kpis = analytics.compute_kpis()
print("\nKPIs:")
print(kpis)

rev_by_customer = analytics.revenue_by_customer()
print("\nRevenue by Customer:")
print(rev_by_customer)

print(analytics.df.dtypes)



print("-----------------------------")
print("\nMonthly Revenue:")
print(analytics.monthly_revenue())



print("-----------------------------")
print("\nMonthly Growth:")
print(analytics.monthly_growth())

print("-----------------------------")
print("\nMonthly Profit:")
print(analytics.monthly_profit())

print("-----------------------------")
print("\nRevenue Spikes:")
print(analytics.detect_revenue_spikes())


print("-----------------------------")
print("\nRevenue Spikes:")
print(analytics.generate_summary())

#Insight Agent
'''
from agents.insight_agent import InsightAgent

insight_agent = InsightAgent()

insights = insight_agent.generate_insights(analytics.df)

import json
print(json.dumps(insights, indent=2))
'''

#######################################################
from agents.planner_agent import PlannerAgent
from agents.insight_agent import InsightAgent
import json

# Planner
planner = PlannerAgent()
question = "How is the business performing and are there any risks?"

raw_plan, plan = planner.create_plan(question)
print("RAW PLAN:", raw_plan)
print("AI Plan:", json.dumps(plan, indent=2))

# Run tools
import pandas as pd

analytics_cache = {}

def cached_run(tool_name):
    if tool_name in analytics_cache:
        return analytics_cache[tool_name]
    result = analytics.run_tool(tool_name)
    analytics_cache[tool_name] = result
    return result

results = {}

for tool in plan["plan"]:
    #tool_result = analytics.run_tool(tool)
    tool_result = cached_run(tool)

    if tool == "revenue_by_customer":
        # Keep only top 10 customers
        tool_result = tool_result.sort_values("revenue", ascending=False).head(10)

    if isinstance(tool_result, pd.DataFrame):
        tool_result = tool_result.copy()
        # Convert datetime columns to string
        for col in tool_result.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]):
            tool_result[col] = tool_result[col].astype(str)
        tool_result = tool_result.to_dict(orient="records")

    elif isinstance(tool_result, pd.Series):
        # Convert datetime index to string
        if pd.api.types.is_datetime64_any_dtype(tool_result.index):
            tool_result.index = tool_result.index.astype(str)
        # Convert values if needed
        if pd.api.types.is_datetime64_any_dtype(tool_result):
            tool_result = tool_result.apply(str)
        tool_result = tool_result.to_dict()

    results[tool] = tool_result

print("\nTool Results:")
print(json.dumps(results, indent=2))

# Generate insights
insight_agent = InsightAgent()
raw_insights, insights = insight_agent.generate_insights(results)

print("\nRAW INSIGHT RESPONSE:")
print(raw_insights)

print("\nAI Business Analysis:")
print(json.dumps(insights, indent=2))

print("-------------------------------------------------------------")
from agents.autonomous_analyst import AutonomousAnalyst

autonomous_analyst = AutonomousAnalyst(planner, analytics, insight_agent)

question = "How is the business performing and are there any risks?"
raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run(question)

import json
print("AI Plan:", json.dumps(plan, indent=2))
print("Tool Results:", json.dumps(results, indent=2))
print("AI Business Insights:", json.dumps(insights, indent=2))