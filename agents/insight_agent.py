import os
import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from agents.monitoring import get_performance_tracker, timer, get_audit_logger, get_cost_tracker
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
    """Extract first JSON block from text safely, handling both // and # comments."""
    
    print(f"\n🔧 Cleaning JSON response (original length: {len(text)} chars)")
    
    # First, remove any comments (both // and #) from the text
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Check for // comments
        if '//' in line:
            parts = line.split('//')
            before_comment = parts[0].rstrip()
            # If the comment is inside a string (unlikely but possible), keep the whole line
            if before_comment and before_comment[-1] in '0123456789"\'':
                cleaned_lines.append(line)  # Keep the whole line
            else:
                cleaned_lines.append(parts[0].rstrip())  # Remove comment
        # Check for # comments
        elif '#' in line:
            parts = line.split('#')
            before_comment = parts[0].rstrip()
            # Only remove if it's a real comment (not inside a string)
            if before_comment and before_comment[-1] not in '"\'0123456789':
                cleaned_lines.append(parts[0].rstrip())  # Remove comment
            else:
                cleaned_lines.append(line)  # Keep the whole line
        else:
            cleaned_lines.append(line)
    
    cleaned_text = '\n'.join(cleaned_lines)
    
    # Fix numbers with commas (e.g., "25,895.0" -> "25895.0")
    def fix_number_commas(match):
        """Remove commas from numbers"""
        num_str = match.group(0)
        return num_str.replace(',', '')
    
    # Find and fix numbers with commas (pattern: digits, comma, digits)
    cleaned_text = re.sub(r'\d+,\d+\.?\d*', fix_number_commas, cleaned_text)
    
    # Remove any remaining comments (like the ones with # in the JSON)
    cleaned_text = re.sub(r'#.*$', '', cleaned_text, flags=re.MULTILINE)
    
    # Try to find JSON block
    match = re.search(r'\{.*\}', cleaned_text, flags=re.DOTALL)
    if not match:
        print("⚠️ No JSON pattern found in text")
        return {}

    json_text = match.group()
    
    # Remove trailing commas before } or ]
    json_text = re.sub(r',\s*([}\]])', r'\1', json_text)
    
    # Remove any remaining # comments inside the JSON (like array entries with #)
    json_text = re.sub(r'#.*?\n', '\n', json_text)
    
    # Remove any placeholder comments (like "  # Example monthly average")
    json_text = re.sub(r'\s*#.*$', '', json_text, flags=re.MULTILINE)
    
    # Remove blank lines that might have been created
    json_text = re.sub(r'\n\s*\n', '\n', json_text)

    try:
        # First try: direct parse
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"⚠️ First parse attempt failed: {e}")
        try:
            # Second try: fix unquoted keys
            json_text = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_text)
            return json.loads(json_text)
        except json.JSONDecodeError as e2:
            print(f"⚠️ Second parse attempt failed: {e2}")
            try:
                # Third try: fix unquoted string values
                json_text = re.sub(r':\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*([,}])', r':"\1"\2', json_text)
                return json.loads(json_text)
            except json.JSONDecodeError as e3:
                print(f"⚠️ Third parse attempt failed: {e3}")
                print(f"Problematic JSON text (first 500 chars): {json_text[:500]}...")
                
                # Last resort: try to extract just the answer field
                try:
                    # Look for "answer" field
                    answer_match = re.search(r'"answer"\s*:\s*"([^"]+)"', json_text)
                    summary_match = re.search(r'"human_readable_summary"\s*:\s*"([^"]+)"', json_text)
                    
                    result = {
                        "answer": answer_match.group(1) if answer_match else "Analysis complete.",
                        "supporting_insights": {},
                        "anomalies": {},
                        "recommended_metrics": {},
                        "human_readable_summary": summary_match.group(1) if summary_match else "See analysis results."
                    }
                    print("✅ Extracted basic fields using regex fallback")
                    return result
                except:
                    pass
                
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
- **For product analysis, use monthly_revenue_by_product if available**
- **For customer analysis, use monthly_revenue_by_customer if available**
- **If monthly_revenue_by_product has empty arrays, you don't have product-level monthly data**
- **Do NOT make up data or use placeholder values**
- Only include insights relevant to the question.
- Avoid generic summaries or metrics not related to the query.
- If no specific question is given, provide a general performance and risk overview.
- **IMPORTANT: Do NOT include any comments (// or #) in your JSON response.**
- **Use actual data values from the provided data.**
- **Respond with valid JSON ONLY - no explanation outside the JSON.**

Return ONLY valid JSON, nothing else, in this format:

{{{{ 
  "answer": "...direct answer to the user's question...",
  "supporting_insights": {{}},
  "anomalies": {{}},
  "recommended_metrics": {{}},
  "human_readable_summary": "..."
}}}}
""")
    @timer(operation='generate_insights')
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
            
            # Check if the parsed JSON itself contains a nested JSON string
            if parsed_json and 'answer' in parsed_json:
                answer = parsed_json['answer']
                # If answer looks like a JSON string, try to parse it
                if isinstance(answer, str) and answer.strip().startswith('{'):
                    try:
                        nested = json.loads(answer)
                        if isinstance(nested, dict) and 'answer' in nested:
                            # Use the nested structure instead
                            parsed_json = nested
                    except:
                        pass  # Keep original if parsing fails
            
            # If parsing failed but we have raw text, create a simple response
            if not parsed_json and raw:
                parsed_json = {
                    "answer": raw[:500],
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