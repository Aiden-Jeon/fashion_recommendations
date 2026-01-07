"""
Data loading and manipulation utilities
"""

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import *
from typing import List
import sys
import os

# Add config to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.catalog_config import *


def get_spark() -> SparkSession:
    """Get or create Spark session"""
    return SparkSession.builder.getOrCreate()


def load_delta_table(table_name: str) -> DataFrame:
    """
    Load Delta table from catalog

    Args:
        table_name: Fully qualified table name (e.g., "fashion_demo.bronze.articles")

    Returns:
        Spark DataFrame
    """
    spark = get_spark()
    return spark.table(table_name)


def get_customer_purchase_history(
    customer_id: str, transactions_df: DataFrame
) -> DataFrame:
    """
    Get purchase history for a specific customer

    Args:
        customer_id: Customer identifier
        transactions_df: Transactions DataFrame

    Returns:
        DataFrame with customer's purchase history ordered by date
    """
    return (
        transactions_df.filter(col("customer_id") == customer_id)
        .orderBy("t_dat")
        .select("article_id", "t_dat", "price")
    )


def create_ground_truth_labels(
    transactions_df: DataFrame, prediction_window_start: str, prediction_window_end: str
) -> DataFrame:
    """
    Create ground truth labels for evaluation

    Args:
        transactions_df: Transactions DataFrame
        prediction_window_start: Start date of prediction window (YYYY-MM-DD)
        prediction_window_end: End date of prediction window (YYYY-MM-DD)

    Returns:
        DataFrame with columns: [customer_id, actual_articles (array)]
    """
    ground_truth = (
        transactions_df.filter(
            (col("t_dat") >= prediction_window_start)
            & (col("t_dat") <= prediction_window_end)
        )
        .groupBy("customer_id")
        .agg(collect_list("article_id").alias("actual_articles"))
    )

    return ground_truth


def get_popular_items(
    transactions_df: DataFrame,
    n_days: int = 7,
    reference_date: str = None,
    top_n: int = 12,
) -> DataFrame:
    """
    Get most popular items from recent time window

    Args:
        transactions_df: Transactions DataFrame
        n_days: Number of days to look back
        reference_date: Reference date (default: max date in data)
        top_n: Number of top items to return

    Returns:
        DataFrame with [article_id, purchase_count] sorted by popularity
    """
    if reference_date is None:
        reference_date = transactions_df.select(max("t_dat")).collect()[0][0]

    cutoff_date = to_date(lit(reference_date)) - expr(f"INTERVAL {n_days} DAYS")

    popular_items = (
        transactions_df.filter(col("t_dat") >= cutoff_date)
        .groupBy("article_id")
        .agg(count("*").alias("purchase_count"))
        .orderBy(col("purchase_count").desc())
        .limit(top_n)
    )

    return popular_items


def get_popular_items_by_segment(
    transactions_df: DataFrame,
    customers_df: DataFrame,
    segment_column: str,
    segment_value,
    n_days: int = 7,
    reference_date: str = None,
    top_n: int = 12,
) -> DataFrame:
    """
    Get popular items for a specific customer segment

    Args:
        transactions_df: Transactions DataFrame
        customers_df: Customers DataFrame
        segment_column: Column name for segmentation (e.g., "age_group")
        segment_value: Value to filter segment by
        n_days: Number of days to look back
        reference_date: Reference date
        top_n: Number of top items to return

    Returns:
        DataFrame with [article_id, purchase_count]
    """
    if reference_date is None:
        reference_date = transactions_df.select(max("t_dat")).collect()[0][0]

    cutoff_date = to_date(lit(reference_date)) - expr(f"INTERVAL {n_days} DAYS")

    # Filter customers by segment
    segment_customers = customers_df.filter(
        col(segment_column) == segment_value
    ).select("customer_id")

    # Get transactions for segment
    segment_transactions = transactions_df.join(
        segment_customers, on="customer_id"
    ).filter(col("t_dat") >= cutoff_date)

    # Get popular items
    popular = (
        segment_transactions.groupBy("article_id")
        .agg(count("*").alias("purchase_count"))
        .orderBy(col("purchase_count").desc())
        .limit(top_n)
    )

    return popular


def ensure_catalog_exists(
    catalog_name: str = "jongseob_demo",
    schema_name: str = "fashion_recommendations",
):
    """
    Ensure catalog and schemas exist

    Args:
        catalog_name: Name of the catalog to create
    """
    spark = get_spark()

    # Create catalog if not exists
    spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog_name}")

    # Create schema
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.{schema_name}")

    print(f"Catalog '{catalog_name}' and schemas created successfully")


def add_date_features(transactions_df: DataFrame) -> DataFrame:
    """
    Add date-based features to transactions

    Args:
        transactions_df: Transactions DataFrame with 't_dat' column

    Returns:
        DataFrame with additional date features
    """
    return (
        transactions_df.withColumn("year", year("t_dat"))
        .withColumn("month", month("t_dat"))
        .withColumn("day", dayofmonth("t_dat"))
        .withColumn("dayofweek", dayofweek("t_dat"))
        .withColumn("week", weekofyear("t_dat"))
        .withColumn("year_month", date_format("t_dat", "yyyy-MM"))
    )


def get_customer_list(transactions_df: DataFrame) -> List[str]:
    """
    Get list of all customer IDs

    Args:
        transactions_df: Transactions DataFrame

    Returns:
        List of customer IDs
    """
    return [
        row.customer_id
        for row in transactions_df.select("customer_id").distinct().collect()
    ]


def log_data_quality_metrics(df: DataFrame, table_name: str):
    """
    Log data quality metrics for a DataFrame

    Args:
        df: DataFrame to analyze
        table_name: Name of the table for logging
    """
    import mlflow

    with mlflow.start_run(run_name=f"{table_name}_data_quality"):
        print(f"\nData Quality Metrics for {table_name}")
        print("=" * 60)

        # Row count
        row_count = df.count()
        print(f"Row count: {row_count:,}")
        mlflow.log_metric(f"{table_name}_row_count", row_count)

        # Column count
        col_count = len(df.columns)
        print(f"Column count: {col_count}")
        mlflow.log_metric(f"{table_name}_column_count", col_count)

        # Null counts
        null_counts = df.select(
            [count(when(col(c).isNull(), c)).alias(c) for c in df.columns]
        )
        null_summary = null_counts.collect()[0].asDict()

        print("\nNull counts:")
        for col_name, null_count in null_summary.items():
            if null_count > 0:
                print(f"  {col_name}: {null_count:,}")
                mlflow.log_metric(f"{table_name}_{col_name}_null_count", null_count)

        print("=" * 60 + "\n")
