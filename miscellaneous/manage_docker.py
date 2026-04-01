import subprocess
import sys

def run_command(cmd):
    """Run shell command and print output"""
    print(f"🚀 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"⚠️  Errors: {result.stderr}")
    return result

def check_docker():
    """Check Docker status"""
    print("🐳 Checking Docker status...")
    run_command("docker ps")

def start_postgres():
    """Start PostgreSQL container"""
    print("🚀 Starting PostgreSQL container...")
    run_command("docker start test-postgres")

def stop_postgres():
    """Stop PostgreSQL container"""
    print("🛑 Stopping PostgreSQL container...")
    run_command("docker stop test-postgres")

def restart_postgres():
    """Restart PostgreSQL container"""
    print("🔄 Restarting PostgreSQL container...")
    run_command("docker restart test-postgres")

def create_postgres():
    """Create new PostgreSQL container"""
    print("🆕 Creating new PostgreSQL container...")
    run_command(
        "docker run --name test-postgres "
        "-e POSTGRES_PASSWORD=testpass "
        "-e POSTGRES_DB=testdb "
        "-p 5432:5432 "
        "-d postgres:15"
    )

def remove_postgres():
    """Remove PostgreSQL container"""
    print("🗑️  Removing PostgreSQL container...")
    run_command("docker stop test-postgres")
    run_command("docker rm test-postgres")

def show_logs():
    """Show PostgreSQL logs"""
    print("📋 Showing PostgreSQL logs...")
    run_command("docker logs test-postgres --tail 50")

def test_connection():
    """Test database connection"""
    print("🔌 Testing database connection...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="testdb",
            user="postgres",
            password="testpass"
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        print(f"✅ Connection successful! Result: {result}")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def list_tables():
    """List tables in database"""
    print("📋 Listing tables...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="testdb",
            user="postgres",
            password="testpass"
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cur.fetchall()
        if tables:
            print("Tables found:")
            for table in tables:
                print(f"  📊 {table[0]}")
        else:
            print("No tables found in database")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

def load_large_file():
    """Load the large test file"""
    print("📂 Loading large test file...")
    try:
        import pandas as pd
        from sqlalchemy import create_engine
        
        print("📖 Reading CSV file...")
        df = pd.read_csv("large_test_file.csv", nrows=100)  # Read just 100 rows for testing
        
        engine = create_engine("postgresql://postgres:testpass@localhost:5432/testdb")
        
        print("💾 Loading to database...")
        df.to_sql("large_test", engine, if_exists='replace', index=False)
        
        print(f"✅ Loaded {len(df)} rows to 'large_test' table")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "start":
            start_postgres()
        elif command == "stop":
            stop_postgres()
        elif command == "restart":
            restart_postgres()
        elif command == "create":
            create_postgres()
        elif command == "remove":
            remove_postgres()
        elif command == "logs":
            show_logs()
        elif command == "test":
            test_connection()
        elif command == "tables":
            list_tables()
        elif command == "load":
            load_large_file()
        elif command == "status":
            check_docker()
        else:
            print("Unknown command")
    else:
        print("""
🐳 Docker PostgreSQL Manager
===========================
Commands:
  python manage_docker.py status    - Check Docker status
  python manage_docker.py start     - Start PostgreSQL container
  python manage_docker.py stop      - Stop PostgreSQL container
  python manage_docker.py restart   - Restart PostgreSQL container
  python manage_docker.py create    - Create new PostgreSQL container
  python manage_docker.py remove    - Remove PostgreSQL container
  python manage_docker.py logs      - Show PostgreSQL logs
  python manage_docker.py test      - Test database connection
  python manage_docker.py tables    - List tables in database
  python manage_docker.py load      - Load large test file
        """)