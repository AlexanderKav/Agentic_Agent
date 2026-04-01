# agents/autonomous_analyst.py
"""
Autonomous Analyst - Orchestrates the analysis pipeline.
Now refactored to delegate responsibilities to focused components.
"""

import time
from typing import Dict, Any, Tuple, Optional, List

from agents.orchestrator import (
    QuestionClassifier,
    CacheManager,
    PlanExecutor,
    DataPreparer,
    ChartGenerator
)
from agents.monitoring import get_performance_tracker, timer, get_audit_logger, get_cost_tracker
from agents.self_healing import get_healing_agent
from agents.insight_agent import make_json_safe


class AutonomousAnalyst:
    """
    Orchestrates the entire analysis pipeline.
    Delegates responsibilities to specialized components.
    """
    
    def __init__(self, planner, analytics, insight_agent, viz_agent):
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
    def run(self, question: Optional[str] = None) -> Tuple[Dict, List, Dict, Dict, Dict]:
        """
        Run analysis based on a question.
        
        Returns:
            Tuple of (raw_plan, plan, results, raw_insights, insights)
        """
        start_time = time.time()
        
        try:
            # Audit log start
            self.audit_logger.log_action(
                action_type='run_start',
                agent='autonomous',
                details={'question': question, 'has_question': question is not None},
                session_id=self.session_id
            )
            
            # Step 1: Classify question and extract period
            question_type = self.question_classifier.classify(question)
            period = self.question_classifier.extract_period(question)
            
            print(f"🔍 Question type: {question_type}")
            if period:
                print(f"📅 Period detected: {period}")
            
            # Step 2: Create plan
            if question:
                raw_plan, plan_data = self.planner.create_plan(question)
                plan = self._parse_plan(plan_data)
                plan_period = period or self._extract_period_from_plan(plan_data)
            else:
                # Default overview plan
                raw_plan = "Default general analysis plan applied."
                plan = self.question_classifier.get_recommended_tools('overview')
                plan_period = None
            
            print(f"📋 Plan: {plan}")
            
            # Track planner cost
            if question:
                self.cost_tracker.track_call(
                    model='gpt-4o-mini',
                    input_tokens=len(question.split()),
                    output_tokens=len(str(plan).split()),
                    agent='planner',
                    user='system',
                    session_id=self.session_id
                )
            
            # Step 3: Execute plan
            execution_results = self.plan_executor.execute_plan(plan, plan_period)
            
            # Step 4: Extract raw results for charts
            raw_results = self.plan_executor.get_raw_results(execution_results)
            
            # Step 5: Generate charts
            charts = self.chart_generator.generate_charts(raw_results)
            
            # Step 6: Prepare combined data for insights
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
                skipped_tools
            )
            
            # Audit log completion
            self.audit_logger.log_action(
                action_type='run_complete',
                agent='autonomous',
                details={
                    'tools_used': list(execution_results.keys()),
                    'failed_tools': self.plan_executor.get_failed_tools(),
                    'skipped_tools': skipped_tools,
                    'has_charts': bool(charts),
                    'success': len(self.plan_executor.get_failed_tools()) < len(plan)
                },
                session_id=self.session_id
            )
            
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
            # Critical failure
            import traceback
            traceback.print_exc()
            
            self.audit_logger.log_action(
                action_type='run_critical_error',
                agent='autonomous',
                details={'error': str(e), 'question': question},
                session_id=self.session_id
            )
            
            error_result = {"compute_kpis": {"error": f"Analysis failed: {str(e)}"}}
            return (
                make_json_safe("Error in analysis"),
                make_json_safe({"plan": []}),
                make_json_safe(error_result),
                make_json_safe({"error": str(e)}),
                make_json_safe(f"Analysis failed: {str(e)}")
            )
    
    def _parse_plan(self, plan_data) -> List[str]:
        """Parse plan from planner output"""
        if isinstance(plan_data, dict):
            return plan_data.get('plan', [])
        if isinstance(plan_data, list):
            return plan_data
        return []
    
    def _extract_period_from_plan(self, plan_data) -> Optional[str]:
        """Extract period from plan data if present"""
        if isinstance(plan_data, dict):
            return plan_data.get('period')
        return None
    
    def _filter_data_by_type(self, data: Dict, question_type: str) -> Dict:
        """Filter data based on question type"""
        filtered = {}
        
        if question_type == 'forecast':
            # Include ALL forecast-related data
            filtered['product_monthly_trends'] = data.get('product_monthly_trends', {})
            filtered['monthly_growth'] = data.get('monthly_growth', {})
            filtered['monthly_profit'] = data.get('monthly_profit', {})
            filtered['revenue_by_product'] = data.get('revenue_by_product', {})
            filtered['total_revenue'] = data.get('total_revenue', 0)
            filtered['profit_margin'] = data.get('profit_margin', 0)
            
            # CRITICAL: Include forecast data
            filtered['product_forecast'] = data.get('product_forecast', {})
            filtered['forecast_summary'] = data.get('forecast_summary', {})
            filtered['overall_forecast'] = data.get('overall_forecast', {})
            filtered['confidence_forecast'] = data.get('confidence_forecast', {})
            filtered['top_product_forecast'] = data.get('top_product_forecast', '')
            filtered['top_product_forecast_value'] = data.get('top_product_forecast_value', 0)
            
            # Include growth metrics
            if data.get('monthly_growth'):
                filtered['positive_growth_months'] = data.get('positive_growth_months', 0)
                filtered['negative_growth_months'] = data.get('negative_growth_months', 0)
                filtered['avg_growth'] = data.get('avg_growth', 0)
                filtered['latest_growth'] = data.get('latest_growth', 0)
                filtered['latest_growth_month'] = data.get('latest_growth_month', '')
        
        elif question_type == 'risk':
            filtered['payment_status_counts'] = data.get('payment_status_counts', {})
            filtered['revenue_at_risk'] = data.get('revenue_at_risk', 0)
            filtered['missing_customers'] = data.get('missing_customers', 0)
            filtered['failed_payments_count'] = data.get('failed_payments_count', 0)
            filtered['pending_payments_count'] = data.get('pending_payments_count', 0)
            filtered['anomalies'] = data.get('anomalies', {})
            filtered['product_monthly_trends'] = data.get('product_monthly_trends', {})
        
        elif question_type == 'performance':
            filtered['total_revenue'] = data.get('total_revenue', 0)
            filtered['total_profit'] = data.get('total_profit', 0)
            filtered['profit_margin'] = data.get('profit_margin', 0)
            filtered['product_monthly_trends'] = data.get('product_monthly_trends', {})
            filtered['top_customers'] = data.get('top_customers', {})
            filtered['revenue_by_region'] = data.get('revenue_by_region', {})
            filtered['monthly_growth'] = data.get('monthly_growth', {})
            filtered['revenue_by_product'] = data.get('revenue_by_product', {})
        
        elif question_type == 'revenue_analysis':
            filtered['total_revenue'] = data.get('total_revenue', 0)
            filtered['product_monthly_trends'] = data.get('product_monthly_trends', {})
            filtered['revenue_by_product'] = data.get('revenue_by_product', {})
            filtered['revenue_by_region'] = data.get('revenue_by_region', {})
            filtered['top_customers'] = data.get('top_customers', {})
            filtered['monthly_growth'] = data.get('monthly_growth', {})
            filtered['monthly_revenue_by_product_raw'] = data.get('monthly_revenue_by_product_raw', {})
            filtered['revenue_by_product_raw'] = data.get('revenue_by_product_raw', {})
        
        else:
            # General/overview: include everything
            filtered = data
        
        return filtered
    
    def _generate_insights(self, insight_data: Dict, question: Optional[str], question_type: str) -> Tuple[Dict, Dict]:
        """Generate insights using the insight agent"""
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
    
    def _build_results_dict(self, execution_results: Dict, charts: Dict, combined_data: Dict, skipped_tools: List) -> Dict:
        """Build the final results dictionary"""
        results = {}
        
        # Add successful results
        for tool_name, result in execution_results.items():
            if result.success:
                results[tool_name] = result.result
        
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