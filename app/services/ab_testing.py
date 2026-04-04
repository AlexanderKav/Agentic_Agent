# services/ab_testing.py
import hashlib
import json
import os
from datetime import datetime


class ABTestService:
    """A/B testing service for prompt versions and features"""

    def __init__(self, storage_path: str = "logs/ab_tests/"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def get_version_for_user(
        self,
        user_id: int,
        test_name: str,
        control: str = 'v1',
        treatment: str = 'v2',
        traffic_split: float = 0.5
    ) -> str:
        """
        Simple two-version A/B test.
        Returns either control or treatment based on user hash.
        """
        # Create a deterministic hash
        hash_input = f"{user_id}:{test_name}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        bucket = int(hash_value[:8], 16) / 2**32

        if bucket < traffic_split:
            return treatment
        return control

    def record_metric(
        self,
        user_id: int,
        test_name: str,
        version: str,
        metric_name: str,
        metric_value: float,
        additional_data: dict | None = None
    ):
        """Record metrics for A/B test analysis"""
        log_file = os.path.join(self.storage_path, f"{test_name}.jsonl")

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "test_name": test_name,
            "version": version,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "additional_data": additional_data or {}
        }

        with open(log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def get_test_results(self, test_name: str) -> dict:
        """Get aggregated results for a test"""
        log_file = os.path.join(self.storage_path, f"{test_name}.jsonl")

        if not os.path.exists(log_file):
            return {"error": "No data found", "test_name": test_name}

        metrics = {}

        with open(log_file) as f:
            for line in f:
                entry = json.loads(line)
                version = entry['version']
                metric_name = entry['metric_name']
                metric_value = entry['metric_value']

                if metric_name not in metrics:
                    metrics[metric_name] = {}

                if version not in metrics[metric_name]:
                    metrics[metric_name][version] = []

                metrics[metric_name][version].append(metric_value)

        # Calculate statistics
        results = {}
        for metric_name, version_data in metrics.items():
            results[metric_name] = {}
            for version, values in version_data.items():
                if values:
                    results[metric_name][version] = {
                        "avg": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "count": len(values),
                        "p95": sorted(values)[int(len(values) * 0.95)] if len(values) >= 20 else None
                    }

        return {
            "test_name": test_name,
            "metrics": results,
            "total_records": sum(len(v) for m in metrics.values() for v in m.values())
        }

    def get_winner(self, test_name: str, metric_name: str = "answer_length") -> str | None:
        """
        Determine which version is winning based on a metric.
        For latency, lower is better. For answer_length, higher might be better.
        """
        results = self.get_test_results(test_name)

        if "error" in results or metric_name not in results.get("metrics", {}):
            return None

        metric_data = results["metrics"][metric_name]

        if len(metric_data) < 2:
            return None

        versions = list(metric_data.keys())
        v1_avg = metric_data[versions[0]]['avg']
        v2_avg = metric_data[versions[1]]['avg']

        # For latency, lower is better
        if metric_name == 'latency':
            return versions[1] if v2_avg < v1_avg else versions[0]

        # For answer_length, higher might be better
        return versions[1] if v2_avg > v1_avg else versions[0]



__all__ = ['ABTestService']  # For ab_testing.py
__all__ = ['EmailService']   # For email.py
__all__ = ['KeyRotationService', 'get_key_rotation_service']  # For key_rotation.py
__all__ = ['SecretsManager', 'get_secrets_manager']  # For secrets_manager.py