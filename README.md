# 🤖 Agentic Analyst - AI-Powered Business Intelligence Platform

[![Live Demo](https://img.shields.io/badge/Live-Demo-green?style=for-the-badge)](https://agentic-analyst.vercel.app)
[![API Docs](https://img.shields.io/badge/API-Docs-blue?style=for-the-badge)](https://agentic-analyst-backend.onrender.com/api/docs)
[![Tests](https://img.shields.io/badge/Tests-48%20Passing-brightgreen?style=for-the-badge)](https://github.com/AlexanderKav/agentic-analyst/actions)
[![Deployed](https://img.shields.io/badge/Deployed-Render%20%26%20Vercel-success?style=for-the-badge)](https://agentic-analyst.vercel.app)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Agentic Analyst** is an AI-powered business intelligence platform that enables users to analyze business data through natural language conversations. Simply upload your data or connect your database, ask questions in plain English, and get instant insights, forecasts, and visualizations.

> 🚀 **Live Demo:** [https://agentic-analyst.vercel.app](https://agentic-analyst.vercel.app)

---

## 📋 Table of Contents

- [Features](#features)
- [Use Cases](#use-cases)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Example Workflow](#example-workflow)
- [Example Questions](#example-questions)
- [Data Requirements](#data-requirements)
- [Local Development](#local-development)
- [Technology Stack](#technology-stack)

---

## Features

### 🔌 Multi-Source Data Integration

| Source | Format | Status |
|--------|--------|--------|
| **CSV/Excel** | `.csv`, `.xlsx`, `.xls` | ✅ Drag & drop upload |
| **Google Sheets** | Read-only access | ✅ Service account auth |
| **PostgreSQL** | Direct connection | ✅ SSL support |
| **MySQL** | Direct connection | ✅ SSL support |
| **SQLite** | File upload | ✅ Table selection |

### 🧠 Natural Language Understanding

- **Question Classification** - Identifies intent (forecast, risk, revenue analysis, performance, customer analysis)
- **Time Period Extraction** - Parses "Q1 2025", "next quarter", "last 6 months", "January 2024"
- **Column Mapping** - Automatically maps any column names to standard schema
- **Relevance Filtering** - Prevents LLM hallucinations on irrelevant questions

### 📊 AI-Powered Analytics

| Analysis Type | Description | Example |
|---------------|-------------|---------|
| **Revenue Analysis** | Breakdown by product, customer, region | "Show me revenue by product" |
| **Forecasting** | ARIMA time series with confidence intervals | "Forecast revenue for next quarter" |
| **Anomaly Detection** | Statistical outlier detection | "Detect anomalies in revenue" |
| **KPI Calculations** | Revenue, profit margin, average order value | "What's our profit margin?" |
| **Seasonality** | Automatic seasonal pattern detection | "Are there seasonal patterns?" |
| **Growth Analysis** | Month-over-month trends | "How has revenue grown?" |

### 📈 Visualizations

- **Automatic chart generation** - Bar charts, line plots, time series
- **Product forecast charts** - Visual comparison of product forecasts
- **High-quality PNG output** - Ready for reports and presentations
- **Email attachments** - Charts included in automated reports

### 👤 User Management

- **JWT Authentication** - Secure token-based auth with refresh
- **Email Verification** - SendGrid-powered verification emails
- **Password Reset** - Secure flow with expiring tokens (24 hours)
- **Analysis History** - All analyses saved per user
- **Rate Limiting** - 10 requests/minute on sensitive endpoints

### 📧 Email Reporting

- **Analysis Results** - Send reports to any email address
- **JSON Attachments** - Complete raw results
- **Chart Attachments** - PNG images included
- **Test Endpoint** - Verify email configuration

### 🔐 Security

| Feature | Implementation |
|---------|----------------|
| Password Hashing | bcrypt with salt |
| Database Encryption | pgcrypto (PostgreSQL), Fernet (SQLite) |
| Key Rotation | Automatic 90-day rotation |
| Audit Logging | HMAC-signed tamper-proof logs |
| SQL Injection | Parameterized queries (SQLAlchemy) |
| CORS | Configurable allowed origins |
| Rate Limiting | SlowAPI (10 req/min for login) |

### 📊 Monitoring & Observability

- **Audit Logging** - Tamper-proof JSONL logs with HMAC hash chaining
- **Performance Tracking** - Tool execution timing, p95 latency, error rates
- **Cost Tracking** - LLM token usage and cost calculation per request
- **Health Checks** - `/health` endpoint for uptime monitoring
- **Self-Healing** - Automatic failure analysis and recovery suggestions

---

## Use Cases

### 📊 Sales Analysis
> *"Show me revenue by product for the last quarter"*

Get instant breakdowns of sales performance across products, customers, and regions with trend analysis.

### 🔮 Forecasting
> *"What is most likely to be the most successful product for Q1 2025?"*

Predict future revenue trends using ARIMA time series forecasting with confidence intervals and product-level projections.

### ⚠️ Risk Detection
> *"Detect anomalies in revenue for the past 6 months"*

Automatically identify unusual patterns, spikes, or drops in your business data with statistical outlier detection.

### 📈 Performance Overview
> *"How is the business performing?"*

Get a comprehensive dashboard with KPIs, top customers, top products, trend analysis, and risk assessment.

### 🎯 Customer Insights
> *"Who are my top customers and what are they buying?"*

Analyze customer behavior, retention patterns, lifetime value, and purchase preferences.

### 📦 Product Analysis
> *"Describe how the Basic Plan product is performing"*

Get detailed product performance analysis with revenue trends, anomalies, and actionable recommendations.

---

## Architecture

### Multi-Agent AI System

| Agent | Responsibility |
|-------|----------------|
| **Question Classifier** | Classifies question type, extracts time periods, determines relevance |
| **Planner Agent** | Creates execution plan, selects appropriate tools |
| **Analytics Agent** | Computes KPIs, runs forecasts, detects anomalies |
| **Insight Agent** | Generates LLM-powered insights and recommendations |
| **Visualization Agent** | Creates charts and visualizations |

### Schema Mapper - Critical Business Feature

This module solves a fundamental real-world problem that every business analyst faces - data from different sources never has the same column names!

**Example:** One customer exports "Transaction Date", another uses "sale_date", a third uses "created_at". Without this mapper, the AI would fail to understand any of them. With this mapper, ALL work seamlessly.

**Why the Schema Mapper is Critical:**

1. **NO COLUMN RENAMING REQUIRED** - "Transaction Date", "sale_date", "order_date" → ALL map to "date"
2. **MULTI-CURRENCY SUPPORT** - €100 + £100 + $100 → All normalized to USD
3. **INTERNATIONAL NUMBER FORMATS** - Handles both US (1,234.56) and European (1.234,56) formats
4. **FUZZY MATCHING** - Finds "Transactin Date" when user meant "Transaction Date"
5. **EXTENSIBLE** - Add custom mappings without changing core code
6. **CLEAR FEEDBACK** - Detailed warnings about unmapped columns and conversion statistics

---

## Quick Start

### For Users (No Installation Required)

1. **Visit:** [https://agentic-analyst.vercel.app](https://agentic-analyst.vercel.app)
2. **Direct Download:** Test valid and/or invalid data sources [test_files.zip](https://github.com/AlexanderKav/agentic-analyst/raw/main/test_files.zip)
3. **Create an account** (email verification required) or use username: `Tester123` & password: `Testpass123`
4. **Upload your data** or connect a database
5. **Ask a question** in natural language
6. **Get insights** with charts and recommendations

### Sample Questions to Try

**📊 Revenue Analysis:**
- "Show me revenue by product"
- "What are the sales trends over time?"
- "Which customers generate the most revenue?"

**🔮 Forecasting:**
- "Forecast revenue for next quarter"
- "What is most likely to be the most successful product for Q1 2025?"
- "Predict revenue for next 6 months"

**⚠️ Risk Detection:**
- "Detect anomalies in the data"
- "Are there any unusual patterns?"
- "Show me revenue spikes"

**📈 Performance:**
- "How is the business performing?"
- "What are the risks in our data?"
- "Give me an overview"

---

## Example Workflow

### 1. User login
<img width="1900" height="891" alt="Screenshot 2026-04-08 142745" src="https://github.com/user-attachments/assets/47bd6c44-6041-4c30-bf1a-8cc4f1620c72" />

### 2. User connect business data
<img width="1884" height="869" alt="image" src="https://github.com/user-attachments/assets/9929edc4-e59c-432c-be10-7002e1d67665" />

### 3. User successfully connects data source
<img width="1877" height="909" alt="image" src="https://github.com/user-attachments/assets/2cb1133b-3dd2-4250-ab37-68efcd03ee22" />

### 4. Asks a question in relation to data
<img width="1897" height="709" alt="image" src="https://github.com/user-attachments/assets/cdfde6c4-7c04-40d2-8bc0-2b3e05b5ef0d" />

### 5. Example of output
<img width="1838" height="615" alt="image" src="https://github.com/user-attachments/assets/2b38b952-9f49-4e37-9ea4-a1cc2b87a89a" />

<img width="1851" height="825" alt="image" src="https://github.com/user-attachments/assets/64008467-600f-495b-842a-bc30f15f3029" />

<img width="1851" height="725" alt="image" src="https://github.com/user-attachments/assets/196a5ebd-3b83-4ff9-8504-5502f20e8f83" />

<img width="1874" height="605" alt="image" src="https://github.com/user-attachments/assets/a956ebff-fc8f-4661-bbda-6f8f55807c94" />

---

## Example Questions

See the [Sample Questions to Try](#sample-questions-to-try) section above.

### Data Requirements

- Must contain at least `date` and `revenue` columns (case-insensitive)
- Minimum 5 rows, maximum 100,000 rows
- Date format: YYYY-MM-DD (or any pandas-parsable format)
- Revenue must be numeric

### Google Sheets Connection

1. Share your sheet with the service account email: `agentic-analyst-bot@agentic-analyst-489012.iam.gserviceaccount.com`
2. Grant "Viewer" (read-only) access
3. Enter the Sheet ID (from the URL)
4. Enter the Sheet/Tab Name (case-sensitive)

### PostgreSQL / MySQL Connection

Connection parameters:
- **Host:** your-db-host.com
- **Port:** 5432 (PostgreSQL) / 3306 (MySQL)
- **Database:** your_database
- **Username:** your_username
- **Password:** your_password
- **Table:** your_table

### SQLite Connection

1. Upload `.db`, `.sqlite`, or `.sqlite3` files
2. Select the table containing your data
3. File size limit: 10MB

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (optional, SQLite works for development)
- Redis (optional, for caching)
- Docker (optional)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/AlexanderKav/agentic-analyst.git
cd agentic-analyst

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Edit .env with your API keys
# OPENAI_API_KEY=sk-...
# SENDGRID_API_KEY=SG...
Database (optional - SQLite used by default)
DATABASE_URL=postgresql://user:pass@localhost:5432/agentic_analyst

# Security - Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-secret-key-min-32-chars
AUDIT_SECRET_KEY=your-audit-secret-key
DB_ENCRYPTION_KEY=your-encryption-key
SECRETS_MASTER_PASSWORD=your-master-password

# Run the backend
python -m app.main
```

### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create environment file
echo "REACT_APP_API_URL=http://localhost:8000/api/v1" > .env

# Start the development server
npm start
```

### Docker Setup
```bash
# Build and run all services
docker-compose -f docker/docker-compose.dev.yml up --build

# Build the production image
docker build -f docker/Dockerfile.prod -t agentic-analyst .

# Run the container
docker run -p 8000:8000 --env-file .env agentic-analyst

# Services start at:
# - Backend: http://localhost:8000
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379

# Start all services
docker-compose -f docker/docker-compose.prod.yml up -d

# View logs
docker-compose -f docker/docker-compose.prod.yml logs -f app

# Stop services
docker-compose -f docker/docker-compose.prod.yml down

# Stop and remove volumes (reset database)
docker-compose -f docker/docker-compose.prod.yml down -v
``` 

## Technology Stack

### Backend

- **Framework:** FastAPI
- **Database:** PostgreSQL, SQLite, Redis
- **AI/ML:** OpenAI GPT-4o-mini, LangChain, Statsmodels (ARIMA), Scikit-learn
- **Data Processing:** Pandas, NumPy, SciPy
- **Visualization:** Matplotlib, Plotly
- **Authentication:** JWT, bcrypt
- **Email:** SendGrid API
- **Security:** Cryptography, pgcrypto, SlowAPI
- **Async:** asyncio, BackgroundTasks

### Frontend

- **Framework:** React 18
- **UI Library:** Material-UI (MUI)
- **HTTP Client:** Axios
- **File Upload:** React Dropzone
- **Routing:** React Router DOM
- **State Management:** React Context API

### DevOps & Infrastructure

- **Containerization:** Docker, Docker Compose
- **CI/CD:** GitHub Actions (7 workflows)
- **Hosting:** Vercel (frontend), Render (backend)
- **Database Hosting:** Render PostgreSQL
- **Cache:** Render Redis (Key Value)
- **Email:** SendGrid
- **Monitoring:** Custom audit, performance, cost tracking
