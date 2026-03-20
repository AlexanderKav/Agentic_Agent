import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class PlannerAgent:

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.6,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        self.prompt = ChatPromptTemplate.from_template("""
You are an AI data analyst planner.

Given a user question, select **only the tools necessary to answer it**.
Map question intent to available tools. Do NOT include tools unrelated to the question.

Available tools:

1. compute_kpis            -> overall revenue, profit, margins
2. revenue_by_customer     -> top customers by revenue/spending trends
3. revenue_by_product      -> top products by revenue/sales trends
4. monthly_growth          -> month-over-month revenue/profit changes
5. monthly_profit          -> monthly profit totals
6. detect_revenue_spikes   -> detect sudden revenue changes
7. forecast_revenue        -> predict future revenue
8. visualization           -> generate charts from results
9. monthly_revenue_by_customer -> monthly revenue trends for customers
10. monthly_revenue_by_product -> monthly revenue trends for products

User Question:
{question}

Instructions:
- Identify the intent and pick only the tools that directly answer it.
- Return a JSON object with a list of tools in order.
- Include `visualization` last if charts are useful.
If the question contains:
- "top products" → add "revenue_by_product"
- "top customers" → add "revenue_by_customer"
- "monthly trends" → add "monthly_growth" or "monthly_profit"
- "product monthly trends" → add "monthly_revenue_by_product"
- "customer monthly trends" → add "monthly_revenue_by_customer"
- "forecast" → add "forecast_revenue"
Always include "visualization" if charts are helpful.

Example:
Question: "Who are the top three customers this year and their spending trend?"
Plan: ["revenue_by_customer", "monthly_growth", "visualization"]

Return ONLY valid JSON:

{{
  "plan": [ ...tools to run... ]
}}
""")
    def create_plan(self, question):
        messages = self.prompt.format_messages(question=question)
        response = self.llm.invoke(messages)

        raw = response.content
        # DEBUG: print raw response
        print("RAW RESPONSE:", repr(raw))

        # Extract JSON safely
        match = re.search(r'\{.*\}', raw, flags=re.DOTALL)
        if match:
            parsed_json = json.loads(match.group())
        else:
            raise ValueError("LLM did not return valid JSON:\n" + raw)

        return raw, parsed_json
    
