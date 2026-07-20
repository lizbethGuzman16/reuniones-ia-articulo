from __future__ import annotations

import torch
from torch import nn


MODEL_GROUPS: dict[str, tuple[str, ...]] = {
    "base": ("CNN-1D", "LSTM", "BiLSTM"),
    "hybrid": ("MLP-TFIDF", "CNN-BiLSTM", "BiLSTM-Atencion"),
}
MODEL_NAMES: tuple[str, ...] = MODEL_GROUPS["base"] + MODEL_GROUPS["hybrid"]
SEQUENCE_MODEL_NAMES: tuple[str, ...] = tuple(
    name for name in MODEL_NAMES if name != "MLP-TFIDF"
)


class CNN1DClassifier(nn.Module):
    def __init__(self, vocab_size: int, num_classes: int, embedding_dim: int = 48, channels: int = 64, kernel_size: int = 3, dropout: float = 0.25):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.conv = nn.Conv1d(embedding_dim, channels, kernel_size, padding=kernel_size // 2)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Sequential(nn.Linear(channels, 64), nn.ReLU(), nn.Dropout(dropout), nn.Linear(64, num_classes))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.embedding(x).transpose(1, 2)
        z = torch.relu(self.conv(z))
        z = torch.amax(z, dim=2)
        return self.classifier(self.dropout(z))


class LSTMClassifier(nn.Module):
    def __init__(self, vocab_size: int, num_classes: int, embedding_dim: int = 48, hidden_dim: int = 48, dropout: float = 0.25):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.lstm = nn.LSTM(embedding_dim, hidden_dim, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.embedding(x)
        _, (h, _) = self.lstm(z)
        return self.classifier(self.dropout(h[-1]))


class BiLSTMClassifier(nn.Module):
    def __init__(self, vocab_size: int, num_classes: int, embedding_dim: int = 48, hidden_dim: int = 48, dropout: float = 0.25):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.bilstm = nn.LSTM(embedding_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_dim * 2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.embedding(x)
        _, (h, _) = self.bilstm(z)
        joined = torch.cat((h[-2], h[-1]), dim=1)
        return self.classifier(self.dropout(joined))


class CNNBiLSTMClassifier(nn.Module):
    def __init__(self, vocab_size: int, num_classes: int, embedding_dim: int = 48, channels: int = 48, hidden_dim: int = 40, kernel_size: int = 3, dropout: float = 0.25):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.conv = nn.Conv1d(embedding_dim, channels, kernel_size, padding=kernel_size // 2)
        self.bilstm = nn.LSTM(channels, hidden_dim, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Sequential(nn.Linear(hidden_dim * 2, 64), nn.ReLU(), nn.Dropout(dropout), nn.Linear(64, num_classes))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.embedding(x).transpose(1, 2)
        z = torch.relu(self.conv(z)).transpose(1, 2)
        _, (h, _) = self.bilstm(z)
        pooled = torch.cat((h[-2], h[-1]), dim=1)
        return self.classifier(self.dropout(pooled))


class BiLSTMAttentionClassifier(nn.Module):
    def __init__(self, vocab_size: int, num_classes: int, embedding_dim: int = 48, hidden_dim: int = 48, dropout: float = 0.25):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.bilstm = nn.LSTM(embedding_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.attention = nn.Linear(hidden_dim * 2, 1)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Sequential(nn.Linear(hidden_dim * 2, 64), nn.ReLU(), nn.Dropout(dropout), nn.Linear(64, num_classes))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        mask = x.ne(0)
        z = self.embedding(x)
        outputs, _ = self.bilstm(z)
        scores = self.attention(outputs).squeeze(-1)
        scores = scores.masked_fill(~mask, -1e9)
        weights = torch.softmax(scores, dim=1).unsqueeze(-1)
        context = torch.sum(outputs * weights, dim=1)
        return self.classifier(self.dropout(context))


class TfidfMLP(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_dim: int = 128, dropout: float = 0.3):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


def create_sequence_model(name: str, vocab_size: int, num_classes: int, **kwargs) -> nn.Module:
    if name == "CNN-1D":
        return CNN1DClassifier(vocab_size, num_classes, **kwargs)
    if name == "LSTM":
        return LSTMClassifier(vocab_size, num_classes, **kwargs)
    if name == "BiLSTM":
        return BiLSTMClassifier(vocab_size, num_classes, **kwargs)
    if name == "CNN-BiLSTM":
        return CNNBiLSTMClassifier(vocab_size, num_classes, **kwargs)
    if name == "BiLSTM-Atencion":
        return BiLSTMAttentionClassifier(vocab_size, num_classes, **kwargs)
    raise ValueError(f"Modelo desconocido: {name}")
