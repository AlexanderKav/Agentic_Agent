"""Tests for prompt versioning and management."""

import pytest
import json
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.prompts import PromptRegistry
from agents.insight_agent import InsightAgent
from tests.fixtures.sample_data import sample_business_data


class TestPromptVersions:
    """Test prompt version loading and functionality."""
    
    @pytest.fixture
    def sample_data(self, sample_business_data):
        """Sample data for testing."""
        return sample_business_data
    
    def test_prompt_version_loading(self):
        """Test that prompts load correctly."""
        # Get prompts for existing versions
        prompt_v1 = PromptRegistry.get_prompt('insight_agent', 'v1')
        prompt_v2 = PromptRegistry.get_prompt('insight_agent', 'v2')
        prompt_v3 = PromptRegistry.get_prompt('insight_agent', 'v3')
        
        # Verify versions
        assert prompt_v1['version'] == 'v1'
        assert prompt_v2['version'] == 'v2'  # Now this should pass
        assert prompt_v3['version'] == 'v3'
        
        # Templates should be different between versions
        assert prompt_v1['template'] != prompt_v2['template']
        assert prompt_v2['template'] != prompt_v3['template']
        assert 'parameters' in prompt_v1
        assert 'parameters' in prompt_v2
        assert 'parameters' in prompt_v3
    
    def test_prompt_current_version(self):
        """Test that current version loads correctly."""
        current = PromptRegistry.get_current_version('insight_agent')
        assert current in ['v1', 'v2', 'v3']
        
        prompt = PromptRegistry.get_prompt('insight_agent')
        assert prompt['version'] == current
    
    def test_prompt_schema_compliance(self, sample_data):
        """Test that generated outputs match schema."""
        with patch('agents.insight_agent.ChatOpenAI') as mock_chat:
            # Create mock LLM
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "answer": "Business is performing well with 43% profit margin.",
                "supporting_insights": {
                    "revenue_trend": "Growth in February",
                    "top_customer": "Acme Corp"
                },
                "anomalies": {},
                "recommended_metrics": {
                    "primary": "Customer retention"
                },
                "human_readable_summary": "Overall healthy performance."
            })
            mock_llm.invoke.return_value = mock_response
            mock_chat.return_value = mock_llm
            
            agent = InsightAgent(prompt_version='v2', enable_cost_tracking=False)
            raw, parsed = agent.generate_insights(sample_data, "How is business?")
            
            # Check required fields
            assert 'answer' in parsed
            assert 'human_readable_summary' in parsed
            assert 'supporting_insights' in parsed
            assert 'anomalies' in parsed
            assert 'recommended_metrics' in parsed
            
            # Check types
            assert isinstance(parsed['answer'], str)
            assert isinstance(parsed['human_readable_summary'], str)
            assert isinstance(parsed['supporting_insights'], dict)
    
    def test_version_switching(self, sample_data):
        """Test that different versions can be used."""
        with patch('agents.insight_agent.ChatOpenAI') as mock_chat:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = json.dumps({
                "answer": "Test answer",
                "supporting_insights": {},
                "anomalies": {},
                "recommended_metrics": {},
                "human_readable_summary": "Test summary"
            })
            mock_llm.invoke.return_value = mock_response
            mock_chat.return_value = mock_llm
            
            agent_v1 = InsightAgent(prompt_version='v1', enable_cost_tracking=False)
            agent_v2 = InsightAgent(prompt_version='v2', enable_cost_tracking=False)
            agent_v3 = InsightAgent(prompt_version='v3', enable_cost_tracking=False)
            
            assert agent_v1.prompt_version == 'v1'
            assert agent_v2.prompt_version == 'v2'
            assert agent_v3.prompt_version == 'v3'
    
    def test_invalid_version_fallback(self):
        """Test that invalid version raises error."""
        with pytest.raises(FileNotFoundError):
            InsightAgent(prompt_version='invalid_version', enable_cost_tracking=False)
    
    def test_prompt_registry_list_versions(self):
        """Test listing available versions."""
        # Get the prompts directory and list files
        prompts_dir = PromptRegistry.PROMPTS_DIR
        if os.path.exists(prompts_dir):
            files = os.listdir(prompts_dir)
            insight_files = [f for f in files if f.startswith('insight_agent_')]
            versions = [f.replace('insight_agent_', '').replace('.json', '') for f in insight_files]
            assert isinstance(versions, list)
            assert len(versions) >= 3
            assert 'v1' in versions
            assert 'v2' in versions
            assert 'v3' in versions
        else:
            pytest.skip("Prompts directory not found")
    
    def test_prompt_parameters(self):
        """Test that prompt parameters are loaded correctly."""
        prompt_v2 = PromptRegistry.get_prompt('insight_agent', 'v2')
        
        params = prompt_v2.get('parameters', {})
        assert 'model' in params
        assert 'temperature' in params
        assert params['model'] in ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])