# agents/orchestrator/question_classifier.py
"""
Question Classifier - Detects question type and extracts time periods.
Single responsibility: Understand what the user is asking.
"""

import re
from typing import Optional, Tuple


class QuestionClassifier:
    """Classify questions and extract parameters"""
    
    # Question type keywords
    QUESTION_TYPES = {
        'forecast': [
            'forecast', 'predict', 'future', 'will be', 'will look',
            'projection', 'estimate', 'expected', 'anticipate',
            'next year', 'coming year', '2025', '2026', '2027',
            'q1', 'q2', 'q3', 'q4', 'quarter',
            'first quarter', 'second quarter', 'third quarter', 'fourth quarter',
            'most likely', 'likely to be'
        ],
        'risk': [
            'risk', 'risks', 'concern', 'threat', 'vulnerability',
            'danger', 'issue', 'problem', 'challenge', 'exposure',
            'downside', 'warning', 'alert'
        ],
        'performance': [
            'performance', 'overview', 'dashboard', 'summary',
            'how is', 'how are', 'doing', 'health', 'status',
            'business performance', 'company performance'
        ],
        'revenue_analysis': [
            'revenue', 'sales', 'profit', 'income', 'earnings',
            'product', 'customer', 'region', 'top', 'best', 'worst',
            'ranking', 'rank', 'trend', 'growth', 'decline'
        ]
    }
    
    # Time period patterns
    PERIOD_PATTERNS = [
        (r'Q([1-4])\s*(\d{4})', 'quarter'),  # Q1 2025
        (r'(first|second|third|fourth)\s+quarter\s+of\s+(\d{4})', 'quarter_text'),  # first quarter of 2025
        (r'\b(20\d{2})\b', 'year'),  # 2024, 2025
        (r'first\s+half\s+of\s+(\d{4})', 'half_year'),  # first half of 2024
        (r'second\s+half\s+of\s+(\d{4})', 'half_year'),
        (r'next\s+(\d+)\s+months?', 'months'),  # next 3 months
        (r'next\s+quarter', 'quarter'),
        (r'this\s+year', 'year'),
        (r'this\s+quarter', 'quarter'),
    ]
    
    # Month mapping for text quarters
    QUARTER_MONTHS = {
        'first': 'Q1',
        'second': 'Q2',
        'third': 'Q3',
        'fourth': 'Q4'
    }
    
    def classify(self, question: Optional[str]) -> str:
        """
        Classify the question type.
        
        Args:
            question: The user's question (can be None)
            
        Returns:
            One of: 'forecast', 'risk', 'performance', 'revenue_analysis', 'overview', 'general'
        """
        if not question or not question.strip():
            return 'overview'
        
        question_lower = question.lower()
        
        for qtype, keywords in self.QUESTION_TYPES.items():
            if any(kw in question_lower for kw in keywords):
                return qtype
        
        return 'general'
    
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
        
        question_lower = question.lower()
        
        for pattern, period_type in self.PERIOD_PATTERNS:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                return self._format_period(match, period_type)
        
        return None
    
    def _format_period(self, match, period_type: str) -> str:
        """Format extracted period into standard string"""
        
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
        
        elif period_type == 'half_year':
            year = match.group(1)
            # Check if it's first or second half
            if 'first' in match.string.lower():
                return f"H1 {year}"
            return f"H2 {year}"
        
        elif period_type == 'months':
            months = match.group(1)
            return f"next {months} months"
        
        return match.group(0)
    
    def get_recommended_tools(self, question_type: str) -> list:
        """
        Get recommended tools based on question type.
        
        Args:
            question_type: The classified question type
            
        Returns:
            List of tool names to include in the plan
        """
        base_tools = ['compute_kpis', 'visualization']
        
        if question_type == 'forecast':
            return base_tools + [
                'monthly_revenue_by_product',
                'monthly_growth',
                'revenue_by_product',
                'forecast_revenue_by_product'
            ]
        
        elif question_type == 'risk':
            return base_tools + [
                'detect_revenue_spikes',
                'revenue_by_payment_status',
                'monthly_revenue_by_product'
            ]
        
        elif question_type == 'performance':
            return base_tools + [
                'revenue_by_product',
                'revenue_by_region',
                'revenue_by_customer',
                'monthly_growth'
            ]
        
        elif question_type == 'revenue_analysis':
            return base_tools + [
                'revenue_by_product',
                'revenue_by_region',
                'revenue_by_customer',
                'monthly_revenue_by_product'
            ]
        
        else:  # general or overview
            return base_tools + [
                'revenue_by_product',
                'revenue_by_customer',
                'monthly_revenue_by_product',
                'detect_revenue_spikes'
            ]