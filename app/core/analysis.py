# app/core/analysis.py
import time
import pandas as pd
from typing import Dict, Any, Tuple, Optional

from connectors.data_loader import DataLoader
from agents.schema_mapper import SchemaMapper
from agents.autonomous_analyst import AutonomousAnalyst
from agents.analytics_agent import AnalyticsAgent
from agents.insight_agent import InsightAgent
from agents.planner_agent import PlannerAgent
from agents.visualization_agent import VisualizationAgent

# Constants for validation
MAX_ROWS = 100000
MINIMUM_REQUIRED_COLUMNS = ['date', 'revenue']
MAX_STRING_LENGTH = 10000

class AnalysisOrchestrator:
    """Orchestrates the entire analysis pipeline"""
    
    def __init__(self, data_loader: Optional[DataLoader] = None):
        self.data_loader = data_loader or DataLoader()
        self.planner = PlannerAgent()
        self.insight = InsightAgent()
        self.viz = VisualizationAgent()
    
    def validate_dataframe(self, df: pd.DataFrame):
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
    
    async def analyze_dataframe(self, df: pd.DataFrame, question: str) -> Tuple[Dict[str, Any], float]:
        """
        Analyze a pandas DataFrame directly (used by both file upload and database)
        """
        start_time = time.time()
        
        try:
            # 🔐 VALIDATE THE DATAFRAME FIRST
            self.validate_dataframe(df)
            
            print(f"🧹 Cleaning and mapping schema...")
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
                kpis = analytics.compute_kpis()
                top_customers = analytics.revenue_by_customer().head(5).to_dict() if hasattr(analytics, 'revenue_by_customer') else {}
                top_products = analytics.revenue_by_product().head(5).to_dict() if hasattr(analytics, 'revenue_by_product') else {}
                monthly_trend = analytics.monthly_revenue().to_dict() if hasattr(analytics, 'monthly_revenue') else {}
                anomalies = analytics.detect_revenue_spikes().to_dict() if hasattr(analytics, 'detect_revenue_spikes') else {}
                
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
                
            else:
                print(f"❓ Question: {question}")
                raw_plan, plan, results, raw_insights, insights = analyst.run(question)
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "insights": insights,
                "raw_insights": raw_insights if 'raw_insights' in locals() else None,
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
        source_config: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], float]:
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
    
    def _generate_overview_summary(self, kpis, top_customers, top_products, anomalies):
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
    
    def _load_data(self, source_type: str, config: Dict[str, Any]) -> pd.DataFrame:
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