# Databricks notebook source
# MAGIC %md
# MAGIC # Time-Based Popularity Model
# MAGIC
# MAGIC Baseline recommendation model using recency-weighted popularity.
# MAGIC
# MAGIC **Algorithm:**
# MAGIC - Score = purchase_frequency * exp(-alpha * days_ago)
# MAGIC - Recommend top-12 trending items from last N days
# MAGIC
# MAGIC **Expected Performance:** MAP@12 ~ 0.005-0.015

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------
# MAGIC %pip install -r ../../requirements.txt
# MAGIC %restart_python

# COMMAND ----------

import sys

# Add project root to path (go up 2 levels from notebooks/)
sys.path.append("../../")

from pyspark.sql.functions import *
import mlflow

from config.catalog_config import *
from config.model_config import POPULARITY_CONFIG, EVAL_CONFIG
from data_engineering.data_utils import load_delta_table
from utils.evaluation_utils import calculate_map_at_k, log_evaluation_metrics

# COMMAND ----------

# Get parameters from bundle (passed as notebook parameters)
catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")
experiment_name = dbutils.widgets.get("experiment_name")
model_name = dbutils.widgets.get("model_name")

print(f"Parameters:")
print(f"  Catalog: {catalog_name}")
print(f"  Schema: {schema_name}")
print(f"  Experiment: {experiment_name}")
print(f"  Model: {model_name}")

# COMMAND ----------

# Initialize MLflow with experiment from parameters
mlflow.set_experiment(experiment_name)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Data

# COMMAND ----------

# Load training data
train_df = load_delta_table(TRAIN_TABLE)
customers_df = load_delta_table(CUSTOMERS_TABLE)
val_ground_truth = load_delta_table(VAL_GROUND_TRUTH_TABLE)

print(f"Training transactions: {train_df.count():,}")
print(f"Customers: {customers_df.count():,}")
print(f"Validation ground truth customers: {val_ground_truth.count():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Calculate Recency-Weighted Popularity

# COMMAND ----------

# Get parameters
n_days = POPULARITY_CONFIG["n_days"]
alpha = POPULARITY_CONFIG["alpha"]
top_n = POPULARITY_CONFIG["top_n"]
reference_date = EVAL_CONFIG["train_cutoff"]

print(f"Parameters:")
print(f"  Time window: last {n_days} days")
print(f"  Recency decay: alpha = {alpha}")
print(f"  Top N items: {top_n}")
print(f"  Reference date: {reference_date}")

# COMMAND ----------

# Calculate cutoff date
cutoff_date = to_date(lit(reference_date)) - expr(f"INTERVAL {n_days} DAYS")

print(f"\nFiltering transactions from {cutoff_date} to {reference_date}")

# Filter to recent time window
recent_transactions = train_df.filter(col("t_dat") >= cutoff_date)

print(f"Recent transactions: {recent_transactions.count():,}")

# COMMAND ----------

# Calculate recency weights
weighted_transactions = recent_transactions.withColumn(
    "days_ago", datediff(lit(reference_date), col("t_dat"))
).withColumn("recency_weight", exp(-lit(alpha) * col("days_ago")))

# Show sample
print("Sample weighted transactions:")
display(
    weighted_transactions.select(
        "t_dat", "article_id", "days_ago", "recency_weight"
    ).limit(10)
)

# COMMAND ----------

# Aggregate by article
popular_items = (
    weighted_transactions.groupBy("article_id")
    .agg(
        sum("recency_weight").alias("popularity_score"),
        count("*").alias("purchase_count"),
    )
    .orderBy(col("popularity_score").desc())
)

print(f"\nTotal unique articles in window: {popular_items.count():,}")

# Show top items
print(f"\nTop {top_n} popular items:")
display(popular_items.limit(top_n))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Predictions

# COMMAND ----------

# Get top N articles as recommendations
top_articles = (
    popular_items.limit(top_n).select("article_id").toPandas()["article_id"].tolist()
)

print(f"Recommending {len(top_articles)} articles to all customers")
print(f"Top 5 article IDs: {top_articles[:5]}")

# COMMAND ----------

# Create predictions for all customers
# Non-personalized: same recommendations for everyone
predictions_df = customers_df.select("customer_id").withColumn(
    "predicted_articles", array([lit(a) for a in top_articles])
)

print(f"Predictions generated for {predictions_df.count():,} customers")

# Show sample
print("\nSample predictions:")
display(predictions_df.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evaluate Model

# COMMAND ----------

# Start MLflow run
with mlflow.start_run(run_name="popularity_baseline") as run:

    # Log parameters
    mlflow.log_param("model_type", "popularity")
    mlflow.log_param("n_days", n_days)
    mlflow.log_param("alpha", alpha)
    mlflow.log_param("top_n", top_n)
    mlflow.log_param("reference_date", reference_date)

    # Evaluate on validation set
    print("\n" + "=" * 60)
    print("EVALUATING POPULARITY MODEL")
    print("=" * 60)

    metrics = log_evaluation_metrics(
        predictions_df, val_ground_truth, "Popularity Baseline", k=12
    )

    # Log top articles as artifact
    top_articles_df = popular_items.limit(top_n).toPandas()
    mlflow.log_dict(top_articles_df.to_dict(orient="records"), "top_articles.json")

    # Log model artifact (just the list of top articles)
    import json

    model_artifact = {
        "model_type": "popularity",
        "top_articles": top_articles,
        "parameters": {
            "n_days": n_days,
            "alpha": alpha,
            "reference_date": reference_date,
        },
    }

    mlflow.log_dict(model_artifact, "model.json")

    # Save run ID for later use
    run_id = run.info.run_id
    print(f"\nMLflow run ID: {run_id}")

    mlflow.set_tag("stage", "training")
    mlflow.set_tag("model_type", "popularity")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Register Model to MLflow Model Registry

# COMMAND ----------

# Create a PyFunc model wrapper for the popularity model
import mlflow.pyfunc
import pandas as pd


class PopularityModelWrapper(mlflow.pyfunc.PythonModel):
    """MLflow PyFunc wrapper for popularity-based recommendation model"""

    def __init__(self, top_articles, model_params):
        self.top_articles = top_articles
        self.model_params = model_params

    def predict(self, context, model_input):
        """
        Generate predictions for customers

        Args:
            model_input: DataFrame with customer_id column

        Returns:
            DataFrame with customer_id and predicted_articles (list)
        """
        if isinstance(model_input, pd.DataFrame):
            # Return same recommendations for all customers (non-personalized)
            result = model_input[["customer_id"]].copy()
            result["predicted_articles"] = [self.top_articles] * len(result)
            return result
        else:
            raise ValueError("Input must be a pandas DataFrame with 'customer_id' column")


# Register the model
print("\nRegistering model to MLflow Model Registry...")

with mlflow.start_run(run_id=run_id):
    # Create model instance
    popularity_model = PopularityModelWrapper(
        top_articles=top_articles, model_params=model_artifact["parameters"]
    )

    # Define input/output signature
    from mlflow.models.signature import infer_signature

    # Create sample input/output for signature
    sample_input = pd.DataFrame({"customer_id": ["sample_customer_1"]})
    sample_output = popularity_model.predict(None, sample_input)
    signature = infer_signature(sample_input, sample_output)

    # Log model
    mlflow.pyfunc.log_model(
        artifact_path="popularity_model",
        python_model=popularity_model,
        signature=signature,
    )

# Register to Unity Catalog Model Registry
# Use fully qualified name: catalog.schema.model_name
uc_model_name = f"{catalog_name}.{schema_name}.{model_name}"
model_uri = f"runs:/{run_id}/popularity_model"

print(f"\nRegistering model to Unity Catalog: {uc_model_name}")

registered_model = mlflow.register_model(model_uri, uc_model_name)

print(f"✓ Model registered: {uc_model_name}")
print(f"✓ Version: {registered_model.version}")
print(f"✓ Run ID: {run_id}")

# Add model description
from mlflow.tracking import MlflowClient

client = MlflowClient()
client.update_registered_model(
    name=uc_model_name,
    description=f"Time-based recency-weighted popularity model. "
    f"MAP@12: {metrics['map@12']:.6f}. "
    f"Non-personalized baseline recommending top {len(top_articles)} trending items.",
)

client.update_model_version(
    name=uc_model_name,
    version=registered_model.version,
    description=f"Trained on last {n_days} days. "
    f"MAP@12: {metrics['map@12']:.6f}. "
    f"Alpha={alpha}, Reference date={reference_date}",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save Predictions

# COMMAND ----------

# Save predictions to Delta table for later comparison
predictions_df.withColumn("model_type", lit("popularity")).withColumn(
    "run_id", lit(run_id)
).write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{FULL_NAME}.popularity_predictions_gold"
)

print(f"✓ Predictions saved to {FULL_NAME}.popularity_predictions_gold")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Model Analysis

# COMMAND ----------

# Analyze popular articles
popular_with_details = (
    popular_items.limit(50)
    .join(load_delta_table(ARTICLES_TABLE), on="article_id", how="left")
    .select(
        "article_id",
        "product_type_name",
        "product_group_name",
        "colour_group_name",
        "popularity_score",
        "purchase_count",
    )
)

print("Top 20 popular articles with details:")
display(popular_with_details.limit(20))

# COMMAND ----------

# Visualize distribution
import matplotlib.pyplot as plt

# Get top 30 for visualization
top_30 = popular_items.limit(30).toPandas()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

# Popularity scores
ax1.barh(range(len(top_30)), top_30["popularity_score"])
ax1.set_xlabel("Popularity Score")
ax1.set_ylabel("Article Rank")
ax1.set_title("Top 30 Articles by Recency-Weighted Popularity")
ax1.invert_yaxis()

# Purchase counts
ax2.barh(range(len(top_30)), top_30["purchase_count"])
ax2.set_xlabel("Purchase Count")
ax2.set_ylabel("Article Rank")
ax2.set_title("Top 30 Articles by Purchase Count")
ax2.invert_yaxis()

plt.tight_layout()
display(fig)

# Log figure to MLflow in a separate analysis run
with mlflow.start_run(run_name="popularity_analysis"):
    mlflow.log_figure(fig, "popularity_distribution.png")
    mlflow.set_tag("analysis_type", "item_popularity_distribution")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "=" * 60)
print("POPULARITY MODEL SUMMARY")
print("=" * 60)
print(f"Model Type: Time-based recency-weighted popularity")
print(f"Training Period: {n_days} days before {reference_date}")
print(f"Recommendations: Top {top_n} articles for all customers")
print(f"MAP@12: {metrics['map@12']:.6f}")
print(f"Customers Evaluated: {metrics['num_customers']:,}")
if "catalog_coverage" in metrics:
    print(f"Catalog Coverage: {metrics['catalog_coverage']:.4f}")
print("=" * 60)
print(f"\n✓ Sprint 1 Complete! First working model deployed.")
print(f"✓ MLflow run: {run_id}")
print("=" * 60)
