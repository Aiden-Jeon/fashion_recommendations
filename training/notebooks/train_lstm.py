# Databricks notebook source
# MAGIC %md
# MAGIC # LSTM Sequential Recommendation Model
# MAGIC
# MAGIC Deep learning model using PyTorch LSTM to capture sequential patterns in customer purchase history.
# MAGIC
# MAGIC **Architecture:**
# MAGIC - Embedding layer (64 dims) for article representations
# MAGIC - 2-layer LSTM (128 hidden units) with dropout
# MAGIC - Fully connected layers (256 units)
# MAGIC - Output: Probability distribution over catalog
# MAGIC
# MAGIC **Expected Performance:** MAP@12 ~ 0.015-0.025

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

import sys

# Add project root to path (go up 2 levels from notebooks/)
sys.path.append("../../")

from pyspark.sql.functions import *
from pyspark.sql import Window
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from datetime import datetime
import mlflow
import mlflow.pytorch
import pickle
import os

from config.catalog_config import *
from config.model_config import LSTM_CONFIG, EVAL_CONFIG
from data_engineering.data_utils import load_delta_table
from utils.evaluation_utils import log_evaluation_metrics
from utils.preprocessing_utils import (
    ArticleEncoder,
    create_customer_sequences,
    create_train_sequences,
    prepare_dataloaders
)
from utils.pytorch_utils import (
    LSTMRecommender,
    LSTMTrainer,
    generate_recommendations
)

# COMMAND ----------

# Get parameters from bundle
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

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")
if device.type == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Model hyperparameters
config = LSTM_CONFIG.copy()
print("LSTM Configuration:")
for key, value in config.items():
    print(f"  {key}: {value}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Data

# COMMAND ----------

print("Loading data from Delta tables...")

# Load transactions
transactions_df = load_delta_table(f"{catalog_name}.{schema_name}.transactions_bronze")

# Load train/val splits
train_df = load_delta_table(f"{catalog_name}.{schema_name}.train_transactions_silver")
val_df = load_delta_table(f"{catalog_name}.{schema_name}.val_transactions_silver")

# Load ground truth
val_ground_truth = load_delta_table(f"{catalog_name}.{schema_name}.val_ground_truth_silver")
test_ground_truth = load_delta_table(f"{catalog_name}.{schema_name}.test_ground_truth_silver")

print(f"Total transactions: {transactions_df.count():,}")
print(f"Train: {train_df.count():,}")
print(f"Val: {val_df.count():,}")
print(f"Val ground truth customers: {val_ground_truth.count():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Build Article Encoder

# COMMAND ----------

print("Building article vocabulary...")

# Get all unique articles from transactions
all_articles = (
    transactions_df
    .select("article_id")
    .distinct()
    .collect()
)
article_ids = [row["article_id"] for row in all_articles]

print(f"Total unique articles: {len(article_ids):,}")

# Create and fit encoder
encoder = ArticleEncoder()
encoder.fit(article_ids)

print(f"Vocabulary size (including padding): {encoder.vocab_size:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Purchase Sequences

# COMMAND ----------

print("Creating customer purchase sequences...")

# Get unique customers from each split
train_customers = train_df.select("customer_id").distinct()
val_customers = val_df.select("customer_id").distinct()

print(f"Train customers: {train_customers.count():,}")
print(f"Val customers: {val_customers.count():,}")

# COMMAND ----------

# Filter transactions by customer set
train_transactions = transactions_df.join(
    train_customers,
    "customer_id",
    "inner"
)

val_transactions = transactions_df.join(
    val_customers,
    "customer_id",
    "inner"
)

print(f"Train transactions: {train_transactions.count():,}")
print(f"Val transactions: {val_transactions.count():,}")

# COMMAND ----------

# Create sequences for each split
train_sequences = create_customer_sequences(
    train_transactions,
    max_sequence_length=config['sequence_length'] + 5,  # Extra for target
    min_sequence_length=config['min_sequence_length']
)

val_sequences = create_customer_sequences(
    val_transactions,
    max_sequence_length=config['sequence_length'] + 5,
    min_sequence_length=config['min_sequence_length']
)

print(f"Train sequences: {train_sequences.count():,}")
print(f"Val sequences: {val_sequences.count():,}")

# Show sample
print("\nSample sequence:")
sample = train_sequences.limit(1).collect()[0]
print(f"Customer: {sample['customer_id']}")
print(f"Sequence length: {sample['sequence_length']}")
print(f"First 5 articles: {sample['sequence'][:5]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Training Pairs

# COMMAND ----------

print("Creating input/target pairs for training...")

# Create input/target pairs
train_pairs = create_train_sequences(
    train_sequences,
    sequence_length=config['sequence_length'],
    prediction_window=1  # Predict next item
)

val_pairs = create_train_sequences(
    val_sequences,
    sequence_length=config['sequence_length'],
    prediction_window=1
)

print(f"Train pairs: {train_pairs.count():,}")
print(f"Val pairs: {val_pairs.count():,}")

# Show sample
print("\nSample training pair:")
sample = train_pairs.limit(1).collect()[0]
print(f"Customer: {sample['customer_id']}")
print(f"Input sequence: {sample['input_sequence']}")
print(f"Target articles: {sample['target_articles']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Prepare DataLoaders

# COMMAND ----------

print("Preparing PyTorch DataLoaders...")

train_loader, val_loader = prepare_dataloaders(
    train_pairs,
    val_pairs,
    encoder=encoder,
    batch_size=config['batch_size'],
    sequence_length=config['sequence_length'],
    num_workers=4
)

print(f"Train batches: {len(train_loader)}")
print(f"Val batches: {len(val_loader)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Initialize Model

# COMMAND ----------

print("Initializing LSTM model...")

model = LSTMRecommender(
    vocab_size=encoder.vocab_size,
    embedding_dim=config['embedding_dim'],
    hidden_dim=config['hidden_dim'],
    num_layers=config['num_layers'],
    dropout=config['dropout'],
    padding_idx=encoder.padding_idx
)

# Count parameters (use builtins.sum to avoid conflict with PySpark sum)
import builtins
total_params = builtins.sum(p.numel() for p in model.parameters())
trainable_params = builtins.sum(p.numel() for p in model.parameters() if p.requires_grad)

print(f"Total parameters: {total_params:,}")
print(f"Trainable parameters: {trainable_params:,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Train Model with MLflow Tracking

# COMMAND ----------

print("Starting model training...")

# Start MLflow run
with mlflow.start_run(run_name="lstm_sequential") as run:
    # Log parameters
    mlflow.log_param("model_type", "lstm")
    mlflow.log_param("vocab_size", encoder.vocab_size)
    mlflow.log_param("embedding_dim", config['embedding_dim'])
    mlflow.log_param("hidden_dim", config['hidden_dim'])
    mlflow.log_param("num_layers", config['num_layers'])
    mlflow.log_param("dropout", config['dropout'])
    mlflow.log_param("batch_size", config['batch_size'])
    mlflow.log_param("learning_rate", config['learning_rate'])
    mlflow.log_param("sequence_length", config['sequence_length'])
    mlflow.log_param("num_epochs", config['num_epochs'])
    mlflow.log_param("device", str(device))
    mlflow.log_param("total_parameters", total_params)

    mlflow.set_tag("stage", "training")
    mlflow.set_tag("model_type", "lstm")

    # Initialize trainer
    trainer = LSTMTrainer(
        model=model,
        device=device,
        learning_rate=config['learning_rate'],
        weight_decay=config['weight_decay']
    )

    # Train model
    history = trainer.train(
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=config['num_epochs'],
        early_stopping_patience=config['early_stopping_patience'],
        mlflow_logging=True
    )

    print("\n" + "="*60)
    print("Training completed!")
    print("="*60)
    print(f"Best validation loss: {min(history['val_loss']):.4f}")
    print(f"Best validation accuracy: {max(history['val_accuracy']):.4f}")
    print("="*60)

    # Save encoder
    encoder_path = "/tmp/article_encoder.pkl"
    encoder.save(encoder_path)
    mlflow.log_artifact(encoder_path, "encoder")

    # Log model to MLflow
    mlflow.pytorch.log_model(
        model,
        "model",
        code_paths=[
            "../../utils/pytorch_utils.py",
            "../../utils/preprocessing_utils.py"
        ]
    )

    run_id = run.info.run_id
    print(f"\nMLflow Run ID: {run_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Recommendations for Validation Set

# COMMAND ----------

print("Generating recommendations for validation customers...")

# Get all validation customers
val_customer_ids_list = [row['customer_id'] for row in val_ground_truth.select('customer_id').collect()]

print(f"Validation customers: {len(val_customer_ids_list):,}")

# COMMAND ----------

# Get sequences for validation customers
val_sequences_dict = {}
for row in val_sequences.collect():
    val_sequences_dict[row['customer_id']] = row['sequence']

# Prepare test input sequences
test_input_sequences = []
test_customer_ids = []

for customer_id in val_customer_ids_list:
    if customer_id in val_sequences_dict:
        sequence = val_sequences_dict[customer_id]

        # Encode sequence
        encoded_seq = encoder.encode_batch(sequence[-config['sequence_length']:])

        # Pad if necessary
        if len(encoded_seq) < config['sequence_length']:
            padded = [encoder.padding_idx] * (config['sequence_length'] - len(encoded_seq)) + encoded_seq
        else:
            padded = encoded_seq[-config['sequence_length']:]

        test_customer_ids.append(customer_id)
        test_input_sequences.append(torch.tensor(padded, dtype=torch.long))

print(f"Generating recommendations for {len(test_customer_ids):,} customers with sufficient history")

# COMMAND ----------

# Generate recommendations
recommendations = generate_recommendations(
    model=model,
    input_sequences=test_input_sequences,
    customer_ids=test_customer_ids,
    encoder=encoder,
    device=device,
    k=12,
    batch_size=config['batch_size']
)

print(f"Generated recommendations for {len(recommendations)} customers")

# Show sample
if len(test_customer_ids) > 0:
    sample_customer = test_customer_ids[0]
    print(f"\nSample recommendations for customer {sample_customer}:")
    print(recommendations[sample_customer])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Convert to Spark DataFrame

# COMMAND ----------

print("Converting recommendations to DataFrame...")

# Convert to list of tuples
recommendations_list = [
    (customer_id, article_ids)
    for customer_id, article_ids in recommendations.items()
]

# Create DataFrame
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()

predictions_df = spark.createDataFrame(
    recommendations_list,
    schema=["customer_id", "predicted_articles"]
)

print(f"Predictions DataFrame: {predictions_df.count()} rows")
display(predictions_df.limit(5))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evaluate on Validation Set

# COMMAND ----------

print("Evaluating model on validation set...")

# Evaluate (will log to MLflow automatically)
with mlflow.start_run(run_id=run_id):
    metrics = log_evaluation_metrics(
        predictions_df,
        val_ground_truth,
        "LSTM Sequential Model",
        k=12
    )

print(f"\n{'='*60}")
print(f"LSTM Model Performance")
print(f"{'='*60}")
print(f"MAP@12: {metrics['map@12']:.6f}")
if 'map@5' in metrics:
    print(f"MAP@5: {metrics['map@5']:.6f}")
if 'catalog_coverage' in metrics:
    print(f"Coverage: {metrics['catalog_coverage']:.4f}")
print(f"Customers Evaluated: {metrics['num_customers']:,}")
print(f"{'='*60}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Register Model to MLflow Model Registry

# COMMAND ----------

print("Registering model to Unity Catalog Model Registry...")

# Register the PyTorch model to Unity Catalog
uc_model_name = f"{catalog_name}.{schema_name}.{model_name}"
model_uri = f"runs:/{run_id}/model"

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
    description=f"PyTorch LSTM sequential recommendation model. "
    f"MAP@12: {metrics['map@12']:.6f}. "
    f"Captures temporal purchase patterns with {total_params:,} parameters.",
)

client.update_model_version(
    name=uc_model_name,
    version=registered_model.version,
    description=f"LSTM architecture: Embedding({config['embedding_dim']}) → "
    f"LSTM({config['num_layers']} layers, {config['hidden_dim']} units) → Dense(256). "
    f"MAP@12: {metrics['map@12']:.6f}. "
    f"Vocabulary: {encoder.vocab_size:,} articles, Sequence length: {config['sequence_length']}",
)

print(f"\n✓ Model {uc_model_name} v{registered_model.version} registered successfully!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save Predictions

# COMMAND ----------

# Save predictions to gold schema
output_table = f"{catalog_name}.{schema_name}.lstm_predictions_gold"
print(f"Saving predictions to {output_table}...")

predictions_df \
    .withColumn("model_type", lit("lstm")) \
    .withColumn("run_id", lit(run_id)) \
    .write.format("delta").mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(output_table)

print(f"✓ Predictions saved to {output_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Model Analysis

# COMMAND ----------

# Analyze embedding quality
print("Analyzing learned embeddings...")

# Get embedding weights
embeddings = model.embedding.weight.detach().cpu().numpy()

print(f"Embedding shape: {embeddings.shape}")
print(f"Embedding statistics:")
print(f"  Mean: {embeddings.mean():.4f}")
print(f"  Std: {embeddings.std():.4f}")
print(f"  Min: {embeddings.min():.4f}")
print(f"  Max: {embeddings.max():.4f}")

# COMMAND ----------

# Visualize training history
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# Training and validation loss
axes[0].plot(history['train_loss'], label='Train Loss')
axes[0].plot(history['val_loss'], label='Val Loss')
axes[0].set_xlabel('Epoch')
axes[0].set_ylabel('Loss')
axes[0].set_title('Training and Validation Loss')
axes[0].legend()
axes[0].grid(True)

# Validation accuracy
axes[1].plot(history['val_accuracy'], label='Val Accuracy', color='green')
axes[1].set_xlabel('Epoch')
axes[1].set_ylabel('Accuracy')
axes[1].set_title('Validation Accuracy (Top-1)')
axes[1].legend()
axes[1].grid(True)

plt.tight_layout()
display(fig)

# Log figure to MLflow
with mlflow.start_run(run_name="lstm_analysis"):
    mlflow.log_figure(fig, "training_history.png")
    mlflow.set_tag("analysis_type", "training_curves")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("\n" + "="*60)
print("LSTM MODEL TRAINING COMPLETE")
print("="*60)
print(f"Model Type: Sequential LSTM (PyTorch)")
print(f"Architecture:")
print(f"  - Embedding: {config['embedding_dim']} dims")
print(f"  - LSTM: {config['num_layers']} layers x {config['hidden_dim']} units")
print(f"  - Total Parameters: {total_params:,}")
print(f"")
print(f"Data:")
print(f"  - Vocabulary Size: {encoder.vocab_size:,} articles")
print(f"  - Sequence Length: {config['sequence_length']}")
print(f"  - Training Samples: {len(train_loader.dataset):,}")
print(f"  - Validation Samples: {len(recommendations):,}")
print(f"")
print(f"Performance:")
print(f"  - MAP@12: {metrics['map@12']:.6f}")
if 'map@5' in metrics:
    print(f"  - MAP@5: {metrics['map@5']:.6f}")
if 'catalog_coverage' in metrics:
    print(f"  - Coverage: {metrics['catalog_coverage']:.4f}")
print(f"")
print(f"MLflow:")
print(f"  - Experiment: {MLFLOW_EXPERIMENT_MODELS}")
print(f"  - Run ID: {run_id}")
print(f"  - Predictions: {output_table}")
print("="*60)
print("\n✓ Sprint 3 Complete! Deep learning model trained successfully.")
print("="*60)
