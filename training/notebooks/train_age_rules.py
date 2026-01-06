# Databricks notebook source
# MAGIC %md
# MAGIC # Age-Based Rules Model
# MAGIC
# MAGIC Rule-based recommendation model using customer age segmentation.
# MAGIC
# MAGIC **Algorithm:**
# MAGIC - Segment customers by age groups (18-24, 25-34, 35-44, 45-54, 55+)
# MAGIC - Calculate popular items within each age segment
# MAGIC - Recommend segment-specific popular items to customers
# MAGIC
# MAGIC **Expected Performance:** MAP@12 ~ 0.010-0.020

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
import matplotlib.pyplot as plt
from databricks.feature_engineering import FeatureEngineeringClient

from config.catalog_config import *
from config.model_config import AGE_RULES_CONFIG, EVAL_CONFIG
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

# Initialize clients with experiment from parameters
mlflow.set_experiment(experiment_name)
fe = FeatureEngineeringClient()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Data

# COMMAND ----------

# Load data
train_df = load_delta_table(TRAIN_TABLE)
val_ground_truth = load_delta_table(VAL_GROUND_TRUTH_TABLE)

# Load customer features from Feature Store
customer_features = fe.read_table(name=CUSTOMER_FEATURES)

print(f"Training transactions: {train_df.count():,}")
print(f"Customer features: {customer_features.count():,}")
print(f"Validation ground truth: {val_ground_truth.count():,}")

# COMMAND ----------

# Check age group distribution
print("Age group distribution:")
display(customer_features.groupBy("age_group").count().orderBy("age_group"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Calculate Popular Items by Age Segment

# COMMAND ----------

# Get parameters
n_days = AGE_RULES_CONFIG.get("n_days", 7)
top_n = AGE_RULES_CONFIG["top_n_per_segment"]
reference_date = EVAL_CONFIG["train_cutoff"]

print(f"Parameters:")
print(f"  Time window: last {n_days} days")
print(f"  Top N per segment: {top_n}")
print(f"  Reference date: {reference_date}")

# COMMAND ----------

# Filter to recent transactions
cutoff_date = to_date(lit(reference_date)) - expr(f"INTERVAL {n_days} DAYS")

recent_transactions = train_df.filter(col("t_dat") >= cutoff_date)

print(f"\nRecent transactions: {recent_transactions.count():,}")

# COMMAND ----------

# Join transactions with customer age groups
transactions_with_age = recent_transactions.join(
    customer_features.select("customer_id", "age_group"), on="customer_id", how="left"
)

# Filter out unknown age groups
transactions_with_age = transactions_with_age.filter(
    col("age_group").isNotNull() & (col("age_group") != "Unknown")
)

print(f"Transactions with age groups: {transactions_with_age.count():,}")

# COMMAND ----------

# Calculate popular items per age segment
from pyspark.sql.window import Window

popular_by_age = (
    transactions_with_age.groupBy("age_group", "article_id")
    .agg(count("*").alias("segment_purchases"))
    .withColumn(
        "rank",
        row_number().over(
            Window.partitionBy("age_group").orderBy(col("segment_purchases").desc())
        ),
    )
    .filter(col("rank") <= top_n)
    .orderBy("age_group", "rank")
)

print(f"\nPopular items by age segment:")
display(popular_by_age)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Analyze Segment Differences

# COMMAND ----------

# Compare top items across age groups
print("Top 5 items per age group:")

for age_group in ["18-24", "25-34", "35-44", "45-54", "55+"]:
    segment_items = (
        popular_by_age.filter(col("age_group") == age_group)
        .select("article_id", "segment_purchases", "rank")
        .limit(5)
    )

    print(f"\n{age_group}:")
    display(segment_items)

# COMMAND ----------

# Visualize segment popularity
segment_stats = (
    popular_by_age.groupBy("age_group")
    .agg(
        sum("segment_purchases").alias("total_purchases"),
        count("*").alias("unique_articles"),
    )
    .orderBy("age_group")
    .toPandas()
)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))

# Total purchases by age group
ax1.bar(segment_stats["age_group"], segment_stats["total_purchases"])
ax1.set_title("Total Purchases by Age Group")
ax1.set_xlabel("Age Group")
ax1.set_ylabel("Purchase Count")
ax1.tick_params(axis="x", rotation=45)

# Unique articles by age group
ax2.bar(segment_stats["age_group"], segment_stats["unique_articles"])
ax2.set_title(f"Number of Top {top_n} Articles by Age Group")
ax2.set_xlabel("Age Group")
ax2.set_ylabel("Article Count")
ax2.tick_params(axis="x", rotation=45)

plt.tight_layout()
display(fig)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Predictions

# COMMAND ----------

# Create mapping of age_group -> recommended articles
age_recommendations = {}

for row in popular_by_age.select("age_group", "article_id", "rank").collect():
    if row.age_group not in age_recommendations:
        age_recommendations[row.age_group] = []
    age_recommendations[row.age_group].append(row.article_id)

print("Recommendations per age group:")
for age_group, articles in age_recommendations.items():
    print(f"  {age_group}: {len(articles)} articles")

# COMMAND ----------

# Generate predictions for all customers
predictions_df = customer_features.select("customer_id", "age_group")

# Create UDF to map age_group to recommendations
from pyspark.sql.types import ArrayType, IntegerType


def get_age_recommendations(age_group):
    return age_recommendations.get(age_group, [])


get_recommendations_udf = udf(get_age_recommendations, ArrayType(IntegerType()))

predictions_df = predictions_df.withColumn(
    "predicted_articles", get_recommendations_udf(col("age_group"))
)

# Filter out customers with no recommendations (Unknown age group)
predictions_df = predictions_df.filter(size(col("predicted_articles")) > 0)

print(f"Predictions generated for {predictions_df.count():,} customers")

# Show sample
print("\nSample predictions:")
display(predictions_df.limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evaluate Model

# COMMAND ----------

# Start MLflow run
with mlflow.start_run(run_name="age_rules_model") as run:

    # Log parameters
    mlflow.log_param("model_type", "age_rules")
    mlflow.log_param("n_days", n_days)
    mlflow.log_param("top_n_per_segment", top_n)
    mlflow.log_param("reference_date", reference_date)
    mlflow.log_param("num_age_groups", len(age_recommendations))

    # Evaluate on validation set
    print("\n" + "=" * 60)
    print("EVALUATING AGE RULES MODEL")
    print("=" * 60)

    metrics = log_evaluation_metrics(
        predictions_df, val_ground_truth, "Age Rules Model", k=12
    )

    # Log age-specific recommendations
    for age_group, articles in age_recommendations.items():
        mlflow.log_dict(
            {"article_ids": articles}, f"recommendations_age_{age_group}.json"
        )

    # Log model artifact
    model_artifact = {
        "model_type": "age_rules",
        "age_recommendations": {k: v for k, v in age_recommendations.items()},
        "parameters": {"n_days": n_days, "reference_date": reference_date},
    }

    mlflow.log_dict(model_artifact, "model.json")

    # Log visualization
    mlflow.log_figure(fig, "age_segment_analysis.png")

    # Save run ID
    run_id = run.info.run_id
    print(f"\nMLflow run ID: {run_id}")

    mlflow.set_tag("stage", "training")
    mlflow.set_tag("model_type", "age_rules")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Register Model to MLflow Model Registry

# COMMAND ----------

# Create a PyFunc model wrapper for the age rules model
import mlflow.pyfunc
import pandas as pd


class AgeRulesModelWrapper(mlflow.pyfunc.PythonModel):
    """MLflow PyFunc wrapper for age-based rules recommendation model"""

    def __init__(self, age_recommendations, model_params):
        self.age_recommendations = age_recommendations
        self.model_params = model_params

    def load_context(self, context):
        """Load any necessary artifacts"""
        pass

    def predict(self, context, model_input):
        """
        Generate predictions for customers based on age group

        Args:
            model_input: DataFrame with customer_id and age_group columns

        Returns:
            DataFrame with customer_id and predicted_articles (list)
        """
        if not isinstance(model_input, pd.DataFrame):
            raise ValueError("Input must be a pandas DataFrame")

        if "age_group" not in model_input.columns:
            raise ValueError("Input DataFrame must contain 'age_group' column")

        # Map age groups to recommendations
        result = model_input[["customer_id"]].copy()
        result["predicted_articles"] = model_input["age_group"].apply(
            lambda age: self.age_recommendations.get(age, [])
        )

        return result


# Register the model
print("\nRegistering model to MLflow Model Registry...")

with mlflow.start_run(run_id=run_id):
    # Create model instance
    age_model = AgeRulesModelWrapper(
        age_recommendations=age_recommendations, model_params=model_artifact["parameters"]
    )

    # Define input/output signature
    from mlflow.models.signature import infer_signature

    # Create sample input/output for signature
    sample_input = pd.DataFrame(
        {"customer_id": ["sample_1", "sample_2"], "age_group": ["25-34", "35-44"]}
    )
    sample_output = age_model.predict(None, sample_input)
    signature = infer_signature(sample_input, sample_output)

    # Log model
    mlflow.pyfunc.log_model(
        artifact_path="age_rules_model",
        python_model=age_model,
        signature=signature,
    )

# Register to Unity Catalog Model Registry
# Use fully qualified name: catalog.schema.model_name
uc_model_name = f"{catalog_name}.{schema_name}.{model_name}"
model_uri = f"runs:/{run_id}/age_rules_model"

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
    description=f"Age-based segmentation recommendation model. "
    f"MAP@12: {metrics['map@12']:.6f}. "
    f"Personalized by age group with {len(age_recommendations)} segments.",
)

client.update_model_version(
    name=uc_model_name,
    version=registered_model.version,
    description=f"Trained on last {n_days} days. "
    f"MAP@12: {metrics['map@12']:.6f}. "
    f"Top {top_n} items per age segment. Reference date={reference_date}",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save Predictions

# COMMAND ----------

# Save predictions to Delta table
predictions_df.withColumn("model_type", lit("age_rules")).withColumn(
    "run_id", lit(run_id)
).write.format("delta").mode("overwrite").option("overwriteSchema", "true").saveAsTable(
    f"{FULL_NAME}.age_rules_predictions_gold"
)

print(f"✓ Predictions saved to {FULL_NAME}.age_rules_predictions_gold")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Compare with Popularity Model

# COMMAND ----------

# Load popularity model predictions for comparison
try:
    popularity_predictions = load_delta_table(f"{FULL_NAME}.popularity_predictions")

    # Both models should have predictions for the same customers
    comparison = predictions_df.alias("age").join(
        popularity_predictions.alias("pop"),
        col("age.customer_id") == col("pop.customer_id"),
        how="inner",
    )

    # Check overlap in recommendations
    from pyspark.sql.functions import array_intersect, size as array_size

    comparison = comparison.withColumn(
        "overlap",
        array_size(
            array_intersect(
                col("age.predicted_articles"), col("pop.predicted_articles")
            )
        ),
    )

    avg_overlap = comparison.select(avg("overlap")).collect()[0][0]

    print(
        f"\nAverage overlap between age rules and popularity: {avg_overlap:.2f} articles"
    )

    # Log comparison metric in a separate run
    with mlflow.start_run(run_name="age_rules_comparison"):
        mlflow.log_metric("avg_recommendation_overlap", avg_overlap)
        mlflow.set_tag("comparison_type", "age_rules_vs_popularity")

    print("Sample comparison:")
    display(
        comparison.select(
            col("age.customer_id"),
            col("age.age_group"),
            col("age.predicted_articles").alias("age_recommendations"),
            col("pop.predicted_articles").alias("popularity_recommendations"),
            "overlap",
        ).limit(10)
    )

except Exception as e:
    print(f"Could not compare with popularity model: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Model Insights

# COMMAND ----------

# Analyze which age groups have most distinct preferences
print("Segment Analysis:")

for age_group in age_recommendations.keys():
    articles = age_recommendations[age_group]
    num_articles = len(articles)

    # Count how many are unique to this segment
    other_articles = []
    for other_group, other_recs in age_recommendations.items():
        if other_group != age_group:
            other_articles.extend(other_recs)

    unique_to_segment = len([a for a in articles if a not in other_articles])
    uniqueness_pct = (unique_to_segment / num_articles * 100) if num_articles > 0 else 0

    print(f"\n{age_group}:")
    print(f"  Total recommendations: {num_articles}")
    print(f"  Unique to segment: {unique_to_segment} ({uniqueness_pct:.1f}%)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "=" * 60)
print("AGE RULES MODEL SUMMARY")
print("=" * 60)
print(f"Model Type: Age-based segmentation")
print(f"Age Groups: {len(age_recommendations)}")
print(f"Training Period: {n_days} days before {reference_date}")
print(f"Recommendations: Top {top_n} articles per age segment")
print(f"MAP@12: {metrics['map@12']:.6f}")
print(f"Customers Evaluated: {metrics['num_customers']:,}")
if "catalog_coverage" in metrics:
    print(f"Catalog Coverage: {metrics['catalog_coverage']:.4f}")
print("=" * 60)
print(f"\n✓ Sprint 2 Complete! Age-based model with Feature Store integration.")
print(f"✓ MLflow run: {run_id}")
print("=" * 60)
