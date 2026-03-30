#!/usr/bin/env python
"""Initialize database tables for production"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine
from app.api.v1.models.user import Base
from app.api.v1.models.analysis import AnalysisHistory, AnalysisMetric, AnalysisInsight, AnalysisChart

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully!")