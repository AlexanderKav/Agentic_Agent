"""
Planner Agent - Creates execution plans based on user questions
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


class PlannerAgent:
    """
    AI-powered planner that maps user questions to appropriate analysis tools.
    
    Features:
    - Intent detection and tool selection
    - Period extraction (e.g., "Q1 2025", "next quarter")
    - Data requirement validation
    - JSON response parsing with error recovery
    """

    # Tool definitions with descriptions and requirements
    TOOLS: Dict[str, Dict[str, Any]] = {
        "compute_kpis": {
            "description": "overall revenue, profit, margins",
            "requires_months": 0,
            "keywords": ["kpi", "overall", "total", "revenue", "profit", "margin"]
        },
        "revenue_by_customer": {
            "description": "top customers by revenue/spending trends",
            "requires_months": 0,
            "keywords": ["customer", "client", "top customer", "spending"]
        },
        "revenue_by_product": {
            "description": "top products by revenue/sales trends",
            "requires_months": 0,
            "keywords": ["product", "item", "sku", "best selling", "top product"]
        },
        "monthly_growth": {
            "description": "month-over-month revenue/profit changes",
            "requires_months": 3,
            "keywords": ["growth", "month over month", "increase", "decrease", "trend"]
        },
        "monthly_profit": {
            "description": "monthly profit totals",
            "requires_months": 3,
            "keywords": ["monthly profit", "profit by month"]
        },
        "detect_revenue_spikes": {
            "description": "detect sudden revenue changes",
            "requires_months": 3,
            "keywords": ["spike", "anomaly", "unusual", "sudden", "detect"]
        },
        "forecast_revenue": {
            "description": "basic ARIMA forecast (requires 12+ months)",
            "requires_months": 12,
            "keywords": ["forecast", "predict", "future", "will be", "project"]
        },
        "forecast_revenue_with_explanation": {
            "description": "ARIMA forecast with plain English explanation (requires 12+ months)",
            "requires_months": 12,
            "keywords": ["forecast", "predict", "explanation", "explain", "will be"]
        },
        "forecast_with_confidence": {
            "description": "ARIMA forecast with confidence intervals (requires 12+ months)",
            "requires_months": 12,
            "keywords": ["confidence", "likely", "probability", "range", "interval"]
        },
        "forecast_ensemble": {
            "description": "compare multiple forecasting methods (requires 12+ months)",
            "requires_months": 12,
            "keywords": ["ensemble", "compare", "multiple methods", "best forecast"]
        },
        "detect_seasonality": {
            "description": "find seasonal patterns (REQUIRES 24+ months of data)",
            "requires_months": 24,
            "keywords": ["seasonal", "pattern", "cycle", "yearly", "annual", "quarterly"]
        },
        "visualization": {
            "description": "generate charts from results",
            "requires_months": 0,
            "keywords": ["chart", "graph", "plot", "visualize", "see"]
        },
        "monthly_revenue_by_customer": {
            "description": "monthly revenue trends for customers",
            "requires_months": 3,
            "keywords": ["customer trend", "customer monthly", "by customer over time"]
        },
        "monthly_revenue_by_product": {
            "description": "monthly revenue trends for products",
            "requires_months": 3,
            "keywords": ["product trend", "product monthly", "by product over time"]
        },
        "forecast_revenue_by_product": {
            "description": "forecast revenue for each product individually",
            "requires_months": 12,
            "keywords": ["product forecast", "forecast by product", "each product", "product future"]
        },
    }

    # Period extraction patterns
    PERIOD_PATTERNS: List[Tuple[str, str]] = [
        (r'Q([1-4])\s+(\d{4})', 'Q{quarter} {year}'),  # Q1 2025
        (r'quarter\s+([1-4])\s+of\s+(\d{4})', 'Q{quarter} {year}'),
        (r'first\s+quarter\s+of\s+(\d{4})', 'Q1 {year}'),
        (r'second\s+quarter\s+of\s+(\d{4})', 'Q2 {year}'),
        (r'third\s+quarter\s+of\s+(\d{4})', 'Q3 {year}'),
        (r'fourth\s+quarter\s+of\s+(\d{4})', 'Q4 {year}'),
        (r'next\s+quarter', 'next_quarter'),
        (r'next\s+month', 'next_month'),
        (r'(\d{4})\s*-\s*(\d{4})', '{year1}-{year2}'),  # 2024-2025
        (r'(\d{4})', '{year}'),  # 2025
    ]

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        temperature: float = 0.6,
        max_tokens: Optional[int] = None
    ) -> None:
        """
        Initialize the Planner Agent.
        
        Args:
            model: OpenAI model to use (default: gpt-4o-mini)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
        """
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=max_tokens
        )

        self.prompt = self._create_prompt_template()

    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Create the prompt template for the planner."""
        template = """You are an AI data analyst planner.

Given a user question, select **only the tools necessary to answer it**.
Map question intent to available tools. Do NOT include tools unrelated to the question.

Available tools:

1. compute_kpis            -> overall revenue, profit, margins
2. revenue_by_customer     -> top customers by revenue/spending trends
3. revenue_by_product      -> top products by revenue/sales trends
4. monthly_growth          -> month-over-month revenue/profit changes
5. monthly_profit          -> monthly profit totals
6. detect_revenue_spikes   -> detect sudden revenue changes
7. forecast_revenue        -> basic ARIMA forecast (requires 12+ months)
8. forecast_revenue_with_explanation -> ARIMA forecast with plain English explanation (requires 12+ months)
9. forecast_with_confidence -> ARIMA forecast with confidence intervals (requires 12+ months)
10. forecast_ensemble      -> compare multiple forecasting methods (requires 12+ months)
11. detect_seasonality     -> find seasonal patterns (REQUIRES 24+ months of data)
12. visualization          -> generate charts from results
13. monthly_revenue_by_customer -> monthly revenue trends for customers
14. monthly_revenue_by_product -> monthly revenue trends for products
15. forecast_revenue_by_product  -> forecast revenue for each product individually

CRITICAL DATA REQUIREMENTS:
- `detect_seasonality` requires AT LEAST 24 months of data (2 years)
- `forecast_*` tools require AT LEAST 12 months of data
- If data requirements aren't met, do NOT include those tools

User Question:
{question}

Instructions:
- Identify the intent and pick only the tools that directly answer it.
- Return a JSON object with a list of tools in order.
- Include `visualization` last if charts are useful.

If the question contains:
- "forecast" or "predict" → add "forecast_revenue_with_explanation" (if data available)
- "confidence" or "likely" → add "forecast_with_confidence" (if data available)
- "seasonal" or "pattern" → add "detect_seasonality" (ONLY if 24+ months data available)

Important:
- **For questions about specific time periods (Q1 2025, next quarter, next month), pass that as context**
- **Use `forecast_revenue_by_product` when asked about product success in future periods**
- **If the question contains a specific time period (e.g., "Q1 2025", "first quarter of 2025"), extract that period and add it to the plan as a context parameter**

**Return format:**
{{
  "plan": ["tool1", "tool2", ...],
  "period": "Q1 2025"  // Include this if a specific period is mentioned
}}

Return ONLY valid JSON:
{{
  "plan": [ ...tools to run... ],
  "period": "period_string_if_mentioned"
}}
"""
        return ChatPromptTemplate.from_template(template)

    def create_plan(self, question: str) -> Tuple[str, Dict[str, Any]]:
        """
        Create an execution plan for the given question.
        
        Args:
            question: The user's question
            
        Returns:
            Tuple of (raw_response, parsed_plan)
            
        Raises:
            ValueError: If the LLM response cannot be parsed as JSON
        """
        try:
            messages = self.prompt.format_messages(question=question)
            response = self.llm.invoke(messages)
            raw_content = response.content

            print(f"RAW RESPONSE from LLM:\n{raw_content}")

            # Extract and parse JSON
            parsed = self._parse_json_response(raw_content)
            
            # Validate and clean the plan
            parsed = self._validate_plan(parsed)
            
            return raw_content, parsed

        except Exception as e:
            print(f"Error creating plan: {e}")
            # Return a fallback plan
            fallback_plan = self._create_fallback_plan(question)
            return f"Error: {str(e)}", fallback_plan

    def _parse_json_response(self, raw_content: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response with error recovery.
        
        Args:
            raw_content: Raw LLM response string
            
        Returns:
            Parsed JSON dictionary
        """
        # Try to find JSON in the response
        match = re.search(r'\{.*\}', raw_content, flags=re.DOTALL)
        if not match:
            raise ValueError(f"No JSON found in response: {raw_content}")
        
        json_str = match.group()
        
        # Clean common JSON issues
        json_str = self._clean_json_string(json_str)
        
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}\nJSON string: {json_str}")
        
        return parsed

    def _clean_json_string(self, json_str: str) -> str:
        """Clean common JSON formatting issues."""
        # Remove trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # Ensure property names are quoted
        json_str = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        
        return json_str

    def _validate_plan(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean the parsed plan.
        
        Args:
            parsed: Parsed JSON dictionary
            
        Returns:
            Validated plan dictionary
        """
        # Ensure plan is a list
        plan = parsed.get("plan", [])
        if not isinstance(plan, list):
            plan = []
        
        # Remove duplicates while preserving order
        seen = set()
        unique_plan = []
        for tool in plan:
            if tool not in seen:
                seen.add(tool)
                unique_plan.append(tool)
        
        # Ensure visualization is last if present
        if "visualization" in unique_plan:
            unique_plan.remove("visualization")
            unique_plan.append("visualization")
        
        # Get period if present
        period = parsed.get("period")
        
        return {"plan": unique_plan, "period": period}

    def _create_fallback_plan(self, question: str) -> Dict[str, Any]:
        """
        Create a fallback plan when LLM parsing fails.
        
        Args:
            question: The user's question
            
        Returns:
            A basic plan dictionary
        """
        plan = ["compute_kpis"]
        
        # Add tools based on keywords
        question_lower = question.lower()
        
        if "customer" in question_lower:
            plan.append("revenue_by_customer")
        if "product" in question_lower:
            plan.append("revenue_by_product")
        if "growth" in question_lower or "trend" in question_lower:
            plan.append("monthly_growth")
        if "forecast" in question_lower or "predict" in question_lower:
            plan.append("forecast_revenue_with_explanation")
        if "spike" in question_lower or "anomaly" in question_lower:
            plan.append("detect_revenue_spikes")
        
        # Always add visualization if there are multiple tools
        if len(plan) > 1:
            plan.append("visualization")
        
        # Extract period
        period = self._extract_period(question)
        
        return {"plan": plan, "period": period}

    def _extract_period(self, question: str) -> Optional[str]:
        """
        Extract time period from question.
        
        Args:
            question: The user's question
            
        Returns:
            Extracted period string or None
        """
        question_lower = question.lower()
        
        # Check for "next" periods
        if "next quarter" in question_lower:
            return "next_quarter"
        if "next month" in question_lower:
            return "next_month"
        
        # Check for pattern matches
        for pattern, format_str in self.PERIOD_PATTERNS:
            match = re.search(pattern, question_lower)
            if match:
                groups = match.groups()
                if len(groups) == 1:
                    return format_str.format(year=groups[0])
                elif len(groups) == 2:
                    return format_str.format(quarter=groups[0], year=groups[1])
        
        return None

    def get_required_tools_for_question(self, question: str, months_available: int = 0) -> List[str]:
        """
        Get list of tools that can be used based on available data.
        
        Args:
            question: The user's question
            months_available: Number of months of data available
            
        Returns:
            List of available tools that meet requirements
        """
        question_lower = question.lower()
        available_tools = []
        
        for tool_name, tool_info in self.TOOLS.items():
            # Check data requirements
            if tool_info["requires_months"] <= months_available:
                # Check if any keyword matches
                if any(kw in question_lower for kw in tool_info["keywords"]):
                    available_tools.append(tool_name)
        
        return available_tools

    def add_custom_tool(
        self,
        tool_name: str,
        description: str,
        requires_months: int = 0,
        keywords: List[str] = None
    ) -> None:
        """
        Add a custom tool to the planner.
        
        Args:
            tool_name: Name of the tool
            description: Description of what the tool does
            requires_months: Minimum months of data required
            keywords: List of keywords that trigger this tool
        """
        self.TOOLS[tool_name] = {
            "description": description,
            "requires_months": requires_months,
            "keywords": keywords or []
        }


__all__ = ['PlannerAgent']