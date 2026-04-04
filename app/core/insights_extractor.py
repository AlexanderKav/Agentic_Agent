# app/core/insights_extractor.py
from typing import Any, List


class InsightsExtractor:
    """Extract structured insights from analysis results"""

    def extract(self, insights_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract insights from the insight agent response"""
        insights = []

        # Extract main answer
        if 'answer' in insights_data:
            insights.append({
                'text': insights_data['answer'],
                'type': 'answer',
                'confidence_score': insights_data.get('confidence_score', 0.9)
            })

        # Extract human-readable summary
        if 'human_readable_summary' in insights_data:
            insights.append({
                'text': insights_data['human_readable_summary'],
                'type': 'summary',
                'confidence_score': insights_data.get('confidence_score', 0.85)
            })

        # Extract anomalies
        if 'anomalies' in insights_data:
            anomalies = insights_data['anomalies']
            anomaly_texts = self._extract_anomaly_texts(anomalies)
            for text in anomaly_texts:
                insights.append({
                    'text': text,
                    'type': 'anomaly',
                    'confidence_score': 0.7
                })

        # Extract recommendations
        if 'recommended_metrics' in insights_data:
            recommendations = insights_data['recommended_metrics']
            for key, value in recommendations.items():
                if isinstance(value, str):
                    insights.append({
                        'text': f"{key.replace('_', ' ').title()}: {value}",
                        'type': 'recommendation',
                        'confidence_score': 0.75
                    })
                elif isinstance(value, list):
                    for item in value:
                        insights.append({
                            'text': item,
                            'type': 'recommendation',
                            'confidence_score': 0.75
                        })

        return insights

    def _extract_anomaly_texts(self, anomalies: dict | list | str) -> list[str]:
        """
        Extract readable text from anomaly objects.
        
        Handles various anomaly formats:
        - Dict with month/description pairs
        - Simple string descriptions
        - Lists of anomalies
        """
        texts = []

        if isinstance(anomalies, dict):
            for key, value in anomalies.items():
                if isinstance(value, dict):
                    for month, description in value.items():
                        if description:
                            texts.append(f"{key} in {month}: {description}")
                elif isinstance(value, str) and value:
                    texts.append(f"{key}: {value}")
                elif isinstance(value, list):
                    for item in value:
                        if item:
                            texts.append(f"{key}: {item}")
        elif isinstance(anomalies, list):
            for item in anomalies:
                if isinstance(item, str) and item:
                    texts.append(item)
                elif isinstance(item, dict):
                    texts.extend(self._extract_anomaly_texts(item))
        elif isinstance(anomalies, str) and anomalies:
            texts.append(anomalies)

        return texts


__all__ = ['InsightsExtractor']