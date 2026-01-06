"""
Utility functions for safely handling Databricks widgets with default values.

This module provides helper functions to get widget values with fallback defaults,
allowing notebooks to run both in job mode (with parameters) and interactive mode (without).
"""


def get_widget_or_default(widget_name: str, default_value: str) -> str:
    """
    Get widget value with fallback to default for interactive notebook usage.

    When running as a job, widgets are passed as parameters from the bundle.
    When running interactively, widgets don't exist and this falls back to defaults.

    Args:
        widget_name: Name of the widget parameter
        default_value: Default value to use if widget is not available

    Returns:
        Widget value if running as job, default value if running interactively

    Example:
        catalog_name = get_widget_or_default("catalog_name", "jongseob_demo")
        schema_name = get_widget_or_default("schema_name", "dev_fashion_recommendations")
    """
    try:
        # Try to get widget value (works in job mode)
        value = dbutils.widgets.get(widget_name)
        # If value is empty string, use default
        return value if value else default_value
    except Exception:
        # Widget doesn't exist (interactive mode), use default
        return default_value


def get_bundle_parameters(catalog_default="jongseob_demo",
                          schema_default="dev_fashion_recommendations",
                          experiment_default=None,
                          model_default=None):
    """
    Get all standard bundle parameters with sensible defaults.

    Args:
        catalog_default: Default catalog name (default: "jongseob_demo")
        schema_default: Default schema name (default: "dev_fashion_recommendations")
        experiment_default: Default experiment name (default: auto-generated dev path)
        model_default: Default model name (default: None, must be specified if needed)

    Returns:
        Dictionary with keys: catalog_name, schema_name, experiment_name, model_name

    Example:
        params = get_bundle_parameters(model_default="popularity_model")
        catalog_name = params["catalog_name"]
        schema_name = params["schema_name"]
    """
    # Auto-generate experiment default if not provided
    if experiment_default is None:
        # Try to get current user using methods that work in serverless mode
        user = None
        try:
            # Method 1: Try dbutils notebook context (works in interactive notebooks)
            user = dbutils.notebook.entry_point.getDbutils().notebook().getContext().userName().get()
        except Exception:
            try:
                # Method 2: Try SQL current_user() function (works in serverless)
                from pyspark.sql import SparkSession
                spark = SparkSession.builder.getOrCreate()
                user = spark.sql("SELECT current_user()").collect()[0][0]
            except Exception:
                # Method 3: Fall back to Shared experiments if user detection fails
                user = None

        if user:
            experiment_default = f"/Users/{user}/experiments/fashion-recs-dev_models"
        else:
            # Ultimate fallback for cases where user detection is not available
            experiment_default = "/Shared/experiments/fashion-recs-dev_models"

    return {
        "catalog_name": get_widget_or_default("catalog_name", catalog_default),
        "schema_name": get_widget_or_default("schema_name", schema_default),
        "experiment_name": get_widget_or_default("experiment_name", experiment_default),
        "model_name": get_widget_or_default("model_name", model_default) if model_default else None
    }
