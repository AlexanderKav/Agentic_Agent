import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

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

    # -----------------------------
    # Helper to extract first JSON block
    # -----------------------------
    def _extract_first_json_block(self, text: str):
        start = text.find("{")
        if start == -1:
            return None

        bracket_count = 0
        for i, c in enumerate(text[start:], start):
            if c == "{":
                bracket_count += 1
            elif c == "}":
                bracket_count -= 1
            if bracket_count == 0:
                return text[start:i+1]
        return None

    # -----------------------------
    # Sanitize JSON-like text
    # -----------------------------
    def _sanitize_json_like_string(self, raw_text):
        # Wrap patterns like '33.67% in June 2024' in quotes
        raw_text = re.sub(r'[-+]?\d+(\.\d+)?%? in [A-Za-z0-9\s]+', lambda m: f'"{m.group(0)}"', raw_text)

        # Wrap unquoted words after : (e.g., profit: High) in quotes
        raw_text = re.sub(r'(:\s*)([A-Za-z][A-Za-z0-9 _]+)(\s*[,}])', r'\1"\2"\3', raw_text)

        # Remove trailing commas before } or ]
        raw_text = re.sub(r',(\s*[}\]])', r'\1', raw_text)

        return raw_text

    # -----------------------------
    # Generate insights
    # -----------------------------
    def generate_insights(self, data, question="General business insights"):
        try:
            # Convert pandas DataFrame to dict if needed
            if hasattr(data, "to_dict"):
                data_dict = data.to_dict(orient="records")
            else:
                data_dict = data

            data_json = json.dumps(data_dict, indent=2, default=str)
            messages = self.prompt.format_messages(data=data_json, question=question)

            response = self.llm.invoke(messages)
            raw = response.content

            # Extract JSON safely
            json_str = self._extract_first_json_block(raw)
            if json_str:
                json_str = self._sanitize_json_like_string(json_str)
                try:
                    parsed_json = json.loads(json_str)
                except json.JSONDecodeError as e:
                    print("Warning: JSON parse failed:", e)
                    parsed_json = {}
            else:
                parsed_json = {}

            return raw, parsed_json

        except Exception as e:
            print("Error in InsightAgent.generate_insights:", e)
            return "", {}
'''
    import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


class InsightAgent:

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # Prompt with escaped braces for JSON
        self.prompt = ChatPromptTemplate.from_template("""
You are a senior AI business analyst.

Analyze the following structured business data.

{data}

Your tasks:
1. Identify key revenue or profit trends
2. Highlight anomalies or unusual patterns
3. Suggest additional metrics worth analyzing

Return ONLY valid JSON, nothing else, in this format:

{{
"key_trends": {{}},
"anomalies": {{}},
"suggested_metrics_to_analyze": {{}}
}}
""")

    def generate_insights(self, data):

        # If Pandas DataFrame, convert to dict first
        if hasattr(data, "to_dict"):
            data_json = json.dumps(data.to_dict(orient="records"), indent=2, default=str)
        else:
            data_json = json.dumps(data, indent=2, default=str)  # already dict

        messages = self.prompt.format_messages(data=data_json)
        response = self.llm.invoke(messages)
        raw = response.content

        # Extract JSON safely
        match = re.search(r'\{.*\}', raw, flags=re.DOTALL)
        parsed_json = json.loads(match.group()) if match else None

        return raw, parsed_json
'''