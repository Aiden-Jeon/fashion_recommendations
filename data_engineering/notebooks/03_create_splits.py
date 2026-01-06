# Databricks notebook source
# MAGIC %md
# MAGIC # Train/Validation/Test Split
# MAGIC
# MAGIC Create temporal splits for recommendation model evaluation.
# MAGIC
# MAGIC **Approach:**
# MAGIC - Use temporal split (not random) to prevent data leakage
# MAGIC - Predict next 7 days based on historical purchases
# MAGIC
# MAGIC **Split Strategy:**
# MAGIC - **Training**: All data up to 2020-09-01
# MAGIC - **Validation**: 2020-09-02 to 2020-09-15 (predict 2020-09-16 to 2020-09-22)
# MAGIC - **Test**: 2020-09-16 to 2020-09-22 (predict 2020-09-23 to 2020-09-29)
# MAGIC
# MAGIC **Note:** Adjust dates based on actual data availability

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import sys
import os

# Add project root to path (go up 2 levels from notebooks/)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__) if '__file__' in dir() else '.', "../..")))

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
import mlflow

from config.catalog_config import *
from config.model_config import EVAL_CONFIG
from data_engineering.data_utils import load_delta_table, create_ground_truth_labels

# COMMAND ----------

# Initialize MLflow (use data experiment for splits)
from config.paths import MLFLOW_EXPERIMENT_DATA

mlflow.set_experiment(MLFLOW_EXPERIMENT_DATA)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Transactions

# COMMAND ----------

transactions_df = load_delta_table(TRANSACTIONS_TABLE)

print(f"Total transactions: {transactions_df.count():,}")

# Check date range
date_stats = transactions_df.select(
    min("t_dat").alias("min_date"),
    max("t_dat").alias("max_date"),
    countDistinct("customer_id").alias("unique_customers"),
    countDistinct("article_id").alias("unique_articles")
).collect()[0]

print(f"\nDate range: {date_stats.min_date} to {date_stats.max_date}")
print(f"Unique customers: {date_stats.unique_customers:,}")
print(f"Unique articles: {date_stats.unique_articles:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Define Split Dates

# COMMAND ----------

# Get split dates from config
train_cutoff = EVAL_CONFIG["train_cutoff"]
val_cutoff = EVAL_CONFIG["val_cutoff"]
test_cutoff = EVAL_CONFIG["test_cutoff"]
prediction_days = EVAL_CONFIG["prediction_window_days"]

print("Split Configuration:")
print(f"  Training data: up to {train_cutoff}")
print(f"  Validation obs: {train_cutoff} to {val_cutoff}")
print(f"  Validation target: next {prediction_days} days after {val_cutoff}")
print(f"  Test obs: up to {test_cutoff}")
print(f"  Test target: next {prediction_days} days after {test_cutoff}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Training Set

# COMMAND ----------

train_df = transactions_df.filter(col("t_dat") <= train_cutoff)

print(f"Training transactions: {train_df.count():,}")
print(f"Training period: {train_df.select(min('t_dat')).collect()[0][0]} to {train_cutoff}")

# Save to Delta
train_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(TRAIN_TABLE)

print(f"✓ Training table saved: {TRAIN_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Validation Set

# COMMAND ----------

# Validation observations (for training models)
val_obs_df = transactions_df.filter(
    (col("t_dat") > train_cutoff) & (col("t_dat") <= val_cutoff)
)

print(f"Validation observations: {val_obs_df.count():,}")

# Save to Delta
val_obs_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(VAL_TABLE)

print(f"✓ Validation table saved: {VAL_TABLE}")

# COMMAND ----------

# Create validation ground truth (for evaluation)
# These are the purchases we're trying to predict
val_target_start = (
    to_date(lit(val_cutoff)) + expr("INTERVAL 1 DAY")
)
val_target_end = (
    to_date(lit(val_cutoff)) + expr(f"INTERVAL {prediction_days} DAYS")
)

print(f"\nValidation ground truth period:")
print(f"  From: {val_cutoff} + 1 day")
print(f"  To: {val_cutoff} + {prediction_days} days")

# Get ground truth labels
val_ground_truth = transactions_df.filter(
    (col("t_dat") > val_cutoff) &
    (col("t_dat") <= to_date(lit(val_cutoff)) + expr(f"INTERVAL {prediction_days} DAYS"))
).groupBy("customer_id").agg(
    collect_list("article_id").alias("actual_articles"),
    count("*").alias("num_purchases")
)

print(f"Validation ground truth customers: {val_ground_truth.count():,}")
print(f"Validation ground truth total purchases: {val_ground_truth.select(sum('num_purchases')).collect()[0][0]:,}")

# Save to Delta
val_ground_truth.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(VAL_GROUND_TRUTH_TABLE)

print(f"✓ Validation ground truth saved: {VAL_GROUND_TRUTH_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Test Set

# COMMAND ----------

# Test observations (all data up to test cutoff)
test_obs_df = transactions_df.filter(col("t_dat") <= test_cutoff)

print(f"Test observations: {test_obs_df.count():,}")

# Save to Delta
test_obs_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(TEST_TABLE)

print(f"✓ Test table saved: {TEST_TABLE}")

# COMMAND ----------

# Create test ground truth
test_ground_truth = transactions_df.filter(
    (col("t_dat") > test_cutoff) &
    (col("t_dat") <= to_date(lit(test_cutoff)) + expr(f"INTERVAL {prediction_days} DAYS"))
).groupBy("customer_id").agg(
    collect_list("article_id").alias("actual_articles"),
    count("*").alias("num_purchases")
)

print(f"Test ground truth customers: {test_ground_truth.count():,}")

# Save to Delta
test_ground_truth.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(TEST_GROUND_TRUTH_TABLE)

print(f"✓ Test ground truth saved: {TEST_GROUND_TRUTH_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Split Summary

# COMMAND ----------

with mlflow.start_run(run_name="train_test_split") as run:

    # Log parameters
    mlflow.log_param("train_cutoff", train_cutoff)
    mlflow.log_param("val_cutoff", val_cutoff)
    mlflow.log_param("test_cutoff", test_cutoff)
    mlflow.log_param("prediction_window_days", prediction_days)

    # Log metrics
    train_count = spark.table(TRAIN_TABLE).count()
    val_count = spark.table(VAL_TABLE).count()
    test_count = spark.table(TEST_TABLE).count()
    val_gt_count = spark.table(VAL_GROUND_TRUTH_TABLE).count()
    test_gt_count = spark.table(TEST_GROUND_TRUTH_TABLE).count()

    mlflow.log_metric("train_transactions", train_count)
    mlflow.log_metric("val_transactions", val_count)
    mlflow.log_metric("test_transactions", test_count)
    mlflow.log_metric("val_ground_truth_customers", val_gt_count)
    mlflow.log_metric("test_ground_truth_customers", test_gt_count)

    # Summary
    print("\n" + "="*60)
    print("TRAIN/VAL/TEST SPLIT SUMMARY")
    print("="*60)
    print(f"Training transactions:        {train_count:,}")
    print(f"Validation transactions:      {val_count:,}")
    print(f"Test transactions:            {test_count:,}")
    print(f"Val ground truth customers:   {val_gt_count:,}")
    print(f"Test ground truth customers:  {test_gt_count:,}")
    print("="*60)

    mlflow.set_tag("stage", "data_split")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Data Quality

# COMMAND ----------

# Check for customers with no purchases in prediction window
val_all_customers = spark.table(CUSTOMERS_TABLE).select("customer_id")
val_customers_with_purchases = spark.table(VAL_GROUND_TRUTH_TABLE).select("customer_id")

customers_without_purchases = val_all_customers.join(
    val_customers_with_purchases, on="customer_id", how="left_anti"
).count()

total_customers = val_all_customers.count()
purchase_rate = (val_gt_count / total_customers) * 100

print(f"\nValidation set analysis:")
print(f"  Total customers: {total_customers:,}")
print(f"  Customers with purchases in prediction window: {val_gt_count:,} ({purchase_rate:.2f}%)")
print(f"  Customers without purchases: {customers_without_purchases:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sample Ground Truth

# COMMAND ----------

# Show sample ground truth
print("Sample validation ground truth:")
display(spark.table(VAL_GROUND_TRUTH_TABLE).limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC Train/val/test splits created successfully!
# MAGIC
# MAGIC Next notebooks:
# MAGIC 1. `04_model_popularity.py` - Train time-based popularity baseline
# MAGIC 2. `02_feature_engineering.py` - Create customer and article features
# MAGIC 3. `05_model_age_rules.py` - Train age-based rules model
