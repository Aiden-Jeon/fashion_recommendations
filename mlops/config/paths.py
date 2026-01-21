"""
File paths and volume locations
"""

import os

from databricks.sdk import WorkspaceClient

# Project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Volume path
VOLUME_PATH = "/Volumes/shared/fashion_recommendations/data"

# Data files
ARTICLES_CSV = f"{VOLUME_PATH}/articles.csv"
CUSTOMERS_CSV = f"{VOLUME_PATH}/customers.csv"
TRANSACTIONS_CSV = f"{VOLUME_PATH}/transactions_train.csv"
SAMPLE_SUBMISSION_CSV = f"{VOLUME_PATH}/sample_submission.csv"

# Current user for experiment paths
_CURRENT_USER = WorkspaceClient().current_user.me().user_name

# MLflow Experiments (for interactive runs only)
# When running via DAB workflow, experiment paths come from databricks.yml variables
# These defaults use the current user's folder for dev environment
MLFLOW_EXPERIMENT_DATA = f"/Users/{_CURRENT_USER}/fashion-recs-dev_data"
MLFLOW_EXPERIMENT_MODELS = f"/Users/{_CURRENT_USER}/fashion-recs-dev_models"

# Checkpoints (for streaming or incremental loads)
CHECKPOINT_PATH = f"{VOLUME_PATH}/checkpoints"
