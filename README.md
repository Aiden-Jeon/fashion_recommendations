# Fashion Recommendations

<p align="center">
  <img src="https://img.shields.io/badge/Databricks-FF3621?style=for-the-badge&logo=databricks&logoColor=white" alt="Databricks"/>
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch"/>
  <img src="https://img.shields.io/badge/MLflow-0194E2?style=for-the-badge&logo=mlflow&logoColor=white" alt="MLflow"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
</p>

End-to-end fashion recommendation system built on Databricks, featuring data operations, machine learning pipelines, and an interactive analytics dashboard. This project demonstrates production-grade MLOps practices using **Databricks Asset Bundles**, **Unity Catalog**, **Feature Store**, and **MLflow**.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Components](#components)
  - [DataOps](#dataops---data-operations)
  - [MLOps](#mlops---machine-learning-operations)
  - [App](#app---analytics-dashboard)
- [Models](#models)
- [Development Workflow](#development-workflow)
- [Deployment](#deployment)
- [Contributing](#contributing)

## Overview

This project implements a complete fashion recommendation system using the **H&M Fashion dataset**. It showcases:

- **Multi-model ensemble**: Popularity baseline, age-based rules, LSTM sequential, and ensemble blending
- **Production MLOps**: Databricks Asset Bundles for infrastructure-as-code deployment
- **Data Governance**: Unity Catalog for data management and access control
- **Low-latency Serving**: Lakebase synced tables for OLTP access
- **Interactive Dashboard**: FastAPI-based analytics with real-time visualizations

### Key Features

| Feature | Description |
|---------|-------------|
| 🔄 **DataOps Pipeline** | Automated data ingestion from CSV to Delta Lake with Lakebase sync |
| 🧠 **ML Pipeline** | Feature engineering, model training, and batch inference workflows |
| 📊 **Analytics Dashboard** | Interactive product explorer, customer demographics, time series analysis |
| 🎯 **Personalization** | Customer-level recommendations with model comparison |
| 🚀 **Multi-Environment** | Dev/Staging/Prod environment support with isolated schemas |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Data Platform (Databricks)                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │   DataOps   │───▶│   MLOps     │───▶│  Lakebase   │◀──▶│  Databricks App │  │
│  │   (Data)    │    │   (Models)  │    │  (Sync)     │    │   (Dashboard)   │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────────┘  │
│        │                  │                   │                    │            │
│        ▼                  ▼                   ▼                    ▼            │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                        Unity Catalog (Data Governance)                     │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │ │
│  │  │   Bronze    │  │   Silver    │  │    Gold     │  │  Feature Store  │   │ │
│  │  │  (Raw Data) │  │  (Cleaned)  │  │ (Aggregated)│  │   (ML Ready)    │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                              MLflow (Experiments & Registry)               │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │ │
│  │  │ Data Experiments │  │ Model Experiments │  │ Unity Catalog Registry  │ │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
CSV Files → DataOps → Bronze Tables → MLOps Feature Engineering → Silver Tables
                                                ↓
                                      Feature Store Tables
                                                ↓
                                Model Training (Popularity, Age Rules, LSTM)
                                                ↓
                                       Ensemble Blending
                                                ↓
                                    Gold Tables (Predictions)
                                                ↓
                                   Lakebase Synced Tables
                                                ↓
                                    FastAPI Dashboard App
```

## Project Structure

```
fashion_recommendations/
├── README.md                        # This file
│
├── app/                             # 📊 Analytics Dashboard
│   ├── app.py                       # FastAPI application
│   ├── db.py                        # Database utilities (SQL, caching)
│   ├── settings.py                  # Configuration
│   ├── databricks.yml               # App bundle config
│   ├── templates/                   # Jinja2 HTML templates
│   └── static/                      # CSS styles
│
├── dataops/                         # 📥 Data Operations
│   ├── databricks.yml               # DataOps bundle config
│   ├── src/
│   │   ├── 01_load_data.ipynb       # CSV → Bronze tables
│   │   ├── 02_create_features.ipynb # Aggregated features
│   │   └── fashion_rec_dataops/     # Shared utilities
│   ├── config/                      # Catalog & path configs
│   ├── resources/                   # Workflow definitions
│   └── scripts/                     # Management scripts
│
├── mlops/                           # 🧠 ML Operations
│   ├── databricks.yml               # MLOps bundle config
│   ├── CLAUDE.md                    # AI assistant guidance
│   │
│   ├── data_engineering/
│   │   └── notebooks/
│   │       ├── 01_create_features.ipynb  # Feature Store tables
│   │       └── 02_create_splits.ipynb    # Train/Val/Test splits
│   │
│   ├── training/
│   │   └── notebooks/
│   │       ├── train_popularity.ipynb    # Popularity baseline
│   │       ├── train_age_rules.ipynb     # Age-based segmentation
│   │       ├── train_lstm.ipynb          # LSTM sequential model
│   │       └── train_ensemble.ipynb      # Ensemble blending
│   │
│   ├── deployment/
│   │   └── batch_inference/              # Prediction generation
│   │
│   ├── config/
│   │   ├── catalog_config.py        # Unity Catalog tables
│   │   ├── model_config.py          # Model hyperparameters
│   │   └── paths.py                 # Volume paths
│   │
│   ├── utils/                       # Shared utilities
│   │   ├── data_utils.py            # Data loading
│   │   ├── feature_utils.py         # Feature engineering
│   │   ├── evaluation_utils.py      # MAP@K metrics
│   │   └── pytorch_utils.py         # PyTorch helpers
│   │
│   ├── resources/                   # Workflow YAML definitions
│   │   ├── feature-engineering-workflow.yml
│   │   ├── model-training-workflow.yml
│   │   └── batch-inference-workflow.yml
│   │
│   └── environments/                # Databricks environment configs
│       ├── base-core.yml            # Core dependencies
│       ├── base-viz.yml             # + Visualization
│       └── base-dl.yml              # + Deep learning
│
└── assets/                          # Additional resources
```

## Getting Started

### Prerequisites

- **Databricks CLI** installed and configured
- **Python 3.11+**
- Access to a **Databricks workspace** with Unity Catalog enabled
- **SQL Warehouse** for Lakebase synced tables

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fashion_recommendations
   ```

2. **Set up DataOps**
   ```bash
   cd dataops
   
   # Using uv (recommended)
   uv sync --dev
   
   # Or using pip
   pip install -r requirements.txt
   ```

3. **Set up MLOps**
   ```bash
   cd ../mlops
   
   # Using Poetry (recommended)
   make install-all
   
   # Or using pip
   pip install -r requirements.txt
   ```

4. **Set up App** (for local development)
   ```bash
   cd ../app
   pip install -r requirements.txt
   cp env.example .env
   # Edit .env with your Databricks credentials
   ```

### Quick Start

1. **Deploy DataOps and load data**
   ```bash
   cd dataops
   make deploy-dev
   make run-workflow
   ```

2. **Deploy MLOps and train models**
   ```bash
   cd ../mlops
   make deploy-dev
   make run-ml-pipeline  # Runs features → training → inference
   ```

3. **Deploy App**
   ```bash
   cd ../app
   databricks bundle deploy -t dev
   ```

## Components

### DataOps - Data Operations

Handles raw data ingestion and application-specific feature preparation.

| Notebook | Purpose |
|----------|---------|
| `01_load_data.ipynb` | Load CSV files to Bronze Delta tables |
| `02_create_features.ipynb` | Create aggregated feature tables for analytics |

**Key Features:**
- Automatic Lakebase sync for low-latency OLTP access
- SQL-based synced table management
- Change Data Feed enabled for incremental updates

**Commands:**
```bash
cd dataops
make deploy-dev          # Deploy to dev
make run-workflow        # Run full pipeline
make setup-synced-tables # Create Lakebase synced tables
```

[📖 DataOps README](dataops/README.md)

---

### MLOps - Machine Learning Operations

Production-ready ML pipeline for training and deploying recommendation models.

| Workflow | Purpose |
|----------|---------|
| Feature Engineering | Create Feature Store tables and train/val/test splits |
| Model Training | Train all recommendation models in parallel |
| Batch Inference | Generate customer recommendations |

**Environment Strategy:**
- Single catalog (`jongseob_demo`) with environment-specific schemas
- Dev: `dev_fashion_recommendations`
- Staging: `staging_fashion_recommendations`
- Prod: `prod_fashion_recommendations`

**Commands:**
```bash
cd mlops
make validate            # Validate bundle config
make deploy-dev          # Deploy to dev (auto-updates notebooks)
make run-features        # Run feature engineering
make run-training        # Train all models
make run-batch-inference # Generate predictions
make run-ml-pipeline     # Run entire pipeline
```

[📖 MLOps README](mlops/README.md)

---

### App - Analytics Dashboard

FastAPI-based interactive dashboard for fashion analytics and personalized recommendations.

| Page | Description |
|------|-------------|
| **Bestsellers** | Top-selling products with category filters |
| **Demographics** | Customer age, membership, subscription analysis |
| **Time Series** | Revenue, transactions, customer trends over time |
| **Product Explorer** | Search and browse products with pagination |
| **Customers** | Customer list with spending metrics |
| **Transactions** | Transaction history lookup |
| **Personalization** | Model-specific recommendation comparison |

**Key Features:**
- On-Behalf-Of (OBO) authentication for Databricks Apps
- Query caching with TTL
- Interactive Plotly visualizations
- Product image serving from Volumes

**Local Development:**
```bash
cd app
uvicorn app:app --reload
```

[📖 App README](app/README.md)

## Models

### Model Overview

| Model | Description | MAP@12 |
|-------|-------------|--------|
| **Popularity** | Recency-weighted product popularity baseline | ~0.015 |
| **Age Rules** | Age-segment specific recommendations | ~0.018 |
| **LSTM** | Sequential purchase prediction with attention | ~0.022 |
| **Ensemble** | Weighted blend of all base models | ~0.025 |

### Model Details

#### Popularity Model
- Time-decayed popularity scoring
- Configurable recency window and decay factor
- Global top-N recommendations

#### Age Rules Model
- Customer age binning (18-25, 25-35, 35-45, 45-55, 55+)
- Segment-specific product rankings
- Fallback to global popularity for cold-start

#### LSTM Model
- PyTorch-based sequential model
- Distributed training on A10 GPUs
- Embedding layer + 2-layer LSTM + attention
- Trained on customer purchase sequences

#### Ensemble Model
- Configurable weight blending
- Default weights: Popularity (0.2), Age Rules (0.3), LSTM (0.5)
- Re-ranking with duplicate removal

### Configuration

Edit `mlops/config/model_config.py`:

```python
POPULARITY_CONFIG = {
    "n_days": 7,
    "alpha": 0.5,  # recency weight decay
    "top_n": 12
}

LSTM_CONFIG = {
    "embedding_dim": 64,
    "hidden_dim": 128,
    "num_layers": 2,
    "dropout": 0.3,
    "batch_size": 256,
    "num_epochs": 10,
    "learning_rate": 0.001
}

ENSEMBLE_CONFIG = {
    "models": ["popularity", "age_rules", "lstm"],
    "weights": {
        "popularity": 0.2,
        "age_rules": 0.3,
        "lstm": 0.5
    }
}
```

## Development Workflow

### Standard Process

1. **Local Development**
   - Work in notebooks or IDE
   - Test with `dev` target

2. **Validate Changes**
   ```bash
   make validate
   ```

3. **Deploy to Dev**
   ```bash
   make deploy-dev
   ```

4. **Test in Dev Environment**
   ```bash
   make run-training
   ```

5. **Deploy to Staging**
   ```bash
   make deploy-staging
   ```

6. **Production Deployment**
   ```bash
   make deploy-prod
   ```

### Dependency Management

**MLOps uses Poetry:**
```bash
poetry add new-package           # Add dependency
make update-requirements         # Export to requirements.txt
make update-environments         # Update Databricks environment YAML
```

**DataOps uses uv:**
```bash
uv add new-package              # Add dependency
uv sync                         # Sync environment
```

## Deployment

### Databricks Asset Bundles

All components use **Databricks Asset Bundles** for deployment:

| Component | Bundle Name | Targets |
|-----------|-------------|---------|
| DataOps | `fashion_recommendations_dataops` | dev, prod |
| MLOps | `fashion_recommendations_mlops` | dev, staging, prod |
| App | `fashion_recommendations_app` | dev |

### Environment Variables

For local development, set these environment variables:

```bash
# Databricks authentication
export DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
export DATABRICKS_TOKEN=your-token

# Unity Catalog
export CATALOG_NAME=jongseob_demo
export SCHEMA_NAME=dev_fashion_recommendations
```

### Monitoring

- **MLflow Experiments**: Track model metrics and data quality
- **Job Run History**: Monitor workflow execution in Databricks
- **Evaluation Metric**: MAP@12 (Mean Average Precision at K=12)

## Data Tables

### Bronze Layer (Raw)
| Table | Description |
|-------|-------------|
| `articles_bronze` | Product catalog |
| `customers_bronze` | Customer profiles |
| `transactions_bronze` | Purchase history |

### Silver Layer (Cleaned)
| Table | Description |
|-------|-------------|
| `train_transactions_silver` | Training set transactions |
| `val_transactions_silver` | Validation set transactions |
| `test_transactions_silver` | Test set transactions |
| `val_ground_truth_silver` | Validation labels |
| `test_ground_truth_silver` | Test labels |

### Gold Layer (Aggregated)
| Table | Description |
|-------|-------------|
| `popularity_predictions_gold` | Popularity model predictions |
| `age_rules_predictions_gold` | Age rules model predictions |
| `lstm_predictions_gold` | LSTM model predictions |
| `ensemble_predictions_gold` | Ensemble predictions |
| `customer_recommendations_gold` | Final recommendations |

### Synced Tables (Lakebase)
| Table | Purpose |
|-------|---------|
| `articles_synced` | Product data for dashboard |
| `customers_synced` | Customer data for dashboard |
| `product_sales_summary_synced` | Sales aggregations |
| `customer_demographics_synced` | Customer analytics |
| `time_series_sales_synced` | Time series data |
| `predictions_synced` | Model predictions for personalization |

## Contributing

1. Create a feature branch
2. Make changes
3. Test with `dev` target
4. Submit pull request

## Resources

- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/index.html)
- [MLflow on Databricks](https://docs.databricks.com/mlflow/index.html)
- [Unity Catalog](https://docs.databricks.com/data-governance/unity-catalog/index.html)
- [Feature Store](https://docs.databricks.com/machine-learning/feature-store/index.html)
- [Databricks Apps](https://docs.databricks.com/apps/index.html)

---

<p align="center">
  Built with ❤️ using Databricks
</p>

