"""
File paths and volume locations
"""

import os

# Project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Volume path
VOLUME_PATH = "/Volumes/jongseob_demo/fashion_recommendations/data"

# Data files
ARTICLES_CSV = f"{VOLUME_PATH}/articles.csv"
CUSTOMERS_CSV = f"{VOLUME_PATH}/customers.csv"
TRANSACTIONS_CSV = f"{VOLUME_PATH}/transactions_train.csv"
SAMPLE_SUBMISSION_CSV = f"{VOLUME_PATH}/sample_submission.csv"

# MLflow Experiments (split into data and model experiments)
MLFLOW_EXPERIMENT_DATA = os.path.join(PROJECT_ROOT, "fashion_recommendations_data")
MLFLOW_EXPERIMENT_MODELS = os.path.join(PROJECT_ROOT, "fashion_recommendations_models")

# Checkpoints (for streaming or incremental loads)
CHECKPOINT_PATH = f"{VOLUME_PATH}/checkpoints"
