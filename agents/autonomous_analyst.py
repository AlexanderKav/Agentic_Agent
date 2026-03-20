import pandas as pd
import numpy as np
from agents.insight_agent import make_json_safe  # import the JSON-safe helper
from agents.monitoring import get_performance_tracker, timer, get_audit_logger, get_cost_tracker
from agents.self_healing import get_healing_agent

class AutonomousAnalyst:
    def __init__(self, planner, analytics, insight_agent, viz_agent):
        self.planner = planner
        self.analytics = analytics
        self.insight_agent = insight_agent
        self.viz_agent = viz_agent
        self.analytics_cache = {}
        
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

    def make_json_safe(obj):
        """Recursively convert all objects to JSON-serializable types."""
        if isinstance(obj, dict):
            return {str(k): make_json_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_json_safe(x) for x in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, (pd.Timestamp, pd.Timedelta)):
            return str(obj)
        elif obj is None:
            return None
        else:
            return obj

    @timer(operation='cached_run')
    def cached_run(self, tool_name):
        """Cache tool results to avoid repeated computation."""
        try:
            if tool_name in self.analytics_cache:
                self.audit_logger.log_action(
                    action_type='cache_hit',
                    agent='autonomous',
                    details={'tool': tool_name},
                    session_id=self.session_id
                )
                return self.analytics_cache[tool_name]
                
            result = self.analytics.run_tool(tool_name)
            self.analytics_cache[tool_name] = result
            
            self.audit_logger.log_action(
                action_type='cache_miss',
                agent='autonomous',
                details={'tool': tool_name},
                session_id=self.session_id
            )
            
            return result
            
        except Exception as e:
            self.healer.analyze_failure(e, {
                'tool': 'cached_run',
                'tool_name': tool_name,
                'cache_keys': list(self.analytics_cache.keys())
            })
            raise

    @timer(operation='autonomous_run')
    def run(self, question=None):
        """
        Run analysis based on a question.
        - Returns: JSON-safe raw_plan, plan, results, raw_insights, insights
        """
        try:
            # Audit log start
            self.audit_logger.log_action(
                action_type='run_start',
                agent='autonomous',
                details={'question': question, 'has_question': question is not None},
                session_id=self.session_id
            )
            
            # Step 1: Determine tools
            if question:
                raw_plan, plan = self.planner.create_plan(question)
                # Track LLM cost for planner
                self.cost_tracker.track_call(
                    model='gpt-4o-mini',
                    input_tokens=len(question.split()),
                    output_tokens=len(str(plan).split()),
                    agent='planner',
                    user='system',
                    session_id=self.session_id
                )
                self.audit_logger.log_action(
                    action_type='plan_created',
                    agent='autonomous',
                    details={
                        'question': question,
                        'plan': plan,
                        'num_tools': len(plan["plan"])
                    },
                    session_id=self.session_id
                )
            else:
                plan = {
                    "plan": [
                        "compute_kpis",
                        "monthly_profit",
                        "monthly_growth",
                        "detect_revenue_spikes",
                        "forecast_revenue",
                        "visualization",
                        "revenue_by_customer",
                        "revenue_by_product",
                        "monthly_revenue_by_customer",
                        "monthly_revenue_by_product"
                    ]
                }
                raw_plan = "Default general analysis plan applied."
                self.audit_logger.log_action(
                    action_type='default_plan_used',
                    agent='autonomous',
                    details={'num_tools': len(plan["plan"])},
                    session_id=self.session_id
                )

            # Step 2: Run tools
            results = {}
            raw_results = {}
            failed_tools = []

            for tool in plan["plan"]:
                if tool == "visualization":
                    continue

                try:
                    tool_result = self.cached_run(tool)
                    raw_results[tool] = tool_result

                    # Convert pandas → JSON-compatible
                    if isinstance(tool_result, pd.DataFrame):
                        tool_result = tool_result.copy()
                        for col in tool_result.select_dtypes(include=["datetime64[ns]"]):
                            tool_result[col] = tool_result[col].astype(str)
                        tool_result = tool_result.to_dict(orient="records")
                    elif isinstance(tool_result, pd.Series):
                        if pd.api.types.is_datetime64_any_dtype(tool_result.index):
                            tool_result.index = tool_result.index.astype(str)
                        tool_result = tool_result.to_dict()

                    # Make JSON-safe
                    results[tool] = make_json_safe(tool_result)
                    
                except Exception as e:
                    failed_tools.append(tool)
                    self.healer.analyze_failure(e, {
                        'tool': tool,
                        'phase': 'tool_execution',
                        'question': question
                    })
                    # Continue with other tools instead of failing completely
                    results[tool] = {"error": str(e), "status": "failed"}

            # Step 3: Generate charts (only if we have successful results)
            if raw_results:
                try:
                    charts = self.viz_agent.generate_from_results(raw_results)
                    if charts:
                        results["charts"] = make_json_safe(charts)
                        self.audit_logger.log_action(
                            action_type='charts_generated',
                            agent='autonomous',
                            details={'num_charts': len(charts)},
                            session_id=self.session_id
                        )
                except Exception as e:
                    self.healer.analyze_failure(e, {'tool': 'visualization'})
                    results["charts"] = {"error": str(e), "status": "failed"}

            # Step 4: Generate insights
            try:
                if question:
                    raw_insights, insights = self.insight_agent.generate_insights(results, question)
                    # Track LLM cost for insight agent - safely calculate token estimates
                    input_text = str(results)
                    output_text = str(insights) if insights else ""
                    
                    self.cost_tracker.track_call(
                        model='gpt-4o-mini',
                        input_tokens=len(input_text.split()) if input_text else 0,
                        output_tokens=len(output_text.split()) if output_text else 0,
                        agent='insight',
                        user='system',
                        session_id=self.session_id
                    )
                else:
                    raw_insights, insights = self.insight_agent.generate_insights(
                        results, question="General business performance overview"
                    )
                    
                self.audit_logger.log_action(
                    action_type='insights_generated',
                    agent='autonomous',
                    details={'insights_length': len(insights) if insights else 0},
                    session_id=self.session_id
                )
                
            except Exception as e:
                self.healer.analyze_failure(e, {'tool': 'insight_generation', 'question': question})
                raw_insights = {"error": str(e)}
                insights = f"Error generating insights: {str(e)}"

            # Audit log completion
            self.audit_logger.log_action(
                action_type='run_complete',
                agent='autonomous',
                details={
                    'tools_used': list(results.keys()),
                    'failed_tools': failed_tools,
                    'has_charts': 'charts' in results,
                    'success': len(failed_tools) < len(plan["plan"])
                },
                session_id=self.session_id
            )
            self.perf_tracker.export_metrics()
            # Ensure JSON-safe return values
            return (
                make_json_safe(raw_plan),
                make_json_safe(plan),
                make_json_safe(results),
                make_json_safe(raw_insights),
                make_json_safe(insights)
            )
            
        except Exception as e:
            # Critical failure - log and let healing agent learn
            context = {
                'tool': 'autonomous_run',
                'question': question,
                'error_type': type(e).__name__
            }
            action = self.healer.analyze_failure(e, context)
            
            self.audit_logger.log_action(
                action_type='run_critical_error',
                agent='autonomous',
                details={
                    'error': str(e),
                    'suggestion': action.suggestion if action else None
                },
                session_id=self.session_id
            )
            
            # Return error response instead of crashing
            error_result = {
                "compute_kpis": {"error": f"Analysis failed: {str(e)}"}
            }
            return (
                make_json_safe("Error in analysis"),
                make_json_safe({"plan": []}),
                make_json_safe(error_result),
                make_json_safe({"error": str(e)}),
                make_json_safe(f"Analysis failed: {str(e)}")
            )