# Fashion Recommendations Dashboard

A FastAPI-based dashboard for fashion product recommendations and analytics.

## Features

- **Bestseller Analysis**: View top-selling products with filters
- **Customer Demographics**: Analyze customer age, membership, and subscription patterns
- **Time Series Analysis**: Track revenue, transactions, and customer trends over time
- **Product Explorer**: Search and browse products with pagination

## Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (create .env file)
cp env.example .env
# Edit .env with your Databricks credentials

# Run the app
uvicorn app:app --reload
```

## Deployment

```bash
# Deploy to Databricks Apps
databricks bundle deploy -t dev
```
