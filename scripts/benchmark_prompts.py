#!/usr/bin/env python
"""Benchmark different prompt versions against test data"""

import json
import time
from agents.insight_agent import InsightAgent
from agents.prompts import PromptRegistry
import pandas as pd

class PromptBenchmark:
    def __init__(self):
        self.results = []
    
    def benchmark(self, test_questions: list, test_data: dict):
        """Run benchmarks on all prompt versions"""
        versions = ['v1', 'v2']  # Get from registry
        
        for version in versions:
            agent = InsightAgent(prompt_version=version)
            version_results = []
            
            for question in test_questions:
                start = time.time()
                raw, parsed = agent.generate_insights(test_data, question)
                latency = time.time() - start
                
                version_results.append({
                    'question': question[:50],
                    'latency': latency,
                    'answer_length': len(parsed.get('answer', '')),
                    'has_confidence': 'confidence_score' in parsed
                })
            
            self.results.append({
                'version': version,
                'results': version_results,
                'avg_latency': sum(r['latency'] for r in version_results) / len(version_results)
            })
    
    def export_report(self):
        """Generate comparison report"""
        df = pd.DataFrame([
            {'version': r['version'], 'avg_latency': r['avg_latency']} 
            for r in self.results
        ])
        print(df)
        
        # Save to file for A/B test analysis
        with open('prompt_benchmark_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)

if __name__ == '__main__':
    benchmark = PromptBenchmark()
    # Load test data
    with open('tests/fixtures/sample_data.json') as f:
        test_data = json.load(f)
    
    test_questions = [
        "How is the business performing?",
        "What are the top products by revenue?",
        "Identify any risks in the data."
    ]
    
    benchmark.benchmark(test_questions, test_data)
    benchmark.export_report()