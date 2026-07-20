from __future__ import annotations

import torch

from ml.models import MODEL_GROUPS, MODEL_NAMES, SEQUENCE_MODEL_NAMES, create_sequence_model


def test_inventory_has_three_base_and_three_hybrid_models() -> None:
    assert MODEL_GROUPS == {
        "base": ("CNN-1D", "LSTM", "BiLSTM"),
        "hybrid": ("MLP-TFIDF", "CNN-BiLSTM", "BiLSTM-Atencion"),
    }
    assert len(MODEL_NAMES) == 6
    assert len(set(MODEL_NAMES)) == 6
    assert len(SEQUENCE_MODEL_NAMES) == 5


def test_each_sequence_model_outputs_one_score_per_class() -> None:
    batch = torch.tensor([[1, 2, 3, 0], [4, 5, 0, 0]], dtype=torch.long)
    for name in SEQUENCE_MODEL_NAMES:
        model = create_sequence_model(name, vocab_size=12, num_classes=5)
        assert model(batch).shape == (2, 5)
