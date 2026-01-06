"""
Preprocessing utilities for LSTM sequential model
Handles sequence generation, encoding, and batch preparation
"""
from pyspark.sql import DataFrame
from pyspark.sql.functions import *
from typing import Dict, List, Tuple, Optional
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import pickle
import os


class ArticleEncoder:
    """Encode article IDs to sequential integers for embedding layer"""

    def __init__(self):
        self.article_to_idx: Dict[str, int] = {}
        self.idx_to_article: Dict[int, str] = {}
        self.vocab_size = 0
        # Reserve 0 for padding
        self.padding_idx = 0
        self._next_idx = 1

    def fit(self, articles: List[str]) -> 'ArticleEncoder':
        """
        Build vocabulary from list of article IDs

        Args:
            articles: List of unique article IDs

        Returns:
            self
        """
        # Add padding token
        self.article_to_idx['<PAD>'] = self.padding_idx
        self.idx_to_article[self.padding_idx] = '<PAD>'

        # Add all article IDs
        for article_id in sorted(set(articles)):
            if article_id not in self.article_to_idx:
                self.article_to_idx[article_id] = self._next_idx
                self.idx_to_article[self._next_idx] = article_id
                self._next_idx += 1

        self.vocab_size = self._next_idx
        return self

    def encode(self, article_id: str) -> int:
        """Encode single article ID to integer"""
        return self.article_to_idx.get(article_id, self.padding_idx)

    def encode_batch(self, article_ids: List[str]) -> List[int]:
        """Encode list of article IDs to integers"""
        return [self.encode(aid) for aid in article_ids]

    def decode(self, idx: int) -> str:
        """Decode integer to article ID"""
        return self.idx_to_article.get(idx, '<PAD>')

    def decode_batch(self, indices: List[int]) -> List[str]:
        """Decode list of integers to article IDs"""
        return [self.decode(idx) for idx in indices]

    def save(self, path: str):
        """Save encoder to file"""
        with open(path, 'wb') as f:
            pickle.dump({
                'article_to_idx': self.article_to_idx,
                'idx_to_article': self.idx_to_article,
                'vocab_size': self.vocab_size,
                'padding_idx': self.padding_idx,
                '_next_idx': self._next_idx
            }, f)

    def load(self, path: str) -> 'ArticleEncoder':
        """Load encoder from file"""
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.article_to_idx = data['article_to_idx']
            self.idx_to_article = data['idx_to_article']
            self.vocab_size = data['vocab_size']
            self.padding_idx = data['padding_idx']
            self._next_idx = data['_next_idx']
        return self


def create_customer_sequences(
    transactions_df: DataFrame,
    max_sequence_length: int = 10,
    min_sequence_length: int = 2
) -> DataFrame:
    """
    Create purchase sequences for each customer

    Args:
        transactions_df: Transactions with customer_id, article_id, t_dat
        max_sequence_length: Maximum sequence length to keep
        min_sequence_length: Minimum sequence length (filter shorter)

    Returns:
        DataFrame with customer_id, sequence (array of article_ids), sequence_length
    """
    # Sort by customer and date, collect articles into arrays
    sequences_df = (
        transactions_df
        .select('customer_id', 'article_id', 't_dat')
        .orderBy('customer_id', 't_dat')
        .groupBy('customer_id')
        .agg(
            collect_list('article_id').alias('full_sequence')
        )
        .withColumn('sequence_length', size('full_sequence'))
        # Filter out customers with very few purchases
        .filter(col('sequence_length') >= min_sequence_length)
        # Limit sequence length (take last N purchases)
        .withColumn(
            'sequence',
            when(col('sequence_length') > max_sequence_length,
                 slice('full_sequence', -max_sequence_length, max_sequence_length))
            .otherwise(col('full_sequence'))
        )
        .select('customer_id', 'sequence', 'sequence_length')
    )

    return sequences_df


def create_train_sequences(
    sequences_df: DataFrame,
    sequence_length: int = 10,
    prediction_window: int = 1
) -> DataFrame:
    """
    Create input/target pairs for LSTM training
    Split sequences into input (history) and target (next purchases)

    Args:
        sequences_df: DataFrame with customer_id, sequence arrays
        sequence_length: Input sequence length
        prediction_window: Number of next items to predict

    Returns:
        DataFrame with customer_id, input_sequence, target_articles
    """
    # For each customer sequence, create input/target pairs
    # Input: first N items, Target: next M items
    result_df = (
        sequences_df
        .filter(col('sequence_length') > sequence_length + prediction_window)
        .withColumn(
            'input_sequence',
            slice('sequence', 1, sequence_length)
        )
        .withColumn(
            'target_articles',
            slice('sequence', sequence_length + 1, prediction_window)
        )
        .select('customer_id', 'input_sequence', 'target_articles')
    )

    return result_df


class SequenceDataset(Dataset):
    """PyTorch Dataset for customer purchase sequences"""

    def __init__(
        self,
        customer_ids: List[str],
        input_sequences: List[List[int]],  # Already encoded
        target_articles: List[List[int]],  # Already encoded
        sequence_length: int,
        padding_idx: int = 0
    ):
        """
        Args:
            customer_ids: List of customer IDs
            input_sequences: List of encoded article sequences
            target_articles: List of target article IDs (encoded)
            sequence_length: Fixed sequence length (for padding)
            padding_idx: Index to use for padding
        """
        self.customer_ids = customer_ids
        self.input_sequences = input_sequences
        self.target_articles = target_articles
        self.sequence_length = sequence_length
        self.padding_idx = padding_idx

    def __len__(self) -> int:
        return len(self.customer_ids)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, str]:
        """
        Returns:
            input_seq: Padded input sequence tensor [sequence_length]
            target: Target articles tensor [num_targets]
            customer_id: Customer ID string
        """
        input_seq = self.input_sequences[idx]
        target = self.target_articles[idx]
        customer_id = self.customer_ids[idx]

        # Pad input sequence
        if len(input_seq) < self.sequence_length:
            # Pad at the beginning
            padded_seq = [self.padding_idx] * (self.sequence_length - len(input_seq)) + input_seq
        else:
            # Truncate to sequence_length
            padded_seq = input_seq[-self.sequence_length:]

        return (
            torch.tensor(padded_seq, dtype=torch.long),
            torch.tensor(target, dtype=torch.long),
            customer_id
        )


def prepare_dataloaders(
    train_sequences_df: DataFrame,
    val_sequences_df: DataFrame,
    encoder: ArticleEncoder,
    batch_size: int = 256,
    sequence_length: int = 10,
    num_workers: int = 4
) -> Tuple[DataLoader, DataLoader]:
    """
    Prepare PyTorch DataLoaders for training and validation

    Args:
        train_sequences_df: Training sequences (customer_id, input_sequence, target_articles)
        val_sequences_df: Validation sequences
        encoder: Fitted ArticleEncoder
        batch_size: Batch size for training
        sequence_length: Fixed sequence length
        num_workers: Number of workers for data loading

    Returns:
        train_loader, val_loader
    """
    def df_to_dataset(df: DataFrame) -> SequenceDataset:
        """Convert Spark DataFrame to PyTorch Dataset"""
        # Collect to driver (assuming data fits in memory for demo)
        data = df.select('customer_id', 'input_sequence', 'target_articles').collect()

        customer_ids = []
        input_sequences = []
        target_articles = []

        for row in data:
            customer_ids.append(row['customer_id'])
            # Encode sequences
            input_seq_encoded = encoder.encode_batch(row['input_sequence'])
            target_encoded = encoder.encode_batch(row['target_articles'])
            input_sequences.append(input_seq_encoded)
            target_articles.append(target_encoded)

        return SequenceDataset(
            customer_ids=customer_ids,
            input_sequences=input_sequences,
            target_articles=target_articles,
            sequence_length=sequence_length,
            padding_idx=encoder.padding_idx
        )

    # Create datasets
    train_dataset = df_to_dataset(train_sequences_df)
    val_dataset = df_to_dataset(val_sequences_df)

    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )

    return train_loader, val_loader


def prepare_dataloaders_distributed(
    train_sequences_pd,
    val_sequences_pd,
    encoder: ArticleEncoder,
    batch_size: int = 256,
    sequence_length: int = 10,
    num_workers: int = 4,
    rank: int = 0,
    world_size: int = 1
) -> Tuple[DataLoader, DataLoader]:
    """
    Prepare PyTorch DataLoaders for distributed training

    Args:
        train_sequences_pd: Pandas DataFrame with training sequences
        val_sequences_pd: Pandas DataFrame with validation sequences
        encoder: Fitted ArticleEncoder
        batch_size: Batch size per GPU
        sequence_length: Fixed sequence length
        num_workers: Number of workers for data loading
        rank: Process rank in distributed training
        world_size: Total number of processes

    Returns:
        train_loader, val_loader (with DistributedSampler)
    """
    from torch.utils.data.distributed import DistributedSampler

    def pd_to_dataset(df_pd) -> SequenceDataset:
        """Convert Pandas DataFrame to PyTorch Dataset"""
        customer_ids = []
        input_sequences = []
        target_articles = []

        for _, row in df_pd.iterrows():
            customer_ids.append(row['customer_id'])
            # Encode sequences
            input_seq_encoded = encoder.encode_batch(row['input_sequence'])
            target_encoded = encoder.encode_batch(row['target_articles'])
            input_sequences.append(input_seq_encoded)
            target_articles.append(target_encoded)

        return SequenceDataset(
            customer_ids=customer_ids,
            input_sequences=input_sequences,
            target_articles=target_articles,
            sequence_length=sequence_length,
            padding_idx=encoder.padding_idx
        )

    # Create datasets
    train_dataset = pd_to_dataset(train_sequences_pd)
    val_dataset = pd_to_dataset(val_sequences_pd)

    # Create distributed samplers
    train_sampler = DistributedSampler(
        train_dataset,
        num_replicas=world_size,
        rank=rank,
        shuffle=True
    )

    val_sampler = DistributedSampler(
        val_dataset,
        num_replicas=world_size,
        rank=rank,
        shuffle=False
    )

    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        sampler=train_sampler,
        num_workers=num_workers,
        pin_memory=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        sampler=val_sampler,
        num_workers=num_workers,
        pin_memory=True
    )

    return train_loader, val_loader


def encode_article_features(
    articles_df: DataFrame,
    encoder: ArticleEncoder
) -> Dict[int, Dict]:
    """
    Encode article features for use in LSTM model

    Args:
        articles_df: Articles DataFrame with metadata
        encoder: Fitted ArticleEncoder

    Returns:
        Dictionary mapping encoded article_id to feature dict
    """
    # Collect article features
    articles_data = articles_df.collect()

    article_features = {}
    for row in articles_data:
        article_id = row['article_id']
        encoded_id = encoder.encode(article_id)

        article_features[encoded_id] = {
            'article_id': article_id,
            'product_type_no': row.get('product_type_no'),
            'product_group_name': row.get('product_group_name'),
            'colour_group_code': row.get('colour_group_code'),
            'section_no': row.get('section_no'),
            'garment_group_no': row.get('garment_group_no')
        }

    return article_features
