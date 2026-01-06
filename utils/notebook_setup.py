"""
Notebook setup utilities for Databricks serverless notebooks.

Usage in notebook:
    %pip install -r ../../requirements.txt
    %restart_python

    # Then in next cell:
    from utils.notebook_setup import setup_notebook
    setup_notebook()
"""

import sys
from pathlib import Path


def setup_notebook(project_root_levels_up: int = 2):
    """
    Setup notebook environment for Fashion Recommendations project.

    Args:
        project_root_levels_up: How many levels up from notebook to project root
                               Default is 2 (for notebooks in training/notebooks or data_engineering/notebooks)

    Returns:
        Path to project root
    """
    # Add project root to Python path
    notebook_dir = Path.cwd()
    project_root = notebook_dir
    for _ in range(project_root_levels_up):
        project_root = project_root.parent

    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
        print(f"✓ Added project root to path: {project_root_str}")

    return project_root


def get_catalog_schema(environment: str = "dev"):
    """
    Get Unity Catalog and schema names based on environment.

    Args:
        environment: One of 'dev', 'staging', 'prod'

    Returns:
        Tuple of (catalog_name, schema_name)
    """
    catalog = "jongseob_demo"

    schema_map = {
        "dev": "dev_fashion_recommendations",
        "staging": "staging_fashion_recommendations",
        "prod": "prod_fashion_recommendations"
    }

    schema = schema_map.get(environment, "dev_fashion_recommendations")
    print(f"✓ Using catalog: {catalog}, schema: {schema}")

    return catalog, schema


def check_environment():
    """Check and display current environment configuration."""
    import mlflow
    import pandas as pd
    import numpy as np
    import sklearn

    print("=" * 50)
    print("Environment Check")
    print("=" * 50)
    print(f"Python path entries: {len(sys.path)}")
    print(f"MLflow version: {mlflow.__version__}")
    print(f"Pandas version: {pd.__version__}")
    print(f"NumPy version: {np.__version__}")
    print(f"Scikit-learn version: {sklearn.__version__}")
    print("=" * 50)


if __name__ == "__main__":
    # Test setup
    setup_notebook()
    check_environment()
