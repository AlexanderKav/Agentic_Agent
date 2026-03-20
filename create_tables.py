from app.core.database import engine
from app.api.v1.models.user import Base as UserBase
from app.api.v1.models.analysis import Base as AnalysisBase

print("Creating database tables...")
UserBase.metadata.create_all(bind=engine)
AnalysisBase.metadata.create_all(bind=engine)
print("✅ Tables created successfully!")