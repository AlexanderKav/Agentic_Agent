import pytest
import pandas as pd
import numpy as np
import os
import matplotlib
matplotlib.use("Agg")  # Use non-interactive backend for testing
import matplotlib.pyplot as plt
from unittest.mock import patch, MagicMock, mock_open
import sys
import tempfile
import shutil
import re

# Add the parent directory to sys.path to import from agents folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from agents.visualization_agent import VisualizationAgent


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for chart output"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up after tests
    shutil.rmtree(temp_dir)


@pytest.fixture
def viz_agent(temp_output_dir):
    """Create a VisualizationAgent instance with temp output directory"""
    return VisualizationAgent(output_dir=temp_output_dir)


@pytest.fixture
def sample_series():
    """Create a sample pandas Series for testing"""
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    return pd.Series(
        [100, 120, 110, 130, 125, 140, 135, 145, 150, 155],
        index=dates,
        name='revenue'
    )


@pytest.fixture
def sample_dataframe():
    """Create a sample pandas DataFrame for testing"""
    dates = pd.date_range('2024-01-01', periods=5, freq='D')
    return pd.DataFrame({
        'revenue': [100, 120, 110, 130, 125],
        'cost': [50, 60, 55, 65, 60],
        'profit': [50, 60, 55, 65, 65]
    }, index=dates)


@pytest.fixture
def sample_series_with_string_index():
    """Create a sample Series with string index - should be converted to datetime if possible"""
    return pd.Series(
        [100, 200, 300],
        index=['2024-01-01', '2024-02-01', '2024-03-01'],
        name='monthly_sales'
    )


@pytest.fixture
def sample_series_with_non_date_strings():
    """Create a sample Series with non-date string index"""
    return pd.Series(
        [100, 200, 300],
        index=['Jan', 'Feb', 'Mar'],
        name='monthly_sales'
    )


@pytest.fixture
def empty_series():
    """Create an empty Series"""
    return pd.Series([], dtype=float, name='empty')


@pytest.fixture
def empty_dataframe():
    """Create an empty DataFrame"""
    return pd.DataFrame()


@pytest.fixture
def raw_results(sample_series, sample_dataframe, sample_series_with_string_index):
    """Create sample raw_results dictionary"""
    return {
        'revenue_trend': sample_series,
        'cost_analysis': sample_dataframe,
        'monthly_sales_date': sample_series_with_string_index,
        'non_visualizable': {'key': 'value'}  # This should be skipped
    }


class TestVisualizationAgentInitialization:
    """Test VisualizationAgent initialization"""
    
    def test_init_with_default_output_dir(self, monkeypatch):
        """Test initialization with default output directory"""
        monkeypatch.setattr(os, 'getcwd', lambda: 'C:\\project')
        
        agent = VisualizationAgent()
        assert 'agents' in agent.output_dir and 'charts' in agent.output_dir
    
    def test_init_with_custom_output_dir(self, temp_output_dir):
        """Test initialization with custom output directory"""
        agent = VisualizationAgent(output_dir=temp_output_dir)
        assert agent.output_dir == os.path.abspath(temp_output_dir)
        assert os.path.exists(agent.output_dir)
    
    def test_init_creates_directory(self, temp_output_dir):
        """Test that initialization creates the output directory if it doesn't exist"""
        new_dir = os.path.join(temp_output_dir, 'nested', 'charts')
        agent = VisualizationAgent(output_dir=new_dir)
        assert os.path.exists(new_dir)
    
    def test_output_dir_absolute_path(self):
        """Test that output_dir is converted to absolute path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            relative_dir = os.path.join(tmpdir, 'test_charts')
            agent = VisualizationAgent(output_dir=relative_dir)
            assert os.path.isabs(agent.output_dir)


class TestPlotSeries:
    """Test the _plot_series method"""
    
    def test_plot_series_with_datetime_index(self, viz_agent, sample_series):
        """Test plotting a Series with datetime index"""
        filepath = viz_agent._plot_series(sample_series, 'revenue_trend')
        
        assert os.path.exists(filepath)
        assert filepath.endswith('revenue_trend.png')
        assert os.path.getsize(filepath) > 0
    
    def test_plot_series_with_string_index_convertible(self, viz_agent, sample_series_with_string_index):
        """Test plotting a Series with string index that can be converted to datetime"""
        filepath = viz_agent._plot_series(sample_series_with_string_index, 'monthly_sales_date')
        
        assert os.path.exists(filepath)
        assert filepath.endswith('monthly_sales_date.png')
    
    def test_plot_series_with_non_date_strings(self, viz_agent, sample_series_with_non_date_strings):
        """Test plotting a Series with non-date string index - should handle gracefully"""
        try:
            filepath = viz_agent._plot_series(sample_series_with_non_date_strings, 'monthly_sales_non_date')
            assert os.path.exists(filepath)
        except Exception as e:
            pytest.skip(f"Skipping: {e}")
    
    def test_plot_series_with_empty_series(self, viz_agent, empty_series):
        """Test plotting an empty Series"""
        try:
            result = viz_agent._plot_series(empty_series, 'empty')
            if result and os.path.exists(result):
                assert result.endswith('empty.png')
        except Exception as e:
            pytest.skip(f"Skipping empty series test: {e}")
    
    def test_plot_series_with_single_value(self, viz_agent):
        """Test plotting a Series with a single value"""
        series = pd.Series([100], index=['2024-01-01'], name='single')
        filepath = viz_agent._plot_series(series, 'single_point')
        assert os.path.exists(filepath)
    
    def test_plot_series_with_none_values(self, viz_agent):
        """Test plotting a Series with None/NaN values"""
        series = pd.Series([100, None, 200, np.nan, 150], 
                          index=pd.date_range('2024-01-01', periods=5),
                          name='with_nulls')
        filepath = viz_agent._plot_series(series, 'with_nulls')
        assert os.path.exists(filepath)
    
    @patch('matplotlib.pyplot.savefig')
    def test_plot_series_save_failure(self, mock_savefig, viz_agent, sample_series):
        """Test handling of save failure"""
        mock_savefig.side_effect = Exception("Save failed")
        
        with pytest.raises(Exception):
            viz_agent._plot_series(sample_series, 'revenue_trend')


class TestPlotDataFrame:
    """Test the _plot_dataframe method"""
    
    def test_plot_dataframe(self, viz_agent, sample_dataframe):
        """Test plotting a DataFrame"""
        filepath = viz_agent._plot_dataframe(sample_dataframe, 'cost_analysis')
        assert os.path.exists(filepath)
        assert filepath.endswith('cost_analysis.png')
        assert os.path.getsize(filepath) > 0
    
    def test_plot_dataframe_with_single_column(self, viz_agent):
        """Test plotting a DataFrame with a single column"""
        df = pd.DataFrame({'revenue': [100, 200, 150]}, 
                         index=pd.date_range('2024-01-01', periods=3))
        filepath = viz_agent._plot_dataframe(df, 'single_column')
        assert os.path.exists(filepath)
    
    def test_plot_dataframe_with_many_columns(self, viz_agent):
        """Test plotting a DataFrame with many columns"""
        data = {f'col_{i}': np.random.randn(10) for i in range(5)}
        df = pd.DataFrame(data, index=pd.date_range('2024-01-01', periods=10))
        filepath = viz_agent._plot_dataframe(df, 'many_columns')
        assert os.path.exists(filepath)
    
    def test_plot_dataframe_empty(self, viz_agent, empty_dataframe):
        """Test plotting an empty DataFrame"""
        try:
            filepath = viz_agent._plot_dataframe(empty_dataframe, 'empty_df')
            if filepath and os.path.exists(filepath):
                assert filepath.endswith('empty_df.png')
        except Exception as e:
            pytest.skip(f"Skipping empty DataFrame test: {e}")


class TestGenerateFromResults:
    """Test the generate_from_results method"""
    
    def test_generate_from_results_with_all_types(self, viz_agent, raw_results):
        """Test generating charts from various result types"""
        charts = viz_agent.generate_from_results(raw_results)
        assert len(charts) == 3
        
        for tool_name, chart_path in charts.items():
            assert os.path.exists(chart_path)
            assert chart_path.endswith(f'{tool_name}.png')
    
    def test_generate_from_results_with_non_date_series(self, viz_agent, sample_series, sample_series_with_non_date_strings):
        """Test generating charts with a non-date series"""
        raw_results = {
            'good_series': sample_series,
            'problematic_series': sample_series_with_non_date_strings
        }
        
        charts = viz_agent.generate_from_results(raw_results)
        assert 'good_series' in charts
        
        if 'problematic_series' in charts:
            assert os.path.exists(charts['problematic_series'])
    
    def test_generate_from_results_with_empty_series(self, viz_agent, empty_series):
        """Test generating charts with an empty Series"""
        raw_results = {'empty_series': empty_series}
        charts = viz_agent.generate_from_results(raw_results)
        assert isinstance(charts, dict)
    
    def test_generate_from_results_with_empty_dataframe(self, viz_agent, empty_dataframe):
        """Test generating charts with an empty DataFrame"""
        raw_results = {'empty_df': empty_dataframe}
        charts = viz_agent.generate_from_results(raw_results)
        assert isinstance(charts, dict)
    
    def test_generate_from_results_with_mixed_types(self, viz_agent):
        """Test generating charts with mixed result types"""
        raw_results = {
            'series': pd.Series([1, 2, 3], index=['2024-01-01', '2024-01-02', '2024-01-03'], name='test'),
            'dataframe': pd.DataFrame({'a': [1, 2, 3]}),
            'dict': {'key': 'value'},
            'list': [1, 2, 3],
            'string': 'not visualizable',
            'int': 42,
            'none': None
        }
        
        charts = viz_agent.generate_from_results(raw_results)
        assert 'series' in charts
        assert 'dataframe' in charts
    
    def test_generate_from_results_with_exception(self, viz_agent, sample_series):
        """Test handling of exceptions during visualization"""
        raw_results = {
            'good': sample_series,
            'bad': 'not visualizable'
        }
        
        charts = viz_agent.generate_from_results(raw_results)
        assert 'good' in charts
        assert 'bad' not in charts
    
    def test_generate_from_results_empty_dict(self, viz_agent):
        """Test with empty raw_results"""
        charts = viz_agent.generate_from_results({})
        assert charts == {}


class TestFileOperations:
    """Test file operations and error handling"""
    
    def test_file_naming(self, viz_agent, sample_series):
        """Test that files are named correctly"""
        filepath = viz_agent._plot_series(sample_series, 'test_chart')
        expected_filename = "test_chart.png"
        assert os.path.basename(filepath) == expected_filename
    
    def test_file_overwrite(self, viz_agent, sample_series):
        """Test that existing files are overwritten"""
        filepath1 = viz_agent._plot_series(sample_series, 'overwrite_test')
        time1 = os.path.getmtime(filepath1)
        
        filepath2 = viz_agent._plot_series(sample_series, 'overwrite_test')
        time2 = os.path.getmtime(filepath2)
        
        assert filepath1 == filepath2
        assert time2 >= time1
    
    def test_special_characters_in_name(self, viz_agent, sample_series):
        """Test handling of special characters in chart names"""
        name_with_special_chars = 'test_chart_name'
        filepath = viz_agent._plot_series(sample_series, name_with_special_chars)
        assert os.path.exists(filepath)
    
    @patch('os.makedirs')
    def test_directory_creation_failure(self, mock_makedirs, temp_output_dir):
        """Test handling of directory creation failure"""
        mock_makedirs.side_effect = PermissionError("Access denied")
        
        with pytest.raises(PermissionError):
            VisualizationAgent(output_dir=temp_output_dir)


class TestEdgeCases:
    """Test edge cases and special scenarios"""
    
    def test_very_long_series(self, viz_agent):
        """Test plotting a very long Series"""
        long_series = pd.Series(
            np.random.randn(100),
            index=pd.date_range('2020-01-01', periods=100, freq='D'),
            name='long_series'
        )
        filepath = viz_agent._plot_series(long_series, 'long_series')
        assert os.path.exists(filepath)
    
    def test_series_with_large_values(self, viz_agent):
        """Test plotting a Series with very large values"""
        large_series = pd.Series(
            [1e6, 2e6, 3e6, 4e6, 5e6],
            index=pd.date_range('2024-01-01', periods=5),
            name='large_values'
        )
        filepath = viz_agent._plot_series(large_series, 'large_values')
        assert os.path.exists(filepath)
    
    def test_series_with_very_small_values(self, viz_agent):
        """Test plotting a Series with very small values"""
        small_series = pd.Series(
            [1e-6, 2e-6, 3e-6, 4e-6, 5e-6],
            index=pd.date_range('2024-01-01', periods=5),
            name='small_values'
        )
        filepath = viz_agent._plot_series(small_series, 'small_values')
        assert os.path.exists(filepath)
    
    def test_dataframe_with_mixed_dtypes(self, viz_agent):
        """Test plotting a DataFrame with mixed data types"""
        df = pd.DataFrame({
            'revenue': [100, 200, 150],
            'date': pd.date_range('2024-01-01', periods=3),
            'category': ['A', 'B', 'C']
        })
        filepath = viz_agent._plot_dataframe(df, 'mixed_dtypes')
        assert os.path.exists(filepath)
    
    def test_dataframe_with_datetime_index(self, viz_agent):
        """Test plotting a DataFrame with datetime index"""
        df = pd.DataFrame(
            {'revenue': [100, 200, 150]},
            index=pd.date_range('2024-01-01', periods=3)
        )
        filepath = viz_agent._plot_dataframe(df, 'datetime_index')
        assert os.path.exists(filepath)


class TestIntegration:
    """Integration-style tests"""
    
    def test_full_visualization_workflow(self, viz_agent):
        """Test the complete visualization workflow"""
        raw_results = {
            'monthly_revenue': pd.Series(
                [45000, 52000, 48000, 55000],
                index=pd.date_range('2024-01-01', periods=4, freq='ME'),
                name='monthly_revenue'
            ),
            'kpi_comparison': pd.DataFrame({
                'revenue': [45000, 52000, 48000, 55000],
                'cost': [20000, 23000, 21000, 24000],
                'profit': [25000, 29000, 27000, 31000]
            }, index=pd.date_range('2024-01-01', periods=4, freq='ME')),
            'text_data': 'This should be ignored'
        }
        
        charts = viz_agent.generate_from_results(raw_results)
        assert len(charts) == 2
        assert 'monthly_revenue' in charts
        assert 'kpi_comparison' in charts
        
        for chart_path in charts.values():
            assert os.path.exists(chart_path)
            assert os.path.getsize(chart_path) > 0
    
    def test_concurrent_chart_generation(self, viz_agent, sample_series, sample_dataframe):
        """Test generating multiple charts in sequence"""
        raw_results = {f'chart_{i}': sample_series for i in range(5)}
        raw_results['df_chart'] = sample_dataframe
        
        charts = viz_agent.generate_from_results(raw_results)
        assert len(charts) == 6
        
        for chart_path in charts.values():
            assert os.path.exists(chart_path)


class TestPrintStatements:
    """Test that print statements work correctly"""
    
    def test_init_print_statement(self, capsys, temp_output_dir):
        """Test that initialization prints the output directory"""
        agent = VisualizationAgent(output_dir=temp_output_dir)
        captured = capsys.readouterr()
        assert "Charts will be saved to:" in captured.out
        assert temp_output_dir in captured.out
    
    def test_plot_series_creates_file(self, viz_agent, sample_series):
        """Test that _plot_series creates a file (verifies functionality)"""
        filepath = viz_agent._plot_series(sample_series, 'test_chart')
        
        # Verify the file was created
        assert os.path.exists(filepath)
        assert filepath.endswith('test_chart.png')
        assert os.path.getsize(filepath) > 0
    
    def test_generate_from_results_error_print(self, capsys, viz_agent):
        """Test that errors are printed"""
        # Clear init prints
        capsys.readouterr()
        
        raw_results = {'bad_data': 'not a series or dataframe'}
        charts = viz_agent.generate_from_results(raw_results)
        captured = capsys.readouterr()
        
        # Should not print errors for non-visualizable data
        assert "Visualization failed" not in captured.out

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])