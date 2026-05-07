from __future__ import annotations

import torch
from torch import nn


class EnrolmentEncoder(nn.Module):
    def __init__(self, input_dim: int = 64, z_dim: int = 48) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 96),
            nn.ReLU(),
            nn.Linear(96, z_dim),
        )

    def forward(self, enrolment_features: torch.Tensor) -> torch.Tensor:
        return self.net(enrolment_features)


class NeuroGuardStudent(nn.Module):
    """Small distillation student with z-vector personalization.

    This is the trainable v2 audio head. It can later be swapped for a
    Wav2Vec2/HuBERT backbone while keeping the same `forward(log_mel, z)` API.
    """

    def __init__(
        self,
        n_mels: int = 64,
        hidden_dim: int = 128,
        z_dim: int = 48,
        class_count: int = 3,
    ) -> None:
        super().__init__()
        self.frame_encoder = nn.Sequential(
            nn.Conv1d(n_mels, hidden_dim, kernel_size=5, padding=2),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Conv1d(hidden_dim, hidden_dim, kernel_size=3, padding=1),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
        )
        self.enrolment_encoder = EnrolmentEncoder(n_mels, z_dim)
        self.z_to_bias = nn.Linear(z_dim, hidden_dim)
        self.head = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(0.15),
            nn.Linear(hidden_dim // 2, class_count),
        )

    def forward(
        self,
        log_mel: torch.Tensor,
        enrolment_features: torch.Tensor | None = None,
        z_vector: torch.Tensor | None = None,
    ) -> torch.Tensor:
        encoded = self.frame_encoder(log_mel)
        pooled = encoded.mean(dim=-1)

        if z_vector is None:
            if enrolment_features is None:
                enrolment_features = log_mel.mean(dim=-1)
            z_vector = self.enrolment_encoder(enrolment_features)

        personalized = pooled + self.z_to_bias(z_vector)
        return self.head(personalized)
