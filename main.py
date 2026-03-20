# main.py
from connectors.google_sheets import GoogleSheetsConnector
from connectors.csv_sheets import CSVConnector
from agents.schema_mapper import SchemaMapper
from agents.analytics_agent import AnalyticsAgent
from agents.planner_agent import PlannerAgent
from agents.insight_agent import InsightAgent
from agents.visualization_agent import VisualizationAgent
from agents.autonomous_analyst import AutonomousAnalyst
from connectors.data_loader import DataLoader

import os
from dotenv import load_dotenv
import pandas as pd
import json

# Load environment variables (API keys)
load_dotenv()
loader = DataLoader()
'''
def load_data(source, source_type=None):
    """Load data from various sources
    
    Args:
        source: The sheet ID or file path
        source_type: Optional explicit type ('google_sheets' or 'csv')
    """
    # If source type is explicitly provided
    if source_type == 'google_sheets':
        connector = GoogleSheetsConnector(source)
        return connector.fetch_sheet()
    elif source_type == 'csv':
        connector = CSVConnector(source)
        return connector.fetch_data()
    
    # Otherwise try to infer
    if source.endswith('.csv'):
        connector = CSVConnector(source)
        return connector.fetch_data()
    else:
        # Assume it's a Google Sheet ID
        connector = GoogleSheetsConnector(source)
        return connector.fetch_sheet()

# -------------------------
# Load and clean data
# -------------------------
# For Google Sheets
DATA_SOURCE = os.getenv('SHEET_ID')
if DATA_SOURCE:
    raw_df = load_data(DATA_SOURCE, source_type='google_sheets')
    print("GOOOOOOGLE")
else:
    # For CSV
    DATA_SOURCE = os.getenv('CSV_PATH', 'data.csv')
    raw_df = load_data(DATA_SOURCE, source_type='csv')
    print("CSSSSSSSSSSSVVVVVVVV")
# -------------------------
# Load and clean data
# -------------------------
#SHEET_ID = os.getenv('SHEET_ID')
#connector = GoogleSheetsConnector(sheet_id=SHEET_ID)
#raw_df = connector.fetch_sheet()

#csv_path = os.getenv('CSV_PATH', 'updated.csv')  # Set your CSV file path
#connector = CSVConnector(csv_path)
#raw_df = connector.fetch_data()  # Note: fetch_data(), not fetch_sheet()
'''
    # OPTION 1: CSV File
#df = loader.load('csv', 'data.csv')
    
    # OPTION 2: Excel File
#df = loader.load('csv', 'data.xlsx')  # CSV connector handles both
    
      #OPTION 3: Google Sheets
df = loader.load('google_sheets', {
         'sheet_id': os.getenv('SHEET_ID'),
         'range': 'A1:Z1000'
     })
    
    # OPTION 4: Docker PostgreSQL Database
#df = loader.load('database', {
 #       'connection_string': 'postgresql://postgres:testpass@localhost:5432/testdb',
  #      'table': 'sales'  # or use 'query': 'SELECT * FROM sales'
   # })
    
    # OPTION 5: SQLite Database
    # df = loader.load('database', {
    #     'connection_string': 'sqlite:///database.db',
    #     'table': 'sales'
    # })
    
    # OPTION 6: Using environment variables (if .env is configured)
    # df = loader.load_from_env()  # Reads DATA_SOURCE_TYPE from .env
mapper = SchemaMapper(df)
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
# Initialize Agents
# -------------------------
analytics = AnalyticsAgent(clean_df)
planner = PlannerAgent()
insight_agent = InsightAgent()
viz_agent = VisualizationAgent()
# -------------------------
# Define Autonomous Analyst (LangGraph)
# -------------------------


# -------------------------
# Run the workflow
# -------------------------
autonomous_analyst = AutonomousAnalyst(planner, analytics, insight_agent, viz_agent)

#question = "How is the business performing and are there any risks?"
#question = "Show profit trends in 2024 with a chart"
question = "Which three products contributed the most to revenue in 2024, and how did their monthly sales trend over the year?"
#question = "Which customers show declining revenue trends over the past 6 months?"
#question = ""
if question is None or question.strip() == "":
    question = "Provide a general business performance and risk overview."
print(question)
raw_plan, plan, results, raw_insights, insights = autonomous_analyst.run(question)


# -------------------------
# Display outputs
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