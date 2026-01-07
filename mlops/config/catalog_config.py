"""
Unity Catalog and Delta table configuration

This configuration supports environment-specific schemas through bundle targets:
- dev: jongseob_demo.dev_fashion_recommendations
- staging: jongseob_demo.staging_fashion_recommendations
- prod: jongseob_demo.prod_fashion_recommendations

Source data location:
- Raw data: jongseob_demo.fashion_recommendations (shared across all environments)

Usage:
    Pass catalog_name and schema_name as notebook parameters from bundle
"""
import os

# Source data configuration (shared across all environments)
SOURCE_CATALOG = "jongseob_demo"
SOURCE_SCHEMA = "fashion_recommendations"


def get_full_table_name(catalog_name: str, schema_name: str, table_suffix: str) -> str:
    """
    Get fully qualified table name

    Args:
        catalog_name: Catalog name (e.g., "jongseob_demo")
        schema_name: Schema name (e.g., "dev_fashion_recommendations")
        table_suffix: Table name suffix (e.g., "articles_bronze")

    Returns:
        Fully qualified table name
    """
    return f"{catalog_name}.{schema_name}.{table_suffix}"


# Table name suffixes (to be combined with catalog and schema from bundle)
class TableNames:
    # Source tables (from shared source schema)
    ARTICLES_SOURCE = "articles"
    CUSTOMERS_SOURCE = "customers"
    TRANSACTIONS_SOURCE = "transactions"
    
    # Bronze tables (raw data in environment-specific schema)
    ARTICLES_BRONZE = "articles_bronze"
    CUSTOMERS_BRONZE = "customers_bronze"
    TRANSACTIONS_BRONZE = "transactions_bronze"

    # Silver tables (cleaned/transformed)
    TRAIN_SILVER = "train_transactions_silver"
    VAL_SILVER = "val_transactions_silver"
    TEST_SILVER = "test_transactions_silver"
    VAL_GROUND_TRUTH_SILVER = "val_ground_truth_silver"
    TEST_GROUND_TRUTH_SILVER = "test_ground_truth_silver"

    # Gold tables (aggregated/business-ready)
    CUSTOMER_RECOMMENDATIONS_GOLD = "customer_recommendations_gold"
    MODEL_PREDICTIONS_GOLD = "model_predictions_gold"
    POPULARITY_PREDICTIONS_GOLD = "popularity_predictions_gold"
    AGE_RULES_PREDICTIONS_GOLD = "age_rules_predictions_gold"
    LSTM_PREDICTIONS_GOLD = "lstm_predictions_gold"
    ENSEMBLE_PREDICTIONS_GOLD = "ensemble_predictions_gold"

    # Synced tables (for OLTP access via Lakebase)
    POPULARITY_PREDICTIONS_SYNCED = "popularity_predictions_synced"
    AGE_RULES_PREDICTIONS_SYNCED = "age_rules_predictions_synced"
    LSTM_PREDICTIONS_SYNCED = "lstm_predictions_synced"
    ENSEMBLE_PREDICTIONS_SYNCED = "ensemble_predictions_synced"

    # Feature tables
    CUSTOMER_FEATURES = "customer_features"
    ARTICLE_FEATURES = "article_features"


# Helper function for notebooks
def get_table_config(catalog_name: str, schema_name: str):
    """
    Get table configuration object for a specific environment

    Usage in notebook:
        catalog_name = dbutils.widgets.get("catalog_name")
        schema_name = dbutils.widgets.get("schema_name")
        tables = get_table_config(catalog_name, schema_name)
        df = spark.table(tables.ARTICLES_SOURCE)  # Read from shared source schema
        df = spark.table(tables.ARTICLES_BRONZE)  # Read from environment-specific bronze
    """
    class Tables:
        # Source tables (from shared source schema)
        ARTICLES_SOURCE = get_full_table_name(SOURCE_CATALOG, SOURCE_SCHEMA, TableNames.ARTICLES_SOURCE)
        CUSTOMERS_SOURCE = get_full_table_name(SOURCE_CATALOG, SOURCE_SCHEMA, TableNames.CUSTOMERS_SOURCE)
        TRANSACTIONS_SOURCE = get_full_table_name(SOURCE_CATALOG, SOURCE_SCHEMA, TableNames.TRANSACTIONS_SOURCE)
        
        # Bronze (environment-specific)
        ARTICLES_BRONZE = get_full_table_name(catalog_name, schema_name, TableNames.ARTICLES_BRONZE)
        CUSTOMERS_BRONZE = get_full_table_name(catalog_name, schema_name, TableNames.CUSTOMERS_BRONZE)
        TRANSACTIONS_BRONZE = get_full_table_name(catalog_name, schema_name, TableNames.TRANSACTIONS_BRONZE)

        # Silver
        TRAIN_SILVER = get_full_table_name(catalog_name, schema_name, TableNames.TRAIN_SILVER)
        VAL_SILVER = get_full_table_name(catalog_name, schema_name, TableNames.VAL_SILVER)
        TEST_SILVER = get_full_table_name(catalog_name, schema_name, TableNames.TEST_SILVER)
        VAL_GROUND_TRUTH_SILVER = get_full_table_name(catalog_name, schema_name, TableNames.VAL_GROUND_TRUTH_SILVER)
        TEST_GROUND_TRUTH_SILVER = get_full_table_name(catalog_name, schema_name, TableNames.TEST_GROUND_TRUTH_SILVER)

        # Gold
        CUSTOMER_RECOMMENDATIONS_GOLD = get_full_table_name(catalog_name, schema_name, TableNames.CUSTOMER_RECOMMENDATIONS_GOLD)
        MODEL_PREDICTIONS_GOLD = get_full_table_name(catalog_name, schema_name, TableNames.MODEL_PREDICTIONS_GOLD)
        POPULARITY_PREDICTIONS_GOLD = get_full_table_name(catalog_name, schema_name, TableNames.POPULARITY_PREDICTIONS_GOLD)
        AGE_RULES_PREDICTIONS_GOLD = get_full_table_name(catalog_name, schema_name, TableNames.AGE_RULES_PREDICTIONS_GOLD)
        LSTM_PREDICTIONS_GOLD = get_full_table_name(catalog_name, schema_name, TableNames.LSTM_PREDICTIONS_GOLD)
        ENSEMBLE_PREDICTIONS_GOLD = get_full_table_name(catalog_name, schema_name, TableNames.ENSEMBLE_PREDICTIONS_GOLD)

        # Synced tables
        POPULARITY_PREDICTIONS_SYNCED = get_full_table_name(catalog_name, schema_name, TableNames.POPULARITY_PREDICTIONS_SYNCED)
        AGE_RULES_PREDICTIONS_SYNCED = get_full_table_name(catalog_name, schema_name, TableNames.AGE_RULES_PREDICTIONS_SYNCED)
        LSTM_PREDICTIONS_SYNCED = get_full_table_name(catalog_name, schema_name, TableNames.LSTM_PREDICTIONS_SYNCED)
        ENSEMBLE_PREDICTIONS_SYNCED = get_full_table_name(catalog_name, schema_name, TableNames.ENSEMBLE_PREDICTIONS_SYNCED)

        # Features
        CUSTOMER_FEATURES = get_full_table_name(catalog_name, schema_name, TableNames.CUSTOMER_FEATURES)
        ARTICLE_FEATURES = get_full_table_name(catalog_name, schema_name, TableNames.ARTICLE_FEATURES)

    return Tables


# Legacy support (for local development)
# Will use dev environment by default
CATALOG = os.getenv("CATALOG_NAME", "jongseob_demo")
SCHEMA = os.getenv("SCHEMA_NAME", "dev_fashion_recommendations")
FULL_NAME = f"{CATALOG}.{SCHEMA}"

# Legacy table names - use source tables from shared schema
ARTICLES_TABLE = get_full_table_name(SOURCE_CATALOG, SOURCE_SCHEMA, TableNames.ARTICLES_SOURCE)
CUSTOMERS_TABLE = get_full_table_name(SOURCE_CATALOG, SOURCE_SCHEMA, TableNames.CUSTOMERS_SOURCE)
TRANSACTIONS_TABLE = get_full_table_name(SOURCE_CATALOG, SOURCE_SCHEMA, TableNames.TRANSACTIONS_SOURCE)
TRAIN_TABLE = get_full_table_name(CATALOG, SCHEMA, TableNames.TRAIN_SILVER)
VAL_TABLE = get_full_table_name(CATALOG, SCHEMA, TableNames.VAL_SILVER)
TEST_TABLE = get_full_table_name(CATALOG, SCHEMA, TableNames.TEST_SILVER)
VAL_GROUND_TRUTH_TABLE = get_full_table_name(CATALOG, SCHEMA, TableNames.VAL_GROUND_TRUTH_SILVER)
TEST_GROUND_TRUTH_TABLE = get_full_table_name(CATALOG, SCHEMA, TableNames.TEST_GROUND_TRUTH_SILVER)
CUSTOMER_RECOMMENDATIONS = get_full_table_name(CATALOG, SCHEMA, TableNames.CUSTOMER_RECOMMENDATIONS_GOLD)
MODEL_PREDICTIONS = get_full_table_name(CATALOG, SCHEMA, TableNames.MODEL_PREDICTIONS_GOLD)
CUSTOMER_FEATURES = get_full_table_name(CATALOG, SCHEMA, TableNames.CUSTOMER_FEATURES)
ARTICLE_FEATURES = get_full_table_name(CATALOG, SCHEMA, TableNames.ARTICLE_FEATURES)
