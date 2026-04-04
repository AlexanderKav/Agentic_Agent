"""
Question Classifier - Detects question type and extracts time periods.
Single responsibility: Understand what the user is asking.
"""

import re
from typing import Dict, List, Optional, Tuple


class QuestionClassifier:
    """
    Classify questions and extract parameters.
    
    Features:
    - Multi-class question classification
    - Time period extraction (quarters, years, months)
    - Recommended tools based on question type
    - Support for natural language date parsing
    """
    
    # Question type keywords with weights for better accuracy
    QUESTION_TYPES: Dict[str, List[str]] = {
        'forecast': [
            'forecast', 'predict', 'future', 'will be', 'will look',
            'projection', 'estimate', 'expected', 'anticipate',
            'next year', 'coming year', '2025', '2026', '2027',
            'q1', 'q2', 'q3', 'q4', 'quarter',
            'first quarter', 'second quarter', 'third quarter', 'fourth quarter',
            'most likely', 'likely to be', 'projected', 'outlook'
        ],
        'risk': [
            'risk', 'risks', 'concern', 'threat', 'vulnerability',
            'danger', 'issue', 'problem', 'challenge', 'exposure',
            'downside', 'warning', 'alert', 'red flag', 'critical',
            'urgent', 'at risk', 'vulnerable'
        ],
        'performance': [
            'performance', 'overview', 'dashboard', 'summary',
            'how is', 'how are', 'doing', 'health', 'status',
            'business performance', 'company performance', 'metrics',
            'kpi', 'kpis', 'scorecard', 'health check'
        ],
        'revenue_analysis': [
            'revenue', 'sales', 'profit', 'income', 'earnings',
            'product', 'customer', 'region', 'top', 'best', 'worst',
            'ranking', 'rank', 'trend', 'growth', 'decline',
            'revenue breakdown', 'revenue by', 'sales by'
        ],
        'customer_analysis': [
            'customer', 'client', 'buyer', 'account',
            'customer behavior', 'purchase pattern', 'retention',
            'churn', 'lifetime value', 'ltv', 'acquisition'
        ],
        'product_analysis': [
            'product', 'item', 'sku', 'inventory', 'stock',
            'product performance', 'product success', 'product health'
        ]
    }
    
    # Time period patterns with extraction logic
    PERIOD_PATTERNS: List[Tuple[str, str]] = [
        (r'Q([1-4])\s*(\d{4})', 'quarter'),  # Q1 2025
        (r'(first|second|third|fourth)\s+quarter\s+of\s+(\d{4})', 'quarter_text'),  # first quarter of 2025
        (r'\b(20\d{2})\b', 'year'),  # 2024, 2025
        (r'first\s+half\s+of\s+(\d{4})', 'half_year'),  # first half of 2024
        (r'second\s+half\s+of\s+(\d{4})', 'half_year'),
        (r'next\s+(\d+)\s+months?', 'months'),  # next 3 months
        (r'next\s+(\d+)\s+quarters?', 'quarters'),  # next 2 quarters
        (r'next\s+quarter', 'next_quarter'),  # ← Changed from 'quarter' to 'next_quarter'
        (r'this\s+year', 'this_year'),  # ← Changed from 'year' to 'this_year'
        (r'this\s+quarter', 'this_quarter'),  # ← Changed from 'quarter' to 'this_quarter'
        (r'current\s+year', 'this_year'),  # ← Changed from 'year' to 'this_year'
        (r'current\s+quarter', 'this_quarter'),  # ← Changed from 'quarter' to 'this_quarter'
        (r'(\d{4})\s*-\s*(\d{4})', 'year_range'),  # 2024-2025
        (r'(\d{4})\s+to\s+(\d{4})', 'year_range'),  # 2024 to 2025
        (r'next\s+year', 'next_year'),
        (r'the\s+coming\s+year', 'next_year'),
        (r'next\s+month', 'next_month'),  # ← Add this
    ]
    
    # Month mapping for text quarters
    QUARTER_MONTHS: Dict[str, str] = {
        'first': 'Q1',
        'second': 'Q2',
        'third': 'Q3',
        'fourth': 'Q4'
    }
    
    # Question type priority for ambiguous queries
    TYPE_PRIORITY: List[str] = [
        'forecast', 'risk', 'performance', 'revenue_analysis',
        'customer_analysis', 'product_analysis'
    ]
    
    def __init__(self):
        """Initialize the Question Classifier."""
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), period_type)
            for pattern, period_type in self.PERIOD_PATTERNS
        ]
    
    def classify(self, question: Optional[str]) -> str:
        """
        Classify the question type.
        
        Args:
            question: The user's question (can be None)
            
        Returns:
            One of: 'forecast', 'risk', 'performance', 'revenue_analysis',
                    'customer_analysis', 'product_analysis', 'overview', 'general'
        """
        if not question or not question.strip():
            return 'overview'
        
        question_lower = question.lower()
        
        # Count matches for each type
        scores: Dict[str, int] = {}
        
        for qtype, keywords in self.QUESTION_TYPES.items():
            score = sum(1 for kw in keywords if kw in question_lower)
            if score > 0:
                scores[qtype] = score
        
        if not scores:
            return 'general'
        
        # Get the highest scoring type
        highest_score = max(scores.values())
        top_types = [t for t, s in scores.items() if s == highest_score]
        
        # If tie, use priority order
        if len(top_types) > 1:
            for priority_type in self.TYPE_PRIORITY:
                if priority_type in top_types:
                    return priority_type
        
        return top_types[0] if top_types else 'general'
    
    def extract_period(self, question: Optional[str]) -> Optional[str]:
        """
        Extract time period from question.
        
        Args:
            question: The user's question
            
        Returns:
            Formatted period string (e.g., "Q1 2025", "2024", "next quarter")
        """
        if not question:
            return None
        
        for pattern, period_type in self._compiled_patterns:
            match = pattern.search(question)
            if match:
                return self._format_period(match, period_type)
        
        return None
    
    def extract_all_periods(self, question: Optional[str]) -> List[str]:
        """
        Extract all time periods from question.
        
        Args:
            question: The user's question
            
        Returns:
            List of all extracted periods
        """
        if not question:
            return []
        
        periods = []
        for pattern, period_type in self._compiled_patterns:
            matches = pattern.findall(question)
            for match in matches:
                if isinstance(match, tuple):
                    # Create a mock match object for formatting
                    mock_match = type('MockMatch', (), {'group': lambda self, x: match[x-1] if x <= len(match) else None})()
                    period = self._format_period(mock_match, period_type)
                    if period not in periods:
                        periods.append(period)
                else:
                    periods.append(match)
        
        return periods
    
    def _format_period(self, match, period_type: str) -> str:
        """Format extracted period into standard string."""
        
        if period_type == 'quarter':
            quarter = match.group(1)
            year = match.group(2)
            return f"Q{quarter} {year}"
        
        elif period_type == 'quarter_text':
            quarter_text = match.group(1).lower()
            year = match.group(2)
            quarter = self.QUARTER_MONTHS.get(quarter_text, quarter_text)
            return f"{quarter} {year}"
        
        elif period_type == 'year':
            return match.group(1)
        
        elif period_type == 'year_range':
            start_year = match.group(1)
            end_year = match.group(2)
            return f"{start_year}-{end_year}"
        
        elif period_type == 'next_year':
            return "next_year"
        
        elif period_type == 'next_quarter':
            return "next_quarter"
        
        elif period_type == 'next_month':
            return "next_month"
        
        elif period_type == 'this_year':
            return "this_year"
        
        elif period_type == 'this_quarter':
            return "this_quarter"
        
        elif period_type == 'half_year':
            year = match.group(1)
            # Check if it's first or second half
            match_string = match.string.lower() if hasattr(match, 'string') else ""
            if 'first' in match_string:
                return f"H1 {year}"
            return f"H2 {year}"
        
        elif period_type == 'months':
            months = match.group(1)
            return f"next {months} months"
        
        elif period_type == 'quarters':
            quarters = match.group(1)
            return f"next {quarters} quarters"
        
        # For any unmatched pattern, return the matched string
        return match.group(0) if hasattr(match, 'group') else str(match)
    
    def get_recommended_tools(self, question_type: str) -> List[str]:
        """
        Get recommended tools based on question type.
        
        Args:
            question_type: The classified question type
            
        Returns:
            List of tool names to include in the plan
        """
        base_tools = ['compute_kpis', 'visualization']
        
        tool_mapping = {
            'forecast': [
                'monthly_revenue_by_product',
                'monthly_growth',
                'revenue_by_product',
                'forecast_revenue_by_product'
            ],
            'risk': [
                'detect_revenue_spikes',
                'revenue_by_payment_status',
                'monthly_revenue_by_product'
            ],
            'performance': [
                'revenue_by_product',
                'revenue_by_region',
                'revenue_by_customer',
                'monthly_growth'
            ],
            'revenue_analysis': [
                'revenue_by_product',
                'revenue_by_region',
                'revenue_by_customer',
                'monthly_revenue_by_product'
            ],
            'customer_analysis': [
                'revenue_by_customer',
                'monthly_revenue_by_customer'
            ],
            'product_analysis': [
                'revenue_by_product',
                'monthly_revenue_by_product'
            ],
            'overview': [
                'revenue_by_product',
                'revenue_by_customer',
                'monthly_revenue_by_product',
                'detect_revenue_spikes'
            ],
            'general': [
                'revenue_by_product',
                'revenue_by_customer',
                'monthly_revenue_by_product',
                'detect_revenue_spikes'
            ]
        }
        
        tools = tool_mapping.get(question_type, tool_mapping['general'])
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for tool in base_tools + tools:
            if tool not in seen:
                seen.add(tool)
                result.append(tool)
        
        return result
    
    def has_forecast_intent(self, question: Optional[str]) -> bool:
        """Check if question has forecast/prediction intent."""
        if not question:
            return False
        
        forecast_indicators = [
            'forecast', 'predict', 'future', 'will be', 'project',
            'estimate', 'expected', 'anticipate', 'outlook'
        ]
        question_lower = question.lower()
        return any(indicator in question_lower for indicator in forecast_indicators)
    
    def has_risk_intent(self, question: Optional[str]) -> bool:
        """Check if question has risk/concern intent."""
        if not question:
            return False
        
        risk_indicators = [
            'risk', 'concern', 'threat', 'danger', 'issue',
            'problem', 'challenge', 'warning', 'alert'
        ]
        question_lower = question.lower()
        return any(indicator in question_lower for indicator in risk_indicators)
    
    def get_question_confidence(self, question: Optional[str]) -> float:
        """
        Get confidence score for the classification.
        
        Args:
            question: The user's question
            
        Returns:
            Confidence score between 0 and 1
        """
        if not question:
            return 0.0
        
        question_lower = question.lower()
        total_matches = 0
        type_matches = 0
        
        for qtype, keywords in self.QUESTION_TYPES.items():
            matches = sum(1 for kw in keywords if kw in question_lower)
            total_matches += matches
            if matches > 0:
                type_matches += matches
        
        if total_matches == 0:
            return 0.0
        
        return min(1.0, type_matches / total_matches)
    
    def get_question_summary(self, question: Optional[str]) -> Dict:
        """
        Get a comprehensive summary of the question analysis.
        
        Args:
            question: The user's question
            
        Returns:
            Dictionary with classification results
        """
        return {
            'question': question,
            'type': self.classify(question),
            'period': self.extract_period(question),
            'all_periods': self.extract_all_periods(question),
            'has_forecast': self.has_forecast_intent(question),
            'has_risk': self.has_risk_intent(question),
            'confidence': self.get_question_confidence(question),
            'recommended_tools': self.get_recommended_tools(self.classify(question))
        }


__all__ = ['QuestionClassifier']