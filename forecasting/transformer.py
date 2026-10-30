"""Lightweight PyTorch Temporal Transformer for multi-step rolling load forecasting.
Uses multi-head self-attention, positional encoding, and a feed-forward projection head.
Fast, deterministic CPU-compatible architecture.
"""

import math
import torch
import torch.nn as nn


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 500):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: [batch_size, seq_len, d_model]
        return x + self.pe[:, : x.size(1)]


class TemporalTransformerForecaster(nn.Module):
    def __init__(
        self,
        input_dim: int = 7,
        d_model: int = 64,
        nhead: int = 4,
        num_encoder_layers: int = 2,
        dim_feedforward: int = 128,
        dropout: float = 0.1,
        history_steps: int = 96,
        horizon_steps: int = 96,
    ):
        super().__init__()
        self.history_steps = history_steps
        self.horizon_steps = horizon_steps

        # Input feature projection
        self.input_proj = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model, max_len=max(history_steps, 200))

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_encoder_layers)

        # Output projection head to predict multi-step horizon
        self.head = nn.Sequential(
            nn.Linear(history_steps * d_model, dim_feedforward),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(dim_feedforward, horizon_steps),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Args:
            x: Tensor of shape [batch_size, history_steps, input_dim]
        Returns:
            Tensor of shape [batch_size, horizon_steps]
        """
        # Linear projection to d_model
        h = self.input_proj(x)
        # Add positional encoding
        h = self.pos_encoder(h)
        # Transformer self-attention
        encoded = self.transformer_encoder(h)
        # Flatten and project to horizon
        batch_size = encoded.size(0)
        flattened = encoded.reshape(batch_size, -1)
        preds = self.head(flattened)
        return preds
