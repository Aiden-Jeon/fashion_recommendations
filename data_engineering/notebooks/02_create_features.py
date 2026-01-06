# Databricks notebook source
# MAGIC %md
# MAGIC # Feature Engineering with Databricks Feature Store
# MAGIC
# MAGIC Create reusable features for customer and article entities and register them
# MAGIC in Databricks Feature Store for lineage tracking and feature reuse.
# MAGIC
# MAGIC **Features Created:**
# MAGIC - Customer features: age groups, purchase frequency, recency, monetary value
# MAGIC - Article features: popularity trends, sales velocity
# MAGIC
# MAGIC **Outputs:**
# MAGIC - Feature Store tables for customers and articles

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

# MAGIC %pip install databricks-feature-engineering
# MAGIC %restart_python

# COMMAND ----------

import sys
import os

# Add project root to path (go up 2 levels from notebooks/)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__) if '__file__' in dir() else '.', "../..")))

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
import mlflow
from databricks.feature_engineering import FeatureEngineeringClient, FeatureLookup

from config.catalog_config import *
from config.model_config import EVAL_CONFIG
from data_engineering.data_utils import load_delta_table
from data_engineering.feature_utils import (
    calculate_customer_features,
    create_age_groups,
    calculate_article_features,
    calculate_recency_frequency_monetary,
    calculate_customer_category_preferences,
)

# COMMAND ----------

# Initialize clients
from config.paths import MLFLOW_EXPERIMENT_DATA

mlflow.set_experiment(MLFLOW_EXPERIMENT_DATA)
fe = FeatureEngineeringClient()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Data

# COMMAND ----------

# Load raw data
transactions_df = load_delta_table(TRANSACTIONS_TABLE)
customers_df = load_delta_table(CUSTOMERS_TABLE)
articles_df = load_delta_table(ARTICLES_TABLE)

print(f"Transactions: {transactions_df.count():,}")
print(f"Customers: {customers_df.count():,}")
print(f"Articles: {articles_df.count():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Customer Features

# COMMAND ----------

reference_date = EVAL_CONFIG["train_cutoff"]
print(f"Reference date for features: {reference_date}")

# COMMAND ----------

# Filter transactions to training period (up to reference_date)
# This prevents data leakage by only using data available at prediction time
train_transactions = transactions_df.filter(col("t_dat") <= reference_date)

print(f"Training transactions (up to {reference_date}): {train_transactions.count():,}")

# COMMAND ----------

# Calculate customer behavioral features
print("Calculating customer features...")

customer_features = calculate_customer_features(train_transactions, customers_df, reference_date)

print(f"Customer features shape: {customer_features.count()} rows, {len(customer_features.columns)} columns")

# COMMAND ----------

# Add age groups
customer_features = create_age_groups(customer_features)

print("\nAge group distribution:")
display(customer_features.groupBy("age_group").count().orderBy("age_group"))

# COMMAND ----------

# Calculate RFM features
rfm_features = calculate_recency_frequency_monetary(train_transactions, reference_date)

# Join with customer features
customer_features = customer_features.join(rfm_features, on="customer_id", how="left")

print("Customer features with RFM:")
display(customer_features.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Register Customer Features to Feature Store

# COMMAND ----------

# Select relevant columns for feature store
customer_feature_columns = [
    "customer_id",
    "age",
    "age_group",
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
    "purchase_frequency_30d",
    "recency_days",
    "frequency",
    "monetary_value",
    "recency_score",
    "frequency_score",
    "monetary_score",
    "rfm_score",
]

customer_features_fs = customer_features.select(
    [c for c in customer_feature_columns if c in customer_features.columns]
)

print(f"Registering {len(customer_features_fs.columns)} customer features to Feature Store...")

# COMMAND ----------

# Create or update feature table
try:
    # Try to create new feature table
    customer_feature_table = fe.create_table(
        name=CUSTOMER_FEATURES,
        primary_keys=["customer_id"],
        df=customer_features_fs,
        description="Customer behavioral features including purchase history, RFM scores, and demographics",
    )
    print(f"✓ Created feature table: {CUSTOMER_FEATURES}")
except Exception as e:
    # If table exists, update it
    print(f"Feature table exists, updating: {e}")
    fe.write_table(name=CUSTOMER_FEATURES, df=customer_features_fs, mode="overwrite")
    print(f"✓ Updated feature table: {CUSTOMER_FEATURES}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Article Features

# COMMAND ----------

print("Calculating article features...")

article_features = calculate_article_features(train_transactions, articles_df, reference_date)

print(
    f"Article features shape: {article_features.count()} rows, {len(article_features.columns)} columns"
)

# COMMAND ----------

# Show sample article features
print("Sample article features:")
display(article_features.select(
    "article_id",
    "product_group_name",
    "product_type_name",
    "popularity_7d",
    "popularity_30d",
    "popularity_lifetime",
    "popularity_trend",
    "days_since_last_sale",
).limit(20))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Register Article Features to Feature Store

# COMMAND ----------

# Select relevant columns for feature store
article_feature_columns = [
    "article_id",
    "product_type_name",
    "product_group_name",
    "colour_group_name",
    "department_name",
    "index_group_name",
    "section_name",
    "popularity_7d",
    "unique_customers_7d",
    "avg_price_7d",
    "popularity_30d",
    "unique_customers_30d",
    "avg_price_30d",
    "popularity_lifetime",
    "unique_customers_lifetime",
    "days_since_last_sale",
    "popularity_trend",
]

article_features_fs = article_features.select(
    [c for c in article_feature_columns if c in article_features.columns]
)

print(f"Registering {len(article_features_fs.columns)} article features to Feature Store...")

# COMMAND ----------

# Create or update feature table
try:
    article_feature_table = fe.create_table(
        name=ARTICLE_FEATURES,
        primary_keys=["article_id"],
        df=article_features_fs,
        description="Article features including popularity metrics, sales trends, and product metadata",
    )
    print(f"✓ Created feature table: {ARTICLE_FEATURES}")
except Exception as e:
    print(f"Feature table exists, updating: {e}")
    fe.write_table(name=ARTICLE_FEATURES, df=article_features_fs, mode="overwrite")
    print(f"✓ Updated feature table: {ARTICLE_FEATURES}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Feature Statistics

# COMMAND ----------

# Customer feature statistics
print("Customer Feature Statistics:")
customer_numeric_cols = [
    "purchases_7d",
    "purchases_30d",
    "purchases_lifetime",
    "recency_days",
    "frequency",
    "monetary_value",
]

display(customer_features_fs.select([c for c in customer_numeric_cols if c in customer_features_fs.columns]).summary())

# COMMAND ----------

# Article feature statistics
print("Article Feature Statistics:")
article_numeric_cols = [
    "popularity_7d",
    "popularity_30d",
    "popularity_lifetime",
    "popularity_trend",
]

display(article_features_fs.select([c for c in article_numeric_cols if c in article_features_fs.columns]).summary())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Visualize Features

# COMMAND ----------

import matplotlib.pyplot as plt
import seaborn as sns

# Customer distribution by age group
age_dist = (
    customer_features_fs.groupBy("age_group").count().orderBy("age_group").toPandas()
)

fig, axes = plt.subplots(2, 2, figsize=(15, 10))

# Age distribution
axes[0, 0].bar(age_dist["age_group"], age_dist["count"])
axes[0, 0].set_title("Customer Distribution by Age Group")
axes[0, 0].set_xlabel("Age Group")
axes[0, 0].set_ylabel("Count")
axes[0, 0].tick_params(axis="x", rotation=45)

# Purchase frequency distribution
purchase_dist = customer_features_fs.select("purchases_30d").toPandas()
axes[0, 1].hist(purchase_dist["purchases_30d"], bins=50)
axes[0, 1].set_title("Distribution of Purchases (30 days)")
axes[0, 1].set_xlabel("Number of Purchases")
axes[0, 1].set_ylabel("Frequency")

# Monetary value distribution
monetary_dist = customer_features_fs.select("monetary_value").toPandas()
axes[1, 0].hist(monetary_dist["monetary_value"], bins=50)
axes[1, 0].set_title("Distribution of Monetary Value")
axes[1, 0].set_xlabel("Total Spent")
axes[1, 0].set_ylabel("Frequency")

# Article popularity distribution
popularity_dist = article_features_fs.select("popularity_7d").toPandas()
axes[1, 1].hist(popularity_dist["popularity_7d"], bins=50)
axes[1, 1].set_title("Distribution of Article Popularity (7 days)")
axes[1, 1].set_xlabel("Popularity Score")
axes[1, 1].set_ylabel("Frequency")

plt.tight_layout()
display(fig)

# Log to MLflow (inside the run context below)
# Will be logged in the feature_engineering run

# COMMAND ----------

# MAGIC %md
# MAGIC ## Log Feature Engineering Summary

# COMMAND ----------

with mlflow.start_run(run_name="feature_engineering") as run:

    # Log parameters
    mlflow.log_param("reference_date", reference_date)
    mlflow.log_param("num_customer_features", len(customer_features_fs.columns) - 1)
    mlflow.log_param("num_article_features", len(article_features_fs.columns) - 1)

    # Log metrics
    mlflow.log_metric("num_customers_with_features", customer_features_fs.count())
    mlflow.log_metric("num_articles_with_features", article_features_fs.count())

    # Log feature table names
    mlflow.log_param("customer_feature_table", CUSTOMER_FEATURES)
    mlflow.log_param("article_feature_table", ARTICLE_FEATURES)

    # Log feature lists
    mlflow.log_dict(
        {"customer_features": customer_features_fs.columns}, "customer_features.json"
    )
    mlflow.log_dict(
        {"article_features": article_features_fs.columns}, "article_features.json"
    )

    # Log visualizations
    mlflow.log_figure(fig, "feature_distributions.png")

    mlflow.set_tag("stage", "feature_engineering")

    print("\n" + "=" * 60)
    print("FEATURE ENGINEERING SUMMARY")
    print("=" * 60)
    print(f"Customer Features: {len(customer_features_fs.columns) - 1}")
    print(f"Article Features: {len(article_features_fs.columns) - 1}")
    print(f"Customers with features: {customer_features_fs.count():,}")
    print(f"Articles with features: {article_features_fs.count():,}")
    print(f"Feature Store tables:")
    print(f"  - {CUSTOMER_FEATURES}")
    print(f"  - {ARTICLE_FEATURES}")
    print("=" * 60)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Feature Lookup

# COMMAND ----------

# Test feature lookup for a sample customer
sample_customer = customer_features_fs.limit(1).select("customer_id")

print("Testing feature lookup...")
display(sample_customer)

# Lookup features
customer_with_features = fe.read_table(name=CUSTOMER_FEATURES)
print(f"\n✓ Successfully read {customer_with_features.count():,} customer features from Feature Store")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC ✓ Feature engineering complete!
# MAGIC
# MAGIC Features registered in Databricks Feature Store:
# MAGIC - Customer features with behavioral, RFM, and demographic data
# MAGIC - Article features with popularity and trend metrics
# MAGIC
# MAGIC **Next notebook:**
# MAGIC - `05_model_age_rules.py` - Train age-based segmentation model using these features
