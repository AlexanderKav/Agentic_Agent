import sqlite3
import sys

# Connect to your SQLite database
db_path = "agentic_analyst.db"  # Adjust path if different

def delete_user_by_username(username):
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First, check if user exists
        cursor.execute("SELECT id, username, email FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if user:
            print(f"📋 Found user: ID={user[0]}, Username={user[1]}, Email={user[2]}")
            
            # Delete user's analysis history first (due to foreign key)
            cursor.execute("DELETE FROM analysis_history WHERE user_id = ?", (user[0],))
            history_deleted = cursor.rowcount
            print(f"🗑️ Deleted {history_deleted} analysis history records")
            
            # Delete the user
            cursor.execute("DELETE FROM users WHERE id = ?", (user[0],))
            conn.commit()
            print(f"✅ Successfully deleted user '{username}'")
        else:
            print(f"❌ User '{username}' not found")
            
        # Show remaining users
        cursor.execute("SELECT id, username, email FROM users")
        users = cursor.fetchall()
        if users:
            print("\n📋 Remaining users:")
            for u in users:
                print(f"   - {u[1]} ({u[2]})")
        else:
            print("\n📋 No users remaining in database")
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Default username to delete
    username = "testuser"
    
    # Allow command line argument
    if len(sys.argv) > 1:
        username = sys.argv[1]
    
    print(f"🗑️ Attempting to delete user: {username}")
    delete_user_by_username(username)