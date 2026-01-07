"""
Model hyperparameters and configuration
"""

# Evaluation configuration
EVAL_CONFIG = {
    "k": 12,  # MAP@K
    "prediction_window_days": 7,
    "train_cutoff": "2020-09-01",
    "val_cutoff": "2020-09-15",
    "test_cutoff": "2020-09-22"
}

# Popularity model
POPULARITY_CONFIG = {
    "n_days": 7,
    "alpha": 0.5,  # recency weight decay
    "top_n": 12
}

# Age-based rules model
AGE_RULES_CONFIG = {
    "age_bins": [18, 25, 35, 45, 55, 100],
    "top_n_per_segment": 12
}

# LSTM model (PyTorch simplified for demo)
LSTM_CONFIG = {
    "embedding_dim": 64,
    "hidden_dim": 128,  # LSTM hidden units
    "num_layers": 2,  # Number of LSTM layers
    "dropout": 0.3,
    "sequence_length": 10,  # Input sequence length
    "min_sequence_length": 3,  # Minimum customer purchase history
    "batch_size": 256,
    "num_epochs": 10,
    "learning_rate": 0.001,
    "weight_decay": 1e-5,  # L2 regularization
    "early_stopping_patience": 3
}

# Ensemble model
ENSEMBLE_CONFIG = {
    "models": ["popularity", "age_rules", "lstm"],
    "weights": {
        "popularity": 0.2,
        "age_rules": 0.3,
        "lstm": 0.5
    }
}
