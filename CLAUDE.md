# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Fashion Recommendations MLOps project using Databricks Asset Bundles. Implements multiple recommendation models (popularity baseline, age-based rules, LSTM, and ensemble) for H&M Fashion dataset using Unity Catalog, Feature Store, and MLflow.

## Common Commands

### Dependency Management (Poetry)
```bash
# Install dependencies
make install                    # Core dependencies only
make install-all               # All dependencies (viz, dl, dev)
poetry install --with viz      # Core + visualization

# Update requirements files for Databricks
make update-requirements       # Export Poetry deps to requirements.txt
make update-environments       # Update Databricks environment YAML files
```

### Databricks Bundle Operations
```bash
# Validate and deploy
make validate                  # Validate bundle configuration
make deploy                    # Deploy to dev (default)
make deploy-staging           # Deploy to staging
make deploy-prod              # Deploy to production

# Or use databricks CLI directly
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run data_engineering_job -t dev
```

### Running Workflows
```bash
# Data pipeline (load, features, splits)
databricks bundle run data_engineering_job -t dev

# Model training (all models)
databricks bundle run model_training_job -t dev

# Batch inference
databricks bundle run batch_inference_job -t dev
```

### Environment Deployment
```bash
make deploy-environments       # Deploy environment YAML files to workspace
```

## Architecture Overview

### Environment Strategy
Single Unity Catalog (`jongseob_demo`) with environment-specific schemas:
- **Dev**: `jongseob_demo.dev_fashion_recommendations`
- **Staging**: `jongseob_demo.staging_fashion_recommendations`
- **Prod**: `jongseob_demo.prod_fashion_recommendations`

Models and tables are registered per environment:
- Tables: `{catalog}.{schema}.{table_name}` (e.g., `jongseob_demo.dev_fashion_recommendations.articles_bronze`)
- Models: `{catalog}.{schema}.{model_name}` (e.g., `jongseob_demo.dev_fashion_recommendations.popularity_model`)

### Configuration System
Bundle variables in [databricks.yml](databricks.yml:19-58) are passed as parameters to all notebooks:
- `catalog_name`: Unity Catalog name (default: `jongseob_demo`)
- `schema_name`: Environment-specific schema (e.g., `dev_fashion_recommendations`)
- `experiment_name`: MLflow experiment path (split into data and models experiments)
- `model_name`: Model name for training notebooks

Notebooks should accept these as widgets:
```python
catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")
tables = get_table_config(catalog_name, schema_name)
```

### Table Organization (Bronze-Silver-Gold)
**Bronze** (raw data): `articles_bronze`, `customers_bronze`, `transactions_bronze`
**Silver** (cleaned): `train_transactions_silver`, `val_transactions_silver`, `test_transactions_silver`, ground truth tables
**Gold** (aggregated): `customer_recommendations_gold`, various model predictions tables

Configured in [config/catalog_config.py](config/catalog_config.py) with helper function `get_table_config(catalog_name, schema_name)` that returns environment-aware table names.

### Workflow Pipeline Structure
Workflows defined in [resources/](resources/) directory as YAML files:
1. **Data Engineering** ([data-engineering-workflow.yml](resources/data-engineering-workflow.yml)): load_data → create_features → create_splits
2. **Model Training** ([model-training-workflow.yml](resources/model-training-workflow.yml)): parallel training of popularity, age_rules models (LSTM and ensemble coming)
3. **Batch Inference** ([batch-inference-workflow.yml](resources/batch-inference-workflow.yml)): model serving and predictions

All tasks use serverless compute by default (no cluster configuration needed).

### MLflow Experiments
Two separate experiments per environment:
- **Data Experiment**: `/Users/{user}/experiments/{env}-fashion-recs-data` - tracks data quality metrics, feature statistics
- **Models Experiment**: `/Users/{user}/experiments/{env}-fashion-recs-models` - tracks model training runs, MAP@12 metrics

### Dependency Management Philosophy
Use Poetry locally for development, export minimal `requirements.txt` for Databricks:
- Core production deps (always): mlflow, databricks-feature-engineering, pandas, numpy, scikit-learn
- Viz group (optional): matplotlib, seaborn - only for analysis notebooks
- DL group (optional): torch, torchvision - only for LSTM model
- Dev group (local only): pytest, pytest-cov

Databricks serverless includes many packages pre-installed. Only install what's missing to reduce cold start time.

### Key Modules
- [config/catalog_config.py](config/catalog_config.py): Unity Catalog table names, `get_table_config()` helper for environment-aware access
- [config/paths.py](config/paths.py): Volume paths and file locations
- [utils/evaluation_utils.py](utils/evaluation_utils.py): MAP@K evaluation metrics for recommendations
- [data_engineering/notebooks/](data_engineering/notebooks/): Data pipeline notebooks (01_load_data, 02_create_features, 03_create_splits)
- [training/notebooks/](training/notebooks/): Model training notebooks (train_popularity, train_age_rules, train_lstm, train_ensemble)

### Data Flow
1. Raw CSV files in `/Volumes/jongseob_demo/fashion_recommendations/data/`
2. Load to Bronze tables via `01_load_data.py`
3. Create features and Feature Store tables via `02_create_features.py`
4. Create train/val/test splits via `03_create_splits.py`
5. Train models using splits, register to Unity Catalog
6. Batch inference generates recommendations to Gold tables

### Model Registration Pattern
Models are registered to Unity Catalog with format: `{catalog}.{schema}.{model_name}`
```python
import mlflow
mlflow.register_model(
    model_uri=f"runs:/{run_id}/model",
    name=f"{catalog_name}.{schema_name}.{model_name}"
)
```

## Testing
Tests located in [tests/](tests/) directory. Run with:
```bash
poetry run pytest
```

## Development Workflow
1. Work locally or in Databricks notebooks
2. Test changes with `make deploy` (dev environment)
3. Validate before staging: `make validate`
4. Deploy to staging: `make deploy-staging`
5. Verify in staging environment
6. Deploy to production: `make deploy-prod`

## Important Notes
- All notebooks must accept bundle parameters (`catalog_name`, `schema_name`, `experiment_name`) as widgets
- Use `get_table_config(catalog_name, schema_name)` from [config/catalog_config.py](config/catalog_config.py) for environment-aware table access
- Models are automatically created when registered via MLflow (no need to pre-create in bundle)
- Primary evaluation metric is MAP@12 (Mean Average Precision at K=12)
- Databricks serverless compute is used by default - no cluster configuration needed in workflows
