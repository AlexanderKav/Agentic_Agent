"""
Autonomous Analyst - Orchestrates the analysis pipeline.
Now refactored to delegate responsibilities to focused components.
"""

import time
import traceback
from typing import Any, Dict, List, Optional, Tuple

from agents.insight_agent import make_json_safe
from agents.monitoring import get_audit_logger, get_cost_tracker, get_performance_tracker, timer
from agents.orchestrator import CacheManager, ChartGenerator, DataPreparer, PlanExecutor, QuestionClassifier
from agents.self_healing import get_healing_agent


class AutonomousAnalyst:
    """
    Orchestrates the entire analysis pipeline.
    Delegates responsibilities to specialized components.
    
    This class is the main entry point for the analysis system.
    It coordinates:
    - Question classification and period extraction
    - Planning (via PlannerAgent)
    - Plan execution (via PlanExecutor)
    - Chart generation (via VisualizationAgent)
    - Insight generation (via InsightAgent)
    """
    
    def __init__(self, planner, analytics, insight_agent, viz_agent):
        """
        Initialize the Autonomous Analyst.
        
        Args:
            planner: PlannerAgent instance for creating execution plans
            analytics: AnalyticsAgent instance for data analysis
            insight_agent: InsightAgent instance for generating insights
            viz_agent: VisualizationAgent instance for creating charts
        """
        self.planner = planner
        self.analytics = analytics
        self.insight_agent = insight_agent
        self.viz_agent = viz_agent
        
        # Initialize orchestrator components
        self.question_classifier = QuestionClassifier()
        self.cache_manager = CacheManager()
        self.plan_executor = PlanExecutor(analytics, self.cache_manager)
        self.data_preparer = DataPreparer(analytics)
        self.chart_generator = ChartGenerator(viz_agent)
        
        # Initialize monitoring
        self.perf_tracker = get_performance_tracker()
        self.audit_logger = get_audit_logger()
        self.cost_tracker = get_cost_tracker()
        self.healer = get_healing_agent()
        self.session_id = id(self)
        
        # Audit log initialization
        self.audit_logger.log_action(
            action_type='autonomous_init',
            agent='autonomous',
            details={
                'has_planner': planner is not None,
                'has_analytics': analytics is not None,
                'has_insight': insight_agent is not None,
                'has_viz': viz_agent is not None
            },
            session_id=self.session_id
        )
    
    @timer(operation='autonomous_run')
    def run(self, question: Optional[str] = None) -> Tuple[Dict[str, Any], List[str], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """
        Run analysis based on a question.
        
        Args:
            question: User's question (None for general overview)
            
        Returns:
            Tuple of (raw_plan, plan, results, raw_insights, insights)
        """
        start_time = time.time()
        
        try:
            # Audit log start
            self._log_run_start(question)
            
            # Step 1: Classify question and extract period
            question_type, period = self._classify_question(question)
            
            # Step 2: Create plan
            raw_plan, plan_data, plan_period = self._create_plan(question, period)
            plan = self._parse_plan(plan_data)
            
            # Step 3: Execute plan
            execution_results = self.plan_executor.execute_plan(plan, plan_period)
            
            # Step 4: Extract raw results for charts
            raw_results = self.plan_executor.get_raw_results(execution_results)
            
            # Step 5: Generate charts
            charts = self.chart_generator.generate_charts(raw_results)
            
            # Step 6: Prepare combined data for insights
            combined_data = self._prepare_combined_data(execution_results, charts)
            
            # Step 7: Filter data based on question type
            insight_data = self._filter_data_by_type(combined_data, question_type)
            insight_data['question_type'] = question_type
            
            # Step 8: Generate insights
            raw_insights, insights = self._generate_insights(insight_data, question, question_type)
            
            # Step 9: Build results dictionary
            results = self._build_results_dict(
                execution_results, 
                charts, 
                combined_data,
                self.plan_executor.get_skipped_tools()
            )
            
            # Log completion
            self._log_run_complete(execution_results, plan, charts)
            
            self.perf_tracker.export_metrics()
            
            # Return values
            return (
                make_json_safe(raw_plan),
                make_json_safe(plan),
                make_json_safe(results),
                make_json_safe(raw_insights),
                make_json_safe(insights)
            )
            
        except Exception as e:
            return self._handle_critical_error(e, question)
    
    def _log_run_start(self, question: Optional[str]) -> None:
        """Log the start of a run."""
        self.audit_logger.log_action(
            action_type='run_start',
            agent='autonomous',
            details={'question': question, 'has_question': question is not None},
            session_id=self.session_id
        )
    
    def _classify_question(self, question: Optional[str]) -> Tuple[str, Optional[str]]:
        """Classify question and extract period."""
        question_type = self.question_classifier.classify(question)
        period = self.question_classifier.extract_period(question)
        
        print(f"🔍 Question type: {question_type}")
        if period:
            print(f"📅 Period detected: {period}")
        
        return question_type, period
    
    def _create_plan(self, question: Optional[str], period: Optional[str]) -> Tuple[str, Dict[str, Any], Optional[str]]:
        """
        Create an execution plan.
        
        Returns:
            Tuple of (raw_plan, plan_data, plan_period)
        """
        if question:
            raw_plan, plan_data = self.planner.create_plan(question)
            plan = self._parse_plan(plan_data)
            plan_period = period or self._extract_period_from_plan(plan_data)
            
            # Track planner cost
            self.cost_tracker.track_call(
                model='gpt-4o-mini',
                input_tokens=len(question.split()),
                output_tokens=len(str(plan).split()),
                agent='planner',
                user='system',
                session_id=self.session_id
            )
        else:
            # Default overview plan
            raw_plan = "Default general analysis plan applied."
            plan = self.question_classifier.get_recommended_tools('overview')
            plan_period = None
        
        print(f"📋 Plan: {plan}")
        return raw_plan, plan_data if question else {"plan": plan}, plan_period
    
    def _parse_plan(self, plan_data: Any) -> List[str]:
        """Parse plan from planner output."""
        if isinstance(plan_data, dict):
            return plan_data.get('plan', [])
        if isinstance(plan_data, list):
            return plan_data
        return []
    
    def _extract_period_from_plan(self, plan_data: Any) -> Optional[str]:
        """Extract period from plan data if present."""
        if isinstance(plan_data, dict):
            return plan_data.get('period')
        return None
    
    def _prepare_combined_data(self, execution_results: Dict, charts: Dict) -> Dict:
        """Prepare combined data for insights."""
        combined_data = self.data_preparer.prepare_for_insights(execution_results)
        
        # Add charts to results
        if charts:
            combined_data['charts'] = charts
        
        # Add skipped tools note
        skipped_tools = self.plan_executor.get_skipped_tools()
        if skipped_tools:
            combined_data['_skipped_tools_note'] = {
                "message": f"The following tools were skipped due to insufficient data: {', '.join(skipped_tools)}",
                "skipped_tools": skipped_tools
            }
        
        return combined_data
    
    def _filter_data_by_type(self, data: Dict[str, Any], question_type: str) -> Dict[str, Any]:
        """Filter data based on question type."""
        filtered = {}
        
        # Define filter patterns for each question type
        filters = {
            'forecast': self._get_forecast_filters(),
            'risk': self._get_risk_filters(),
            'performance': self._get_performance_filters(),
            'revenue_analysis': self._get_revenue_analysis_filters(),
        }
        
        if question_type in filters:
            for key in filters[question_type]:
                if key in data:
                    filtered[key] = data[key]
        else:
            # General/overview: include everything
            filtered = data
        
        return filtered
    
    def _get_forecast_filters(self) -> List[str]:
        """Get filter keys for forecast questions."""
        return [
            'product_monthly_trends', 'monthly_growth', 'monthly_profit',
            'revenue_by_product', 'total_revenue', 'profit_margin',
            'product_forecast', 'forecast_summary', 'overall_forecast',
            'confidence_forecast', 'top_product_forecast', 'top_product_forecast_value',
            'positive_growth_months', 'negative_growth_months', 'avg_growth',
            'latest_growth', 'latest_growth_month'
        ]
    
    def _get_risk_filters(self) -> List[str]:
        """Get filter keys for risk questions."""
        return [
            'payment_status_counts', 'revenue_at_risk', 'missing_customers',
            'failed_payments_count', 'pending_payments_count', 'anomalies',
            'product_monthly_trends'
        ]
    
    def _get_performance_filters(self) -> List[str]:
        """Get filter keys for performance questions."""
        return [
            'total_revenue', 'total_profit', 'profit_margin', 'product_monthly_trends',
            'top_customers', 'revenue_by_region', 'monthly_growth', 'revenue_by_product'
        ]
    
    def _get_revenue_analysis_filters(self) -> List[str]:
        """Get filter keys for revenue analysis questions."""
        return [
            'total_revenue', 'product_monthly_trends', 'revenue_by_product',
            'revenue_by_region', 'top_customers', 'monthly_growth',
            'monthly_revenue_by_product_raw', 'revenue_by_product_raw'
        ]
    
    def _generate_insights(
        self,
        insight_data: Dict[str, Any],
        question: Optional[str],
        question_type: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Generate insights using the insight agent."""
        try:
            if question:
                return self.insight_agent.generate_insights(insight_data, question)
            else:
                return self.insight_agent.generate_insights(
                    insight_data, question="General business performance overview"
                )
        except Exception as e:
            print(f"❌ Error generating insights: {e}")
            return {"error": str(e)}, {
                "answer": f"Error generating insights: {str(e)}",
                "human_readable_summary": "An error occurred during analysis."
            }
    
    def _build_results_dict(
        self,
        execution_results: Dict,
        charts: Dict,
        combined_data: Dict,
        skipped_tools: List[str]
    ) -> Dict[str, Any]:
        """Build the final results dictionary."""
        results = {}
        
        # Add successful results
        for tool_name, result in execution_results.items():
            if hasattr(result, 'success') and result.success:
                results[tool_name] = result.result
            elif isinstance(result, dict) and result.get('success', True):
                results[tool_name] = result
        
        # Add charts
        if charts:
            results['charts'] = charts
        
        # Add note about skipped tools
        if skipped_tools:
            results['_skipped_tools_note'] = {
                "message": f"The following tools were skipped due to insufficient data: {', '.join(skipped_tools)}",
                "skipped_tools": skipped_tools
            }
        
        return results
    
    def _log_run_complete(self, execution_results: Dict, plan: List[str], charts: Dict) -> None:
        """Log the completion of a run."""
        skipped_tools = self.plan_executor.get_skipped_tools()
        failed_tools = self.plan_executor.get_failed_tools()
        
        self.audit_logger.log_action(
            action_type='run_complete',
            agent='autonomous',
            details={
                'tools_used': list(execution_results.keys()),
                'failed_tools': failed_tools,
                'skipped_tools': skipped_tools,
                'has_charts': bool(charts),
                'success': len(failed_tools) < len(plan)
            },
            session_id=self.session_id
        )
    
    def _handle_critical_error(self, error: Exception, question: Optional[str]) -> Tuple:
        """Handle critical errors and return a safe fallback response."""
        traceback.print_exc()
        
        self.audit_logger.log_action(
            action_type='run_critical_error',
            agent='autonomous',
            details={'error': str(error), 'question': question},
            session_id=self.session_id
        )
        
        error_result = {"compute_kpis": {"error": f"Analysis failed: {str(error)}"}}
        return (
            make_json_safe("Error in analysis"),
            make_json_safe({"plan": []}),
            make_json_safe(error_result),
            make_json_safe({"error": str(error)}),
            make_json_safe(f"Analysis failed: {str(error)}")
        )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the analyst.
        
        Returns:
            Dictionary with status information
        """
        return {
            'has_planner': self.planner is not None,
            'has_analytics': self.analytics is not None,
            'has_insight': self.insight_agent is not None,
            'has_viz': self.viz_agent is not None,
            'session_id': self.session_id,
            'failed_tools': self.plan_executor.get_failed_tools(),
            'skipped_tools': self.plan_executor.get_skipped_tools()
        }


__all__ = ['AutonomousAnalyst']