"""Simple test to verify the testing environment."""

import sys
import os
import pytest


class TestEnvironment:
    """Test the testing environment setup."""
    
    @pytest.fixture
    def project_root(self):
        """Get the project root directory."""
        # Navigate up from tests directory to project root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # If we're in tests directory, go up one level
        if os.path.basename(current_dir) == 'tests':
            return os.path.dirname(current_dir)
        return current_dir
    
    def test_imports(self):
        """Test that all agents can be imported."""
        try:
            from agents.analytics_agent import AnalyticsAgent
            from agents.autonomous_analyst import AutonomousAnalyst
            from agents.insight_agent import InsightAgent
            from agents.planner_agent import PlannerAgent
            from agents.visualization_agent import VisualizationAgent
            from agents.schema_mapper import SchemaMapper
            from agents.monitoring import get_performance_tracker, get_audit_logger, get_cost_tracker
            from agents.self_healing import get_healing_agent
            from agents.orchestrator import QuestionClassifier, CacheManager, PlanExecutor, DataPreparer, ChartGenerator
            
            print("✅ All imports successful!")
            assert True
        except ImportError as e:
            print(f"❌ Import failed: {e}")
            assert False, f"Import failed: {e}"
    
    def test_python_path(self, project_root):
        """Test that Python path is set correctly."""
        print(f"\nPython path (first 3): {sys.path[:3]}...")
        print(f"Current directory: {os.getcwd()}")
        print(f"Project root: {project_root}")
        
        # Check for required directories at project root
        required_dirs = ['agents', 'app', 'tests']
        missing_dirs = []
        
        for dir_name in required_dirs:
            dir_path = os.path.join(project_root, dir_name)
            if os.path.exists(dir_path):
                print(f"✅ Found '{dir_name}' directory at {dir_path}")
            else:
                print(f"❌ Missing '{dir_name}' directory at {dir_path}")
                missing_dirs.append(dir_name)
        
        if missing_dirs:
            print(f"Missing directories: {missing_dirs}")
            print(f"Contents of project root: {os.listdir(project_root)}")
        
        assert len(missing_dirs) == 0, f"Missing directories: {missing_dirs}"
    
    def test_environment_variables(self):
        """Test that required environment variables are set (or have defaults)."""
        import os
        
        # Check for OpenAI API key (optional for tests, but should be set)
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            print(f"✅ OPENAI_API_KEY is set (starts with: {openai_key[:10]}...)")
        else:
            print("⚠️ OPENAI_API_KEY is not set - tests will use mocks")
        
        # Check for secret key (should have default)
        secret_key = os.getenv('SECRET_KEY')
        if secret_key:
            print(f"✅ SECRET_KEY is set")
        else:
            print("⚠️ SECRET_KEY is not set - using default")
        
        assert True
    
    def test_directories_exist(self, project_root):
        """Test that all required directories exist."""
        required_dirs = [
            'agents',
            'agents/orchestrator',
            'agents/monitoring',
            'agents/self_healing',
            'app',
            'app/api/v1/endpoints',
            'app/api/v1/models',
            'app/core',
            'app/services',
            'tests',
            'tests/unit',
            'tests/integration',
            'tests/fixtures'
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            full_path = os.path.join(project_root, dir_path)
            if os.path.exists(full_path):
                print(f"✅ {dir_path}")
            else:
                print(f"❌ Missing: {dir_path}")
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            print(f"\nMissing {len(missing_dirs)} directories")
        
        assert len(missing_dirs) == 0, f"Missing directories: {missing_dirs}"
    
    def test_import_agents(self):
        """Test importing all agent classes."""
        from agents.analytics_agent import AnalyticsAgent
        from agents.autonomous_analyst import AutonomousAnalyst
        from agents.insight_agent import InsightAgent
        from agents.planner_agent import PlannerAgent
        from agents.visualization_agent import VisualizationAgent
        from agents.schema_mapper import SchemaMapper
        
        # Just verify they exist
        assert AnalyticsAgent is not None
        assert AutonomousAnalyst is not None
        assert InsightAgent is not None
        assert PlannerAgent is not None
        assert VisualizationAgent is not None
        assert SchemaMapper is not None
        
        print("✅ All agent classes imported successfully")
    
    def test_import_monitoring(self):
        """Test importing monitoring modules."""
        from agents.monitoring import get_performance_tracker, get_audit_logger, get_cost_tracker
        
        assert get_performance_tracker is not None
        assert get_audit_logger is not None
        assert get_cost_tracker is not None
        
        print("✅ Monitoring modules imported successfully")
    
    def test_import_orchestrator(self):
        """Test importing orchestrator components."""
        from agents.orchestrator import (
            QuestionClassifier, CacheManager, PlanExecutor, 
            DataPreparer, ChartGenerator
        )
        
        assert QuestionClassifier is not None
        assert CacheManager is not None
        assert PlanExecutor is not None
        assert DataPreparer is not None
        assert ChartGenerator is not None
        
        print("✅ Orchestrator components imported successfully")


if __name__ == '__main__':
    # Change to project root before running tests
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(current_dir) == 'tests':
        project_root = os.path.dirname(current_dir)
        os.chdir(project_root)
        print(f"Changed working directory to: {os.getcwd()}")
    
    pytest.main([__file__, '-v', '--tb=short'])