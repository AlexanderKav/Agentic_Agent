import requests

# Your backend URL
BASE_URL = "https://agentic-analyst-backend.onrender.com/api/v1"

# First, login to get a token
def login(username, password):
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={"username": "Testuser123", "password": "Testpass123"}
    )
    response.raise_for_status()
    return response.json()["access_token"]

# Delete a user (if you have admin endpoint)
def delete_user(token, username):
    response = requests.delete(
        f"{BASE_URL}/auth/admin/delete-user/{username}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()

# Or directly via database connection (using psycopg2)
def delete_user_via_db(username):
    import psycopg2
    import os
    
    # Get your Render database URL from environment or enter manually
    DATABASE_URL = "postgresql://agentic_analyst_db_user:BL1XayxOVoyigUlaHeXOubNh9UCROFUE@dpg-d79q8vpr0fns73eme7l0-a.frankfurt-postgres.render.com/agentic_analyst_db"
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("DELETE FROM users WHERE username = %s", (username,))
    conn.commit()
    
    print(f"Deleted user: {username}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    # Option 1: Using API (needs admin endpoint)
    # token = login("your_admin_username", "your_password")
    # result = delete_user(token, "testuser123")
    
    # Option 2: Direct database connection
    delete_user_via_db("Testuser123")