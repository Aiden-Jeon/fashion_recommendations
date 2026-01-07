"""
Data evaluation configuration for dataops workflows
"""

# Evaluation configuration - used for train/val/test splits
EVAL_CONFIG = {
    "k": 12,  # MAP@K
    "prediction_window_days": 7,
    "train_cutoff": "2020-09-01",
    "val_cutoff": "2020-09-15",
    "test_cutoff": "2020-09-22"
}
