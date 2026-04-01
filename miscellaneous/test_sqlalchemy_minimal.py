from sqlalchemy import create_engine, text
import os

path = r"C:\Users\alexk\Desktop\agentic-analyst\test_files\test_validation.db"
path_fwd = path.replace('\\', '/')

# Test different formats
formats = [
    f"sqlite:///{path_fwd}",
    f"sqlite:///{path_fwd}?mode=ro",
    f"sqlite:///{path_fwd}?mode=ro&uri=true",
]

for i, conn_str in enumerate(formats):
    print(f"\nTest {i+1}: {conn_str}")
    try:
        engine = create_engine(conn_str)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"✅ SUCCESS: {result.fetchone()}")
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")