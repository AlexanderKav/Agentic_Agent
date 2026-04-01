# agents/orchestrator/plan_executor.py
"""
Plan Executor - Executes the list of tools and handles errors.
Single responsibility: Run the tools in the plan.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ExecutionResult:
    """Type-safe execution result for a tool"""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    raw_result: Any = None  # Original result before conversion


class PlanExecutor:
    """
    Executes a list of tools from a plan.
    Handles period parameters, caching, and error collection.
    """
    
    # Tools that understand period parameters
    PERIOD_AWARE_TOOLS = {
        'forecast_revenue_by_product',
        'forecast_revenue_with_explanation',
        'forecast_with_confidence',
        'forecast_ensemble'
    }
    
    def __init__(self, analytics_agent, cache_manager):
        """
        Args:
            analytics_agent: The AnalyticsAgent instance
            cache_manager: CacheManager instance for storing results
        """
        self.analytics = analytics_agent
        self.cache = cache_manager
        self.failed_tools: List[str] = []
        self.skipped_tools: List[str] = []
    
    def execute_plan(
        self, 
        plan: List[str], 
        period: Optional[str] = None
    ) -> Dict[str, ExecutionResult]:
        """
        Execute all tools in the plan.
        
        Args:
            plan: List of tool names to execute
            period: Optional time period (e.g., "Q1 2025")
            
        Returns:
            Dictionary mapping tool names to ExecutionResult objects
        """
        results = {}
        self.failed_tools = []
        self.skipped_tools = []
        
        for tool_name in plan:
            if tool_name == "visualization":
                continue
            
            result = self._execute_tool(tool_name, period)
            results[tool_name] = result
            
            if not result.success:
                self.failed_tools.append(tool_name)
            
            # Check for insufficient data
            if isinstance(result.result, dict) and result.result.get("error") == "insufficient_data":
                self.skipped_tools.append(tool_name)
        
        return results
    
    def _execute_tool(
        self, 
        tool_name: str, 
        period: Optional[str] = None
    ) -> ExecutionResult:
        """Execute a single tool"""
        start_time = time.time()
        
        try:
            # Check if tool needs period parameter
            if period and tool_name in self.PERIOD_AWARE_TOOLS:
                tool_func = getattr(self.analytics, tool_name, None)
                if tool_func:
                    result = tool_func(period_label=period)
                else:
                    result = self.cache.get_or_execute(tool_name, lambda: getattr(self.analytics, tool_name)())
            else:
                result = self.cache.get_or_execute(tool_name, lambda: getattr(self.analytics, tool_name)())
            
            # Convert pandas types to JSON-safe
            result = self._sanitize_result(result)
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                tool_name=tool_name,
                success=True,
                result=result,
                raw_result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def _sanitize_result(self, result):
        """Convert pandas/DataFrame results to JSON-safe format"""
        import pandas as pd
        import numpy as np
        
        if isinstance(result, pd.DataFrame):
            result = result.copy()
            for col in result.select_dtypes(include=["datetime64[ns]"]):
                result[col] = result[col].astype(str)
            return result.to_dict(orient="records")
        
        elif isinstance(result, pd.Series):
            if pd.api.types.is_datetime64_any_dtype(result.index):
                result.index = result.index.astype(str)
            return result.to_dict()
        
        elif isinstance(result, (np.integer, np.int64)):
            return int(result)
        
        elif isinstance(result, (np.floating, np.float64)):
            return float(result)
        
        return result
    
    def get_failed_tools(self) -> List[str]:
        """Get list of tools that failed during execution"""
        return self.failed_tools
    
    def get_skipped_tools(self) -> List[str]:
        """Get list of tools skipped due to insufficient data"""
        return self.skipped_tools
    
    def get_raw_results(self, execution_results: Dict[str, ExecutionResult]) -> Dict[str, Any]:
        """Extract raw results from execution results"""
        return {
            tool_name: result.raw_result 
            for tool_name, result in execution_results.items() 
            if result.success
        }