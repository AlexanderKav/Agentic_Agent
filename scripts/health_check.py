#!/usr/bin/env python
"""
Health check script for Docker.
Returns 0 if healthy, 1 if unhealthy.
"""

import sys
import os
import requests

def health_check():
    """Check if the application is healthy"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Application is healthy")
            sys.exit(0)
        else:
            print(f"❌ Health check failed: {response.status_code}")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    health_check()