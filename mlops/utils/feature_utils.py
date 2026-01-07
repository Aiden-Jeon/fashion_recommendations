"""
Feature engineering utilities for customer and article features
"""

from pyspark.sql import DataFrame
from pyspark.sql.functions import *
from pyspark.sql.window import Window
from typing import Optional


def calculate_customer_features(
    transactions_df: DataFrame, customers_df: DataFrame, reference_date: str
) -> DataFrame:
    """
    Calculate customer behavioral features

    Args:
        transactions_df: Transactions DataFrame
        customers_df: Customers DataFrame
        reference_date: Reference date for calculating recency features

    Returns:
        DataFrame with customer features
    """

    # Add recency column
    transactions_with_recency = transactions_df.withColumn(
        "days_ago", datediff(lit(reference_date), col("t_dat"))
    )

    # 7-day features
    purchases_7d = (
        transactions_with_recency.filter(col("days_ago") <= 7)
        .groupBy("customer_id")
        .agg(
            count("*").alias("purchases_7d"),
            sum("price").alias("total_spent_7d"),
            countDistinct("article_id").alias("unique_items_7d"),
            avg("price").alias("avg_price_7d"),
        )
    )

    # 30-day features
    purchases_30d = (
        transactions_with_recency.filter(col("days_ago") <= 30)
        .groupBy("customer_id")
        .agg(
            count("*").alias("purchases_30d"),
            sum("price").alias("total_spent_30d"),
            countDistinct("article_id").alias("unique_items_30d"),
            avg("price").alias("avg_price_30d"),
        )
    )

    # Lifetime features
    purchases_lifetime = transactions_df.groupBy("customer_id").agg(
        count("*").alias("purchases_lifetime"),
        sum("price").alias("total_spent_lifetime"),
        countDistinct("article_id").alias("unique_items_lifetime"),
        min("t_dat").alias("first_purchase_date"),
        max("t_dat").alias("last_purchase_date"),
    )

    # Calculate recency (days since last purchase)
    purchases_lifetime = purchases_lifetime.withColumn(
        "days_since_last_purchase",
        datediff(lit(reference_date), col("last_purchase_date")),
    )

    # Calculate tenure (days since first purchase)
    purchases_lifetime = purchases_lifetime.withColumn(
        "customer_tenure_days", datediff(lit(reference_date), col("first_purchase_date"))
    )

    # Join all features
    customer_features = (
        customers_df.join(purchases_7d, on="customer_id", how="left")
        .join(purchases_30d, on="customer_id", how="left")
        .join(purchases_lifetime, on="customer_id", how="left")
    )

    # Fill nulls with 0 for numeric columns
    numeric_cols = [
        "purchases_7d",
        "total_spent_7d",
        "unique_items_7d",
        "avg_price_7d",
        "purchases_30d",
        "total_spent_30d",
        "unique_items_30d",
        "avg_price_30d",
        "purchases_lifetime",
        "total_spent_lifetime",
        "unique_items_lifetime",
        "days_since_last_purchase",
        "customer_tenure_days",
    ]

    for col_name in numeric_cols:
        if col_name in customer_features.columns:
            customer_features = customer_features.fillna({col_name: 0})

    # Add derived features
    customer_features = customer_features.withColumn(
        "purchase_frequency_30d",
        when(col("customer_tenure_days") > 0, col("purchases_30d") / 30.0).otherwise(0),
    )

    return customer_features


def create_age_groups(customers_df: DataFrame) -> DataFrame:
    """
    Create age group segments for customers

    Args:
        customers_df: Customers DataFrame with 'age' column

    Returns:
        DataFrame with age_group column added
    """
    return customers_df.withColumn(
        "age_group",
        when(col("age") < 18, "Under 18")
        .when((col("age") >= 18) & (col("age") < 25), "18-24")
        .when((col("age") >= 25) & (col("age") < 35), "25-34")
        .when((col("age") >= 35) & (col("age") < 45), "35-44")
        .when((col("age") >= 45) & (col("age") < 55), "45-54")
        .when(col("age") >= 55, "55+")
        .otherwise("Unknown"),
    )


def calculate_article_features(
    transactions_df: DataFrame, articles_df: DataFrame, reference_date: str
) -> DataFrame:
    """
    Calculate article/product features

    Args:
        transactions_df: Transactions DataFrame
        articles_df: Articles DataFrame
        reference_date: Reference date for calculating time-based features

    Returns:
        DataFrame with article features
    """

    # Add recency column
    transactions_with_recency = transactions_df.withColumn(
        "days_ago", datediff(lit(reference_date), col("t_dat"))
    )

    # 7-day popularity
    popularity_7d = (
        transactions_with_recency.filter(col("days_ago") <= 7)
        .groupBy("article_id")
        .agg(
            count("*").alias("popularity_7d"),
            countDistinct("customer_id").alias("unique_customers_7d"),
            avg("price").alias("avg_price_7d"),
        )
    )

    # 30-day popularity
    popularity_30d = (
        transactions_with_recency.filter(col("days_ago") <= 30)
        .groupBy("article_id")
        .agg(
            count("*").alias("popularity_30d"),
            countDistinct("customer_id").alias("unique_customers_30d"),
            avg("price").alias("avg_price_30d"),
        )
    )

    # Lifetime popularity
    popularity_lifetime = transactions_df.groupBy("article_id").agg(
        count("*").alias("popularity_lifetime"),
        countDistinct("customer_id").alias("unique_customers_lifetime"),
        min("t_dat").alias("first_sale_date"),
        max("t_dat").alias("last_sale_date"),
    )

    # Calculate days since last sale
    popularity_lifetime = popularity_lifetime.withColumn(
        "days_since_last_sale", datediff(lit(reference_date), col("last_sale_date"))
    )

    # Join with article metadata
    article_features = (
        articles_df.join(popularity_7d, on="article_id", how="left")
        .join(popularity_30d, on="article_id", how="left")
        .join(popularity_lifetime, on="article_id", how="left")
    )

    # Fill nulls
    numeric_cols = [
        "popularity_7d",
        "unique_customers_7d",
        "avg_price_7d",
        "popularity_30d",
        "unique_customers_30d",
        "avg_price_30d",
        "popularity_lifetime",
        "unique_customers_lifetime",
        "days_since_last_sale",
    ]

    for col_name in numeric_cols:
        if col_name in article_features.columns:
            article_features = article_features.fillna({col_name: 0})

    # Add derived features
    article_features = article_features.withColumn(
        "popularity_trend",
        when(col("popularity_30d") > 0, col("popularity_7d") / col("popularity_30d")).otherwise(
            0
        ),
    )

    return article_features


def calculate_customer_category_preferences(
    transactions_df: DataFrame, articles_df: DataFrame
) -> DataFrame:
    """
    Calculate customer preferences for product categories

    Args:
        transactions_df: Transactions DataFrame
        articles_df: Articles DataFrame with category columns

    Returns:
        DataFrame with customer's preferred categories
    """

    # Join transactions with article categories
    transactions_with_categories = transactions_df.join(
        articles_df.select("article_id", "product_group_name", "product_type_name"),
        on="article_id",
        how="left",
    )

    # Count purchases per customer per category
    category_counts = (
        transactions_with_categories.groupBy("customer_id", "product_group_name")
        .agg(count("*").alias("category_purchases"))
        .withColumn(
            "rank",
            row_number().over(
                Window.partitionBy("customer_id").orderBy(col("category_purchases").desc())
            ),
        )
    )

    # Get top 3 categories per customer
    top_categories = category_counts.filter(col("rank") <= 3).select(
        "customer_id",
        "product_group_name",
        "category_purchases",
        col("rank").alias("category_rank"),
    )

    return top_categories


def calculate_recency_frequency_monetary(transactions_df: DataFrame, reference_date: str) -> DataFrame:
    """
    Calculate RFM (Recency, Frequency, Monetary) features for customers

    Args:
        transactions_df: Transactions DataFrame
        reference_date: Reference date for recency calculation

    Returns:
        DataFrame with RFM features per customer
    """

    rfm = transactions_df.groupBy("customer_id").agg(
        # Recency: days since last purchase
        datediff(lit(reference_date), max("t_dat")).alias("recency_days"),
        # Frequency: total number of purchases
        count("*").alias("frequency"),
        # Monetary: total amount spent
        sum("price").alias("monetary_value"),
    )

    # Add RFM scores (quintiles)
    rfm = rfm.withColumn(
        "recency_score",
        ntile(5).over(Window.orderBy(col("recency_days").asc())),  # Lower recency is better
    ).withColumn(
        "frequency_score",
        ntile(5).over(Window.orderBy(col("frequency").desc())),  # Higher frequency is better
    ).withColumn(
        "monetary_score",
        ntile(5).over(Window.orderBy(col("monetary_value").desc())),  # Higher monetary is better
    )

    # Calculate combined RFM score
    rfm = rfm.withColumn(
        "rfm_score",
        concat(col("recency_score"), col("frequency_score"), col("monetary_score")),
    )

    return rfm


def add_seasonality_features(transactions_df: DataFrame) -> DataFrame:
    """
    Add seasonality features to transactions

    Args:
        transactions_df: Transactions DataFrame with t_dat column

    Returns:
        DataFrame with seasonality features
    """

    return (
        transactions_df.withColumn("month", month("t_dat"))
        .withColumn("quarter", quarter("t_dat"))
        .withColumn("dayofweek", dayofweek("t_dat"))
        .withColumn("week", weekofyear("t_dat"))
        .withColumn(
            "season",
            when(col("month").isin([12, 1, 2]), "Winter")
            .when(col("month").isin([3, 4, 5]), "Spring")
            .when(col("month").isin([6, 7, 8]), "Summer")
            .otherwise("Fall"),
        )
        .withColumn("is_weekend", when(col("dayofweek").isin([1, 7]), 1).otherwise(0))
    )


def get_feature_importance_stats(feature_df: DataFrame) -> DataFrame:
    """
    Calculate basic statistics for feature importance analysis

    Args:
        feature_df: DataFrame with features

    Returns:
        DataFrame with feature statistics
    """

    # Get numeric columns
    numeric_cols = [
        field.name
        for field in feature_df.schema.fields
        if str(field.dataType) in ["IntegerType", "DoubleType", "FloatType", "LongType"]
    ]

    # Calculate statistics
    stats = feature_df.select(
        [
            mean(col(c)).alias(f"{c}_mean"),
            stddev(col(c)).alias(f"{c}_std"),
            min(col(c)).alias(f"{c}_min"),
            max(col(c)).alias(f"{c}_max"),
        ]
        for c in numeric_cols
    )

    return stats

