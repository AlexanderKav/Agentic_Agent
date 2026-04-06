import psycopg2
import random
from datetime import datetime, timedelta

# Connect to your test-postgres container
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="testpass",
    database="testdb"
)
cursor = conn.cursor()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS sales_data (
    id SERIAL PRIMARY KEY,
    date DATE,
    customer VARCHAR(100),
    product VARCHAR(100),
    region VARCHAR(50),
    revenue DECIMAL(10,2),
    cost DECIMAL(10,2),
    currency VARCHAR(3),
    quantity INTEGER,
    payment_status VARCHAR(20)
)
""")

# Insert sample data
customers = ['Acme Corp', 'BetaCo', 'Delta Inc', 'Gamma LLC', 'Zeta Corp']
products = ['Enterprise Plan', 'Premium Plan', 'Basic Plan']
regions = ['US', 'EU', 'APAC', 'LATAM']
currencies = ['USD', 'EUR', 'GBP']
payment_statuses = ['paid', 'pending', 'failed']

data = []
start_date = datetime(2024, 1, 1)
for i in range(200):
    date = start_date + timedelta(days=i % 365)
    data.append((
        date,
        random.choice(customers),
        random.choice(products),
        random.choice(regions),
        round(random.uniform(100, 10000), 2),
        round(random.uniform(50, 5000), 2),
        random.choice(currencies),
        random.randint(1, 10),
        random.choice(payment_statuses)
    ))

cursor.executemany("""
INSERT INTO sales_data (date, customer, product, region, revenue, cost, currency, quantity, payment_status)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
""", data)

conn.commit()

cursor.execute("SELECT COUNT(*) FROM sales_data")
count = cursor.fetchone()[0]
print(f"✅ Inserted {count} rows into test-postgres!")

# Show sample
cursor.execute("SELECT date, customer, product, revenue FROM sales_data LIMIT 5")
print("\n📋 Sample data:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} - {row[2]} - ${row[3]}")

cursor.close()
conn.close()
print("\n🎉 Ready for testing!")