"""
Unity Catalog and Delta table configuration

This configuration supports environment-specific schemas through bundle targets:
- dev: jongseob_demo.dev_fashion_recommendations
- prod: jongseob_demo.fashion_recommendations

Usage:
    Pass catalog_name and schema_name as notebook parameters from bundle
"""
import os


def get_full_table_name(catalog_name: str, schema_name: str, table_suffix: str) -> str:
    """
    Get fully qualified table name

    Args:
        catalog_name: Catalog name (e.g., "jongseob_demo")
        schema_name: Schema name (e.g., "fashion_recommendations")
        table_suffix: Table name suffix (e.g., "articles")

    Returns:
        Fully qualified table name
    """
    return f"{catalog_name}.{schema_name}.{table_suffix}"


# Lakebase configuration
LAKEBASE_INSTANCE = "shared-online-store"  # Default Lakebase instance for OLTP access


# Table name suffixes (to be combined with catalog and schema from bundle)
class TableNames:
    # Bronze tables (raw data) - DataOps responsibility
    ARTICLES = "articles"
    CUSTOMERS = "customers"
    TRANSACTIONS = "transactions"
    
    # App feature tables (synced to Lakebase for low-latency access)
    PRODUCT_SALES_SUMMARY = "product_sales_summary"
    PRODUCT_SALES_SUMMARY_SYNCED = "product_sales_summary_synced"
    CUSTOMER_DEMOGRAPHICS = "customer_demographics"
    CUSTOMER_DEMOGRAPHICS_SYNCED = "customer_demographics_synced"
    TIME_SERIES_SALES = "time_series_sales"
    TIME_SERIES_SALES_SYNCED = "time_series_sales_synced"


# Helper function for notebooks
def get_table_config(catalog_name: str, schema_name: str):
    """
    Get table configuration object for a specific environment

    Usage in notebook:
        catalog_name = dbutils.widgets.get("catalog_name")
        schema_name = dbutils.widgets.get("schema_name")
        tables = get_table_config(catalog_name, schema_name)
        df = spark.table(tables.ARTICLES)
    """
    class Tables:
        # Bronze tables (raw data)
        ARTICLES = get_full_table_name(catalog_name, schema_name, TableNames.ARTICLES)
        CUSTOMERS = get_full_table_name(catalog_name, schema_name, TableNames.CUSTOMERS)
        TRANSACTIONS = get_full_table_name(catalog_name, schema_name, TableNames.TRANSACTIONS)
        
        # App feature tables (Delta tables)
        PRODUCT_SALES_SUMMARY = get_full_table_name(catalog_name, schema_name, TableNames.PRODUCT_SALES_SUMMARY)
        CUSTOMER_DEMOGRAPHICS = get_full_table_name(catalog_name, schema_name, TableNames.CUSTOMER_DEMOGRAPHICS)
        TIME_SERIES_SALES = get_full_table_name(catalog_name, schema_name, TableNames.TIME_SERIES_SALES)
        
        # App feature synced tables (Lakebase OLTP)
        PRODUCT_SALES_SUMMARY_SYNCED = get_full_table_name(catalog_name, schema_name, TableNames.PRODUCT_SALES_SUMMARY_SYNCED)
        CUSTOMER_DEMOGRAPHICS_SYNCED = get_full_table_name(catalog_name, schema_name, TableNames.CUSTOMER_DEMOGRAPHICS_SYNCED)
        TIME_SERIES_SALES_SYNCED = get_full_table_name(catalog_name, schema_name, TableNames.TIME_SERIES_SALES_SYNCED)

    return Tables


# Legacy support (for local development)
# Will use dev environment by default
CATALOG = os.getenv("CATALOG_NAME", "jongseob_demo")
SCHEMA = os.getenv("SCHEMA_NAME", "fashion_recommendations")
FULL_NAME = f"{CATALOG}.{SCHEMA}"

# Legacy table names
ARTICLES_TABLE = get_full_table_name(CATALOG, SCHEMA, TableNames.ARTICLES)
CUSTOMERS_TABLE = get_full_table_name(CATALOG, SCHEMA, TableNames.CUSTOMERS)
TRANSACTIONS_TABLE = get_full_table_name(CATALOG, SCHEMA, TableNames.TRANSACTIONS)
