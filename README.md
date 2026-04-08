# 🤖 Agentic Analyst - AI-Powered Business Intelligence Platform

[![Live Demo](https://img.shields.io/badge/demo-live-green)](https://agentic-analyst.vercel.app)
[![API Docs](https://img.shields.io/badge/API-docs-blue)](https://agentic-analyst-backend.onrender.com/api/docs)
[![Tests](https://img.shields.io/badge/tests-48%20passing-brightgreen)]()
[![Deployed](https://img.shields.io/badge/deployed-Render%20%26%20Vercel-success)]()
[![Docker](https://img.shields.io/badge/docker-ready-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

**Agentic Analyst** is an AI-powered business intelligence platform that enables users to analyze business data through natural language conversations. Simply upload your data or connect your database, ask questions in plain English, and get instant insights, forecasts, and visualizations.

> 🚀 **Live Demo:** [https://agentic-analyst.vercel.app](https://agentic-analyst.vercel.app)

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🎯 Use Cases](#-use-cases)
- [🏗️ Architecture](#️-architecture)
- [🚀 Quick Start](#-quick-start)
- [📊 Data Sources](#-data-sources)
- [💬 Example Questions](#-example-questions)
- [🔧 Local Development](#-local-development)
- [🐳 Docker Setup](#-docker-setup)
- [☁️ Deployment](#️-deployment)
- [🛠️ Technology Stack](#️-technology-stack)
- [📁 Project Structure](#-project-structure)
- [🔐 Security Features](#-security-features)
- [📈 Monitoring & Observability](#-monitoring--observability)
- [📊 Performance Metrics](#-performance-metrics)
- [💰 Cost Analysis](#-cost-analysis)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## ✨ Features

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
- **Beautiful HTML Templates** - Professional email design
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

## 🎯 Use Cases

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

## 🏗️ Architecture

### Multi-Agent AI System
| Agent | Responsibility |
|-------|----------------|
| **Question Classifier** | Classifies question type, extracts time periods, determines relevance |
| **Planner Agent** | Creates execution plan, selects appropriate tools |
| **Analytics Agent** | Computes KPIs, runs forecasts, detects anomalies |
| **Insight Agent** | Generates LLM-powered insights and recommendations |
| **Visualization Agent** | Creates charts and visualizations |

Schema Mapper - Maps raw dataframe columns to standard schema with currency conversion

CRITICAL BUSINESS FEATURE: This module solves a fundamental real-world problem that every 
business analyst faces - data from different sources never has the same column names!

Example: One customer exports "Transaction Date", another uses "sale_date", a third uses 
"created_at". Without this mapper, the AI would fail to understand any of them. With this 
mapper, ALL work seamlessly.

This is what makes the platform truly "plug and play" - users don't need to rename their 
columns or follow any specific format. They just upload their data and start asking questions.

WHY THE SCHEMA MAPPER IS CRITICAL FOR BUSINESS USERS:

1. NO COLUMN RENAMING REQUIRED
   Problem: Business users don't want to rename columns before uploading.
   Solution: SchemaMapper automatically figures out what each column represents.
   
   Example: "Transaction Date", "sale_date", "order_date" → ALL map to "date"

2. MULTI-CURRENCY SUPPORT
   Problem: International businesses deal with multiple currencies.
   Solution: Automatically converts all revenue to USD for consistent analysis.
   
   Example: €100 + £100 + $100 → All normalized to USD

3. INTERNATIONAL NUMBER FORMATS
   Problem: Different countries use different number formats.
   Solution: Handles both US (1,234.56) and European (1.234,56) formats.

4. FUZZY MATCHING
   Problem: Typos and variations in column names.
   Solution: Fuzzy matching finds "Transactin Date" when user meant "Transaction Date"

5. EXTENSIBLE
   Problem: Every business has unique column names.
   Solution: Add custom mappings without changing core code.

6. CLEAR FEEDBACK
   Problem: Users need to know what happened to their data.
   Solution: Detailed warnings about unmapped columns and conversion statistics.

THIS IS WHAT MAKES THE PRODUCT "JUST WORK" FOR BUSINESS USERS!
"""


## 🚀 Quick Start

### For Users (No Installation Required)

1. **Visit:** [https://agentic-analyst.vercel.app](https://agentic-analyst.vercel.app)
2. **Create an account** (email verification required) or use username: Tester123 password Testpass123
3. **Upload your data** or connect a database
4. **Ask a question** in natural language
5. **Get insights** with charts and recommendations

### Sample Questions to Try

📊 Revenue Analysis:
• "Show me revenue by product"
• "What are the sales trends over time?"
• "Which customers generate the most revenue?"

🔮 Forecasting:
• "Forecast revenue for next quarter"
• "What is most likely to be the most successful product for Q1 2025?"
• "Predict revenue for next 6 months"

⚠️ Risk Detection:
• "Detect anomalies in the data"
• "Are there any unusual patterns?"
• "Show me revenue spikes"

📈 Performance:
• "How is the business performing?"
• "What are the risks in our data?"
• "Give me an overview"


# Requirements:

Must contain at least date and revenue columns (case-insensitive)

Minimum 5 rows, maximum 100,000 rows

Date format: YYYY-MM-DD (or any pandas-parsable format)

Revenue must be numeric

**Required format:**
```csv
date,revenue,product,customer,region,quantity,cost
2024-01-01,10000,Enterprise Plan,Acme Corp,North America,5,5000
2024-01-02,5000,Premium Plan,Beta LLC,Europe,3,2500

```Google Sheets
Share your sheet with the service account email: agentic-analyst-bot@agentic-analyst-489012.iam.gserviceaccount.com
Grant "Viewer" (read-only) access

Enter the Sheet ID (from the URL)

Enter the Sheet/Tab Name (case-sensitive)

```PostgreSQL / MySQL
Connection parameters:

Host: your-db-host.com
Port: 5432 (PostgreSQL) / 3306 (MySQL)
Database: your_database
Username: your_username
Password: your_password
Table: your_table
Requirements:

```SQLite
Upload .db, .sqlite, or .sqlite3 files

Select the table containing your data

File size limit: 10MB



# Prerequisites
Python 3.11+

Node.js 18+

PostgreSQL (optional, SQLite works for development)

Redis (optional, for caching)

Docker (optional)

Backend Setup
bash
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

# Run the backend
python -m app.main
Frontend Setup
bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create environment file
echo "REACT_APP_API_URL=http://localhost:8000/api/v1" > .env

# Start the development server
npm start


# API Keys
OPENAI_API_KEY=sk-your-openai-api-key
SENDGRID_API_KEY=SG.your-sendgrid-api-key

# Database (optional - SQLite used by default)
DATABASE_URL=postgresql://user:pass@localhost:5432/agentic_analyst

# Security - Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-secret-key-min-32-chars
AUDIT_SECRET_KEY=your-audit-secret-key
DB_ENCRYPTION_KEY=your-encryption-key
SECRETS_MASTER_PASSWORD=your-master-password

# Frontend URL (for email links)
FRONTEND_URL=http://localhost:3000


# 🛠️ Technology Stack
# Backend
Category	Technologies
Framework	FastAPI, Uvicorn
Database	PostgreSQL, SQLite, Redis
AI/ML	OpenAI GPT-4o-mini, LangChain, Statsmodels (ARIMA), Scikit-learn
Data Processing	Pandas, NumPy, SciPy
Visualization	Matplotlib, Plotly
Authentication	JWT, bcrypt
Email	SendGrid API
Security	Cryptography, pgcrypto, SlowAPI
Async	asyncio, BackgroundTasks

# Frontend
Category	Technologies
Framework	React 18
UI Library	Material-UI (MUI)
HTTP Client	Axios
File Upload	React Dropzone
Routing	React Router DOM
State Management	React Context API

# DevOps & Infrastructure
Category	Technologies
Containerization	Docker, Docker Compose
CI/CD	GitHub Actions (7 workflows)
Hosting	Vercel (frontend), Render (backend)
Database Hosting	Render PostgreSQL
Cache	Render Redis (Key Value)
Email	SendGrid
Monitoring	Custom audit, performance, cost tracking
