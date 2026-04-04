"""
Model Router - Routes requests to appropriate LLM models based on context
"""

import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import os


class AccuracyLevel(Enum):
    """Accuracy level for model selection."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class QuestionType(Enum):
    """Types of questions for model routing."""
    SIMPLE = "simple"
    COMPLEX = "complex"
    FORECAST = "forecast"
    ANOMALY = "anomaly"
    SUMMARY = "summary"
    PRODUCT_ANALYSIS = "product_analysis"
    CUSTOMER_ANALYSIS = "customer_analysis"


@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    cost_per_1k_tokens: float
    max_tokens: int
    priority: int
    avg_latency_ms: int
    name: str = ""
    context_window: int = 0
    recommended_for: List[QuestionType] = field(default_factory=list)


@dataclass
class ModelCallRecord:
    """Record of a model call for analytics."""
    question_type: str
    latency_ms: float
    timestamp: float
    input_tokens: int = 0
    output_tokens: int = 0
    success: bool = True
    error_message: str = ""


class ModelRouter:
    """
    Route requests to different LLM models based on:
    - Question complexity
    - Cost requirements
    - Performance needs
    - Error rates
    """
    
    # Model configurations
    MODELS: Dict[str, ModelConfig] = {
        'gpt-4o-mini': ModelConfig(
            cost_per_1k_tokens=0.00015,
            max_tokens=16384,
            priority=1,
            avg_latency_ms=500,
            context_window=128000,
            recommended_for=[QuestionType.SIMPLE, QuestionType.SUMMARY, QuestionType.ANOMALY]
        ),
        'gpt-4o': ModelConfig(
            cost_per_1k_tokens=0.005,
            max_tokens=128000,
            priority=2,
            avg_latency_ms=1500,
            context_window=128000,
            recommended_for=[QuestionType.COMPLEX, QuestionType.FORECAST, QuestionType.PRODUCT_ANALYSIS]
        ),
        'gpt-3.5-turbo': ModelConfig(
            cost_per_1k_tokens=0.0005,
            max_tokens=16384,
            priority=1,
            avg_latency_ms=300,
            context_window=16384,
            recommended_for=[QuestionType.SIMPLE]
        ),
        'o1-mini': ModelConfig(
            cost_per_1k_tokens=0.003,
            max_tokens=65536,
            priority=3,
            avg_latency_ms=2000,
            context_window=128000,
            recommended_for=[QuestionType.COMPLEX, QuestionType.FORECAST]
        ),
        'o1-preview': ModelConfig(
            cost_per_1k_tokens=0.015,
            max_tokens=128000,
            priority=4,
            avg_latency_ms=3000,
            context_window=128000,
            recommended_for=[QuestionType.COMPLEX]
        ),
    }
    
    # Complexity thresholds
    SIMPLE_QUESTION_MAX_LENGTH = 200
    COMPLEX_QUESTION_MIN_LENGTH = 500
    
    def __init__(
        self,
        default_model: str = 'gpt-4o-mini',
        enable_fallback: bool = True,
        max_retries: int = 3,
        enable_analytics: bool = True
    ) -> None:
        """
        Initialize the Model Router.
        
        Args:
            default_model: Default model to use
            enable_fallback: Whether to enable fallback on errors
            max_retries: Maximum number of retries before fallback
            enable_analytics: Whether to collect analytics
        """
        self.default_model: str = default_model
        self.enable_fallback: bool = enable_fallback
        self.max_retries: int = max_retries
        self.enable_analytics: bool = enable_analytics
        
        # Track model statistics
        self._model_stats: Dict[str, Dict[str, Any]] = {}
        self._call_history: List[ModelCallRecord] = []
        
        # Validate default model exists
        if default_model not in self.MODELS:
            raise ValueError(f"Unknown default model: {default_model}")

    def select_model(
        self,
        question_length: int,
        question_type: Optional[QuestionType] = None,
        required_accuracy: AccuracyLevel = AccuracyLevel.NORMAL,
        budget_constrained: bool = False,
        prefer_speed: bool = False
    ) -> str:
        """
        Select appropriate model based on context.
        
        Args:
            question_length: Length of the user's question in characters
            question_type: Type of question (auto-detected if not provided)
            required_accuracy: 'low', 'normal', 'high'
            budget_constrained: If True, prefer cheaper models
            prefer_speed: If True, prefer faster models
            
        Returns:
            Selected model name
        """
        # Budget-constrained: always use cheapest
        if budget_constrained:
            return self._get_cheapest_model()
        
        # Speed-preferring: use fastest model
        if prefer_speed:
            return self._get_fastest_model()
        
        # High accuracy or long/complex questions
        if required_accuracy == AccuracyLevel.HIGH or question_length > self.COMPLEX_QUESTION_MIN_LENGTH:
            return self._get_best_model_for_complexity()
        
        # Use question type if provided
        if question_type:
            return self._select_model_by_type(question_type)
        
        # Auto-detect question type
        return self.default_model

    def _get_cheapest_model(self) -> str:
        """Get the cheapest available model."""
        cheapest = min(self.MODELS.items(), key=lambda x: x[1].cost_per_1k_tokens)
        return cheapest[0]

    def _get_fastest_model(self) -> str:
        """Get the fastest available model."""
        fastest = min(self.MODELS.items(), key=lambda x: x[1].avg_latency_ms)
        return fastest[0]

    def _get_best_model_for_complexity(self) -> str:
        """Get the best model for complex tasks."""
        # Prefer o1 models for complex tasks
        for model in ['o1-preview', 'o1-mini', 'gpt-4o']:
            if model in self.MODELS:
                return model
        return 'gpt-4o'

    def _select_model_by_type(self, question_type: QuestionType) -> str:
        """Select model based on question type."""
        for model_name, config in self.MODELS.items():
            if question_type in config.recommended_for:
                return model_name
        return self.default_model

    def get_model_config(self, model_name: str) -> ModelConfig:
        """Get configuration for a model."""
        return self.MODELS.get(model_name, self.MODELS[self.default_model])

    def estimate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Estimate cost for a model call.
        
        Args:
            model_name: Name of the model
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        config = self.get_model_config(model_name)
        input_cost = (input_tokens / 1000) * config.cost_per_1k_tokens
        output_cost = (output_tokens / 1000) * config.cost_per_1k_tokens
        return input_cost + output_cost

    def should_use_fallback(self, model_name: str, error_count: int) -> bool:
        """
        Determine if we should fall back to a different model.
        
        Args:
            model_name: Name of the current model
            error_count: Number of consecutive errors
            
        Returns:
            True if fallback should be used
        """
        if not self.enable_fallback:
            return False
        
        # Initialize stats if not exists
        if model_name not in self._model_stats:
            self._model_stats[model_name] = {'errors': 0, 'calls': []}
        
        # Update error count
        self._model_stats[model_name]['errors'] = error_count
        
        # After max_retries errors, fall back
        return error_count >= self.max_retries

    def get_fallback_model(self, current_model: str) -> str:
        """
        Get fallback model when current model fails.
        
        Args:
            current_model: The model that failed
            
        Returns:
            Fallback model name
        """
        # Priority order for fallback
        fallback_order = ['gpt-4o-mini', 'gpt-3.5-turbo']
        
        for fallback in fallback_order:
            if fallback != current_model and fallback in self.MODELS:
                return fallback
        
        return self.default_model

    def record_model_call(
        self,
        model_name: str,
        question_type: str,
        latency_ms: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        success: bool = True,
        error_message: str = ""
    ) -> None:
        """
        Record a model call for analytics.
        
        Args:
            model_name: Name of the model used
            question_type: Type of question
            latency_ms: Latency in milliseconds
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            success: Whether the call was successful
            error_message: Error message if failed
        """
        if not self.enable_analytics:
            return
        
        record = ModelCallRecord(
            question_type=question_type,
            latency_ms=latency_ms,
            timestamp=time.time(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            success=success,
            error_message=error_message
        )
        
        # Initialize stats for model
        if model_name not in self._model_stats:
            self._model_stats[model_name] = {'calls': [], 'errors': 0}
        
        # Add to call history
        self._model_stats[model_name]['calls'].append(record)
        self._call_history.append(record)
        
        # Update error count
        if not success:
            self._model_stats[model_name]['errors'] += 1
        
        # Keep only last 1000 calls per model
        if len(self._model_stats[model_name]['calls']) > 1000:
            self._model_stats[model_name]['calls'] = self._model_stats[model_name]['calls'][-1000:]
        
        # Keep only last 10000 total calls
        if len(self._call_history) > 10000:
            self._call_history = self._call_history[-10000:]

    def get_model_stats(self) -> Dict[str, Any]:
        """
        Get statistics about model usage.
        
        Returns:
            Dictionary with model statistics
        """
        stats = {}
        
        for model_name, data in self._model_stats.items():
            calls = data.get('calls', [])
            if calls:
                latencies = [c.latency_ms for c in calls if c.success]
                successful_calls = [c for c in calls if c.success]
                failed_calls = [c for c in calls if not c.success]
                
                stats[model_name] = {
                    'total_calls': len(calls),
                    'successful_calls': len(successful_calls),
                    'failed_calls': len(failed_calls),
                    'success_rate': len(successful_calls) / len(calls) if calls else 1.0,
                    'avg_latency_ms': sum(latencies) / len(latencies) if latencies else 0,
                    'min_latency_ms': min(latencies) if latencies else 0,
                    'max_latency_ms': max(latencies) if latencies else 0,
                    'error_count': data.get('errors', 0),
                    'total_input_tokens': sum(c.input_tokens for c in calls),
                    'total_output_tokens': sum(c.output_tokens for c in calls),
                    'estimated_cost': self._calculate_total_cost(model_name, calls)
                }
        
        return stats

    def _calculate_total_cost(self, model_name: str, calls: List[ModelCallRecord]) -> float:
        """Calculate total estimated cost for model calls."""
        total_cost = 0.0
        for call in calls:
            total_cost += self.estimate_cost(
                model_name,
                call.input_tokens,
                call.output_tokens
            )
        return round(total_cost, 4)

    def detect_question_type(self, question: str) -> QuestionType:
        """
        Automatically detect the type of question.
        
        Args:
            question: The user's question
            
        Returns:
            Detected question type
        """
        question_lower = question.lower()
        
        # Forecast questions
        forecast_keywords = ['forecast', 'predict', 'future', 'will be', 'project', 'estimate']
        if any(kw in question_lower for kw in forecast_keywords):
            return QuestionType.FORECAST
        
        # Anomaly detection
        anomaly_keywords = ['anomaly', 'spike', 'unusual', 'outlier', 'abnormal', 'sudden']
        if any(kw in question_lower for kw in anomaly_keywords):
            return QuestionType.ANOMALY
        
        # Product analysis
        product_keywords = ['product', 'item', 'sku', 'best selling', 'top product']
        if any(kw in question_lower for kw in product_keywords):
            return QuestionType.PRODUCT_ANALYSIS
        
        # Customer analysis
        customer_keywords = ['customer', 'client', 'top customer', 'buyer']
        if any(kw in question_lower for kw in customer_keywords):
            return QuestionType.CUSTOMER_ANALYSIS
        
        # Summary/overview
        summary_keywords = ['overview', 'summary', 'overall', 'dashboard', 'health']
        if any(kw in question_lower for kw in summary_keywords):
            return QuestionType.SUMMARY
        
        # Complex questions (multiple parts, comparisons, etc.)
        complex_indicators = ['compare', 'versus', 'vs', 'why', 'how', 'analysis of']
        if any(kw in question_lower for kw in complex_indicators) and len(question) > 100:
            return QuestionType.COMPLEX
        
        return QuestionType.SIMPLE

    def get_recommended_model_for_question(self, question: str, budget_constrained: bool = False) -> str:
        """
        Get recommended model for a specific question.
        
        Args:
            question: The user's question
            budget_constrained: Whether to prefer cheaper models
            
        Returns:
            Recommended model name
        """
        question_type = self.detect_question_type(question)
        question_length = len(question)
        
        # Determine accuracy requirement
        if question_type in [QuestionType.FORECAST, QuestionType.COMPLEX]:
            required_accuracy = AccuracyLevel.HIGH
        elif question_type in [QuestionType.ANOMALY]:
            required_accuracy = AccuracyLevel.NORMAL
        else:
            required_accuracy = AccuracyLevel.LOW
        
        return self.select_model(
            question_length=question_length,
            question_type=question_type,
            required_accuracy=required_accuracy,
            budget_constrained=budget_constrained
        )

    def reset_stats(self) -> None:
        """Reset all model statistics."""
        self._model_stats = {}
        self._call_history = []

    def get_available_models(self) -> List[str]:
        """Get list of available model names."""
        return list(self.MODELS.keys())


# Singleton instance for global use
_model_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Get the global model router instance."""
    global _model_router
    if _model_router is None:
        _model_router = ModelRouter()
    return _model_router


__all__ = [
    'ModelRouter',
    'ModelConfig',
    'ModelCallRecord',
    'AccuracyLevel',
    'QuestionType',
    'get_model_router'
]