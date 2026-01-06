"""
Evaluation utilities for recommendation models
Implements MAP@K (Mean Average Precision at K) metric
"""

import numpy as np
import mlflow
from typing import List, Union


def apk(actual: List, predicted: List, k: int = 12) -> float:
    """
    Average Precision at K

    Args:
        actual: list of relevant items (ground truth)
        predicted: list of predicted items (ranked)
        k: cutoff for evaluation

    Returns:
        Average precision score

    Example:
        >>> apk([1, 2, 3], [1, 4, 3, 2], k=3)
        0.611...  # (1/1 + 2/3) / 2
    """
    if len(predicted) > k:
        predicted = predicted[:k]

    score = 0.0
    num_hits = 0.0

    for i, p in enumerate(predicted):
        if p in actual and p not in predicted[:i]:
            num_hits += 1.0
            score += num_hits / (i + 1.0)

    if len(actual) == 0:
        return 0.0

    return score / min(len(actual), k)


def mapk(actual: List[List], predicted: List[List], k: int = 12) -> float:
    """
    Mean Average Precision at K

    Args:
        actual: list of lists of actual items per customer
        predicted: list of lists of predicted items per customer
        k: cutoff

    Returns:
        MAP@K score

    Example:
        >>> actual = [[1, 2, 3], [4, 5]]
        >>> predicted = [[1, 4, 3, 2], [5, 6, 4]]
        >>> mapk(actual, predicted, k=3)
        0.583...
    """
    return np.mean([apk(a, p, k) for a, p in zip(actual, predicted)])


def calculate_map_at_k(predictions_df, ground_truth_df, k: int = 12) -> float:
    """
    Calculate MAP@K from Spark DataFrames

    Args:
        predictions_df: Spark DataFrame with columns [customer_id, predicted_articles (array)]
        ground_truth_df: Spark DataFrame with columns [customer_id, actual_articles (array)]
        k: cutoff

    Returns:
        MAP@K score
    """
    # Join predictions with ground truth
    merged = predictions_df.join(ground_truth_df, on="customer_id", how="inner")

    # Convert to pandas for calculation
    merged_pd = merged.select("actual_articles", "predicted_articles").toPandas()

    actual = merged_pd["actual_articles"].tolist()
    predicted = merged_pd["predicted_articles"].tolist()

    return mapk(actual, predicted, k)


def log_evaluation_metrics(predictions_df, ground_truth_df, model_name: str, k: int = 12):
    """
    Calculate and log comprehensive evaluation metrics to MLflow

    Args:
        predictions_df: Spark DataFrame with predictions
        ground_truth_df: Spark DataFrame with ground truth
        model_name: Name of the model being evaluated
        k: Cutoff for MAP@K

    Returns:
        Dictionary with all calculated metrics
    """
    from pyspark.sql.functions import explode, countDistinct

    # MAP@12 (primary metric)
    map_k = calculate_map_at_k(predictions_df, ground_truth_df, k=k)
    mlflow.log_metric(f"map@{k}", map_k)

    # MAP@5 (additional metric)
    if k >= 5:
        map_5 = calculate_map_at_k(predictions_df, ground_truth_df, k=5)
        mlflow.log_metric("map@5", map_5)
    else:
        map_5 = None

    # Coverage (what % of articles are recommended)
    try:
        # Total unique articles in ground truth
        total_articles = ground_truth_df.select(explode("actual_articles").alias("article_id")) \
            .select("article_id").distinct().count()

        # Unique articles in predictions
        recommended_articles = predictions_df.select(explode("predicted_articles").alias("article_id")) \
            .select("article_id").distinct().count()

        coverage = recommended_articles / total_articles if total_articles > 0 else 0
        mlflow.log_metric("catalog_coverage", coverage)
    except Exception as e:
        print(f"Could not calculate coverage: {e}")
        coverage = None

    # Number of customers evaluated
    num_customers = predictions_df.count()
    mlflow.log_metric("num_customers_evaluated", num_customers)

    metrics = {
        f"map@{k}": map_k,
        "num_customers": num_customers
    }

    if map_5 is not None:
        metrics["map@5"] = map_5

    if coverage is not None:
        metrics["catalog_coverage"] = coverage

    print(f"\n{'='*60}")
    print(f"Evaluation Metrics for {model_name}")
    print(f"{'='*60}")
    for metric_name, value in metrics.items():
        print(f"{metric_name}: {value:.6f}")
    print(f"{'='*60}\n")

    return metrics


def format_predictions_for_submission(predictions_df, output_path: str = None):
    """
    Format predictions for Kaggle submission format

    Args:
        predictions_df: Spark DataFrame with [customer_id, predicted_articles (array)]
        output_path: Optional path to save CSV

    Returns:
        DataFrame in submission format
    """
    from pyspark.sql.functions import concat_ws, col

    submission_df = predictions_df.select(
        col("customer_id"),
        concat_ws(" ", col("predicted_articles")).alias("prediction")
    )

    if output_path:
        submission_df.coalesce(1).write.mode("overwrite") \
            .option("header", "true") \
            .csv(output_path)
        print(f"Submission file saved to: {output_path}")

    return submission_df
