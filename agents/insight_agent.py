import os
import json
import re
import time  # ADD THIS - was missing
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from agents.monitoring import get_performance_tracker, timer, get_audit_logger, get_cost_tracker
import numpy as np
import pandas as pd
import hashlib

from agents.prompts import PromptRegistry
from agents.model_router import ModelRouter



def make_json_safe(obj):
    """Recursively convert all objects to JSON-serializable types."""
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(x) for x in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (np.bool_)):
        return bool(obj)
    elif isinstance(obj, (pd.Timestamp, np.datetime64, datetime)):
        return obj.isoformat()
    elif isinstance(obj, (pd.Timedelta)):
        return str(obj)
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif obj is None:
        return None
    else:
        try:
            return str(obj)
        except:
            return None


def extract_json_from_text(text):
    """Extract first JSON block from text safely, handling both // and # comments."""
    import re
    import json
    
    print(f"\n🔧 Cleaning JSON response (original length: {len(text)} chars)")
    
    # First, remove any comments (both // and #) from the text
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Check for // comments
        if '//' in line:
            parts = line.split('//')
            before_comment = parts[0].rstrip()
            if before_comment and before_comment[-1] in '0123456789"\'':  # Likely data with // in value
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
    
    cleaned_text = re.sub(r'\d+,\d+\.?\d*', fix_number_commas, cleaned_text)
    
    # Remove any remaining comments
    cleaned_text = re.sub(r'#.*$', '', cleaned_text, flags=re.MULTILINE)
    
    # Try to find JSON block
    match = re.search(r'\{.*\}', cleaned_text, flags=re.DOTALL)
    if not match:
        print("⚠️ No JSON pattern found in text")
        return {}

    json_text = match.group()
    
    # Remove trailing commas before } or ]
    json_text = re.sub(r',\s*([}\]])', r'\1', json_text)
    
    # Remove any remaining # comments inside the JSON
    json_text = re.sub(r'#.*?\n', '\n', json_text)
    
    # Remove any placeholder comments
    json_text = re.sub(r'\s*#.*$', '', json_text, flags=re.MULTILINE)
    
    # Remove blank lines
    json_text = re.sub(r'\n\s*\n', '\n', json_text)

    try:
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


def ensure_insight_format(insight_data):
    """
    Ensure insight data has the correct structure with string fields.
    This is the central sanitizer for all insight outputs.
    """
    result = {
        "answer": "",
        "supporting_insights": {},
        "anomalies": {},
        "recommended_metrics": {},
        "human_readable_summary": ""
    }
    
    if not isinstance(insight_data, dict):
        result["answer"] = str(insight_data) if insight_data else "Analysis complete."
        result["human_readable_summary"] = result["answer"][:200]
        return result
    
    # Extract and sanitize answer
    answer = insight_data.get('answer', '')
    if isinstance(answer, dict):
        # If answer is a dict, try to get the actual answer field
        answer = answer.get('answer', str(answer))
    result["answer"] = str(answer) if answer else "Analysis complete."
    
    # Extract and sanitize human_readable_summary
    summary = insight_data.get('human_readable_summary', '')
    if isinstance(summary, dict):
        summary = summary.get('human_readable_summary', str(summary))
    result["human_readable_summary"] = str(summary) if summary else result["answer"][:200]
    
    # Ensure supporting_insights is a dict
    supporting = insight_data.get('supporting_insights', {})
    if isinstance(supporting, dict):
        result["supporting_insights"] = make_json_safe(supporting)
    elif isinstance(supporting, list):
        result["supporting_insights"] = {"items": make_json_safe(supporting)}
    else:
        result["supporting_insights"] = {}
    
    # Ensure anomalies is a dict
    anomalies = insight_data.get('anomalies', {})
    if isinstance(anomalies, dict):
        result["anomalies"] = make_json_safe(anomalies)
    elif isinstance(anomalies, list):
        result["anomalies"] = {"detected": make_json_safe(anomalies)}
    else:
        result["anomalies"] = {}
    
    # Ensure recommended_metrics is a dict
    metrics = insight_data.get('recommended_metrics', {})
    if isinstance(metrics, dict):
        result["recommended_metrics"] = make_json_safe(metrics)
    elif isinstance(metrics, list):
        result["recommended_metrics"] = {"suggestions": make_json_safe(metrics)}
    else:
        result["recommended_metrics"] = {}
    
    return result


class InsightAgent:
    def __init__(self, user_id=None, prompt_version=None):
        self.user_id = user_id
        # self.ab_test = ABTestService()  # Remove this line
        self.model_router = ModelRouter()
        
        # Determine which prompt version to use
        if prompt_version:
            self.prompt_version = prompt_version
            print(f"📌 Using explicit prompt version: {self.prompt_version}")
        else:
            # Always use the version from current.json (which is v3)
            self.prompt_version = PromptRegistry.get_current_version('insight_agent')
            print(f"📌 Using default version from config: {self.prompt_version}")
        
        # Load the prompt
        self.prompt_data = PromptRegistry.get_prompt('insight_agent', self.prompt_version)
        
        # Initialize LLM
        self._init_llm()
        
        print(f"🤖 InsightAgent initialized with prompt version: {self.prompt_version}")
        print(f"   Model: {self.prompt_data['parameters']['model']}")
        print(f"   Temperature: {self.prompt_data['parameters']['temperature']}")
    
    def _init_llm(self):
        params = self.prompt_data.get('parameters', {})
        self.llm = ChatOpenAI(
            model=params.get('model', 'gpt-4o-mini'),
            temperature=params.get('temperature', 0.6),
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.prompt_template = ChatPromptTemplate.from_template(
            self.prompt_data['template']
        )
    
    @timer(operation='generate_insights')
    def generate_insights(self, data, question="General business insights"):
        """Generate insights with version tracking"""
        start_time = time.time()  # ADD THIS - was missing
        
        try:
            # Record which version was used
            print(f"📊 Using prompt version: {self.prompt_version}")
            
            # Prepare data
            if hasattr(data, "to_dict"):
                data_dict = data.to_dict(orient="records")
            else:
                data_dict = make_json_safe(data)
            
            # Check if there's a skipped tools note
            if isinstance(data_dict, dict):
                skipped_note = data_dict.pop("_skipped_tools_note", None)
                if skipped_note:
                    data_dict["_note"] = skipped_note["message"]
                    print(f"📝 Adding note for insight agent: {skipped_note['message']}")
            
            data_json = json.dumps(data_dict, indent=2, default=str)
            
            # Generate response
            messages = self.prompt_template.format_messages(data=data_json, question=question)
            response = self.llm.invoke(messages)
            raw = response.content
            
            print("\n" + "="*60)
            print("RAW INSIGHT RESPONSE:")
            print("="*60)
            print(raw)
            print("="*60 + "\n")
            
            # Parse JSON
            parsed_json = extract_json_from_text(raw)
            
            # Sanitize the output
            sanitized_insights = ensure_insight_format(parsed_json)
            
            return raw, sanitized_insights
            
        except Exception as e:
            print(f"❌ Error in InsightAgent.generate_insights: {e}")
            import traceback
            traceback.print_exc()
            
            # Return a safe error response
            error_insights = ensure_insight_format({
                "answer": f"Error generating insights: {str(e)}",
                "human_readable_summary": "An error occurred during analysis. Please try again or rephrase your question."
            })
            return "", error_insights