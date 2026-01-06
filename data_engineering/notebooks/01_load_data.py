# Databricks notebook source
# MAGIC %md
# MAGIC # Data Preparation: Load CSVs into Delta Tables
# MAGIC
# MAGIC This notebook loads the H&M fashion dataset from CSV files in the volume
# MAGIC into Delta tables for efficient querying and processing.
# MAGIC
# MAGIC **Inputs:**
# MAGIC - CSV files in `/Volumes/jongseob_demo/fashion_recommendations/data`
# MAGIC   - articles.csv
# MAGIC   - customers.csv
# MAGIC   - transactions_train.csv
# MAGIC
# MAGIC **Outputs:**
# MAGIC - Delta tables in `fashion_demo.bronze` schema
# MAGIC   - articles
# MAGIC   - customers
# MAGIC   - transactions

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------
# MAGIC %pip install mlflow>=3.0
# MAGIC %restart_python

# COMMAND ----------

import sys

# Add project root to path (go up 2 levels from notebooks/)
sys.path.append("../../")

from pyspark.sql.functions import *
import mlflow

from config.paths import (
    ARTICLES_CSV,
    CUSTOMERS_CSV,
    TRANSACTIONS_CSV,
    MLFLOW_EXPERIMENT_DATA,
)
from config.catalog_config import *
from data_engineering.data_utils import (
    ensure_catalog_exists,
    log_data_quality_metrics,
    add_date_features,
)

# COMMAND ----------

# Initialize MLflow (use data experiment for data prep)
mlflow.set_experiment(MLFLOW_EXPERIMENT_DATA)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Catalog and Schemas

# COMMAND ----------

# Create catalog and schemas if they don't exist
ensure_catalog_exists(CATALOG)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Articles Data

# COMMAND ----------

print(f"Loading articles from: {ARTICLES_CSV}")

articles_df = (
    spark.read.option("header", "true").option("inferSchema", "true").csv(ARTICLES_CSV)
)

# Show schema and sample
print("\nArticles Schema:")
articles_df.printSchema()

print("\nArticles Sample:")
display(articles_df.limit(5))

# Data quality check
log_data_quality_metrics(articles_df, "articles")

# COMMAND ----------

# Write to Delta table
print(f"Writing articles to Delta table: {ARTICLES_TABLE}")

articles_df.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(ARTICLES_TABLE)

print(f"✓ Articles table created with {articles_df.count():,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Customers Data

# COMMAND ----------

print(f"Loading customers from: {CUSTOMERS_CSV}")

customers_df = (
    spark.read.option("header", "true").option("inferSchema", "true").csv(CUSTOMERS_CSV)
)

# Show schema and sample
print("\nCustomers Schema:")
customers_df.printSchema()

print("\nCustomers Sample:")
display(customers_df.limit(5))

# Data quality check
log_data_quality_metrics(customers_df, "customers")

# COMMAND ----------

# Write to Delta table
print(f"Writing customers to Delta table: {CUSTOMERS_TABLE}")

customers_df.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(CUSTOMERS_TABLE)

print(f"✓ Customers table created with {customers_df.count():,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Transactions Data

# COMMAND ----------

print(f"Loading transactions from: {TRANSACTIONS_CSV}")

transactions_df = (
    spark.read.option("header", "true")
    .option("inferSchema", "true")
    .csv(TRANSACTIONS_CSV)
)

# Show schema and sample
print("\nTransactions Schema:")
transactions_df.printSchema()

print("\nTransactions Sample:")
display(transactions_df.limit(5))

# COMMAND ----------

# Add date features for partitioning and analysis
transactions_df = add_date_features(transactions_df)

print("\nTransactions with date features:")
display(
    transactions_df.select("t_dat", "year", "month", "year_month", "dayofweek").limit(5)
)

# Data quality check
log_data_quality_metrics(transactions_df, "transactions")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Write Transactions with Partitioning

# COMMAND ----------

print(f"Writing transactions to Delta table: {TRANSACTIONS_TABLE}")
print("Partitioning by year_month for efficient querying...")

transactions_df.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).partitionBy("year_month").saveAsTable(TRANSACTIONS_TABLE)

print(f"✓ Transactions table created with {transactions_df.count():,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Data Summary

# COMMAND ----------

# Create summary statistics
with mlflow.start_run(run_name="data_prep_summary") as run:

    # Log row counts
    articles_count = spark.table(ARTICLES_TABLE).count()
    customers_count = spark.table(CUSTOMERS_TABLE).count()
    transactions_count = spark.table(TRANSACTIONS_TABLE).count()

    mlflow.log_metric("articles_count", articles_count)
    mlflow.log_metric("customers_count", customers_count)
    mlflow.log_metric("transactions_count", transactions_count)

    # Date range in transactions
    date_range = (
        spark.table(TRANSACTIONS_TABLE)
        .select(min("t_dat").alias("min_date"), max("t_dat").alias("max_date"))
        .collect()[0]
    )

    print("\n" + "=" * 60)
    print("DATA PREPARATION SUMMARY")
    print("=" * 60)
    print(f"Articles:      {articles_count:,}")
    print(f"Customers:     {customers_count:,}")
    print(f"Transactions:  {transactions_count:,}")
    print(f"Date range:    {date_range.min_date} to {date_range.max_date}")
    print("=" * 60)

    mlflow.log_param("min_date", str(date_range.min_date))
    mlflow.log_param("max_date", str(date_range.max_date))
    mlflow.set_tag("stage", "data_preparation")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Tables

# COMMAND ----------

# Verify all tables are accessible
print("Verifying tables...")

tables_to_verify = [ARTICLES_TABLE, CUSTOMERS_TABLE, TRANSACTIONS_TABLE]

for table in tables_to_verify:
    try:
        df = spark.table(table)
        count = df.count()
        print(f"✓ {table}: {count:,} rows")
    except Exception as e:
        print(f"✗ {table}: ERROR - {str(e)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC Data preparation complete! Next notebooks:
# MAGIC 1. `02_feature_engineering.py` - Create customer and article features
# MAGIC 2. `03_train_test_split.py` - Create temporal train/val/test splits
# MAGIC 3. `04_model_popularity.py` - Train first baseline model
