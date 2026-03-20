from app.core.database import engine
from app.api.v1.models import user, analysis

# Create tables
user.Base.metadata.create_all(bind=engine)
analysis.Base.metadata.create_all(bind=engine)

print("✅ Database tables created!")