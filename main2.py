# main.py
from connectors.google_sheets import GoogleSheetsConnector
from agents.schema_mapper import SchemaMapper
from agents.analytics_agent import AnalyticsAgent
from agents.planner_agent import PlannerAgent
from agents.insight_agent import InsightAgent
from agents.visualization_agent import VisualizationAgent
from agents.autonomous_analyst import AutonomousAnalyst

import os
from dotenv import load_dotenv
import pandas as pd
import json

# Load environment variables (API keys)
load_dotenv()

# -------------------------
# 1️⃣ Load and clean data
# -------------------------
SHEET_ID = os.getenv('SHEET_ID')
connector = GoogleSheetsConnector(sheet_id=SHEET_ID)
raw_df = connector.fetch_sheet()

mapper = SchemaMapper(raw_df)
clean_df, mapping, warnings = mapper.map_schema()

print("Column Mapping:")
print(mapping)
if warnings:
    print("Warnings during mapping:")
    for w in warnings:
        print("-", w)

print("\nCleaned DataFrame (head):")
print(clean_df.head())

# -------------------------
# 2️⃣ Initialize Agents
# -------------------------
analytics = AnalyticsAgent(clean_df)
planner = PlannerAgent()
insight_agent = InsightAgent()
viz_agent = VisualizationAgent()
# -------------------------
# 3️⃣ Define Autonomous Analyst (LangGraph)
# -------------------------


# -------------------------
# 4️⃣ Run the workflow
# -------------------------
autonomous_analyst = AutonomousAnalyst(planner, analytics, insight_agent, viz_agent)

#question = "How is the business performing and are there any risks?"
#question = "Show profit trends in 2024 with a chart"
#question = "Which three products contributed the most to revenue in 2024, and how did their monthly sales trend over the year?"
question = "Which customers show declining revenue trends over the past 6 months?"
#question = ""
if question is None or question.strip() == "":
    question = "Provide a general business performance and risk overview."
print(question)
raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run(question)

# -------------------------
# 5️⃣ Display outputs
# -------------------------
print("\nRAW PLAN:")
print(raw_plan)

print("\nAI Plan (JSON):")
print(json.dumps(plan, indent=2))

print("\nTool Results (JSON):")
print(json.dumps(results, indent=2))

print("\nRAW INSIGHT RESPONSE:")
print(raw_insights)

print("\nAI Business Analysis (JSON):")
print(json.dumps(insights, indent=2))



#from automation.report_scheduler import ReportScheduler

#scheduler = ReportScheduler(autonomous_analyst)

#scheduler.start()


#from agents.visualization_agent import VisualizationAgent

#viz_agent = VisualizationAgent(analytics)

# Example user question
#question = "Show profit trends in 2024"

#charts = viz_agent.run(question)
#print("Generated Charts:", charts)

###############################
#while True:

  #  question = input("\nAsk a business question: ")

  #  raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run(question)

  #  print("\nAI Insights:")
   # print(json.dumps(insights, indent=2))