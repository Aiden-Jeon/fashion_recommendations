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
├── requirements.txt                 # Python dependencies
│
├── training/                        # Model training
│   ├── notebooks/                   # Training notebooks
│   │   ├── train_popularity.py
│   │   └── train_age_rules.py
│   └── steps/                       # Reusable modules
│
├── feature_engineering/             # Feature Store
│   ├── notebooks/
│   │   └── create_features.py
│   ├── features/                    # Feature transforms
│   └── feature_utils.py
│
├── data_preparation/                # Data pipeline
│   ├── notebooks/
│   │   ├── load_data.py
│   │   └── create_splits.py
│   └── data_utils.py
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
│   ├── data-pipeline-workflow.yml
│   ├── feature-engineering-workflow.yml
│   ├── model-training-workflow.yml
│   └── batch-inference-workflow.yml
│
├── utils/                           # Shared utilities
│   └── evaluation_utils.py         # MAP@12 metrics
│
└── config/                          # Configuration
    ├── catalog_config.py
    ├── model_config.py
    └── paths.py
```

## Environment Strategy

**Single Catalog, Schema per Environment:**
- Catalog: `jongseob_demo`
- Schemas:
  - `dev_fashion_recommendations` - Development
  - `staging_fashion_recommendations` - Staging
  - `prod_fashion_recommendations` - Production

**Example Tables:**
- Dev: `jongseob_demo.dev_fashion_recommendations.articles_bronze`
- Staging: `jongseob_demo.staging_fashion_recommendations.articles_bronze`
- Prod: `jongseob_demo.prod_fashion_recommendations.articles_bronze`

**Example Models:**
- Dev: `jongseob_demo.dev_fashion_recommendations.popularity_model`
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
   pip install -r requirements.txt
   ```

### Deployment

**Validate bundle:**
```bash
databricks bundle validate -t dev
```

**Deploy to dev:**
```bash
databricks bundle deploy -t dev
```

**Deploy to staging:**
```bash
databricks bundle deploy -t staging
```

**Deploy to prod:**
```bash
databricks bundle deploy -t prod
```

## Running the Pipeline

### 1. Data Pipeline

Load data and create train/val/test splits:
```bash
databricks bundle run data_pipeline_job -t dev
```

Or run manually in the workspace:
1. `data_preparation/notebooks/load_data.py`
2. `data_preparation/notebooks/create_splits.py`

### 2. Feature Engineering

Create and register features:
```bash
databricks bundle run feature_engineering_job -t dev
```

Or run manually:
- `feature_engineering/notebooks/create_features.py`

### 3. Model Training

Train all models:
```bash
databricks bundle run model_training_job -t dev
```

Or run individual models:
- `training/notebooks/train_popularity.py`
- `training/notebooks/train_age_rules.py`

### 4. Batch Inference

Generate recommendations:
```bash
databricks bundle run batch_inference_job -t dev
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
2. **Validate**: `databricks bundle validate -t staging`
3. **Deploy to Staging**: `databricks bundle deploy -t staging`
4. **Test in Staging**: Run jobs and verify results
5. **Deploy to Production**: `databricks bundle deploy -t prod`

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
databricks bundle validate -t dev
# Check error messages for YAML syntax issues
```

**Notebook fails to find tables:**
- Ensure data pipeline job completed successfully
- Check catalog/schema names are correct
- Verify Unity Catalog permissions

**Import errors:**
- Ensure `requirements.txt` is installed
- Check Python path configuration in notebooks

## Project Status

✅ **Completed:**
- Data preparation pipeline
- Feature Store integration
- Popularity model
- Age rules model
- Bundle configuration
- Resource definitions

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
