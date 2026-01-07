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
# Validate bundle configuration
make validate                  # Validate bundle configuration

# Deploy with automatic notebook environment update (RECOMMENDED)
make deploy-dev               # Update notebooks + deploy to dev
make deploy-staging           # Update notebooks + deploy to staging
make deploy-prod              # Update notebooks + deploy to prod
make deploy                   # Alias for deploy-dev

# Update notebook environment metadata only (before manual deploy)
make update-notebooks-dev     # Update notebook metadata for dev
make update-notebooks-staging # Update notebook metadata for staging
make update-notebooks-prod    # Update notebook metadata for prod

# Or use databricks CLI directly (after updating notebooks)
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run data_engineering_workflow -t dev
```

### Running Workflows
Workflow job names follow pattern: `{target}-fashion-recs-{workflow-name}`

```bash
# Data pipeline (load, features, splits)
databricks bundle run data_engineering_workflow -t dev

# Model training (all models)
databricks bundle run model_training_workflow -t dev

# Batch inference
databricks bundle run batch_inference_workflow -t dev
```

### Notebook Environment Configuration
Notebooks require environment metadata to load dependencies automatically. This metadata must be updated before deployment to match the target workspace path.

The [scripts/update_notebook_environments.py](scripts/update_notebook_environments.py) script updates `.ipynb` notebook metadata with correct workspace paths:
- **Dev**: `/Workspace/Users/${user.userName}/.bundle/fashion_recs/dev/environments/`
- **Staging/Prod**: `/Workspace/Shared/.bundle/fashion_recs/{target}/environments/`

Environment mappings (configured in the script):
- Data engineering + batch inference notebooks → `base-core.yml`
- Popularity, age_rules, ensemble training → `base-viz.yml`
- LSTM training → `databricks_ai_v4` (Databricks-provided, no workspace path)

```bash
# The deployment commands (make deploy-dev/staging/prod) handle this automatically!
# Manual update only needed if deploying with databricks CLI directly:
make update-notebooks-dev     # Updates notebook metadata for dev workspace paths
make update-notebooks-staging # Updates notebook metadata for staging workspace paths
make update-notebooks-prod    # Updates notebook metadata for prod workspace paths
```

**Important**: Always use `make deploy-dev/staging/prod` instead of `databricks bundle deploy` directly, as it ensures notebooks reference the correct environment paths.

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
2. **Model Training** ([model-training-workflow.yml](resources/model-training-workflow.yml)): Parallel training of popularity and age_rules models, followed by LSTM (GPU), then ensemble (depends on all base models)
3. **Batch Inference** ([batch-inference-workflow.yml](resources/batch-inference-workflow.yml)): model serving and predictions

All tasks use serverless compute by default (no cluster configuration needed). The model training workflow defines three environment types:
- `core_env`: Minimal dependencies for basic models
- `viz_env`: Core + matplotlib/seaborn for visualization
- `dl_env`: Core + PyTorch for deep learning models

### LSTM Serverless GPU Training
The LSTM model training uses Databricks serverless GPU compute with A10 GPUs for distributed training:
- **Configuration**: Uses `@distributed` decorator from `databricks.sdk.runtime`
- **Default Setup**: 8x A10 GPUs (configurable via `num_gpus` parameter)
- **Distributed Training**: PyTorch DistributedDataParallel (DDP) with NCCL backend
- **Data Loading**: Optimized with DistributedSampler for parallel data loading across GPUs
- **Training Flow**:
  1. Data preparation on driver (Spark → Pandas)
  2. Distributed training function executed on GPU cluster
  3. Model saved from rank 0 and registered to Unity Catalog
  4. Inference runs on single GPU after training

To modify GPU configuration, update parameters in [model-training-workflow.yml](resources/model-training-workflow.yml):
```yaml
base_parameters:
  num_gpus: "8"      # Number of GPUs (default: 8)
  gpu_type: "A10"    # GPU type (default: A10)
```

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
- [scripts/update_notebook_environments.py](scripts/update_notebook_environments.py): Updates notebook metadata with workspace-specific environment paths
- [data_engineering/notebooks/](data_engineering/notebooks/): Data pipeline notebooks (01_load_data, 02_create_features, 03_create_splits)
- [training/notebooks/](training/notebooks/): Model training notebooks (train_popularity, train_age_rules, train_lstm, train_ensemble)

**Note on notebook formats**: Notebooks exist as both `.py` (source files for version control) and `.ipynb` (Jupyter format for Databricks). The bundle deployment uses `.ipynb` files. The `update_notebook_environments.py` script modifies `.ipynb` metadata only.

### Data Flow
1. Raw CSV files in `/Volumes/jongseob_demo/fashion_recommendations/data/`
2. Load to Bronze tables via `01_load_data.ipynb`
3. Create features and Feature Store tables via `02_create_features.ipynb`
4. Create train/val/test splits via `03_create_splits.ipynb`
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
make test           # Run tests using Poetry
poetry run pytest   # Or run pytest directly
```

## Development Workflow

### Standard Deployment Process
1. Work locally or in Databricks notebooks
2. Test changes: `make deploy-dev` (automatically updates notebook metadata + deploys)
3. Validate: `make validate`
4. Deploy to staging: `make deploy-staging`
5. Verify in staging environment
6. Deploy to production: `make deploy-prod`

### Notebook Environment Metadata
All notebooks contain `environmentMetadata` that references environment configurations:

**Custom workspace environments** (most notebooks):
- Format: `/Workspace/Users/${user.userName}/.bundle/fashion_recs/dev/environments/base-xxx.yml`
- Files: `base-core.yml` (data engineering, batch inference), `base-viz.yml` (popularity, age_rules, ensemble)
- Updated automatically by `make deploy-dev/staging/prod` commands

**Databricks-provided environments**:
- LSTM notebook uses `databricks_ai_v4` - includes PyTorch and deep learning packages pre-installed, optimized for GPU workloads
- No workspace path needed, references Databricks-managed environment directly

**Why this matters**: Databricks notebooks load environment dependencies based on these paths/names. Custom environment paths differ between dev (user workspace) and staging/prod (shared workspace), so metadata must be updated before each deployment.

## Important Notes
- All notebooks must accept bundle parameters (`catalog_name`, `schema_name`, `experiment_name`) as widgets
- Use `get_table_config(catalog_name, schema_name)` from [config/catalog_config.py](config/catalog_config.py) for environment-aware table access
- Models are automatically created when registered via MLflow (no need to pre-create in bundle)
- Primary evaluation metric is MAP@12 (Mean Average Precision at K=12)
- Databricks serverless compute is used by default - no cluster configuration needed in workflows
