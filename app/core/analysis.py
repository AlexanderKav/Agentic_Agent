# app/core/analysis.py
import re
import time
from typing import Any

import pandas as pd

from agents.analytics_agent import AnalyticsAgent
from agents.autonomous_analyst import AutonomousAnalyst
from agents.insight_agent import InsightAgent
from agents.planner_agent import PlannerAgent
from agents.schema_mapper import SchemaMapper
from agents.visualization_agent import VisualizationAgent
from connectors.data_loader import DataLoader

# Constants for validation
MAX_ROWS = 100000
MINIMUM_REQUIRED_COLUMNS = ['date', 'revenue']
MAX_STRING_LENGTH = 10000

class AnalysisOrchestrator:
    def __init__(self, data_loader: DataLoader | None = None, user_id: int | None = None):
        self.data_loader = data_loader or DataLoader()
        self.planner = PlannerAgent()
        # Pass user_id to InsightAgent for A/B testing
        self.insight = InsightAgent(user_id=user_id, prompt_version=None)
        self.viz = VisualizationAgent()


    def validate_dataframe(self, df: pd.DataFrame) -> bool:
        """Validate dataframe has minimum required columns and is safe"""

        # Check for minimum columns
        missing = [col for col in MINIMUM_REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}. Your data must contain at least 'date' and 'revenue' columns.")

        # Check row limit
        if len(df) > MAX_ROWS:
            raise ValueError(f"Too many rows. Maximum allowed is {MAX_ROWS:,} rows.")

        # Check for obviously malicious data
        for col in df.columns:
            if df[col].dtype == 'object':  # String columns
                # Check for extremely long strings (potential injection)
                max_len = df[col].astype(str).str.len().max()
                if max_len > MAX_STRING_LENGTH:
                    raise ValueError(
                        f"Column '{col}' contains suspiciously long strings "
                        f"(max length: {max_len:,} chars). Limit is {MAX_STRING_LENGTH:,} chars."
                    )

        return True

    def _check_question_relevance(self, question: str, df: pd.DataFrame) -> tuple[bool, str]:
        """Check if question is relevant to the business data"""

        if not question or not question.strip():
            return True, "No question provided (using default overview)"

        # Get data columns for context
        columns = [col.lower() for col in df.columns]
        question_lower = question.lower()

        # Business keywords - comprehensive list including performance and risks
        business_keywords = [
            # Revenue/Financial
            'revenue', 'sales', 'profit', 'income', 'earnings', 'turnover',
            'cost', 'expense', 'margin', 'price', 'value', 'amount',
            'total', 'sum', 'average', 'mean', 'median', 'kpi', 'metric',

            # Customer related
            'customer', 'client', 'buyer', 'account', 'user', 'subscription',
            'retention', 'churn', 'acquisition', 'lifetime', 'ltv',

            # Product related
            'product', 'item', 'service', 'plan', 'sku', 'category',
            'inventory', 'stock', 'demand', 'popular', 'best', 'top',
            'worst', 'ranking', 'rank',

            # Trends/Time
            'trend', 'growth', 'decline', 'increase', 'decrease', 'change',
            'month', 'year', 'quarter', 'weekly', 'daily', 'time', 'period',
            'seasonal', 'forecast', 'predict', 'future',

            # Regional
            'region', 'market', 'geo', 'location', 'country', 'city',
            'area', 'territory', 'zone',

            # Performance (CRITICAL for your question)
            'performance', 'performing', 'efficiency', 'conversion', 'rate', 'ratio',
            'percentage', 'share', 'market share', 'health', 'healthy',

            # Risks (CRITICAL for your question)
            'risk', 'risks', 'danger', 'threat', 'issue', 'problem', 'concern',
            'warning', 'alert', 'vulnerability', 'exposure',

            # Status
            'paid', 'pending', 'overdue', 'refunded', 'status', 'payment',
            'order', 'transaction', 'invoice', 'subscription', 'failed',

            # Business health
            'well', 'good', 'bad', 'improve', 'improving', 'declining',
            'stable', 'volatile', 'outlook', 'overview', 'summary', 'dashboard'
        ]

        # Check if any business keywords match
        matches = [kw for kw in business_keywords if kw in question_lower]

        # Check against column names (more specific matching)
        column_matches = []
        for col in columns:
            col_words = col.split('_')
            for word in col_words:
                if word in question_lower and len(word) > 2:
                    column_matches.append(word)
        column_matches = list(set(column_matches))

        # Check for column name matches (strong signal)
        if column_matches:
            print(f"✅ Column matches: {column_matches}")
            return True, f"Question relates to data column(s): {', '.join(column_matches[:3])}"

        # Check for business keyword matches
        if matches:
            print(f"✅ Keyword matches: {matches[:5]}")
            return True, f"Question is relevant (matched: {', '.join(matches[:3])})"

        # Check for business phrase patterns
        business_phrases = [
            r'how\s+is\s+the\s+business',
            r'how\s+are\s+we\s+doing',
            r'business\s+performance',
            r'company\s+performance',
            r'overall\s+performance',
            r'what\'s\s+the\s+state\s+of\s+the\s+business',
            r'give\s+me\s+an\s+overview',
            r'show\s+me\s+the\s+business\s+health',
            r'is\s+the\s+business\s+doing\s+well',
            r'are\s+there\s+any\s+risks',
            r'what\s+are\s+the\s+risks',
            r'business\s+risks',
            r'what\s+should\s+we\s+be\s+concerned\s+about',
            r'how\s+are\s+things\s+looking',
            r'business\s+health',
            r'company\s+health',
            r'performance\s+review'
        ]

        for pattern in business_phrases:
            if re.search(pattern, question_lower):
                print(f"✅ Business phrase matched: {pattern}")
                return True, "Question is relevant (business performance inquiry)"

        # Check for obvious off-topic patterns
        off_topic_patterns = [
            r'\bhappiest\b', r'\bsaddest\b', r'\bweather\b', r'\bclimate\b',
            r'\bpolitics\b', r'\belection\b', r'\bpresident\b', r'\bprime\s+minister\b',
            r'\bfamous\b', r'\bcelebrity\b', r'\bactor\b', r'\bactress\b',
            r'\bsports\b', r'\bfootball\b', r'\bsoccer\b', r'\bbasketball\b',
            r'\bmovie\b', r'\bfilm\b', r'\bmusic\b', r'\bsong\b',
            r'\bworld\s+record\b', r'\bguinness\b',
            r'\bwho\s+is\b', r'\bwhat\s+is\b.*\?$', r'\bmeaning\s+of\b',
            r'\bhistory\b', r'\binventor\b', r'\bdiscovery\b',
            r'\brecipe\b', r'\bcooking\b', r'\bfood\b',
            r'\btravel\b', r'\bvacation\b', r'\bholiday\b',
            r'\bhow\s+to\s+make\b', r'\bhow\s+to\s+build\b'
        ]

        for pattern in off_topic_patterns:
            if re.search(pattern, question_lower):
                print(f"❌ Off-topic pattern matched: {pattern}")
                return False, "This question appears to be off-topic for business data analysis."

        # If question contains business-related terms, be permissive
        business_terms = ['business', 'company', 'performance', 'risk', 'overview', 'summary']
        if any(term in question_lower for term in business_terms):
            print("✅ Question contains business terms, marking as relevant")
            return True, "Question is relevant (business inquiry)"

        # Default - if we have data columns and the question isn't obviously off-topic, assume it's relevant
        if columns:
            print("⚠️ No clear match but data exists. Defaulting to relevant.")
            return True, "Question is potentially relevant to business data."

        return False, "Question doesn't seem related to your business data. Try asking about revenue, customers, products, or trends."

    async def analyze_dataframe(self, df: pd.DataFrame, question: str) -> tuple[dict[str, Any], float]:
        """
        Analyze a pandas DataFrame directly (used by both file upload and database)
        """
        start_time = time.time()

        try:
            # 🔐 VALIDATE THE DATAFRAME FIRST
            self.validate_dataframe(df)

            # Check if question is relevant (if provided)
            if question and question.strip():
                # Use the class method instead of inner function
                is_relevant, relevance_message = self._check_question_relevance(question, df)
                print(f"🔍 Relevance check: {relevance_message}")

                if not is_relevant:
                    execution_time = time.time() - start_time
                    # Generate helpful suggestions based on data columns
                    columns = list(df.columns)

                    suggested_questions = [
                        "What are our top products by revenue?",
                        "Show me revenue trends over time",
                        "Who are our top customers?",
                        "What's our profit margin?",
                        "Which region has the highest sales?",
                        "How has revenue grown month-over-month?"
                    ]

                    return {
                        "success": False,
                        "error": "irrelevant_question",
                        "insights": f"❓ {relevance_message}\n\n" +
                                    f"I'm designed to analyze business data. Your dataset contains columns like: {', '.join(columns[:8])}{'...' if len(columns) > 8 else ''}\n\n" +
                                    "Here are some questions you could ask:\n" +
                                    "\n".join([f"  • {q}" for q in suggested_questions[:5]]),
                        "results": {},
                        "plan": {"plan": []},
                        "warnings": [relevance_message],
                        "data_summary": {
                            "rows": len(df),
                            "columns": list(df.columns)
                        },
                        "execution_time": execution_time,
                        "is_generic_overview": False
                    }, execution_time

            print("🧹 Cleaning and mapping schema...")
            mapper = SchemaMapper(df)
            clean_df, mapping, warnings = mapper.map_schema()
            print(f"✅ Schema mapped. Shape: {clean_df.shape}")

            analytics = AnalyticsAgent(clean_df)

            analyst = AutonomousAnalyst(
                planner=self.planner,
                analytics=analytics,
                insight_agent=self.insight,
                viz_agent=self.viz
            )

            if not question or question.strip() == "":
                # Generic overview
                print("📊 Generating generic overview")

                # Compute KPIs
                kpis = analytics.compute_kpis()

                # Get top customers - handle dict return
                customer_data = analytics.revenue_by_customer()
                if isinstance(customer_data, dict):
                    # Sort and take top 5
                    sorted_customers = sorted(customer_data.items(), key=lambda x: x[1], reverse=True)[:5]
                    top_customers = dict(sorted_customers)
                else:
                    top_customers = {}

                # Get top products - handle dict return
                product_data = analytics.revenue_by_product()
                if isinstance(product_data, dict):
                    # Sort and take top 5
                    sorted_products = sorted(product_data.items(), key=lambda x: x[1], reverse=True)[:5]
                    top_products = dict(sorted_products)
                else:
                    top_products = {}

                # Get monthly trend - handle Series return
                monthly_data = analytics.monthly_revenue()
                if hasattr(monthly_data, 'to_dict'):
                    monthly_trend = monthly_data.to_dict()
                elif isinstance(monthly_data, dict):
                    monthly_trend = monthly_data
                else:
                    monthly_trend = {}

                # Get anomalies - handle Series return
                spikes_data = analytics.detect_revenue_spikes()
                if hasattr(spikes_data, 'to_dict'):
                    anomalies = spikes_data.to_dict()
                elif isinstance(spikes_data, dict):
                    anomalies = spikes_data
                else:
                    anomalies = {}

                overview = {
                    "answer": "Here's a comprehensive overview of your business data:",
                    "supporting_insights": {
                        "key_metrics": kpis,
                        "top_customers": top_customers,
                        "top_products": top_products,
                        "monthly_trend": monthly_trend,
                        "anomalies_detected": len(anomalies) > 0
                    },
                    "anomalies": anomalies if anomalies else {"note": "No significant anomalies detected"},
                    "recommended_metrics": {
                        "customer_retention": "Analyze customer retention rates",
                        "profit_margin_trend": "Track profit margin over time",
                        "seasonal_patterns": "Look for seasonal patterns in your data"
                    },
                    "human_readable_summary": self._generate_overview_summary(
                        kpis, top_customers, top_products, anomalies
                    )
                }

                results = {
                    "kpis": kpis,
                    "top_customers": top_customers,
                    "top_products": top_products,
                    "monthly_trend": monthly_trend
                }

                insights = overview["human_readable_summary"]
                plan = {"plan": ["compute_kpis", "revenue_by_customer", "revenue_by_product", "monthly_revenue", "detect_revenue_spikes"]}
                raw_insights = None

            else:
                print(f"❓ Question: {question}")
                raw_plan, plan, results, raw_insights, insights = analyst.run(question)

            execution_time = time.time() - start_time

            return {
                "success": True,
                "insights": insights,
                "raw_insights": raw_insights,
                "results": results,
                "plan": plan,
                "warnings": warnings,
                "mapping": mapping,
                "data_summary": {
                    "rows": len(clean_df),
                    "columns": list(clean_df.columns)
                },
                "execution_time": execution_time,
                "is_generic_overview": not question or question.strip() == ""
            }, execution_time

        except ValueError as e:
            # Validation errors - return as user-friendly message
            execution_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "insights": f"Validation Error: {str(e)}",
                "results": {},
                "plan": {"plan": []},
                "warnings": [],
                "data_summary": {
                    "rows": len(df) if 'df' in locals() else 0,
                    "columns": list(df.columns) if 'df' in locals() else []
                },
                "execution_time": execution_time,
                "is_generic_overview": False
            }, execution_time

        except Exception as e:
            import traceback
            traceback.print_exc()
            execution_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "insights": f"Analysis Error: {str(e)}",
                "results": {},
                "plan": {"plan": []},
                "warnings": [],
                "data_summary": {
                    "rows": len(df) if 'df' in locals() else 0,
                    "columns": list(df.columns) if 'df' in locals() else []
                },
                "execution_time": execution_time,
                "is_generic_overview": False
            }, execution_time

    async def analyze(
        self,
        question: str,
        source_type: str,
        source_config: dict[str, Any]
    ) -> tuple[dict[str, Any], float]:
        """
        Run complete analysis pipeline
        
        If question is empty, provides a generic business overview
        """
        start_time = time.time()

        try:
            # Step 1: Load data
            print(f"📂 Loading data from {source_type}...")
            df = self._load_data(source_type, source_config)
            print(f"✅ Loaded {len(df)} rows")

            # Step 2: Validate and analyze
            return await self.analyze_dataframe(df, question)

        except Exception as e:
            import traceback
            traceback.print_exc()
            execution_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "insights": f"Error: {str(e)}",
                "results": {},
                "plan": {"plan": []},
                "warnings": [],
                "data_summary": {
                    "rows": 0,
                    "columns": []
                },
                "execution_time": execution_time,
                "is_generic_overview": False
            }, execution_time

    def _generate_overview_summary(self, kpis: dict, top_customers: dict, top_products: dict, anomalies: dict) -> str:
        """Generate a human-readable overview summary"""
        summary = f"Your business has generated ${kpis.get('total_revenue', 0):,.0f} in revenue "
        summary += f"with a {kpis.get('profit_margin', 0)*100:.1f}% profit margin. "

        if top_customers:
            top_cust = list(top_customers.keys())[0] if top_customers else "N/A"
            top_cust_value = list(top_customers.values())[0] if top_customers else 0
            summary += f"Your top customer is {top_cust} "
            summary += f"contributing ${top_cust_value:,.0f}. "

        if top_products:
            top_prod = list(top_products.keys())[0] if top_products else "N/A"
            top_prod_value = list(top_products.values())[0] if top_products else 0
            summary += f"The best-selling product is {top_prod} "
            summary += f"with ${top_prod_value:,.0f} in revenue. "

        if anomalies:
            summary += f"We detected {len(anomalies)} revenue anomalies that may need investigation."
        else:
            summary += "No significant revenue anomalies were detected."

        return summary

    def _load_data(self, source_type: str, config: dict[str, Any]) -> pd.DataFrame:
        """Load data based on source type"""
        print(f"📂 Loading data from {source_type}...")

        if source_type == "database":
            return self.data_loader.load('database', config)

        elif source_type in ["csv", "excel"]:
            # For file uploads, config contains the file path
            file_path = config.get('path')
            if not file_path:
                raise ValueError("No file path provided")

            print(f"📁 File path: {file_path}")

            # Use the correct source type - don't force 'csv'
            return self.data_loader.load(source_type, file_path)

        elif source_type == "google_sheets":
            return self.data_loader.load('google_sheets', {
                'sheet_id': config.get('sheet_id'),
                'range': config.get('range', 'A1:Z1000')
            })

        else:
            raise ValueError(f"Unsupported source type: {source_type}")
