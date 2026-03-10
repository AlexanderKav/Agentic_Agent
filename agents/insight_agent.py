import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import numpy as np
import pandas as pd


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


def extract_json_from_text(text):
    """Extract first JSON block from text safely."""
    import re
    import json
    
    # Try to find JSON block
    match = re.search(r'\{.*\}', text, flags=re.DOTALL)
    if not match:
        print("No JSON pattern found in text")
        return {}

    json_text = match.group()
    
    # Remove trailing commas before } or ]
    json_text = re.sub(r',\s*([}\]])', r'\1', json_text)

    try:
        # First try: direct parse
        return json.loads(json_text)
    except json.JSONDecodeError:
        try:
            # Second try: fix unquoted keys
            # Add quotes around keys
            json_text = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_text)
            return json.loads(json_text)
        except json.JSONDecodeError:
            try:
                # Third try: fix unquoted string values
                json_text = re.sub(r':\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*([,}])', r':"\1"\2', json_text)
                return json.loads(json_text)
            except json.JSONDecodeError as e:
                print(f"Warning: unable to parse AI JSON safely. Error: {e}")
                print(f"Problematic JSON text: {json_text[:200]}...")
                return {}


class InsightAgent:

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.6,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        self.prompt = ChatPromptTemplate.from_template("""
You are a senior AI business analyst.

A user asked the following question (or request):

{question}

Analyze the following structured business data:

{data}

Your tasks:
1. Directly answer the user's question in plain language.
2. Provide supporting insights (key revenue/profit trends).
3. Highlight anomalies or unusual patterns.
4. Suggest additional metrics worth analyzing.

Important:
- Only include insights relevant to the question.
- Avoid generic summaries or metrics not related to the query.
- If no specific question is given, provide a general performance and risk overview.
- Do not include metrics not relevant to the question.

Return ONLY valid JSON, nothing else, in this format:

{{
  "answer": "...direct answer to the user's question...",
  "supporting_insights": {{ }},
  "anomalies": {{ }},
  "recommended_metrics": {{ }},
  "human_readable_summary": "..."  # one paragraph summary suitable for email
}}
""")

    def generate_insights(self, data, question="General business insights"):
        try:
            # Convert tool results to JSON-safe dict
            if hasattr(data, "to_dict"):
                data_dict = data.to_dict(orient="records")
            else:
                data_dict = make_json_safe(data)

            data_dict = make_json_safe(data_dict)
            data_json = json.dumps(data_dict, indent=2, default=str)

            messages = self.prompt.format_messages(data=data_json, question=question)
            response = self.llm.invoke(messages)
            raw = response.content

            print("\nRAW INSIGHT RESPONSE:")
            print(raw)
            print()

            # Extract JSON safely
            parsed_json = extract_json_from_text(raw)
            
            # If parsing failed but we have raw text, try to create a simple response
            if not parsed_json and raw:
                # Create a minimal valid response
                parsed_json = {
                    "answer": raw[:500],  # First 500 chars as answer
                    "supporting_insights": {},
                    "anomalies": {},
                    "recommended_metrics": {},
                    "human_readable_summary": raw[:200]
                }

            return raw, parsed_json

        except Exception as e:
            print("Error in InsightAgent.generate_insights:", e)
            import traceback
            traceback.print_exc()
            return "", {}