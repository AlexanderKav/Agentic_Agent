# copy_correct_db.py
import shutil
import os

# Source is the database with all tables
source = r"test_files\test_validation.db"
# Destination in working directory
destination = r"test_validation.db"

print("="*60)
print("📋 DATABASE FILE CHECK")
print("="*60)

# Check source file
if os.path.exists(source):
    source_size = os.path.getsize(source)
    print(f"✅ Source file exists: {source}")
    print(f"📏 Source size: {source_size:,} bytes")
    
    # Check if it has tables
    import sqlite3
    conn = sqlite3.connect(source)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"📋 Source tables: {[t[0] for t in tables]}")
    conn.close()
else:
    print(f"❌ Source file NOT found: {source}")

# Check destination file
if os.path.exists(destination):
    dest_size = os.path.getsize(destination)
    print(f"\n✅ Destination file exists: {destination}")
    print(f"📏 Destination size: {dest_size:,} bytes")
    
    if dest_size == 0:
        print("❌ Destination file is EMPTY (0 bytes)")
        print("🔄 Removing empty file...")
        os.remove(destination)
else:
    print(f"\n❌ Destination file NOT found: {destination}")

# Copy the file
if os.path.exists(source) and source_size > 0:
    print(f"\n📋 Copying database...")
    shutil.copy2(source, destination)
    print(f"✅ Copied {source} to {destination}")
    print(f"📏 New file size: {os.path.getsize(destination):,} bytes")
    
    # Verify the copy
    conn = sqlite3.connect(destination)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"📋 Tables in copied database: {[t[0] for t in tables]}")
    conn.close()
else:
    print(f"\n❌ Cannot copy - source file issues")