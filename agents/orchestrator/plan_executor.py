"""
Plan Executor - Executes the list of tools and handles errors.
Single responsibility: Run the tools in the plan.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Type-safe execution result for a tool."""
    
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    raw_result: Any = None  # Original result before conversion
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'tool_name': self.tool_name,
            'success': self.success,
            'result': self.result,
            'error': self.error,
            'execution_time': self.execution_time
        }
    
    def has_insufficient_data(self) -> bool:
        """Check if result indicates insufficient data."""
        if isinstance(self.result, dict):
            return self.result.get("error") == "insufficient_data"
        return False


class PlanExecutor:
    """
    Executes a list of tools from a plan.
    Handles period parameters, caching, and error collection.
    
    Features:
    - Period-aware tool execution
    - Caching integration
    - Error handling and collection
    - Result sanitization for JSON
    """
    
    # Tools that understand period parameters
    PERIOD_AWARE_TOOLS: set = {
        'forecast_revenue_by_product',
        'forecast_revenue_with_explanation',
        'forecast_with_confidence',
        'forecast_ensemble',
        'forecast_revenue'
    }
    
    # Tools that require sufficient data
    DATA_DEPENDENT_TOOLS: set = {
        'forecast_revenue_by_product',
        'forecast_revenue_with_explanation',
        'forecast_with_confidence',
        'forecast_ensemble',
        'forecast_revenue',
        'detect_seasonality'
    }
    
    def __init__(self, analytics_agent, cache_manager):
        """
        Initialize the Plan Executor.
        
        Args:
            analytics_agent: The AnalyticsAgent instance
            cache_manager: CacheManager instance for storing results
        """
        self.analytics = analytics_agent
        self.cache = cache_manager
        self.failed_tools: List[str] = []
        self.skipped_tools: List[str] = []
        self._execution_order: List[str] = []
    
    def execute_plan(
        self, 
        plan: List[str], 
        period: Optional[str] = None,
        skip_visualization: bool = True
    ) -> Dict[str, ExecutionResult]:
        """
        Execute all tools in the plan.
        
        Args:
            plan: List of tool names to execute
            period: Optional time period (e.g., "Q1 2025")
            skip_visualization: If True, skip visualization tool
            
        Returns:
            Dictionary mapping tool names to ExecutionResult objects
        """
        results: Dict[str, ExecutionResult] = {}
        self.failed_tools = []
        self.skipped_tools = []
        self._execution_order = []
        
        logger.info(f"Executing plan with {len(plan)} tools: {plan}")
        
        for tool_name in plan:
            # Skip visualization if requested (handled separately)
            if skip_visualization and tool_name == "visualization":
                continue
            
            self._execution_order.append(tool_name)
            
            # Check data requirements before execution
            if self._should_skip_tool(tool_name):
                self.skipped_tools.append(tool_name)
                logger.info(f"Skipping {tool_name} due to data requirements")
                continue
            
            result = self._execute_tool(tool_name, period)
            results[tool_name] = result
            
            if not result.success:
                self.failed_tools.append(tool_name)
                logger.warning(f"Tool {tool_name} failed: {result.error}")
            
            if result.has_insufficient_data():
                self.skipped_tools.append(tool_name)
                logger.info(f"Tool {tool_name} skipped due to insufficient data")
        
        # Log execution summary
        self._log_execution_summary()
        
        return results
    
    def _should_skip_tool(self, tool_name: str) -> bool:
        """
        Check if a tool should be skipped based on data availability.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if the tool should be skipped
        """
        if tool_name not in self.DATA_DEPENDENT_TOOLS:
            return False
        
        # Check data availability using analytics agent
        try:
            if tool_name.startswith('forecast'):
                # Check if we have enough data for forecasting
                monthly = getattr(self.analytics, 'monthly_revenue', lambda: pd.Series())()
                has_enough_data = len(monthly) >= 12
                
                if not has_enough_data:
                    logger.debug(f"Insufficient data for {tool_name}: only {len(monthly)} months available")
                return not has_enough_data
                
            elif tool_name == 'detect_seasonality':
                monthly = getattr(self.analytics, 'monthly_revenue', lambda: pd.Series())()
                has_enough_data = len(monthly) >= 24
                
                if not has_enough_data:
                    logger.debug(f"Insufficient data for seasonality: only {len(monthly)} months available")
                return not has_enough_data
                
        except Exception as e:
            logger.warning(f"Error checking data requirements for {tool_name}: {e}")
        
        return False
    
    def _execute_tool(
        self, 
        tool_name: str, 
        period: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute a single tool.
        
        Args:
            tool_name: Name of the tool to execute
            period: Optional period parameter for forecast tools
            
        Returns:
            ExecutionResult object
        """
        start_time = time.time()
        
        try:
            # Get the tool function
            tool_func = self._get_tool_function(tool_name)
            if tool_func is None:
                raise AttributeError(f"Tool '{tool_name}' not found in analytics agent")
            
            # Execute with or without period parameter
            if period and tool_name in self.PERIOD_AWARE_TOOLS:
                logger.debug(f"Executing {tool_name} with period={period}")
                result = self.cache.get_or_execute(
                    tool_name,
                    lambda: tool_func(period_label=period),
                    params={'period': period}
                )
            else:
                logger.debug(f"Executing {tool_name}")
                result = self.cache.get_or_execute(
                    tool_name,
                    lambda: tool_func()
                )
            
            # Sanitize result for JSON
            sanitized_result = self._sanitize_result(result)
            
            execution_time = time.time() - start_time
            logger.debug(f"Tool {tool_name} completed in {execution_time:.2f}s")
            
            return ExecutionResult(
                tool_name=tool_name,
                success=True,
                result=sanitized_result,
                raw_result=result,
                execution_time=execution_time
            )
            
        except AttributeError as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool {tool_name} not found: {e}")
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)
            return ExecutionResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def _get_tool_function(self, tool_name: str) -> Optional[Callable]:
        """Get the tool function from analytics agent."""
        # Handle special case for forecast methods
        if tool_name == 'forecast_revenue_by_product':
            return getattr(self.analytics, 'forecast_revenue_by_product', None)
        elif tool_name == 'forecast_revenue_with_explanation':
            return getattr(self.analytics, 'forecast_revenue_with_explanation', None)
        elif tool_name == 'forecast_with_confidence':
            return getattr(self.analytics, 'forecast_with_confidence', None)
        elif tool_name == 'forecast_ensemble':
            return getattr(self.analytics, 'forecast_ensemble', None)
        elif tool_name == 'detect_seasonality':
            return getattr(self.analytics, 'detect_seasonality', None)
        
        return getattr(self.analytics, tool_name, None)
    
    def _sanitize_result(self, result: Any) -> Any:
        """
        Convert pandas/DataFrame results to JSON-safe format.
        
        Args:
            result: Raw result from analytics tool
            
        Returns:
            JSON-sanitized result
        """
        if result is None:
            return None
            
        if isinstance(result, pd.DataFrame):
            result = result.copy()
            # Convert datetime columns to strings
            for col in result.select_dtypes(include=['datetime64[ns]', 'datetime64']):
                result[col] = result[col].astype(str)
            # Convert to records for JSON serialization
            return result.to_dict(orient='records')
        
        elif isinstance(result, pd.Series):
            # Convert datetime index to strings
            if pd.api.types.is_datetime64_any_dtype(result.index):
                result.index = result.index.astype(str)
            return result.to_dict()
        
        elif isinstance(result, (np.integer, np.int64, np.int32)):
            return int(result)
        
        elif isinstance(result, (np.floating, np.float64, np.float32)):
            if np.isnan(result) or np.isinf(result):
                return None
            return float(result)
        
        elif isinstance(result, np.bool_):
            return bool(result)
        
        elif isinstance(result, pd.Timestamp):
            return result.isoformat()
        
        elif isinstance(result, dict):
            return {k: self._sanitize_result(v) for k, v in result.items()}
        
        elif isinstance(result, (list, tuple)):
            return [self._sanitize_result(item) for item in result]
        
        return result
    
    def _log_execution_summary(self) -> None:
        """Log a summary of the execution."""
        total = len(self._execution_order)
        successful = total - len(self.failed_tools)
        skipped = len(self.skipped_tools)
        
        logger.info(
            f"Plan execution complete: {successful}/{total} successful, "
            f"{skipped} skipped, {len(self.failed_tools)} failed"
        )
        
        if self.skipped_tools:
            logger.info(f"Skipped tools: {self.skipped_tools}")
        if self.failed_tools:
            logger.warning(f"Failed tools: {self.failed_tools}")
    
    def get_failed_tools(self) -> List[str]:
        """Get list of tools that failed during execution."""
        return self.failed_tools.copy()
    
    def get_skipped_tools(self) -> List[str]:
        """Get list of tools skipped due to insufficient data."""
        return self.skipped_tools.copy()
    
    def get_execution_order(self) -> List[str]:
        """Get the order in which tools were executed."""
        return self._execution_order.copy()
    
    def get_raw_results(self, execution_results: Dict[str, ExecutionResult]) -> Dict[str, Any]:
        """
        Extract raw results from execution results.
        
        Args:
            execution_results: Dictionary of ExecutionResult objects
            
        Returns:
            Dictionary of raw results for successful executions
        """
        return {
            tool_name: result.raw_result 
            for tool_name, result in execution_results.items() 
            if result.success
        }
    
    def get_successful_results(self, execution_results: Dict[str, ExecutionResult]) -> Dict[str, Any]:
        """
        Extract sanitized results from successful executions.
        
        Args:
            execution_results: Dictionary of ExecutionResult objects
            
        Returns:
            Dictionary of sanitized results for successful executions
        """
        return {
            tool_name: result.result 
            for tool_name, result in execution_results.items() 
            if result.success
        }
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the last execution.
        
        Returns:
            Dictionary with execution statistics
        """
        return {
            'total_tools_executed': len(self._execution_order),
            'successful_tools': len(self._execution_order) - len(self.failed_tools),
            'failed_tools': self.failed_tools.copy(),
            'skipped_tools': self.skipped_tools.copy(),
            'failed_count': len(self.failed_tools),
            'skipped_count': len(self.skipped_tools),
            'execution_order': self._execution_order.copy()
        }
    
    def clear_state(self) -> None:
        """Clear the execution state."""
        self.failed_tools = []
        self.skipped_tools = []
        self._execution_order = []


__all__ = ['PlanExecutor', 'ExecutionResult']