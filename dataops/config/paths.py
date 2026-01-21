"""
File paths and volume locations for dataops workflows
"""

from databricks.sdk import WorkspaceClient

# Volume path
VOLUME_PATH = "/Volumes/shared/fashion_recommendations/data"

# Data files
ARTICLES_CSV = f"{VOLUME_PATH}/articles.csv"
CUSTOMERS_CSV = f"{VOLUME_PATH}/customers.csv"
TRANSACTIONS_CSV = f"{VOLUME_PATH}/transactions_train.csv"

# Current user for experiment paths
_CURRENT_USER = WorkspaceClient().current_user.me().user_name

# MLflow Experiment for data engineering workflows
# When running via DAB workflow, experiment paths come from databricks.yml variables
# This default uses the current user's folder for dev environment
MLFLOW_EXPERIMENT_DATA = f"/Users/{_CURRENT_USER}/fashion-recs-dev_data"
