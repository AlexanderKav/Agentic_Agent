"""
Insight Agent - Generates AI-powered insights from analysis results
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import math

import numpy as np
import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from agents.model_router import ModelRouter
from agents.monitoring import get_audit_logger, get_cost_tracker, get_performance_tracker, timer
from agents.prompts import PromptRegistry


# In agents/insight_agent.py, update the make_json_safe function:

def make_json_safe(obj: Any) -> Any:
    """
    Recursively convert all objects to JSON-serializable types.
    
    Args:
        obj: Object to convert
        
    Returns:
        JSON-serializable object
    """
    # Handle None
    if obj is None:
        return None
    
    # Handle NaN and Inf for float types
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    
    # Handle numpy floats (which may contain NaN/Inf)
    if isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    
    # Handle numpy integers
    if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    
    # Handle numpy booleans
    if isinstance(obj, (np.bool_)):
        return bool(obj)
    
    # Handle numpy arrays - convert to list FIRST
    if isinstance(obj, np.ndarray):
        return make_json_safe(obj.tolist())
    
    # Handle pandas Timestamp and numpy datetime64
    if isinstance(obj, (pd.Timestamp, np.datetime64, datetime)):
        return obj.isoformat()
    
    # Handle pandas Timedelta
    if isinstance(obj, (pd.Timedelta)):
        return str(obj)
    
    # Handle pandas Series - convert to dict
    if isinstance(obj, pd.Series):
        return make_json_safe(obj.to_dict())
    
    # Handle pandas DataFrame - convert to list of dicts
    if isinstance(obj, pd.DataFrame):
        return make_json_safe(obj.to_dict(orient='records'))
    
    # Handle dictionaries
    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}
    
    # Handle lists/tuples/sets
    if isinstance(obj, (list, tuple, set)):
        return [make_json_safe(x) for x in obj]
    
    # Handle basic types
    if isinstance(obj, (str, int, bool)):
        return obj
    
    # Fallback: try to convert to string
    try:
        return str(obj)
    except Exception:
        return None
    
    
def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Extract first JSON block from text safely, handling both // and # comments.
    
    Args:
        text: Raw text containing JSON
        
    Returns:
        Parsed JSON dictionary, empty dict if parsing fails
    """
    print(f"\n🔧 Cleaning JSON response (original length: {len(text)} chars)")
    
    # Remove comments line by line
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Handle // comments
        if '//' in line:
            parts = line.split('//')
            before_comment = parts[0].rstrip()
            if before_comment and before_comment[-1] in '0123456789"\'':
                cleaned_lines.append(line)  # Keep if number/string contains // as data
            else:
                cleaned_lines.append(parts[0].rstrip())
        # Handle # comments
        elif '#' in line:
            parts = line.split('#')
            before_comment = parts[0].rstrip()
            if before_comment and before_comment[-1] not in '"\'0123456789':
                cleaned_lines.append(parts[0].rstrip())
            else:
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)
    
    cleaned_text = '\n'.join(cleaned_lines)
    
    # Fix numbers with commas (e.g., "25,895.0" -> "25895.0")
    def fix_number_commas(match: re.Match) -> str:
        """Remove commas from numbers."""
        return match.group(0).replace(',', '')
    
    cleaned_text = re.sub(r'\d+,\d+\.?\d*', fix_number_commas, cleaned_text)
    cleaned_text = re.sub(r'#.*$', '', cleaned_text, flags=re.MULTILINE)
    
    # Find JSON block
    match = re.search(r'\{.*\}', cleaned_text, flags=re.DOTALL)
    if not match:
        print("⚠️ No JSON pattern found in text")
        return {}

    json_text = match.group()
    
    # Clean JSON
    json_text = re.sub(r',\s*([}\]])', r'\1', json_text)  # Remove trailing commas
    json_text = re.sub(r'#.*?\n', '\n', json_text)  # Remove # comments
    json_text = re.sub(r'\s*#.*$', '', json_text, flags=re.MULTILINE)
    json_text = re.sub(r'\n\s*\n', '\n', json_text)  # Remove blank lines

    # Attempt to parse with multiple strategies
    parse_strategies = [
        lambda: json.loads(json_text),
        lambda: json.loads(re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_text)),
        lambda: json.loads(re.sub(r':\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*([,}])', r':"\1"\2', json_text)),
    ]
    
    for i, strategy in enumerate(parse_strategies):
        try:
            return strategy()
        except json.JSONDecodeError as e:
            print(f"⚠️ Parse attempt {i + 1} failed: {e}")
            continue
    
    # Fallback: extract basic fields with regex
    print("⚠️ All JSON parsing attempts failed, using regex fallback")
    try:
        answer_match = re.search(r'"answer"\s*:\s*"([^"]+)"', json_text)
        summary_match = re.search(r'"human_readable_summary"\s*:\s*"([^"]+)"', json_text)
        
        return {
            "answer": answer_match.group(1) if answer_match else "Analysis complete.",
            "supporting_insights": {},
            "anomalies": {},
            "recommended_metrics": {},
            "human_readable_summary": summary_match.group(1) if summary_match else "See analysis results."
        }
    except Exception:
        return {}


def ensure_insight_format(insight_data: Any) -> Dict[str, Any]:
    """
    Ensure insight data has the correct structure with string fields.
    This is the central sanitizer for all insight outputs.
    
    Args:
        insight_data: Raw insight data from LLM
        
    Returns:
        Properly formatted insight dictionary
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
    """
    Agent for generating AI-powered insights from analysis results.
    
    Features:
    - Versioned prompt management
    - Model routing based on complexity
    - JSON extraction and sanitization
    - Performance monitoring and cost tracking
    """
    
    def __init__(
        self,
        user_id: Optional[int] = None,
        prompt_version: Optional[str] = None,
        enable_cost_tracking: bool = True
    ) -> None:
        """
        Initialize the Insight Agent.
        
        Args:
            user_id: User ID for A/B testing and tracking
            prompt_version: Specific prompt version to use (None = use current)
            enable_cost_tracking: Whether to track API costs
        """
        self.user_id: Optional[int] = user_id
        self.enable_cost_tracking: bool = enable_cost_tracking
        
        # Initialize monitoring
        self.perf_tracker = get_performance_tracker()
        self.audit_logger = get_audit_logger()
        self.cost_tracker = get_cost_tracker() if enable_cost_tracking else None
        
        # Initialize model router
        self.model_router: ModelRouter = ModelRouter()
        
        # Determine which prompt version to use
        if prompt_version:
            self.prompt_version: str = prompt_version
            print(f"📌 Using explicit prompt version: {self.prompt_version}")
        else:
            self.prompt_version = PromptRegistry.get_current_version('insight_agent')
            print(f"📌 Using default version from config: {self.prompt_version}")
        
        # Load the prompt
        self.prompt_data: Dict[str, Any] = PromptRegistry.get_prompt('insight_agent', self.prompt_version)
        
        # Initialize LLM
        self._init_llm()
        
        print(f"🤖 InsightAgent initialized with prompt version: {self.prompt_version}")
        print(f"   Model: {self.prompt_data['parameters']['model']}")
        print(f"   Temperature: {self.prompt_data['parameters']['temperature']}")
    
    def _init_llm(self) -> None:
        """Initialize the LLM with parameters from the prompt configuration."""
        params = self.prompt_data.get('parameters', {})
        model_name = params.get('model', 'gpt-4o-mini')
        
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=params.get('temperature', 0.6),
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.prompt_template = ChatPromptTemplate.from_template(
            self.prompt_data['template']
        )
    
    def _estimate_tokens(self, text: str) -> int:
        """Roughly estimate token count (4 chars per token is a common approximation)."""
        return len(text) // 4
    
    def _track_cost(self, input_text: str, output_text: str) -> None:
        """Track API cost for the call."""
        if not self.enable_cost_tracking or not self.cost_tracker:
            return
        
        input_tokens = self._estimate_tokens(input_text)
        output_tokens = self._estimate_tokens(output_text)
        
        self.cost_tracker.track_call(
            model='insight_agent',
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            agent='insight_agent',
            user=str(self.user_id) if self.user_id else 'anonymous',
            session_id=id(self)
        )
    
    @timer(operation='generate_insights')
    def generate_insights(
        self,
        data: Union[pd.DataFrame, Dict[str, Any], List[Any]],
        question: str = "General business insights"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate insights from analysis results.
        
        Args:
            data: Analysis data (DataFrame, dict, or list)
            question: User's question or context
            
        Returns:
            Tuple of (raw_response, sanitized_insights)
        """
        start_time = time.time()
        
        try:
            # Record which version was used
            print(f"📊 Using prompt version: {self.prompt_version}")
            
            # Prepare data for JSON serialization
            data_dict = self._prepare_data(data)
            
            # Add note about skipped tools if present
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
            
            # Track cost
            self._track_cost(data_json, raw)
            
            # Log the response for debugging
            self._log_raw_response(raw)
            
            # Parse and sanitize JSON
            parsed_json = extract_json_from_text(raw)
            sanitized_insights = ensure_insight_format(parsed_json)
            
            # Log to audit
            self.audit_logger.log_action(
                action_type='generate_insights',
                agent='insight_agent',
                details={
                    'prompt_version': self.prompt_version,
                    'question_length': len(question),
                    'data_size': len(data_json),
                    'response_length': len(raw)
                },
                session_id=id(self)
            )
            
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
    
    def _prepare_data(self, data: Union[pd.DataFrame, Dict[str, Any], List[Any]]) -> Any:
        """
        Prepare data for JSON serialization.
        
        Args:
            data: Raw data input
            
        Returns:
            JSON-serializable data
        """
        if hasattr(data, "to_dict"):
            return data.to_dict(orient="records")
        return make_json_safe(data)
    
    def _log_raw_response(self, raw: str) -> None:
        """Log the raw response for debugging."""
        print("\n" + "=" * 60)
        print("RAW INSIGHT RESPONSE:")
        print("=" * 60)
        # Truncate very long responses
        if len(raw) > 2000:
            print(raw[:2000] + "\n... (truncated)")
        else:
            print(raw)
        print("=" * 60 + "\n")
    
    def reload_prompt(self, version: Optional[str] = None) -> None:
        """
        Reload the prompt configuration.
        
        Args:
            version: New prompt version to use (None = keep current)
        """
        if version:
            self.prompt_version = version
        
        self.prompt_data = PromptRegistry.get_prompt('insight_agent', self.prompt_version)
        self._init_llm()
        
        print(f"🔄 Prompt reloaded: version {self.prompt_version}")
    
    def get_version_info(self) -> Dict[str, Any]:
        """
        Get information about the current prompt version.
        
        Returns:
            Dictionary with version information
        """
        return {
            "version": self.prompt_version,
            "model": self.prompt_data.get('parameters', {}).get('model', 'unknown'),
            "temperature": self.prompt_data.get('parameters', {}).get('temperature', 0.6),
            "template_length": len(self.prompt_data.get('template', ''))
        }


__all__ = ['InsightAgent', 'make_json_safe', 'extract_json_from_text', 'ensure_insight_format']