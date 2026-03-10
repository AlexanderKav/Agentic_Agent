"""Simple test to verify the testing environment."""

import sys
import os

def test_imports():
    """Test that all agents can be imported."""
    try:
        from agents.analytics_agent import AnalyticsAgent
        from agents.autonomous_analyst import AutonomousAnalyst
        from agents.insight_agent import InsightAgent
        from agents.planner_agent import PlannerAgent
        from agents.visualization_agent import VisualizationAgent
        from agents.monitoring import get_performance_tracker
        from agents.self_healing import get_healing_agent
        print("✅ All imports successful!")
        assert True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        assert False, f"Import failed: {e}"

def test_python_path():
    """Test that Python path is set correctly."""
    print(f"Python path: {sys.path}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Files in current directory: {os.listdir('.')}")
    assert 'agents' in os.listdir('.') or os.path.exists('agents'), "agents directory not found"