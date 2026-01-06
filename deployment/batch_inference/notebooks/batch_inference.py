# Databricks notebook source
# MAGIC %md
# MAGIC # Batch Inference: Fashion Recommendations
# MAGIC
# MAGIC This notebook performs batch inference using the registered models to generate
# MAGIC recommendations for all customers.
# MAGIC
# MAGIC **Inputs:**
# MAGIC - catalog_name: Unity Catalog name
# MAGIC - schema_name: Schema containing tables and models
# MAGIC - model_name: Model name to use for inference (popularity_model, age_rules_model, etc.)
# MAGIC
# MAGIC **Outputs:**
# MAGIC - Recommendations table: `{catalog}.{schema}.recommendations`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import pyspark.sql.functions as F
from pyspark.sql.types import ArrayType, StringType
from datetime import datetime
import mlflow

# COMMAND ----------

# Get parameters
dbutils.widgets.text("catalog_name", "jongseob_demo")
dbutils.widgets.text("schema_name", "dev_fashion_recommendations")
dbutils.widgets.text("model_name", "popularity_model")

catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")
model_name = dbutils.widgets.get("model_name")

print(f"Catalog: {catalog_name}")
print(f"Schema: {schema_name}")
print(f"Model: {model_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Model

# COMMAND ----------

# Load the latest production model
model_uri = f"models:/{catalog_name}.{schema_name}.{model_name}/Production"
print(f"Loading model from: {model_uri}")

try:
    model = mlflow.pyfunc.load_model(model_uri)
    print("Model loaded successfully")
except Exception as e:
    print(f"Could not load model from Production alias, trying latest version: {e}")
    # Fallback to latest version if Production alias doesn't exist
    model_uri = f"models:/{catalog_name}.{schema_name}.{model_name}/latest"
    model = mlflow.pyfunc.load_model(model_uri)
    print(f"Loaded latest version from: {model_uri}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Customer Data

# COMMAND ----------

# Load customer data for scoring
customers_table = f"{catalog_name}.{schema_name}.customers_silver"
print(f"Loading customers from: {customers_table}")

customers_df = spark.table(customers_table)
print(f"Loaded {customers_df.count()} customers")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Recommendations

# COMMAND ----------

# TODO: Implement batch scoring logic
# This is a placeholder that should be implemented based on your model's input/output schema

print("Generating recommendations...")

# Example structure (to be implemented):
# recommendations_df = model.predict(customers_df)
# recommendations_df = recommendations_df.withColumn("created_at", F.current_timestamp())

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save Recommendations

# COMMAND ----------

# Save recommendations to Delta table
recommendations_table = f"{catalog_name}.{schema_name}.recommendations"
print(f"Saving recommendations to: {recommendations_table}")

# TODO: Uncomment when recommendations_df is implemented
# recommendations_df.write \
#     .format("delta") \
#     .mode("overwrite") \
#     .option("overwriteSchema", "true") \
#     .saveAsTable(recommendations_table)

print("Batch inference completed successfully")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Display summary statistics
print(f"""
Batch Inference Summary:
========================
Model: {model_name}
Model URI: {model_uri}
Customers Scored: {customers_df.count()}
Output Table: {recommendations_table}
Status: Completed
""")
