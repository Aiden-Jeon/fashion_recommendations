# Fashion Recommendations MLOps Project

Production-ready MLOps project for personalized fashion recommendations using Databricks Asset Bundles.

## Overview

This project implements multiple recommendation models for the H&M Fashion dataset:
- **Popularity Model**: Time-based recency-weighted baseline
- **Age Rules Model**: Customer age segmentation
- **LSTM Model**: Sequential purchase prediction (coming soon)
- **Ensemble Model**: Blend of all base models (coming soon)

## Project Structure

```
fashion_recommendations/
├── databricks.yml                   # Bundle configuration
├── pyproject.toml                   # Poetry dependencies
├── requirements.txt                 # Python dependencies (generated from Poetry)
├── Makefile                         # Development commands
│
├── training/                        # Model training
│   └── notebooks/                   # Training notebooks
│       ├── train_popularity.py
│       ├── train_age_rules.py
│       ├── train_lstm.py
│       └── train_ensemble.py
│
├── data_engineering/                # Data pipeline & Feature Store
│   ├── notebooks/
│   │   ├── 01_load_data.py
│   │   ├── 02_create_features.py
│   │   └── 03_create_splits.py
│   ├── features/                    # Feature transforms
│   ├── data_utils.py
│   └── feature_utils.py
│
├── deployment/                      # Model deployment
│   ├── batch_inference/
│   └── model_deployment/
│
├── validation/                      # Model validation
├── monitoring/                      # Model monitoring
│
├── resources/                       # Infrastructure as Code
│   ├── ml-artifacts-resource.yml
│   ├── data-engineering-workflow.yml
│   ├── model-training-workflow.yml
│   └── batch-inference-workflow.yml
│
├── utils/                           # Shared utilities
│   └── evaluation_utils.py         # MAP@12 metrics
│
├── config/                          # Configuration
│   ├── catalog_config.py
│   ├── model_config.py
│   └── paths.py
│
└── environments/                    # Environment documentation
    └── README.md                    # Serverless Runtime 4 package info
```

## Package & Environment Strategy

**Databricks Serverless Runtime 4** includes most packages out-of-the-box:
- Core ML: `pandas`, `numpy`, `scikit-learn`, `scipy`, `matplotlib`, `seaborn`
- Deep Learning: `torch`, `torchvision`, `pytorch-lightning`, `transformers`
- MLflow: Pre-installed on Databricks

**Installation Approach:**
- Notebooks use `%pip install` for additional packages (e.g., `databricks-feature-engineering`)
- No custom environment files needed
- Faster cluster startup times

See `environments/README.md` for details.

## Data & Model Environment Strategy

**Single Catalog, Schema per Environment:**
- Catalog: `jongseob_demo`
- Schemas:
  - `fashion_recommendations` - Development
  - `staging_fashion_recommendations` - Staging
  - `prod_fashion_recommendations` - Production

**Example Tables:**
- Dev: `jongseob_demo.fashion_recommendations.articles_bronze`
- Staging: `jongseob_demo.staging_fashion_recommendations.articles_bronze`
- Prod: `jongseob_demo.prod_fashion_recommendations.articles_bronze`

**Example Models:**
- Dev: `jongseob_demo.fashion_recommendations.popularity_model`
- Staging: `jongseob_demo.staging_fashion_recommendations.popularity_model`
- Prod: `jongseob_demo.prod_fashion_recommendations.popularity_model`

## Getting Started

### Prerequisites

- Databricks CLI installed and configured
- Access to Databricks workspace
- Unity Catalog enabled
- Data uploaded to `/Volumes/jongseob_demo/fashion_recommendations/data`

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   # Using Poetry (recommended for development)
   make install              # Core dependencies only
   make install-all          # All dependencies (viz, dl, dev)

   # Or using pip
   pip install -r requirements.txt
   ```

### Deployment

**Validate bundle:**
```bash
make validate
# Or: databricks bundle validate -t dev
```

**Deploy to environments:**
```bash
make deploy              # Deploy to dev (default)
make deploy-staging      # Deploy to staging
make deploy-prod         # Deploy to production
```

## Running the Pipeline

### 1. Data Loading (DataOps)

Load raw data to bronze tables (handled by DataOps project):
```bash
cd ../dataops
make run-workflow
```

This creates bronze tables that MLOps will read from.

### 2. Feature Engineering (MLOps)

Create features and train/val/test splits:
```bash
databricks bundle run feature_engineering_job -t dev
# Or: make run-features
```

Or run notebooks manually in the workspace:
1. `data_engineering/notebooks/02_create_features.ipynb`
2. `data_engineering/notebooks/03_create_splits.ipynb`

### 3. Model Training

Train all models:
```bash
databricks bundle run model_training_job -t dev
# Or: make run-training
```

Or run individual models:
- `training/notebooks/train_popularity.ipynb`
- `training/notebooks/train_age_rules.ipynb`
- `training/notebooks/train_lstm.ipynb` (coming soon)
- `training/notebooks/train_ensemble.ipynb` (coming soon)

### 4. Batch Inference

Generate recommendations:
```bash
databricks bundle run batch_inference_job -t dev
# Or: make run-batch-inference
```

### Full Pipeline

Run entire ML pipeline (features → training → inference):
```bash
make run-ml-pipeline
```

## MLflow Experiments

**Data Experiment:**
- Dev: `/Users/{user}/dev-fashion-recs-data`
- Staging: `/Users/{user}/staging-fashion-recs-data`
- Prod: `/Users/{user}/prod-fashion-recs-data`

**Models Experiment:**
- Dev: `/Users/{user}/dev-fashion-recs-models`
- Staging: `/Users/{user}/staging-fashion-recs-models`
- Prod: `/Users/{user}/prod-fashion-recs-models`

## Notebook Parameters

All notebooks accept these parameters (provided automatically by bundle):
- `catalog_name`: Unity Catalog name
- `schema_name`: Schema name for environment
- `experiment_name`: MLflow experiment path
- `model_name`: Model name (for training notebooks)

## Development Workflow

1. **Local Development**: Work in notebooks, test with `dev` target
2. **Update Dependencies** (if needed):
   ```bash
   poetry add new-package
   make update-requirements     # Export to requirements.txt
   ```
3. **Validate**: `make validate`
4. **Deploy to Staging**: `make deploy-staging`
5. **Test in Staging**: Run jobs and verify results
6. **Deploy to Production**: `make deploy-prod`

## Configuration

### Updating Model Hyperparameters

Edit `config/model_config.py`:
```python
POPULARITY_CONFIG = {
    "n_days": 7,
    "alpha": 0.5,
    "top_n": 12
}
```

### Managing Dependencies

This project uses Poetry for dependency management:
```bash
# Add a new dependency
poetry add package-name

# Update requirements.txt for Databricks
make update-requirements

# Update Databricks environment YAML files
make update-environments
```

See [docs/poetry-databricks-guide.md](docs/poetry-databricks-guide.md) for detailed guide.

### Updating Job Schedules

Edit resource YAMLs in `resources/`:
```yaml
schedule:
  quartz_cron_expression: "0 0 9 * * ?"
  timezone_id: UTC
```

## Monitoring

- Check MLflow experiments for metrics (MAP@12)
- Review job run history in Databricks workspace
- Monitor data quality metrics in data experiment

## Troubleshooting

**Bundle validation fails:**
```bash
make validate
# Check error messages for YAML syntax issues
```

**Notebook fails to find tables:**
- Ensure data engineering job completed successfully
- Check catalog/schema names are correct for your environment
- Verify Unity Catalog permissions

**Import errors:**
- Ensure dependencies are up to date:
  ```bash
  make update-requirements
  make deploy
  ```
- Check that notebooks use correct parameters from bundle

## Project Status

✅ **Completed:**
- Data engineering pipeline (load, features, splits)
- Feature Store integration
- Popularity model
- Age rules model
- Bundle configuration with multi-environment support
- Resource definitions (workflows)
- Poetry dependency management

🚧 **In Progress:**
- LSTM model
- Ensemble model
- Model validation
- Batch inference
- Monitoring

## Contributing

1. Create feature branch
2. Make changes
3. Test with `dev` target
4. Submit pull request

## Resources

- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/index.html)
- [MLflow on Databricks](https://docs.databricks.com/mlflow/index.html)
- [Unity Catalog](https://docs.databricks.com/data-governance/unity-catalog/index.html)
- [Feature Store](https://docs.databricks.com/machine-learning/feature-store/index.html)
